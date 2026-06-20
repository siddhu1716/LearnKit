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
from typing import Any, Optional

from .trajectory import Trajectory

# Hard caps so a runaway trajectory can't write an unbounded procedure blob.
MAX_PROCEDURE_STEPS = 50
MAX_ARG_BYTES = 2 * 1024
MAX_RESULT_PREVIEW = 160


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
            "procedure":     [{"tool", "args", "result_preview"}],  # ordered
            "tool_sequence": ["tool_a", "tool_b", ...],             # signature
            "call_count":    int,
        }

    or ``None`` if the trajectory has no tool steps (nothing procedural to learn).
    """
    procedure: list[dict] = []
    tool_sequence: list[str] = []

    for step in trajectory.steps:
        if step.role != "tool":
            continue
        # Exclude dead-end exploration: store only the cleaned successful path,
        # so replay reproduces the minimal procedure (Agent Workflow Memory).
        if getattr(step, "productive", True) is False:
            continue
        tool_name = step.tool_name or "tool"
        tool_sequence.append(tool_name)
        procedure.append(
            {
                "tool": tool_name,
                "args": _bounded(step.tool_input, MAX_ARG_BYTES)
                if step.tool_input is not None
                else None,
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
        "call_count": len(procedure),
    }


def procedure_fingerprint(tool_sequence: list[str]) -> str:
    """Stable fingerprint of a tool-call sequence — the discriminative signature
    for procedural dedup. Two trajectories that call the same tools in the same
    order produce the same procedure and should not be stored twice.
    """
    normalized = "|".join(t.strip().lower() for t in tool_sequence if isinstance(t, str))
    return hashlib.sha256(normalized.encode()).hexdigest()
