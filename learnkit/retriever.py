import math

from .backends.base import BaseBackend
from .diversity import reciprocal_rank_fusion
from .logging import get_logger
from .router import CONFIDENCE_FLOOR
from .schemas.base import MemoryRecord

logger = get_logger("retriever")


class SemanticRetriever:
    """
    Semantic Retriever for fetching past memories relevant to a task.
    """

    def __init__(
        self,
        backend: BaseBackend,
        embedder=None,
        dense_weight: float = 0.5,
        fusion_strategy: str = "weighted",
    ):
        self.backend = backend
        self.embedder = embedder
        self.dense_weight = dense_weight
        self.fusion_strategy = fusion_strategy
        # Cache of record embeddings keyed by record id. Each entry stores the
        # text that was embedded so a record whose content changed is re-embedded
        # rather than served a stale vector. Bounded to avoid unbounded growth.
        self._embed_cache: dict[str, tuple[str, list[float]]] = {}
        self._embed_cache_max = 512

    def retrieve(
        self,
        task: str,
        domain_vector: dict[str, float],
        scope: str | None = None,
        router=None,
    ) -> list:
        # Empty/whitespace query — nothing meaningful to retrieve against.
        if not task or not task.strip():
            return []

        # Get top domains (confidence > 0.5)
        top_domains = [d for d, c in domain_vector.items() if c > 0.5]
        domain = top_domains[0] if top_domains else None

        limit = 20
        # Hard cap for semantic fallback scan to prevent OOM
        semantic_scan_cap = 100

        try:
            if self.embedder is not None and hasattr(self.backend, "hybrid_search"):
                results = self.backend.hybrid_search(
                    query=task,
                    domain=domain,
                    scope=scope,
                    limit=limit,
                    alpha=self.dense_weight,
                )
            else:
                # Fallback: standard lexical search first
                results = self.backend.search(
                    query=task, domain=domain, scope=scope, limit=limit
                )

                if self.embedder is not None and results:
                    # Rerank only the BM25 candidates — safe, bounded to `limit` records
                    results = self._rerank_candidates(task, results, limit=limit)

            # If we got no results, but we have an embedder and backend list_all,
            # this represents a zero-lexical-overlap scenario.
            if (
                not results
                and self.embedder is not None
                and hasattr(self.backend, "list_all")
            ):
                # Zero lexical overlap: fall back to bounded semantic scan.
                all_candidates = self.backend.list_all(limit=semantic_scan_cap)
                active = []
                for r in all_candidates:
                    if r.status != "active" or r.is_expired():
                        continue
                    if domain and domain not in r.domains:
                        continue
                    if scope and r.scope != scope:
                        continue
                    active.append(r)
                if active:
                    results = self._rerank_candidates(task, active, limit=limit)
        except Exception as e:
            logger.error(
                "Retrieval operation failed",
                extra={"event": "retrieval_fail", "error_type": type(e).__name__},
            )
            results = []

        # Confidence floor — drop records below threshold before routing.
        # Sprint 1 fix: prevents low-confidence records from reaching the
        # composer regardless of their FTS5 surface-match score.
        # sql06 regressed (5.0→2.0) because a confidence=0.5 upsert skill
        # matched gap-detection keywords and was injected into an unrelated task.
        floor = CONFIDENCE_FLOOR
        if router is not None and hasattr(router, "confidence_floor_for_domain"):
            try:
                floor = float(router.confidence_floor_for_domain(domain))
            except Exception:
                floor = CONFIDENCE_FLOOR

        before = len(results)
        results = [r for r in results if r.confidence >= floor]
        dropped = before - len(results)
        if dropped:
            logger.warning(
                "Records dropped by confidence floor",
                extra={
                    "event": "confidence_floor_drop",
                    "dropped": dropped,
                    "floor": floor,
                    "domain": domain,
                },
            )

        if router:
            results = router.route(results)

        return results

    def _rerank_candidates(
        self,
        task: str,
        candidates: list[MemoryRecord],
        limit: int,
    ) -> list[MemoryRecord]:
        try:
            query_vec = self.embedder(task)
            # Naive BM25 score proxy based on search rank
            bm25_rank = {
                record.id: 1.0 / (i + 1) for i, record in enumerate(candidates)
            }
            scored = []
            lexical_ranked: list[tuple[float, MemoryRecord]] = []
            dense_ranked: list[tuple[float, MemoryRecord]] = []

            for record in candidates:
                record_vec = self._embed_record(record)
                dense_score = _cosine(query_vec, record_vec)

                # Fetch actual bm25 score if attached by backend, otherwise use proxy
                lexical_score = getattr(
                    record, "_bm25_score", bm25_rank.get(record.id, 0.0)
                )
                lexical_ranked.append((lexical_score, record))
                dense_ranked.append((dense_score, record))

                score = ((1 - self.dense_weight) * lexical_score) + (
                    self.dense_weight * dense_score
                )
                scored.append((score, record.confidence, record))

            if self.fusion_strategy == "rrf":
                lexical_order = [
                    record
                    for _, record in sorted(
                        lexical_ranked, key=lambda item: (item[0], item[1].confidence), reverse=True
                    )
                ]
                dense_order = [
                    record
                    for _, record in sorted(
                        dense_ranked, key=lambda item: (item[0], item[1].confidence), reverse=True
                    )
                ]
                fused = reciprocal_rank_fusion(
                    [lexical_order, dense_order],
                    key_of=lambda r: r.id,
                )
                return fused[:limit]

            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return [record for _, _, record in scored[:limit]]
        except Exception as e:
            logger.warning(
                "In-memory reranking failed, falling back to lexical order",
                extra={"event": "rerank_fail", "error_type": type(e).__name__},
            )
            return candidates

    def _embed_record(self, record: MemoryRecord) -> list[float]:
        """Embed a record's text, caching the vector by record id.

        Avoids re-embedding the same candidate on every retrieval — the dominant
        cost when the same records resurface across tasks. The cached entry is
        invalidated when the record's text changes.
        """
        text = self._record_text(record)
        key = getattr(record, "id", None) or text
        cached = self._embed_cache.get(key)
        if cached is not None and cached[0] == text:
            return cached[1]
        vec = self.embedder(text)
        if len(self._embed_cache) >= self._embed_cache_max:
            # Simple bound — evict the oldest inserted entry.
            self._embed_cache.pop(next(iter(self._embed_cache)))
        self._embed_cache[key] = (text, vec)
        return vec

    def _record_text(self, record: MemoryRecord) -> str:
        parts = [record.task_type or "", " ".join(record.domains.keys())]
        for value in record.content.values():
            if isinstance(value, list):
                parts.append(" ".join(str(item) for item in value))
            elif isinstance(value, dict):
                parts.append(" ".join(str(item) for item in value.values()))
            else:
                parts.append(str(value))
        return " ".join(parts)


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
