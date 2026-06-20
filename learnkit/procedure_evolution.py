"""Procedure evolution for the agent path (`@lk.agent_learn`).

Capturing a procedure once is memory; *evolving* it over repeated use is
learning. This module is the Hermes-inspired layer that makes a stored procedure
get better, more trusted, and self-healing as the agent keeps working — the
mechanism behind "the agent accumulates institutional knowledge" rather than
"the agent replays a fixed script".

Three behaviours, all keyed on the task-signature *family* so every sibling task
reinforces one durable record instead of scattering near-duplicates (Hermes's
"consolidate into an umbrella skill" principle):

- reinforce  — a family procedure that succeeds again gains confidence + reuse.
- refine     — if a fresh successful run found a *shorter* productive path, the
               stored procedure is replaced by the better one (evolution_gen++).
- demote     — a procedure that fails on replay loses confidence and, past a
               threshold, is quarantined so the agent stops trusting it and
               re-learns (self-healing robustness).
"""

from datetime import datetime, timezone
from typing import Optional

from .logging import get_logger
from .playbook import merge_insights

logger = get_logger("procedure_evolution")

# Procedure stops being eligible for replay once it fails this many times or
# drops below this confidence — it is quarantined and the agent re-explores.
DEFAULT_MAX_FAILURES = 2
DEFAULT_CONFIDENCE_FLOOR = 0.25
# Fields that define the procedure body; copied when refining to a better path.
_PROCEDURE_FIELDS = ("procedure", "tool_sequence", "task_signature",
                     "task_tokens", "tools_used")


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def reinforce_or_refine(backend, existing, new_content: dict, score: float) -> str:
    """A family procedure was re-proven. Reinforce it, and if the new run found a
    strictly shorter productive path, evolve the stored procedure to it.

    Returns ``"refined"`` if the procedure body was upgraded, else ``"reinforced"``.
    """
    c = existing.content
    c["success_count"] = int(c.get("success_count", 0)) + 1
    c["last_used_at"] = _now()

    # Accumulate the natural-language playbook: every re-proof can contribute new
    # durable knowledge / pitfalls, merged + deduped into the existing skill body
    # (Hermes "the SKILL.md grows over the week"). Independent of refine/reinforce.
    new_playbook = new_content.get("playbook")
    new_pitfalls = new_content.get("pitfalls")
    if new_playbook:
        merged = merge_insights(c.get("playbook"), new_playbook)
        if merged != (c.get("playbook") or []):
            c["playbook"] = merged
    if new_pitfalls:
        merged_p = merge_insights(c.get("pitfalls"), new_pitfalls)
        if merged_p != (c.get("pitfalls") or []):
            c["pitfalls"] = merged_p

    new_proc = new_content.get("procedure") or []
    old_proc = c.get("procedure") or []
    outcome = "reinforced"
    if 0 < len(new_proc) < len(old_proc):
        for field in _PROCEDURE_FIELDS:
            if field in new_content:
                c[field] = new_content[field]
        existing.evolution_gen += 1
        outcome = "refined"
        logger.info(
            "Procedure evolved to a shorter path",
            extra={
                "event": "procedure_refined",
                "record_id": existing.id,
                "old_steps": len(old_proc),
                "new_steps": len(new_proc),
                "evolution_gen": existing.evolution_gen,
            },
        )

    existing.reinforce(score)  # reuse_count++, confidence up, success_rate EMA
    if existing.status in ("stale", "quarantine"):
        existing.status = "active"  # re-proven — bring it back (Hermes reactivate)
    backend.replace(existing)
    logger.info(
        "Procedure reinforced",
        extra={
            "event": "procedure_reinforced",
            "record_id": existing.id,
            "reuse_count": existing.reuse_count,
            "confidence": round(existing.confidence, 3),
            "outcome": outcome,
        },
    )
    return outcome


def demote_procedure(
    backend,
    record,
    max_failures: int = DEFAULT_MAX_FAILURES,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
) -> bool:
    """A replayed procedure produced a bad outcome. Lower its confidence and,
    once it has failed too often or fallen below the floor, quarantine it so it
    is no longer retrieved/replayed and the agent re-learns the task.

    Returns ``True`` if the procedure was quarantined.
    """
    if record is None:
        return False
    c = record.content
    c["failure_count"] = int(c.get("failure_count", 0)) + 1
    c["last_used_at"] = _now()
    record.confidence = max(0.0, record.confidence - 0.15)

    quarantined = False
    if c["failure_count"] >= max_failures or record.confidence < confidence_floor:
        record.status = "quarantine"
        quarantined = True
    backend.replace(record)
    logger.info(
        "Procedure demoted after failed replay",
        extra={
            "event": "procedure_demoted",
            "record_id": record.id,
            "failure_count": c["failure_count"],
            "confidence": round(record.confidence, 3),
            "quarantined": quarantined,
        },
    )
    return quarantined


def find_family_procedure(backend, signature_fp: str, scope: str) -> Optional[object]:
    """Find the existing durable procedure for a task-signature family, if any.

    Mirrors the fingerprint-dedup lookup already used for prose skills: search by
    the signature fingerprint token and confirm in Python (FTS is a prefilter).
    """
    if not signature_fp:
        return None
    try:
        cands = backend.search(
            query=f"procsig:{signature_fp}", scope=scope, limit=8, exclude_stale=False
        )
    except Exception:
        cands = []
    for r in cands:
        if (getattr(r, "type", None) == "skill"
                and r.content.get("_signature_fp") == signature_fp):
            return r
    return None
