"""LangChain callback adapter for LearnKit.

Integrates LearnKit's memory loop into LangChain agents via the callback
handler interface. Captures trajectory steps from LangChain's
on_llm_start / on_tool_start / on_chain_end events and pipes them
through classify → retrieve → compose → evaluate → distill.

Usage (once implemented):
    from learnkit.adapters.langchain import LangChainAdapter

    lk = LearnKit(memory_backend="sqlite")
    handler = LangChainAdapter(lk)
    agent.run(task, callbacks=[handler])
"""


class LangChainAdapter:
    """LangChain callback handler that injects LearnKit memory into agent runs.

    Not yet implemented — this stub establishes the integration contract.
    """

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance
        raise NotImplementedError(
            "LangChainAdapter is planned for Phase 4. "
            "Use the @lk.agent decorator for direct integration."
        )
