"""LangChain adapter for LearnKit.

Integrates LearnKit's memory loop into LangChain agents. The adapter exposes
both learning paths:

* **model path** — inject retrieved memory into the prompt / system message via
  :meth:`start_run` → ``handle.context``;
* **agent path** — wrap the agent's tools with :meth:`wrap_tools` so each tool
  call is captured, proven procedures are replayed, and the run is gated on the
  real tool outcome instead of the LLM judge.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.langchain import LangChainAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = LangChainAdapter(lk)

    handle = adapter.start_run(task)
    tools = adapter.wrap_tools(handle, tools)          # agent path (optional)
    agent = create_agent(llm, tools, system=handle.context)
    answer = agent.invoke(task)
    adapter.complete_run(handle, answer)

For real LangChain agents, prefer the native callback handler so tool calls are
captured through LangChain's own callback bus instead of manual wrapping::

    handle = adapter.start_run(task)
    cb = adapter.callback_handler(handle)
    result = agent.invoke({"input": task}, config={"callbacks": [cb]})
    adapter.complete_run(handle, result["output"])

The legacy ``inject_context`` / ``finalize`` methods remain for the model-only
single-turn flow.
"""

from .base import BaseAdapter, RunHandle
from .registry import register_adapter

try:  # LangChain is an optional dependency (``learnkit[langchain]``).
    from langchain_core.callbacks import BaseCallbackHandler as _LCBaseCallbackHandler

    LANGCHAIN_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when langchain is absent
    _LCBaseCallbackHandler = object
    LANGCHAIN_AVAILABLE = False


class LearnKitCallbackHandler(_LCBaseCallbackHandler):
    """A real LangChain callback handler that captures the agent's tool calls.

    Attach it via ``config={"callbacks": [handler]}`` (or the legacy
    ``callbacks=[handler]``) and every tool invocation LangChain runs is
    recorded onto the :class:`RunHandle`'s :class:`~learnkit.tool_tracker.ToolTracker`
    — driving the procedural (agent) learning path through LangChain's native
    callback bus rather than manual :meth:`BaseAdapter.wrap_tools`.

    The capture logic does not require LangChain to be importable; when it is,
    the handler also subclasses LangChain's ``BaseCallbackHandler`` so the
    framework accepts it as a callback.
    """

    #: True if this handler subclasses LangChain's real ``BaseCallbackHandler``.
    langchain_available: bool = LANGCHAIN_AVAILABLE

    def __init__(self, handle: RunHandle):
        if LANGCHAIN_AVAILABLE:
            super().__init__()
        self.handle = handle
        # run_id -> (tool_name, tool_input) for matching start/end events.
        self._pending: dict = {}

    def on_tool_start(self, serialized, input_str, *, run_id=None, **kwargs):
        name = None
        if isinstance(serialized, dict):
            name = serialized.get("name")
        self._pending[run_id] = (name or "tool", input_str)

    def on_tool_end(self, output, *, run_id=None, **kwargs):
        tracker = self.handle.tracker
        if tracker is None:
            return
        name, payload = self._pending.pop(run_id, ("tool", None))
        tracker.record(name, payload, output, success=True)

    def on_tool_error(self, error, *, run_id=None, **kwargs):
        tracker = self.handle.tracker
        if tracker is None:
            return
        name, payload = self._pending.pop(run_id, ("tool", None))
        tracker.record(name, payload, None, success=False)


class LangChainAdapter(BaseAdapter):
    """LangChain integration with both the model and agent learning paths."""

    name = "langchain"

    def __init__(self, learnkit_instance, *, capture_tools=None):
        super().__init__(learnkit_instance, capture_tools=capture_tools)
        self._current = None

    def callback_handler(self, handle: RunHandle) -> LearnKitCallbackHandler:
        """Build a LangChain callback handler that captures tool calls for ``handle``.

        Pass it through ``config={"callbacks": [handler]}`` so the agent path is
        driven by LangChain's native callbacks.
        """
        return LearnKitCallbackHandler(handle)

    # ── Legacy single-turn (model path) ──────────────────────────────
    def inject_context(self, task: str) -> str:
        """Begin a run and return the memory context to inject into the prompt.

        Backward-compatible shim around :meth:`start_run`. This is the pure
        model path (no tool loop), so procedure replay is not armed.
        """
        self._current = self.start_run(task, capture_tools=False)
        return self._current.context

    def finalize(self, response: str) -> str:
        """Finish the run started by :meth:`inject_context`."""
        if self._current is None:
            raise ValueError("No active LearnKit run to finalize")
        handle, self._current = self._current, None
        return self.complete_run(handle, response)


register_adapter(LangChainAdapter.name, LangChainAdapter)
