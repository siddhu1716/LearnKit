"""AutoGen reply_func adapter for LearnKit.

Integrates LearnKit into AutoGen multi-agent conversations via the
``register_reply`` mechanism. Each wrapped reply retrieves memory, injects it
via the ``_learnkit_context`` keyword, and finalizes the run on the reply's
output. When tool capture is enabled the agent path is armed too, so AutoGen
tool/function calls can be captured for procedure learning by wrapping them with
:meth:`wrap_tool`.

Usage::

    from learnkit import LearnKit
    from learnkit.adapters.autogen import AutoGenAdapter

    lk = LearnKit(memory_backend="sqlite")
    adapter = AutoGenAdapter(lk)
    adapter.register(autogen_agent)
"""

from .base import BaseAdapter
from .registry import register_adapter


class AutoGenAdapter(BaseAdapter):
    """AutoGen integration with both the model and agent learning paths."""

    name = "autogen"

    def register(self, agent):
        """Register LearnKit memory hooks on an AutoGen agent."""
        if not hasattr(agent, "register_reply"):
            raise TypeError("AutoGen agent must expose register_reply")
        agent.register_reply(self.wrap_reply)
        return agent

    def wrap_reply(self, reply_func):
        """Wrap an AutoGen reply function with the LearnKit memory loop."""

        def wrapped(task: str, *args, **kwargs):
            handle = self.start_run(task)
            kwargs["_learnkit_context"] = handle.context
            if handle.tracker is not None:
                kwargs["_learnkit_tools"] = handle.tracker
            response = reply_func(task, *args, **kwargs)
            return self.complete_run(handle, response)

        return wrapped


register_adapter(AutoGenAdapter.name, AutoGenAdapter)
