"""Procedure replay for the agent path (`@lk.agent_learn`).

`ToolTracker` captures and stores a procedure; this module *executes* one. It is
the framework-agnostic auto-short-circuit primitive (AP4): given a tracker that
already has a plan attached and a mapping of tool name → callable, it runs the
proven tool sequence directly instead of letting the agent re-derive it.

Argument values that were parameterized at capture time (AP6) are re-bound here
via ``bind_args``: stored slot markers are filled from an ``overrides`` map the
caller supplies after parsing the current task, so one captured procedure serves
a whole task family rather than a single literal task.
"""

from typing import Any, Callable, Optional

from .logging import get_logger
from .tool_tracker import ToolTracker

logger = get_logger("replay")


def bind_args(arg_template: Any, overrides: Optional[dict] = None) -> dict:
    """Resolve a stored ``arg_template`` into concrete tool kwargs.

    A slot marker ``{"__slot__": "products"}`` is replaced by
    ``overrides["products"]`` when the caller supplied a substitution for that
    task token, otherwise it falls back to the original captured value. Keys are
    matched case-insensitively. Non-slot values pass through unchanged.
    """
    overrides = {str(k).lower(): v for k, v in (overrides or {}).items()}

    def conv(v: Any) -> Any:
        if isinstance(v, dict) and set(v.keys()) == {"__slot__"}:
            original = v["__slot__"]
            return overrides.get(str(original).lower(), original)
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v

    if not isinstance(arg_template, dict):
        return {}
    return {k: conv(v) for k, v in arg_template.items()}


def replay_plan(
    tracker: ToolTracker,
    tools: dict[str, Callable],
    overrides: Optional[dict] = None,
    mark_success: bool = True,
) -> int:
    """Execute the plan attached to ``tracker`` against ``tools``.

    Each planned step's tool is looked up in ``tools`` (a ``name → callable``
    map), its arguments are re-bound from the template via ``overrides``, the
    call is made, and the result is recorded back onto the tracker so the replay
    counts toward the run's tool-call total and feeds the outcome gate.

    Returns the number of steps executed. Raises ``ValueError`` if the tracker
    has no plan, so a caller never silently "replays" nothing.
    """
    if not tracker.has_plan:
        raise ValueError("replay_plan called but tracker has no attached plan")

    executed = 0
    for step in tracker.plan_steps:
        name = step.get("tool")
        fn = tools.get(name)
        kwargs = bind_args(step.get("arg_template"), overrides)
        if fn is None:
            logger.warning(
                "Replay step skipped — tool not provided",
                extra={"event": "replay_missing_tool", "tool": name},
            )
            tracker.record(name, kwargs, None, success=False, productive=True)
            executed += 1
            continue
        try:
            result = fn(**kwargs)
            tracker.record(name, kwargs, result, success=True, productive=True)
        except Exception:
            tracker.record(name, kwargs, None, success=False, productive=True)
            raise
        executed += 1

    if mark_success and executed:
        tracker.mark_outcome(True)
    logger.info(
        "Replayed stored procedure",
        extra={
            "event": "procedure_replayed",
            "steps": executed,
            "source_id": tracker.plan_source_id,
        },
    )
    return executed
