"""Memory attribution helpers.

The benchmark harness needs to separate retrieval quality from downstream
agent quality. These helpers expose a compact, JSON-serialisable view of the
records LearnKit retrieved and injected for a run.
"""

from __future__ import annotations

from .schemas.base import MemoryRecord


def record_attribution(record: MemoryRecord, rank: int, primary: bool = False) -> dict:
    """Return stable attribution metadata for a retrieved memory record."""
    return {
        "rank": rank,
        "primary": primary,
        "id": record.id,
        "type": record.type,
        "task_type": record.task_type,
        "domains": dict(record.domains),
        "confidence": round(record.confidence, 3),
        "reuse_count": record.reuse_count,
        "success_rate": record.success_rate,
        "scope": record.scope,
        "status": record.status,
        "content_preview": _preview(record),
    }


def build_attribution(records: list[MemoryRecord], context: str) -> dict:
    """Summarise retrieval and context-injection state for one LearnKit run."""
    return {
        "records_retrieved": len(records),
        "context_chars": len(context),
        "primary_record_id": records[0].id if records else None,
        "primary_record_type": records[0].type if records else None,
        "records": [
            record_attribution(record, rank=i + 1, primary=(i == 0))
            for i, record in enumerate(records)
        ],
    }


def _preview(record: MemoryRecord, limit: int = 180) -> str:
    parts: list[str] = []
    if record.task_type:
        parts.append(record.task_type)
    for value in record.content.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value[:3])
        elif isinstance(value, dict):
            parts.extend(str(item) for item in list(value.values())[:3])
        else:
            parts.append(str(value))
    text = " | ".join(part for part in parts if part)
    return text[:limit]

