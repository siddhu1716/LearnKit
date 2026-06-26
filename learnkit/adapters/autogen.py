"""AutoGen adapter for LearnKit.

Integrates LearnKit into AutoGen (AG2 / ``pyautogen``) conversations. AutoGen
agents generate replies internally, so LearnKit does not replace generation —
it does two framework-correct things instead:

* **model path** — :meth:`inject` prepends retrieved memory to the agent's
  system message via AutoGen's ``update_system_message`` before the chat runs;
* **agent path** — wrap the callables you pass to ``register_function`` /
  ``register_for_execution`` with :meth:`wrap_tools` so each tool call is
  captured for procedure learning.

After the conversation, :meth:`finalize` records the outcome. The reply text is
extracted from an AutoGen ``ChatResult`` (``.summary`` / ``.chat_history``), a
plain string, or a dict.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.autogen import AutoGenAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = AutoGenAdapter(lk)

    handle = adapter.inject(assistant, task)
    # optional agent path: assistant.register_function({"search": adapter.wrap_tool(handle, search)})
    result = user.initiate_chat(assistant, message=task)
    adapter.finalize(handle, result)
"""

from .base import BaseAdapter
from .registry import register_adapter


class AutoGenAdapter(BaseAdapter):
    """AutoGen integration with both the model and agent learning paths."""

    name = "autogen"

    def inject(self, agent, task: str):
        """Start a run and prepend LearnKit memory to ``agent``'s system message.

        Uses AutoGen's ``update_system_message`` when available (so the change is
        applied the framework-correct way) and falls back to setting
        ``system_message`` directly. Returns the :class:`RunHandle`; pass it to
        :meth:`finalize` once the conversation produces a result.
        """
        handle = self.start_run(task)
        if handle.context:
            base = getattr(agent, "system_message", "") or ""
            merged = f"{handle.context}\n\n{base}".strip() if base else handle.context
            updater = getattr(agent, "update_system_message", None)
            if callable(updater):
                updater(merged)
            else:
                agent.system_message = merged
        if handle.tracker is not None:
            # Expose the tracker so callers can wrap tools they register.
            setattr(agent, "_learnkit_tools", handle.tracker)
        return handle

    def finalize(self, handle, result) -> str:
        """Finalize a run from an AutoGen reply (``ChatResult``, str, or dict)."""
        return self.complete_run(handle, self._reply_text(result))

    @staticmethod
    def _reply_text(result) -> str:
        """Best-effort extraction of the final reply text from an AutoGen result."""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for key in ("summary", "content", "message"):
                val = result.get(key)
                if isinstance(val, str) and val:
                    return val
            return str(result)
        # AutoGen ChatResult: prefer .summary, else last message in .chat_history.
        summary = getattr(result, "summary", None)
        if isinstance(summary, str) and summary:
            return summary
        history = getattr(result, "chat_history", None)
        if isinstance(history, list) and history:
            last = history[-1]
            if isinstance(last, dict):
                content = last.get("content")
                if isinstance(content, str):
                    return content
            content = getattr(last, "content", None)
            if isinstance(content, str):
                return content
        content = getattr(result, "content", None)
        if isinstance(content, str):
            return content
        return str(result)


register_adapter(AutoGenAdapter.name, AutoGenAdapter)
