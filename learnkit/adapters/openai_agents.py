"""OpenAI Agents SDK adapter for LearnKit.

Integrates LearnKit into the OpenAI Agents SDK (``openai-agents``):

* **model path** — :meth:`inject` returns instructions combining LearnKit memory
  with the agent's base instructions;
* **agent path** — pass :meth:`run_hooks` (a real, import-guarded ``RunHooks``)
  to ``Runner.run(...)`` so each ``on_tool_start`` / ``on_tool_end`` is captured
  for procedure learning, or wrap tool callables with :meth:`wrap_tools`.

After the run, :meth:`finalize` records the outcome, extracting text from a
``RunResult`` (``.final_output``), a string, or a dict.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.openai_agents import OpenAIAgentsAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = OpenAIAgentsAdapter(lk)

    handle = adapter.start_run(task)
    agent = Agent(name="assistant",
                  instructions=adapter.inject(handle, base_instructions),
                  tools=tools)
    result = await Runner.run(agent, task, hooks=adapter.run_hooks(handle))
    adapter.finalize(handle, result)
"""

from .base import BaseAdapter, RunHandle
from .registry import register_adapter

try:  # OpenAI Agents SDK is optional (``learnkit[openai-agents]``).
    from agents.lifecycle import RunHooks as _AgentsRunHooks

    OPENAI_AGENTS_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when the SDK is absent
    _AgentsRunHooks = object
    OPENAI_AGENTS_AVAILABLE = False


class LearnKitRunHooks(_AgentsRunHooks):
    """Run hooks that capture the agent's tool calls into a :class:`RunHandle`.

    Records each ``on_tool_start`` / ``on_tool_end`` pair onto the handle's
    tracker. The capture logic does not depend on the SDK, so it is unit-testable
    even when ``openai-agents`` is not installed; it subclasses the SDK's
    ``RunHooks`` only when available.
    """

    openai_agents_available: bool = OPENAI_AGENTS_AVAILABLE

    def __init__(self, handle: RunHandle):
        if OPENAI_AGENTS_AVAILABLE:
            super().__init__()
        self.handle = handle
        self._pending: dict = {}

    @staticmethod
    def _tool_name(tool) -> str:
        return str(getattr(tool, "name", None) or getattr(tool, "__name__", None) or "tool")

    async def on_tool_start(self, context, agent, tool):
        self._pending[self._tool_name(tool)] = True

    async def on_tool_end(self, context, agent, tool, result):
        tracker = self.handle.tracker
        if tracker is None:
            return
        name = self._tool_name(tool)
        self._pending.pop(name, None)
        tracker.record(name, None, result, success=True)


class OpenAIAgentsAdapter(BaseAdapter):
    """OpenAI Agents SDK integration with both learning paths."""

    name = "openai_agents"

    def inject(self, handle: RunHandle, base_instructions: str = "") -> str:
        """Return agent instructions combining LearnKit memory with the base."""
        if not handle.context:
            return base_instructions
        if base_instructions:
            return f"{handle.context}\n\n{base_instructions}".strip()
        return handle.context

    def run_hooks(self, handle: RunHandle) -> LearnKitRunHooks:
        """Build ``RunHooks`` that capture tool calls for ``handle``."""
        return LearnKitRunHooks(handle)

    def finalize(self, handle, result) -> str:
        """Finalize a run from a ``RunResult`` (or str / dict)."""
        return self.complete_run(handle, self._result_text(result))

    @staticmethod
    def _result_text(result) -> str:
        """Best-effort extraction of the final text from a RunResult."""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            val = result.get("final_output") or result.get("output")
            return val if isinstance(val, str) and val else str(result)
        final = getattr(result, "final_output", None)
        if isinstance(final, str) and final:
            return final
        return str(result)


register_adapter(OpenAIAgentsAdapter.name, OpenAIAgentsAdapter)
