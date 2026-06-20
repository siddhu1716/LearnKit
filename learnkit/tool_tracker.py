"""Tool-call capture for the procedural (Hermes-style) learning path.

The model path (`@lk.learn`) treats the agent as a black box: a task string
goes in, an answer string comes out, and only that final answer is judged and
distilled. That is fine for single-turn QA but it cannot learn *procedures* —
the sequence of tool calls an agent makes to solve a task.

`ToolTracker` is the thin instrument the agent path (`@lk.agent_learn`) injects
into the wrapped function. The agent reports each tool invocation through it,
which records a `tool` step on the run's trajectory. Those steps flow straight
into the existing distiller (it already renders `Tool(name): ...` steps), so a
successful run produces a reusable procedural SkillRecord — and the call count
gives the tool-calls-per-task metric that the whole thesis is measured on.
"""

import functools
import json
from typing import Any, Callable, Optional

from .logging import get_logger
from .trajectory import Trajectory

logger = get_logger("tool_tracker")


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


class ToolTracker:
    """Records an agent's tool calls onto a trajectory and counts them.

    Two usage styles, both supported in the same run:

    Manual::

        def my_agent(task, _learnkit_context="", _learnkit_tools=None):
            result = search_db(query)
            _learnkit_tools.record("search_db", {"query": query}, result)
            ...

    Auto-wrapping::

        def my_agent(task, _learnkit_context="", _learnkit_tools=None):
            search = _learnkit_tools.wrap(search_db)
            result = search(query)   # call captured automatically
            ...
    """

    def __init__(self, trajectory: Trajectory):
        self._traj = trajectory
        self.call_count: int = 0
        self.calls: list[dict] = []
        self.successes: int = 0
        self.failures: int = 0
        self._explicit_outcome: Optional[bool] = None
        self._explicit_score: Optional[float] = None
        # Plan (a retrieved procedure to replay), set by the agent path.
        self.plan_steps: list[dict] = []
        self.plan_source_id: Optional[str] = None
        # "exact" (safe to hard-replay) | "sibling" (needs arg adaptation) | None
        self.plan_kind: Optional[str] = None

    def record(
        self,
        tool_name: str,
        tool_input: Optional[Any] = None,
        output: Optional[Any] = None,
        reasoning: Optional[str] = None,
        success: bool = True,
        productive: bool = True,
    ) -> Any:
        """Log a single tool call onto the trajectory. Returns ``output`` so it
        can be used inline: ``data = tracker.record("fetch", args, fetch(args))``.

        ``success`` records whether the call ran without error (feeds the
        tool-success outcome gate). ``productive`` records whether the call was on
        the path to the goal (default True); dead-end exploration calls marked
        ``productive=False`` are kept in the trajectory but excluded from the
        stored procedure, so replay follows only the cleaned successful path.
        """
        self.call_count += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        normalized_input = tool_input if isinstance(tool_input, dict) else (
            {"value": tool_input} if tool_input is not None else None
        )
        self._traj.add_step(
            "tool",
            _to_text(output),
            tool_name=tool_name,
            tool_input=normalized_input,
            reasoning=reasoning,
            productive=productive,
        )
        self.calls.append(
            {
                "tool": tool_name,
                "input": normalized_input,
                "output": output,
                "success": success,
                "productive": productive,
            }
        )
        return output

    def wrap(self, fn: Callable, name: Optional[str] = None) -> Callable:
        """Wrap a tool callable so every invocation is recorded automatically.
        A raised exception is recorded as a failed call and re-raised.
        """
        tool_name = name or getattr(fn, "__name__", "tool")

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            payload = {"args": list(args), "kwargs": kwargs} if (args or kwargs) else None
            try:
                result = fn(*args, **kwargs)
            except Exception:
                self.record(tool_name, payload, None, success=False)
                raise
            self.record(tool_name, payload, result, success=True)
            return result

        return wrapped

    # ── Outcome (tool-success gate) ────────────────────────────────────
    def mark_outcome(self, success: bool, score: Optional[float] = None) -> None:
        """Explicitly declare the task-level outcome. Overrides the derived
        tool-success rate. Optional ``score`` (0–5) sets the exact gate value.
        """
        self._explicit_outcome = success
        self._explicit_score = score

    @property
    def tool_success_rate(self) -> float:
        if self.call_count == 0:
            return 1.0
        return self.successes / self.call_count

    def outcome_score(self) -> Optional[float]:
        """Trusted outcome on a 0–5 scale for the tool-success gate.

        Priority: explicit score > explicit success/fail > derived tool-success
        rate. Returns ``None`` when there is nothing to gate on (no tool calls
        and no explicit mark), so the caller can fall back to the LLM judge.
        """
        if self._explicit_score is not None:
            return max(0.0, min(5.0, self._explicit_score))
        if self._explicit_outcome is not None:
            return 5.0 if self._explicit_outcome else 0.0
        if self.call_count == 0:
            return None
        return 5.0 * self.tool_success_rate

    # ── Replay ──────────────────────────────────────────────────
    def set_plan(
        self,
        procedure: list[dict],
        source_id: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> None:
        """Attach a retrieved procedure for the agent to replay. ``kind`` records
        the match strength (``"exact"`` / ``"sibling"``) so the agent can choose
        to hard-replay an exact match or merely follow a sibling as guidance.
        """
        self.plan_steps = procedure or []
        self.plan_source_id = source_id
        self.plan_kind = kind
        if self.plan_steps:
            logger.info(
                "Procedure plan available for replay",
                extra={
                    "event": "plan_available",
                    "steps": len(self.plan_steps),
                    "source_id": source_id,
                    "kind": kind,
                    "tools": [s.get("tool") for s in self.plan_steps],
                },
            )

    @property
    def has_plan(self) -> bool:
        return bool(self.plan_steps)

    @property
    def planned_tools(self) -> list[str]:
        return [s.get("tool", "") for s in self.plan_steps]
