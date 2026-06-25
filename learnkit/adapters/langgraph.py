"""LangGraph node wrapper for LearnKit.

Wraps LearnKit's memory loop as a LangGraph node that can be inserted into any
LangGraph workflow. The memory node injects retrieved context (and, on the agent
path, arms tool capture / procedure replay) into the graph state; a downstream
node writes the response and the run is finalized.

Both learning paths are available:

* **model path** — ``context_key`` carries the memory text to inject;
* **agent path** — when tool capture is on, ``handle_key`` carries the
  :class:`~learnkit.adapters.base.RunHandle`; wrap your tool node's callables
  with :meth:`wrap_tools` so each call is captured.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.langgraph import LangGraphAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = LangGraphAdapter(lk)
    graph.add_node("learnkit_memory", adapter.as_node())
    ...
    adapter.finalize(final_state)
"""

from .base import BaseAdapter
from .registry import register_adapter


class LangGraphAdapter(BaseAdapter):
    """LangGraph integration with both the model and agent learning paths."""

    name = "langgraph"

    def as_node(
        self,
        task_key: str = "task",
        context_key: str = "_learnkit_context",
        handle_key: str = "_learnkit_handle",
    ):
        """Return a callable suitable for LangGraph's ``add_node()``.

        The node retrieves memory for ``state[task_key]`` and writes the memory
        text to ``context_key`` and the :class:`RunHandle` to ``handle_key``.
        """

        def node(state: dict) -> dict:
            handle = self.start_run(state[task_key])
            return {**state, context_key: handle.context, handle_key: handle}

        return node

    def finalize(
        self,
        state: dict,
        response_key: str = "response",
        handle_key: str = "_learnkit_handle",
    ) -> str:
        """Finalize a run after a downstream LangGraph node writes a response."""
        return self.complete_run(state[handle_key], state[response_key])


register_adapter(LangGraphAdapter.name, LangGraphAdapter)
