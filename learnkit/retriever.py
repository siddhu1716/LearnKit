import math

from .backends.base import BaseBackend
from .schemas.base import MemoryRecord

class SemanticRetriever:
    """
    Semantic Retriever for fetching past memories relevant to a task.
    """
    def __init__(self, backend: BaseBackend, embedder=None, dense_weight: float = 0.35):
        self.backend = backend
        self.embedder = embedder
        self.dense_weight = dense_weight

    def retrieve(
        self,
        task: str,
        domain_vector: dict[str, float],
        scope: str | None = None,
        router=None
    ) -> list:
        # Get top domains (confidence > 0.5)
        top_domains = [d for d, c in domain_vector.items() if c > 0.5]
        domain = top_domains[0] if top_domains else None
        
        bm25_results = self.backend.search(
            query=task,
            domain=domain,
            scope=scope,
            limit=20  # Retrieve more, let router filter down
        )

        results = bm25_results
        if self.embedder is not None:
            results = self._hybrid_rank(task, bm25_results, domain=domain, scope=scope, limit=20)

        if router:
            results = router.route(results)

        return results

    def _hybrid_rank(
        self,
        task: str,
        bm25_results: list[MemoryRecord],
        domain: str | None,
        scope: str | None,
        limit: int,
    ) -> list[MemoryRecord]:
        candidates = {record.id: record for record in bm25_results}

        if hasattr(self.backend, "list_all"):
            for record in self.backend.list_all():
                if record.status in ("quarantine", "stale") or record.is_expired():
                    continue
                if domain and domain not in record.domains:
                    continue
                if scope and record.scope != scope:
                    continue
                candidates.setdefault(record.id, record)

        query_vec = self.embedder(task)
        bm25_rank = {record.id: 1.0 / (i + 1) for i, record in enumerate(bm25_results)}
        scored = []

        for record in candidates.values():
            record_vec = self.embedder(self._record_text(record))
            dense_score = _cosine(query_vec, record_vec)
            lexical_score = bm25_rank.get(record.id, 0.0)
            score = ((1 - self.dense_weight) * lexical_score) + (self.dense_weight * dense_score)
            scored.append((score, record.confidence, record))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in scored[:limit]]

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
