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
    """Small framework-neutral handler with LangChain-shaped lifecycle methods."""

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance
        self.current_run = None

    def inject_context(self, task: str) -> str:
        self.current_run = self.lk.prepare_run(task)
        return self.current_run["context"]

    def finalize(self, response: str) -> str:
        if self.current_run is None:
            raise ValueError("No active LearnKit run to finalize")
        result = self.lk.finalize_run(self.current_run, response)
        self.current_run = None
        return result
