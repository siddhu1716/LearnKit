"""Raw OpenAI / Anthropic API wrapper for LearnKit.

For users who call the OpenAI or Anthropic APIs directly (without a framework),
this adapter wraps the call to inject LearnKit memory into the system prompt and
capture the response. This is the model path; there is no framework tool loop to
capture, so tool capture is off by default.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.openai_raw import OpenAIRawAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = OpenAIRawAdapter(lk, client=openai_client)

    # Instead of: client.chat.completions.create(...)
    response = adapter.complete(
        task="Summarize this contract",
        messages=[{"role": "user", "content": "..."}],
        model="gpt-4o",
    )
"""

from .base import BaseAdapter
from .registry import register_adapter


class OpenAIRawAdapter(BaseAdapter):
    """Thin wrapper around raw OpenAI-style chat calls with LearnKit memory."""

    name = "openai_raw"
    #: Raw API calls have no framework tool loop to capture by default.
    capture_tools = False

    def __init__(self, learnkit_instance, client=None, complete_fn=None, *, capture_tools=None):
        super().__init__(learnkit_instance, capture_tools=capture_tools)
        self.client = client
        self.complete_fn = complete_fn

    def complete(self, task: str, messages: list, model: str = "gpt-4o", **kwargs):
        """Run a completion with LearnKit memory injection and capture."""
        handle = self.start_run(task)
        enriched_messages = self._inject_context(messages, handle.context)

        if self.complete_fn is not None:
            result = self.complete_fn(model=model, messages=enriched_messages, **kwargs)
        elif self.client is not None:
            result = self.client.chat.completions.create(
                model=model,
                messages=enriched_messages,
                **kwargs,
            )
        else:
            raise ValueError("OpenAIRawAdapter requires either client or complete_fn")

        self.complete_run(handle, self._response_text(result))
        return result

    def _inject_context(self, messages: list, context: str) -> list:
        if not context:
            return list(messages)
        return [{"role": "system", "content": context}, *messages]

    def _response_text(self, result) -> str:
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            choices = result.get("choices") or []
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            return str(result)
        choices = getattr(result, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            return getattr(message, "content", "") if message else ""
        return str(result)


register_adapter(OpenAIRawAdapter.name, OpenAIRawAdapter)
