"""Skill consolidation — background umbrella-merge of overlapping skills.

Adapted from Hermes' curator consolidation pass (``agent/curator.py``): over
time a self-improving store accumulates near-duplicate skills that compete for
the PRIMARY injection slot and bloat retrieval. This pass clusters semantically
overlapping *active* skills, folds each cluster into a single canonical
"umbrella" skill (union of steps / tools / constraints / failure_modes, summed
reuse), and archives the losers as ``deprecated`` with a back-reference.

Invariants borrowed from the Hermes curator:
  - Never deletes — only archives (status -> ``"deprecated"``). Recoverable.
  - Pinned skills are exempt (``content["pinned"]`` truthy).
  - Only touches skills; other record types are never merged.

The similarity signal reuses the backend's embedder when one is available
(cosine over the same text the retriever embeds); otherwise it falls back to a
dependency-free Jaccard token overlap so the default zero-dependency SQLite
backend still consolidates.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

from .logging import get_logger
from .schemas.base import MemoryRecord

logger = get_logger("consolidation")

# Skills at/above this similarity are treated as the same capability and merged.
DEFAULT_SIMILARITY_THRESHOLD = 0.83

# Per-field cap on the merged umbrella so a runaway merge can't unbound a skill.
MAX_MERGED_LIST_ITEMS = 50

# Content list fields that are unioned when skills merge.
_MERGEABLE_LIST_FIELDS = ("steps", "tools_used", "constraints", "failure_modes")


def _is_pinned(record: MemoryRecord) -> bool:
    return bool(record.content.get("pinned"))


def _skill_text(record: MemoryRecord) -> str:
    """Flatten a skill into a comparable text blob (mirrors retriever text)."""
    parts = [record.task_type or "", " ".join(record.domains.keys())]
    for value in record.content.values():
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value))
        elif isinstance(value, dict):
            parts.append(" ".join(str(item) for item in value.values()))
        else:
            parts.append(str(value))
    return " ".join(parts)


def _token_set(text: str) -> set[str]:
    return {t for t in "".join(c.lower() if c.isalnum() else " " for c in text).split() if t}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(left, right))
    left_norm = math.sqrt(sum(x * x for x in left))
    right_norm = math.sqrt(sum(y * y for y in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _rank_key(record: MemoryRecord) -> tuple[float, int, float]:
    """Canonical-selection key: most confident, most reused, longest-lived wins."""
    return (record.confidence, record.reuse_count, len(_skill_text(record)))


def _merge_list_field(canonical: list, others: list) -> list[str]:
    """Union two list fields, case-insensitively deduped, canonical-first, capped."""
    merged: list[str] = []
    seen: set[str] = set()
    for source in (canonical, others):
        if not isinstance(source, list):
            continue
        for item in source:
            text = str(item).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
            if len(merged) >= MAX_MERGED_LIST_ITEMS:
                return merged
    return merged


def consolidate_skills(
    backend,
    embedder: Optional[Callable[[str], list[float]]] = None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict[str, int]:
    """Cluster overlapping active skills and merge each cluster into one umbrella.

    Returns a stats dict: ``skills_scanned``, ``clusters`` (clusters with >=2
    members that were merged), and ``archived`` (skills folded away).
    """
    embedder = embedder or getattr(backend, "embedder", None)

    skills = [
        r
        for r in backend.list_all()
        if r.type == "skill" and r.status == "active" and not _is_pinned(r)
    ]
    stats = {"skills_scanned": len(skills), "clusters": 0, "archived": 0}
    if len(skills) < 2:
        return stats

    # Precompute the comparison signal for each skill once.
    vectors: dict[str, list[float]] = {}
    token_sets: dict[str, set[str]] = {}
    for skill in skills:
        text = _skill_text(skill)
        if embedder is not None:
            try:
                vectors[skill.id] = embedder(text)
            except Exception:
                token_sets[skill.id] = _token_set(text)
        else:
            token_sets[skill.id] = _token_set(text)

    def _similarity(a: MemoryRecord, b: MemoryRecord) -> float:
        if a.id in vectors and b.id in vectors:
            return _cosine(vectors[a.id], vectors[b.id])
        return _jaccard(
            token_sets.get(a.id, _token_set(_skill_text(a))),
            token_sets.get(b.id, _token_set(_skill_text(b))),
        )

    # Greedy single-pass clustering: seed a cluster with the strongest skill,
    # pull in every unassigned skill above threshold.
    remaining = sorted(skills, key=_rank_key, reverse=True)
    assigned: set[str] = set()

    for seed in remaining:
        if seed.id in assigned:
            continue
        cluster = [seed]
        assigned.add(seed.id)
        for other in remaining:
            if other.id in assigned:
                continue
            if _similarity(seed, other) >= threshold:
                cluster.append(other)
                assigned.add(other.id)

        if len(cluster) < 2:
            continue

        canonical = max(cluster, key=_rank_key)
        losers = [s for s in cluster if s.id != canonical.id]

        for field in _MERGEABLE_LIST_FIELDS:
            base = canonical.content.get(field, [])
            for loser in losers:
                base = _merge_list_field(base, loser.content.get(field, []))
            canonical.content[field] = base

        for loser in losers:
            canonical.reuse_count += loser.reuse_count

        consolidated_from = list(canonical.content.get("consolidated_from", []))
        for loser in losers:
            consolidated_from.append(loser.id)
            loser.status = "deprecated"
            loser.content["consolidated_into"] = canonical.id
            backend.replace(loser)
        canonical.content["consolidated_from"] = consolidated_from
        backend.replace(canonical)

        stats["clusters"] += 1
        stats["archived"] += len(losers)
        logger.info(
            "Consolidated overlapping skills into umbrella",
            extra={
                "event": "skills_consolidated",
                "umbrella_id": canonical.id,
                "task_type": canonical.task_type,
                "archived": len(losers),
            },
        )

    return stats
