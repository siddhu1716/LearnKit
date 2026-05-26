"""Raw OpenAI / Anthropic API wrapper for LearnKit.

For users who call the OpenAI or Anthropic APIs directly (without a
framework), this adapter wraps the API call to inject LearnKit memory
into the system prompt and capture the response as a trajectory.

Usage (once implemented):
    from learnkit.adapters.openai_raw import OpenAIRawAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = OpenAIRawAdapter(lk)

    # Instead of: client.chat.completions.create(...)
    response = adapter.complete(
        task="Summarize this contract",
        messages=[{"role": "user", "content": "..."}],
        model="gpt-4o"
    )
"""


class OpenAIRawAdapter:
    """Thin wrapper around raw OpenAI/Anthropic API calls with LearnKit memory.

    Not yet implemented — this stub establishes the integration contract.
    """

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance
        raise NotImplementedError(
            "OpenAIRawAdapter is planned for Phase 4. "
            "Use the @lk.agent decorator for direct integration."
        )

    def complete(self, task: str, messages: list, model: str = "gpt-4o", **kwargs):
        """Run a completion with LearnKit memory injection and capture."""
        raise NotImplementedError
