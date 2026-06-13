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
from datetime import datetime, timezone

from .backends.base import BaseBackend
from .schemas.base import MemoryRecord


@dataclass(frozen=True)
class StoreDecision:
    should_store: bool
    reason: str
    duplicate: MemoryRecord | None = None
    fingerprint: str = ""


# Threshold at which a memory that keeps hurting retrieved-task outcomes is
# moved to quarantine so it stops being injected. Empirical: 3 consecutive
# harmful retrievals is a strong enough signal to silence the record.
HARMFUL_HITS_QUARANTINE = 3

# Heuristic stop-list for the generality check. These are common English
# function words that should not count as "task-specific tokens" even when
# they appear in both the trace and the candidate skill.
_GENERIC_TOKENS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "into", "then",
    "when", "should", "must", "list", "string", "number", "value", "input",
    "output", "result", "task", "step", "steps", "use", "using", "check",
    "first", "next", "last", "code", "function", "method", "class", "data",
    "case", "test", "tests", "true", "false", "none", "null", "type",
    "error", "errors", "fail", "failed", "succeed", "succeeded", "given",
    "return", "returns", "call", "calls", "after", "before", "apply",
    "applies", "make", "makes", "user", "system", "agent", "prompt",
})


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


def is_general(
    record: MemoryRecord,
    task_text: str | None,
    overlap_threshold: float = 0.5,
) -> tuple[bool, float]:
    """Reject skills whose distinctive tokens are mostly lifted from the task.

    A distilled skill is supposed to generalise — its `steps` should describe
    an *approach*, not parrot back identifiers from the specific trace that
    produced it. We flag a record as non-general when more than
    ``overlap_threshold`` of its long, non-generic tokens also appear in the
    task prompt. Returns (is_general, overlap_ratio).
    """
    if not task_text:
        return True, 0.0
    distinctive = {
        t for t in _tokens(record_text(record))
        if len(t) >= 6 and t not in _GENERIC_TOKENS
    }
    if len(distinctive) < 4:
        # Too few distinctive tokens to make a confident judgement either way.
        return True, 0.0
    task_tokens = set(_tokens(task_text))
    overlap = distinctive & task_tokens
    ratio = len(overlap) / len(distinctive)
    return ratio < overlap_threshold, ratio


def decide_storage(
    record: MemoryRecord,
    backend: BaseBackend,
    scope: str | None,
    min_confidence: float = 0.0,
    duplicate_threshold: float = 0.72,
    task_text: str | None = None,
) -> StoreDecision:
    """Decide whether a distilled record should be inserted.

    The check is intentionally conservative: a record with no substantive text
    is dropped; a near-duplicate is returned to the caller so it can reinforce
    the existing row instead of bloating the store. When ``task_text`` is
    supplied, a generality check rejects skills that look like trace summaries
    instead of reusable approaches.
    """
    text = record_text(record)
    if len(_tokens(text)) < 4:
        return StoreDecision(False, "too little substantive content")
    if record.confidence < min_confidence:
        return StoreDecision(False, "below minimum confidence")

    # Generality gate only applies to skills — facts and failures are allowed
    # to be specific (a fact about a particular API or a failure about a
    # particular pattern is still valuable).
    if record.type == "skill":
        general, ratio = is_general(record, task_text)
        if not general:
            return StoreDecision(False, f"not general (task overlap {ratio:.0%})")

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
    """Reinforce a record: raise confidence and refresh its recency signal.

    Bumping ``last_reinforced`` (and ``reuse_count``) keeps the recency-aware
    injection ranking meaningful — a memory that keeps proving useful stays
    "fresh" instead of decaying on creation age alone. Falls back to a
    confidence-only update if the record can't be round-tripped.
    """
    current = backend.read(record.id)
    if current is None:
        backend.update_confidence(record.id, min(0.95, record.confidence + delta))
        return
    current.confidence = min(0.95, current.confidence + delta)
    current.reuse_count += 1
    current.last_reinforced = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    backend.replace(current)


def recover_existing_harm(backend: BaseBackend, record: MemoryRecord, step: int = 1) -> None:
    """Decrease harmful-hit pressure for a record after a strong positive outcome.

    Harmful-hit quarantine is sticky by design, but a memory that starts helping
    again should be able to recover gradually rather than staying permanently
    penalized. This function decrements ``_harmful_hits`` (if present) and keeps
    the value non-negative.
    """
    current = backend.read(record.id)
    if current is None:
        return
    hits = int(current.content.get("_harmful_hits", 0))
    if hits <= 0:
        return
    current.content["_harmful_hits"] = max(0, hits - max(1, step))
    backend.replace(current)


def demote_existing(
    backend: BaseBackend,
    record: MemoryRecord,
    delta: float = 0.05,
    harm_threshold: int = HARMFUL_HITS_QUARANTINE,
) -> None:
    """Lower confidence and track repeated harm.

    Each call increments a persistent ``_harmful_hits`` counter on the record's
    content. Once the counter reaches ``harm_threshold``, the record is moved
    to ``quarantine`` so it stops being retrieved — addressing the sql06-style
    failure mode where a related-but-wrong skill keeps degrading downstream
    tasks. The record can still be promoted back later by ``maintain_memory``.
    """
    current = backend.read(record.id)
    if current is None:
        # Fall back to a confidence-only update if we can't round-trip the record.
        backend.update_confidence(record.id, max(0.0, record.confidence - delta))
        return
    hits = int(current.content.get("_harmful_hits", 0)) + 1
    current.content["_harmful_hits"] = hits
    current.confidence = max(0.0, current.confidence - delta)
    if hits >= harm_threshold and current.status == "active":
        current.status = "quarantine"
    backend.replace(current)


# recursive-improve's confidence-with-denominator principle
# (recursive_improve/eval/detectors.py + harbor_compute_baselines.py): a single
# bad outcome is weak evidence against a memory that already has a long,
# successful track record. Below this many reuses a record is treated as
# "directional-only" and demoted at full strength (new records must prove
# themselves); once it crosses the threshold, transient negative signals are
# damped in proportion to its historical success so one noisy task-mismatch
# can't tank an established skill.
MIN_TRIALS_FOR_FULL_CONFIDENCE = 5


def _demotion_scale(record: MemoryRecord) -> float:
    """Return a demotion multiplier in [0.4, 1.0] based on the record's history.

    New/unproven records demote at full strength. A well-reused record with a
    high rolling ``success_rate`` resists single-trial demotion (floored at
    0.4 so a genuinely-degrading skill still loses confidence over time).
    """
    reuse = getattr(record, "reuse_count", 0) or 0
    if reuse < MIN_TRIALS_FOR_FULL_CONFIDENCE:
        return 1.0
    success = getattr(record, "success_rate", None)
    if success is None:
        return 1.0
    # success in [0,1]: a 0.9-success skill gets ~0.46 demotion, 0.5 gets ~0.7.
    return max(0.4, 1.0 - 0.6 * float(success))


def apply_retrieval_feedback(
    backend: BaseBackend,
    record: MemoryRecord,
    eval_score: float,
    quality_threshold: float,
    primary: bool = False,
) -> None:
    """Apply graded, outcome-aware confidence updates for a retrieved record.

    Score bands:
    - >= 4.5: strong positive signal, reinforce and recover harmful pressure.
    - >= quality_threshold: positive signal, light reinforce.
    - >= 2.5: weak negative signal, light demotion.
    - < 2.5: strong negative signal, stronger demotion.

    PRIMARY records receive slightly larger absolute updates because they have
    disproportionate influence on downstream behavior. Demotions are scaled by
    the record's track record (see ``_demotion_scale``) so a proven memory isn't
    punished for a single noisy outcome.
    """
    if eval_score >= 4.5:
        reinforce_existing(backend, record, delta=0.03 if primary else 0.02)
        recover_existing_harm(backend, record, step=2 if primary else 1)
        return
    if eval_score >= quality_threshold:
        reinforce_existing(backend, record, delta=0.02 if primary else 0.01)
        recover_existing_harm(backend, record, step=1)
        return
    scale = _demotion_scale(record)
    if eval_score >= 2.5:
        demote_existing(backend, record, delta=(0.05 if primary else 0.03) * scale)
        return
    demote_existing(backend, record, delta=(0.08 if primary else 0.05) * scale)


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) > 1]

