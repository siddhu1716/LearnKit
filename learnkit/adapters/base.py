"""Framework-neutral base class for LearnKit adapters.

Every framework integration — LangChain, LangGraph, AutoGen, a raw API call, or
a third-party framework nobody has written an adapter for yet — reduces to the
same two primitives:

1. ``start_run(task)``     → retrieve memory, inject context, (optionally) arm
                             tool capture + procedure replay.
2. ``complete_run(handle, response)`` → judge, distill, and persist the run.

A concrete adapter only has to map its framework's lifecycle (callbacks, graph
nodes, reply functions, API wrappers, …) onto those two calls. By subclassing
:class:`BaseAdapter` an integration gets both LearnKit learning paths for free:

* the **model path** — memory text injected via ``handle.context``;
* the **agent path** — a :class:`~learnkit.tool_tracker.ToolTracker` on
  ``handle.tracker`` that captures tool calls and replays proven procedures.

This is the surface third parties build against to make LearnKit pluggable
into any open-source agent framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..tool_tracker import ToolTracker


@dataclass
class RunHandle:
    """Opaque handle returned by :meth:`BaseAdapter.start_run`.

    Carries everything the framework needs while a single task is in flight:

    * ``context`` — the memory text to inject into the prompt / system message.
    * ``tracker`` — a :class:`ToolTracker` for capturing tool calls and replaying
      learned procedures (``None`` when tool capture is disabled).
    * ``run`` — the internal LearnKit run dict; passed back to
      :meth:`BaseAdapter.complete_run`. Treat it as opaque.
    """

    run: dict
    context: str
    tracker: Optional[ToolTracker] = None

    @property
    def has_plan(self) -> bool:
        """True if a proven procedure was retrieved for replay."""
        return bool(self.tracker and self.tracker.has_plan)

    @property
    def plan_steps(self) -> list[dict]:
        """The retrieved procedure steps to replay, if any."""
        return list(self.tracker.plan_steps) if self.tracker else []


class BaseAdapter:
    """Base class for all LearnKit framework adapters.

    Subclasses MUST set :attr:`name` (used for the adapter registry) and should
    expose framework-shaped convenience methods that delegate to
    :meth:`start_run` / :meth:`complete_run`.
    """

    #: Registry key for this adapter (e.g. ``"langchain"``). Subclasses override.
    name: str = "base"

    #: Whether to arm the tool-capture / procedure-replay path by default.
    capture_tools: bool = True

    def __init__(self, learnkit_instance: Any, *, capture_tools: Optional[bool] = None):
        if learnkit_instance is None:
            raise ValueError("BaseAdapter requires a LearnKit instance")
        self.lk = learnkit_instance
        if capture_tools is not None:
            self.capture_tools = capture_tools

    # ── Core lifecycle ───────────────────────────────────────────────
    def start_run(self, task: str, *, capture_tools: Optional[bool] = None) -> RunHandle:
        """Begin a task: retrieve memory, build the context, and (optionally) arm
        a :class:`ToolTracker` wired for procedure replay.

        ``capture_tools`` overrides the adapter default for this run — pass
        ``False`` for a pure model-path call (no tool loop) so no procedure is
        armed for replay.

        Returns a :class:`RunHandle` that must be passed to
        :meth:`complete_run` once the framework produces a final answer.
        """
        run = self.lk.prepare_run(task)
        arm = self.capture_tools if capture_tools is None else capture_tools
        tracker: Optional[ToolTracker] = None
        if arm:
            tracker = self.lk.arm_tool_tracker(run)
        return RunHandle(run=run, context=run["context"], tracker=tracker)

    def complete_run(self, handle: RunHandle, response: str) -> str:
        """Finish a task: feed the final answer (and any captured tool outcome)
        through the judge → distill → persist pipeline. Returns ``response``.
        """
        if handle is None:
            raise ValueError("complete_run requires the RunHandle from start_run")
        run = handle.run
        if handle.tracker is not None:
            run["tool_calls"] = handle.tracker.call_count
            # Tool-success gate: when real tool calls happened, gate on their
            # outcome rather than the harm-blind LLM judge.
            run["outcome_score"] = handle.tracker.outcome_score()
        return self.lk.finalize_run(run, response)

    # ── Tool helpers ─────────────────────────────────────────────────
    def wrap_tool(self, handle: RunHandle, fn: Callable, name: Optional[str] = None) -> Callable:
        """Wrap a tool callable so each invocation is captured on ``handle``.

        No-ops (returns ``fn`` unchanged) when tool capture is disabled, so it is
        always safe to call.
        """
        if handle.tracker is None:
            return fn
        return handle.tracker.wrap(fn, name=name)

    def wrap_tools(self, handle: RunHandle, tools, name_attr: str = "name"):
        """Wrap an iterable of tools, capturing each call. Falls back to
        ``__name__`` when a tool has no ``name_attr`` attribute.
        """
        wrapped = []
        for tool in tools:
            tool_name = getattr(tool, name_attr, None) or getattr(tool, "__name__", None)
            wrapped.append(self.wrap_tool(handle, tool, name=tool_name))
        return wrapped

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"<{type(self).__name__} name={self.name!r} capture_tools={self.capture_tools}>"
