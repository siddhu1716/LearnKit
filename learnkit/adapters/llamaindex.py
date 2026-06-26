"""LlamaIndex adapter for LearnKit.

Integrates LearnKit into LlamaIndex agents (``ReActAgent`` / ``FunctionAgent``)
and query engines:

* **model path** — :meth:`inject` returns the retrieved memory text to prepend
  to the agent's ``system_prompt``;
* **agent path** — attach :meth:`callback_handler` (a real, import-guarded
  LlamaIndex ``BaseCallbackHandler``) to the agent's ``CallbackManager`` so each
  ``FUNCTION_CALL`` event is captured, or wrap tool callables with
  :meth:`wrap_tools`.

After the run, :meth:`finalize` records the outcome, extracting text from a
LlamaIndex ``AgentChatResponse`` / ``Response`` (``.response``), a string, or a
dict.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.llamaindex import LlamaIndexAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = LlamaIndexAdapter(lk)

    handle = adapter.start_run(task)
    cb = adapter.callback_handler(handle)
    agent = ReActAgent.from_tools(tools, llm=llm,
                                  callback_manager=CallbackManager([cb]),
                                  system_prompt=adapter.inject(handle))
    resp = agent.chat(task)
    adapter.finalize(handle, resp)
"""

from .base import BaseAdapter, RunHandle
from .registry import register_adapter

try:  # LlamaIndex is an optional dependency (``learnkit[llamaindex]``).
    from llama_index.core.callbacks.base_handler import BaseCallbackHandler as _LIBaseHandler
    from llama_index.core.callbacks.schema import CBEventType

    LLAMAINDEX_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when llamaindex is absent
    _LIBaseHandler = object
    CBEventType = None
    LLAMAINDEX_AVAILABLE = False

#: The LlamaIndex event type string for tool/function calls.
_FUNCTION_CALL = getattr(CBEventType, "FUNCTION_CALL", "function_call")


class LearnKitLlamaHandler(_LIBaseHandler):
    """A LlamaIndex callback handler that captures the agent's tool calls.

    Records each ``FUNCTION_CALL`` event onto the :class:`RunHandle`'s tracker.
    The capture logic is independent of LlamaIndex, so it is unit-testable even
    when the package is not installed; it subclasses LlamaIndex's real
    ``BaseCallbackHandler`` only when available.
    """

    llamaindex_available: bool = LLAMAINDEX_AVAILABLE

    def __init__(self, handle: RunHandle):
        if LLAMAINDEX_AVAILABLE:
            super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.handle = handle
        self._pending: dict = {}

    # BaseCallbackHandler abstract surface ------------------------------------
    def start_trace(self, trace_id=None):  # pragma: no cover - trivial
        pass

    def end_trace(self, trace_id=None, trace_map=None):  # pragma: no cover - trivial
        pass

    def on_event_start(self, event_type, payload=None, event_id="", parent_id="", **kwargs):
        if str(getattr(event_type, "value", event_type)) == str(
            getattr(_FUNCTION_CALL, "value", _FUNCTION_CALL)
        ):
            self._pending[event_id] = payload or {}
        return event_id

    def on_event_end(self, event_type, payload=None, event_id="", **kwargs):
        if str(getattr(event_type, "value", event_type)) != str(
            getattr(_FUNCTION_CALL, "value", _FUNCTION_CALL)
        ):
            return
        tracker = self.handle.tracker
        if tracker is None:
            return
        start = self._pending.pop(event_id, {})
        name = (start or {}).get("tool") or (payload or {}).get("tool") or "tool"
        # LlamaIndex tool payloads expose the tool's metadata; use its name.
        name = getattr(name, "name", name)
        tool_input = (start or {}).get("function_call") or (start or {}).get("input")
        output = (payload or {}).get("function_call_response") or (payload or {}).get("output")
        tracker.record(str(name), tool_input, output, success=True)


class LlamaIndexAdapter(BaseAdapter):
    """LlamaIndex integration with both the model and agent learning paths."""

    name = "llamaindex"

    def inject(self, handle: RunHandle, base_prompt: str = "") -> str:
        """Return a system prompt combining LearnKit memory with ``base_prompt``."""
        if not handle.context:
            return base_prompt
        return f"{handle.context}\n\n{base_prompt}".strip() if base_prompt else handle.context

    def callback_handler(self, handle: RunHandle) -> LearnKitLlamaHandler:
        """Build a LlamaIndex callback handler that captures tool calls for ``handle``."""
        return LearnKitLlamaHandler(handle)

    def finalize(self, handle, response) -> str:
        """Finalize a run from a LlamaIndex response (``Response``, str, or dict)."""
        return self.complete_run(handle, self._response_text(response))

    @staticmethod
    def _response_text(response) -> str:
        """Best-effort extraction of the final text from a LlamaIndex response."""
        if response is None:
            return ""
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            val = response.get("response") or response.get("output")
            return val if isinstance(val, str) and val else str(response)
        # AgentChatResponse / Response expose .response (str).
        text = getattr(response, "response", None)
        if isinstance(text, str) and text:
            return text
        return str(response)


register_adapter(LlamaIndexAdapter.name, LlamaIndexAdapter)
