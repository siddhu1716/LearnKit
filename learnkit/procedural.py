"""Procedural skill extraction for the agent path (`@lk.agent_learn`).

The model path distills *prose* — an LLM reads a trajectory and writes a few
sentences describing the approach. That is declarative memory: useful as a hint,
but the agent still re-derives every tool call from scratch next time.

The agent path needs something different and more honest: the **actual sequence
of tool calls the agent executed to succeed**. That is a procedure. This module
pulls that procedure straight off the captured trajectory — deterministically,
no LLM, no hallucinated steps — so a stored skill is grounded in calls that
really happened. The LLM distiller can still *name* and *annotate* it, but the
procedural backbone comes from real execution.

This mirrors the Hermes principle ("durable procedures instead of repeating
yourself") and Agent Workflow Memory / Voyager (induce reusable tool workflows
from successful trajectories).
"""

import hashlib
import json
import re
from typing import Any, Optional

from .trajectory import Trajectory

# Hard caps so a runaway trajectory can't write an unbounded procedure blob.
MAX_PROCEDURE_STEPS = 50
MAX_ARG_BYTES = 2 * 1024
MAX_RESULT_PREVIEW = 160

# Filler words excluded from a task signature — they carry no discriminative
# meaning, so keeping them would make every task look similar.
_STOPWORDS = frozenset(
    {"a", "an", "the", "of", "to", "for", "and", "or", "with", "by", "on", "in"}
)
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(task: str) -> list[str]:
    """Lowercase content tokens of a task string (stopwords kept here)."""
    return _TOKEN_RE.findall((task or "").lower())


def task_signature(task: str, exclude: Optional[set[str]] = None) -> list[str]:
    """The discriminative *skeleton* of a task: content tokens minus stopwords,
    pure numbers, and any ``exclude`` tokens (the slot values a procedure
    parameterizes over). Two tasks in the same family share this skeleton even
    when their slot values differ, which is what lets a parameterized procedure
    be reused. Returns a sorted, de-duplicated list (stable for storage).
    """
    exclude = exclude or set()
    sig = {
        t
        for t in _tokenize(task)
        if t not in _STOPWORDS and not t.isdigit() and t not in exclude
    }
    return sorted(sig)


def signature_coverage(stored: list[str], task: str) -> float:
    """Fraction of a stored skeleton that appears in ``task``.

    Coverage (``|stored ∩ current| / |stored|``) — not Jaccard — because a
    parameterized task adds slot tokens the skeleton never had, which would
    deflate Jaccard. Coverage asks the right question: *is this procedure's
    skeleton fully present in the new task?* Returns 1.0 for an empty skeleton
    (nothing to discriminate on; defer to the retriever's ranking).
    """
    if not stored:
        return 1.0
    current = set(_tokenize(task))
    hits = sum(1 for t in stored if t in current)
    return hits / len(stored)


def content_tokens(task: str) -> list[str]:
    """Full content fingerprint of a task: non-stopword tokens (slot values and
    numbers kept). Used to decide whether a candidate procedure is an *exact*
    re-encounter of a task vs a parameterized sibling.
    """
    return sorted({t for t in _tokenize(task) if t not in _STOPWORDS})


def match_kind(
    stored_signature: list[str],
    stored_tokens: list[str],
    task: str,
    threshold: float = 0.7,
) -> Optional[str]:
    """Classify how a stored procedure relates to ``task``.

    - ``"exact"``  — the task's content tokens equal the procedure's source task
      tokens: the very same task. Safe to replay verbatim (no LLM, no re-binding).
    - ``"sibling"`` — the task skeleton is covered above ``threshold`` but the
      tokens differ: same family, different slot values. Replay needs argument
      re-binding, so it is better handled as guidance than blind replay.
    - ``None`` — not a match; do not replay.
    """
    if stored_tokens and set(content_tokens(task)) == set(stored_tokens):
        return "exact"
    if signature_coverage(stored_signature, task) >= threshold:
        return "sibling"
    return None


def _parameterize(tool_input: Any, slot_tokens: set[str]) -> tuple[Any, list[str]]:
    """Replace string arg values that came from the task with slot markers.

    A value equal to a task token is a *slot* — it varies with the task — so it
    is stored as ``{"__slot__": <value>}`` and can be re-bound to a different
    value when the procedure is replayed on a sibling task (argument
    parameterization / templating). Returns ``(template, slot_values_found)``.
    """
    found: list[str] = []

    def conv(v: Any) -> Any:
        if isinstance(v, str) and v.lower() in slot_tokens:
            found.append(v.lower())
            return {"__slot__": v}
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v

    if not isinstance(tool_input, dict):
        return tool_input, found
    return {k: conv(v) for k, v in tool_input.items()}, found


def _bounded(value: Any, limit: int) -> Any:
    """Bound an arbitrary tool arg/result for storage."""
    try:
        text = value if isinstance(value, str) else json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


def extract_procedure(trajectory: Trajectory) -> Optional[dict]:
    """Pull the executed tool-call sequence off a trajectory.

    Returns a dict with::

        {
            "procedure":     [{"tool", "args", "arg_template", "result_preview"}],
            "tool_sequence": ["tool_a", "tool_b", ...],   # signature
            "task_signature":["build", "report", ...],    # task skeleton (AP5)
            "call_count":    int,
        }

    or ``None`` if the trajectory has no tool steps (nothing procedural to learn).

    ``arg_template`` carries slot markers for task-derived argument values so the
    procedure can be re-bound to a sibling task on replay (AP6). ``task_signature``
    is the task skeleton with those slot values removed, so a parameterized
    procedure still matches its family (AP5).
    """
    procedure: list[dict] = []
    tool_sequence: list[str] = []
    slot_tokens = set(_tokenize(trajectory.task))
    all_slots: set[str] = set()

    for step in trajectory.steps:
        if step.role != "tool":
            continue
        # Exclude dead-end exploration: store only the cleaned successful path,
        # so replay reproduces the minimal procedure (Agent Workflow Memory).
        if getattr(step, "productive", True) is False:
            continue
        tool_name = step.tool_name or "tool"
        tool_sequence.append(tool_name)
        arg_template, slots = _parameterize(step.tool_input, slot_tokens)
        all_slots.update(slots)
        procedure.append(
            {
                "tool": tool_name,
                "args": _bounded(step.tool_input, MAX_ARG_BYTES)
                if step.tool_input is not None
                else None,
                "arg_template": arg_template,
                "result_preview": _bounded(step.content, MAX_RESULT_PREVIEW),
            }
        )
        if len(procedure) >= MAX_PROCEDURE_STEPS:
            break

    if not procedure:
        return None

    return {
        "procedure": procedure,
        "tool_sequence": tool_sequence,
        "task_signature": task_signature(trajectory.task, exclude=all_slots),
        "task_tokens": content_tokens(trajectory.task),
        "call_count": len(procedure),
    }


def procedure_fingerprint(tool_sequence: list[str]) -> str:
    """Stable fingerprint of a tool-call sequence — the discriminative signature
    for procedural dedup. Two trajectories that call the same tools in the same
    order produce the same procedure and should not be stored twice.
    """
    normalized = "|".join(t.strip().lower() for t in tool_sequence if isinstance(t, str))
    return hashlib.sha256(normalized.encode()).hexdigest()


def signature_fingerprint(signature: list[str]) -> str:
    """Stable fingerprint of a task *skeleton* (order-independent).

    Unlike :func:`procedure_fingerprint` (ordered tool sequence), this hashes the
    sorted task-signature tokens, so every task in the same family maps to one
    fingerprint. It is the key for consolidating siblings onto a single durable
    procedure record (institutional knowledge) rather than scattering near-dupes.
    """
    normalized = "|".join(sorted(t.strip().lower() for t in signature if isinstance(t, str)))
    return hashlib.sha256(normalized.encode()).hexdigest()
