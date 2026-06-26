"""CrewAI adapter for LearnKit.

Integrates LearnKit into CrewAI crews. CrewAI agents run their own reasoning
loop, so LearnKit injects memory and observes tool usage rather than driving the
loop:

* **model path** — :meth:`inject` returns the retrieved memory text to prepend
  to an agent's ``backstory`` or a task's ``description``;
* **agent path** — pass :meth:`step_callback` as the crew's ``step_callback`` so
  each ``AgentAction`` (tool call) is captured for procedure learning, or wrap
  tool callables directly with :meth:`wrap_tools`.

After ``crew.kickoff()``, :meth:`finalize` records the outcome, extracting text
from a CrewAI ``CrewOutput`` (``.raw``), a string, or a dict.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.crewai import CrewAIAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = CrewAIAdapter(lk)

    handle = adapter.inject_into(agent, task_text)        # prepend memory to backstory
    crew = Crew(agents=[agent], tasks=[task],
                step_callback=adapter.step_callback(handle))
    result = crew.kickoff()
    adapter.finalize(handle, result)
"""

from .base import BaseAdapter
from .registry import register_adapter


class CrewAIAdapter(BaseAdapter):
    """CrewAI integration with both the model and agent learning paths."""

    name = "crewai"

    def inject_into(self, agent, task: str, attr: str = "backstory"):
        """Start a run and prepend LearnKit memory to ``agent.<attr>``.

        ``attr`` defaults to ``backstory`` (the CrewAI agent field most agents
        condition on); pass ``"goal"`` or another field as needed. Returns the
        :class:`RunHandle`.
        """
        handle = self.start_run(task)
        if handle.context:
            base = getattr(agent, attr, "") or ""
            merged = f"{handle.context}\n\n{base}".strip() if base else handle.context
            setattr(agent, attr, merged)
        return handle

    def step_callback(self, handle):
        """Return a CrewAI ``step_callback`` that records tool calls on ``handle``.

        CrewAI calls the step callback with an ``AgentAction`` (tool, tool_input,
        result) or an ``AgentFinish``. Only tool actions are recorded; finishes
        and malformed steps are ignored.
        """
        def callback(step):
            tracker = handle.tracker
            if tracker is None:
                return
            tool = getattr(step, "tool", None)
            if not tool:
                return
            tool_input = getattr(step, "tool_input", None)
            output = getattr(step, "result", None)
            if output is None:
                output = getattr(step, "text", None)
            tracker.record(str(tool), tool_input, output, success=True)

        return callback

    def finalize(self, handle, result) -> str:
        """Finalize a run from a CrewAI result (``CrewOutput``, str, or dict)."""
        return self.complete_run(handle, self._output_text(result))

    @staticmethod
    def _output_text(result) -> str:
        """Best-effort extraction of the final text from a CrewAI result."""
        if result is None:
            return ""
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            for key in ("raw", "output", "result"):
                val = result.get(key)
                if isinstance(val, str) and val:
                    return val
            return str(result)
        # CrewOutput exposes .raw (and .json_dict / .pydantic).
        raw = getattr(result, "raw", None)
        if isinstance(raw, str) and raw:
            return raw
        return str(result)


register_adapter(CrewAIAdapter.name, CrewAIAdapter)
