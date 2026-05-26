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
    """LangGraph node that wraps LearnKit memory injection and capture.

    Not yet implemented — this stub establishes the integration contract.
    """

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance
        raise NotImplementedError(
            "LangGraphAdapter is planned for Phase 4. "
            "Use the @lk.agent decorator for direct integration."
        )

    def as_node(self):
        """Return a callable suitable for LangGraph's add_node()."""
        raise NotImplementedError
