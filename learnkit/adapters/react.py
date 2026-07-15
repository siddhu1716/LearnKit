"""Auto-replay ReAct runner for the agent path (``@lk.agent_learn``).

This is the framework-agnostic loop that *auto-invokes* procedure replay — the
piece that turns LearnKit's captured procedures into real cost savings without
the caller hand-wiring ``has_plan`` / ``plan_steps`` checks.

Given a LearnKit instance, a task, a ``name -> callable`` tool map, and a
single-step planner callback, :func:`run_react_agent` will:

1. Prepare the run and arm a :class:`~learnkit.tool_tracker.ToolTracker`
   (which retrieves and attaches a matching stored procedure, if any).
2. **Exact match →** hard-replay the proven tool sequence with **zero LLM /
   planning calls** and return.
3. **Sibling / cold →** drive the model's ReAct loop. The retrieved procedure is
   already composed into ``run["context"]`` as guidance for sibling tasks, so the
   model follows the proven shape instead of exploring from scratch.

The planner callback (`llm_step`) is deliberately minimal and framework-neutral
so this runner works with raw OpenAI tool-calls, LangChain, LangGraph, or a
deterministic stub in tests:

    def llm_step(task: str, context: str, history: list[Observation]) -> LLMStep:
        ...  # one planning turn; return tool calls to make OR a final answer

Each ``llm_step`` invocation counts as one planning (LLM) call — the metric the
agent path is measured on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..replay import replay_plan
from ..logging import get_logger

logger = get_logger("adapters.react")


@dataclass
class ToolCall:
    """A single tool invocation the planner wants to make."""

    name: str
    args: dict = field(default_factory=dict)


@dataclass
class Observation:
    """The result of executing one :class:`ToolCall`, fed back to the planner."""

    name: str
    args: dict
    output: object
    success: bool


@dataclass
class LLMStep:
    """One planning turn's output: tool calls to run and/or a final answer.

    Return ``tool_calls`` to keep going, or set ``final`` (with no tool calls) to
    stop the loop.
    """

    tool_calls: list[ToolCall] = field(default_factory=list)
    final: Optional[str] = None


@dataclass
class ReActResult:
    """Outcome of a run, with the cost metrics the agent path optimizes."""

    response: str
    tool_calls: int
    llm_calls: int
    replayed: bool
    plan_kind: Optional[str]


def run_react_agent(
    memory,
    task: str,
    tools: dict[str, Callable],
    llm_step: Callable[[str, str, list[Observation]], LLMStep],
    *,
    max_steps: int = 8,
    overrides: Optional[dict] = None,
    exploration_tools: Optional[set[str]] = None,
    mark_success: Optional[bool] = None,
) -> ReActResult:
    """Run a task through the agent path with automatic procedure replay.

    Args:
        memory: a :class:`~learnkit.core.LearnKit` instance.
        task: the task string.
        tools: mapping of tool name → callable (invoked with keyword args).
        llm_step: planner callback; one call == one planning (LLM) turn.
        max_steps: hard cap on planning turns for the cold/sibling loop.
        overrides: slot substitutions for replay of parameterized (sibling)
            procedures — see :func:`learnkit.replay.bind_args`.
        exploration_tools: tool names to mark ``productive=False`` so dead-end
            orientation calls are excluded from the stored procedure.
        mark_success: explicit success signal for the tool-success gate. When
            ``None`` the gate derives success from the tool call success rate.

    Returns:
        :class:`ReActResult` with the final response, tool-call count, planning
        (LLM) call count, whether a stored procedure was hard-replayed, and the
        match kind (``"exact"`` / ``"sibling"`` / ``None``).
    """
    exploration_tools = exploration_tools or set()
    run = memory.prepare_run(task)
    run["learning_mode"] = "agent_learn"
    tracker = memory.arm_tool_tracker(run)

    # ── Exact match: hard-replay the proven procedure, zero planning calls ──
    if tracker.has_plan and tracker.plan_kind == "exact":
        replay_plan(tracker, tools, overrides=overrides)
        run["tool_calls"] = tracker.call_count
        run["outcome_score"] = tracker.outcome_score()
        response = "[replayed proven procedure]"
        memory.finalize_run(run, response)
        logger.info(
            "Auto-replayed exact procedure",
            extra={"event": "auto_replay", "tool_calls": tracker.call_count},
        )
        return ReActResult(
            response=response,
            tool_calls=tracker.call_count,
            llm_calls=0,
            replayed=True,
            plan_kind="exact",
        )

    # ── Cold / sibling: drive the model loop (context carries guidance) ──
    llm_calls = 0
    history: list[Observation] = []
    final_response = ""
    for _ in range(max_steps):
        step = llm_step(task, run["context"], history)
        llm_calls += 1
        for call in step.tool_calls:
            fn = tools.get(call.name)
            productive = call.name not in exploration_tools
            if fn is None:
                tracker.record(call.name, call.args, None, success=False, productive=productive)
                history.append(Observation(call.name, call.args, None, False))
                continue
            try:
                out = fn(**call.args)
                tracker.record(call.name, call.args, out, success=True, productive=productive)
                history.append(Observation(call.name, call.args, out, True))
            except Exception as exc:  # noqa: BLE001 — surfaced to the planner as an observation
                tracker.record(call.name, call.args, None, success=False, productive=productive)
                history.append(Observation(call.name, call.args, f"error: {exc}", False))
        if step.final is not None:
            final_response = step.final
            break

    run["tool_calls"] = tracker.call_count
    if mark_success is not None:
        tracker.mark_outcome(bool(mark_success))
    run["outcome_score"] = tracker.outcome_score()
    memory.finalize_run(run, final_response)
    return ReActResult(
        response=final_response,
        tool_calls=tracker.call_count,
        llm_calls=llm_calls,
        replayed=False,
        plan_kind=tracker.plan_kind,
    )
