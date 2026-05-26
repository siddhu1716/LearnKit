"""AutoGen reply_func adapter for LearnKit.

Integrates LearnKit into AutoGen multi-agent conversations via the
reply_func registration mechanism. Captures conversation turns as
trajectory steps and injects memory context into each agent's
system message.

Usage (once implemented):
    from learnkit.adapters.autogen import AutoGenAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = AutoGenAdapter(lk)
    adapter.register(autogen_agent)
"""


class AutoGenAdapter:
    """AutoGen reply_func adapter that wraps LearnKit memory into agent replies.

    Not yet implemented — this stub establishes the integration contract.
    """

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance
        raise NotImplementedError(
            "AutoGenAdapter is planned for Phase 4. "
            "Use the @lk.agent decorator for direct integration."
        )

    def register(self, agent):
        """Register LearnKit memory hooks on an AutoGen agent."""
        raise NotImplementedError
