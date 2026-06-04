"""Quality gates and deduplication helpers for distilled memories.

TrueMemory's useful pattern is ADD / UPDATE / SKIP before storage. LearnKit's
version is deliberately lightweight and deterministic: it filters empty or
non-general records, detects near-duplicates with word overlap, and lets the
caller reinforce the existing record instead of inserting another row.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .backends.base import BaseBackend
from .schemas.base import MemoryRecord


@dataclass(frozen=True)
class StoreDecision:
    should_store: bool
    reason: str
    duplicate: MemoryRecord | None = None
    fingerprint: str = ""


def record_text(record: MemoryRecord) -> str:
    parts = [record.type, record.task_type or "", " ".join(record.domains.keys())]
    for value in record.content.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.extend(str(item) for item in value.values())
        else:
            parts.append(str(value))
    return " ".join(part for part in parts if part)


def content_fingerprint(record: MemoryRecord) -> str:
    normalized = " ".join(_tokens(record_text(record)))
    return hashlib.sha256(normalized.encode()).hexdigest()


def decide_storage(
    record: MemoryRecord,
    backend: BaseBackend,
    scope: str | None,
    min_confidence: float = 0.0,
    duplicate_threshold: float = 0.72,
) -> StoreDecision:
    """Decide whether a distilled record should be inserted.

    The check is intentionally conservative: a record with no substantive text
    is dropped; a near-duplicate is returned to the caller so it can reinforce
    the existing row instead of bloating the store.
    """
    text = record_text(record)
    if len(_tokens(text)) < 4:
        return StoreDecision(False, "too little substantive content")
    if record.confidence < min_confidence:
        return StoreDecision(False, "below minimum confidence")

    fp = content_fingerprint(record)
    duplicate = find_duplicate(record, backend, scope, duplicate_threshold)
    if duplicate:
        return StoreDecision(False, "near duplicate", duplicate=duplicate, fingerprint=fp)
    return StoreDecision(True, "store", fingerprint=fp)


def find_duplicate(
    record: MemoryRecord,
    backend: BaseBackend,
    scope: str | None,
    threshold: float = 0.72,
) -> MemoryRecord | None:
    """Find a same-type near-duplicate using backend search + word overlap."""
    query = record_text(record)
    try:
        candidates = backend.search(
            query=query,
            record_type=record.type,
            domain=None,
            scope=scope,
            limit=8,
            exclude_stale=False,
        )
    except Exception:
        return None

    record_words = set(_tokens(query))
    if not record_words:
        return None

    for candidate in candidates:
        if candidate.id == record.id:
            continue
        candidate_words = set(_tokens(record_text(candidate)))
        if not candidate_words:
            continue
        score = len(record_words & candidate_words) / len(record_words | candidate_words)
        if score >= threshold:
            return candidate
    return None


def reinforce_existing(backend: BaseBackend, record: MemoryRecord, delta: float = 0.02) -> None:
    backend.update_confidence(record.id, min(0.95, record.confidence + delta))


def demote_existing(backend: BaseBackend, record: MemoryRecord, delta: float = 0.05) -> None:
    new_conf = max(0.0, record.confidence - delta)
    backend.update_confidence(record.id, new_conf)


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 1]

