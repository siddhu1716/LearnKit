"""LangGraph node wrapper for LearnKit.

Wraps LearnKit's memory loop as a LangGraph node that can be inserted
into any LangGraph workflow. The node intercepts the state, injects
relevant memory context, and captures the trajectory for post-run
distillation.

Usage (once implemented):
    from learnkit.adapters.langgraph import LangGraphAdapter

    lk = LearnKit(memory_backend="sqlite")
    memory_node = LangGraphAdapter(lk).as_node()
    graph.add_node("learnkit_memory", memory_node)
"""


class LangGraphAdapter:
    """LangGraph-compatible callable helpers for memory injection/finalization."""

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance

    def as_node(
        self,
        task_key: str = "task",
        context_key: str = "_learnkit_context",
        run_key: str = "_learnkit_run",
    ):
        """Return a callable suitable for LangGraph's add_node()."""
        def node(state: dict) -> dict:
            run = self.lk.prepare_run(state[task_key])
            return {**state, context_key: run["context"], run_key: run}
        return node

    def finalize(
        self,
        state: dict,
        response_key: str = "response",
        run_key: str = "_learnkit_run",
    ) -> str:
        """Finalize a run after a downstream LangGraph node writes a response."""
        return self.lk.finalize_run(state[run_key], state[response_key])
