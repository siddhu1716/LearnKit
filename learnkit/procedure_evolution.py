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
- refine     - if a fresh successful run found a *shorter* productive path AND
               that run did not regress the family's proven outcome score, the
               stored procedure is replaced by the better one (evolution_gen++).
               This non-regression check is the SkillOpt-style validation gate:
               brevity is never accepted at the cost of proven reliability, and
               the family keeps a monotonic best plus a rollback snapshot.
- demote     - a procedure that fails on replay loses confidence and, past a
               threshold, either rolls back to its last proven body (if a
               snapshot exists) or is quarantined so the agent re-learns
               (self-healing robustness).
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

# Validation-gated refinement (SkillOpt-inspired): a strictly shorter path is
# accepted only when this run did not regress the family's proven outcome score.
# Brevity must never be bought at the cost of reliability. ``_REFINE_TOLERANCE``
# is tiny slack on the 0-5 outcome scale so float noise alone never blocks a
# genuine tie (an equal-quality shorter path should still win).
_REFINE_TOLERANCE = 1e-6


def _established_best_score(record) -> float:
    """The family procedure's proven quality on the 0-5 outcome scale.

    Prefers the explicit monotonic ``_best_score``; falls back to the seed
    ``_quality_score``; finally to the reinforced ``success_rate`` (0-1) scaled
    to 0-5. Returns 0.0 when nothing is known so the first refine is ungated.
    """
    c = record.content
    if c.get("_best_score") is not None:
        return float(c["_best_score"])
    if c.get("_quality_score") is not None:
        return float(c["_quality_score"])
    if record.success_rate is not None:
        return float(record.success_rate) * 5.0
    return 0.0


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def reinforce_or_refine(backend, existing, new_content: dict, score: float) -> str:
    """A family procedure was re-proven. Reinforce it, and if the new run found a
    strictly shorter productive path *that does not regress the family's proven
    outcome score*, evolve the stored procedure to it.

    Returns ``"refined"`` if the procedure body was upgraded, ``"refine_rejected"``
    if a shorter path was found but blocked by the validation gate, else
    ``"reinforced"``.
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
    best_score = _established_best_score(existing)
    if 0 < len(new_proc) < len(old_proc):
        # Gate the shorter path on non-regression: accept only if this run is at
        # least as good as the family's proven best. A rollback snapshot of the
        # current proven body is kept so a future failed replay can self-heal
        # back to it (SkillOpt's monotonic ``best_skill``) instead of losing it.
        if score + _REFINE_TOLERANCE >= best_score:
            c["_prev_procedure"] = {f: c.get(f) for f in _PROCEDURE_FIELDS if f in c}
            for field in _PROCEDURE_FIELDS:
                if field in new_content:
                    c[field] = new_content[field]
            c["_best_score"] = max(best_score, float(score))
            existing.evolution_gen += 1
            outcome = "refined"
            logger.info(
                "Procedure evolved to a shorter path (validation gate passed)",
                extra={
                    "event": "procedure_refined",
                    "record_id": existing.id,
                    "old_steps": len(old_proc),
                    "new_steps": len(new_proc),
                    "candidate_score": round(float(score), 3),
                    "best_score": round(best_score, 3),
                    "evolution_gen": existing.evolution_gen,
                },
            )
        else:
            outcome = "refine_rejected"
            logger.info(
                "Shorter path rejected by validation gate - would regress quality",
                extra={
                    "event": "procedure_refine_rejected",
                    "record_id": existing.id,
                    "candidate_steps": len(new_proc),
                    "candidate_score": round(float(score), 3),
                    "best_score": round(best_score, 3),
                },
            )
    else:
        # A non-refining success still ratchets the monotonic best upward.
        c["_best_score"] = max(best_score, float(score))

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
        prev = c.pop("_prev_procedure", None)
        if prev:
            # Self-heal: a refined body failed, but the family still carries a
            # known-good predecessor. Roll back to it (SkillOpt monotonic best)
            # and stay active instead of forcing a full re-exploration. The
            # snapshot is consumed, so a subsequent failure still quarantines.
            for field, value in prev.items():
                c[field] = value
            record.confidence = max(record.confidence, confidence_floor)
            record.evolution_gen += 1
            logger.info(
                "Procedure rolled back to last proven body after failed replay",
                extra={
                    "event": "procedure_rolled_back",
                    "record_id": record.id,
                    "failure_count": c["failure_count"],
                },
            )
        else:
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
