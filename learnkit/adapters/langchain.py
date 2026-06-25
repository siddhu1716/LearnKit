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

The legacy ``inject_context`` / ``finalize`` methods remain for the model-only
single-turn flow.
"""

from .base import BaseAdapter
from .registry import register_adapter


class LangChainAdapter(BaseAdapter):
    """LangChain integration with both the model and agent learning paths."""

    name = "langchain"

    def __init__(self, learnkit_instance, *, capture_tools=None):
        super().__init__(learnkit_instance, capture_tools=capture_tools)
        self._current = None

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
