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
    """AutoGen-style reply wrapper that injects LearnKit context into replies."""

    def __init__(self, learnkit_instance):
        self.lk = learnkit_instance

    def register(self, agent):
        """Register LearnKit memory hooks on an AutoGen agent."""
        if not hasattr(agent, "register_reply"):
            raise TypeError("AutoGen agent must expose register_reply")
        agent.register_reply(self.wrap_reply)
        return agent

    def wrap_reply(self, reply_func):
        def wrapped(task: str, *args, **kwargs):
            run = self.lk.prepare_run(task)
            kwargs["_learnkit_context"] = run["context"]
            response = reply_func(task, *args, **kwargs)
            return self.lk.finalize_run(run, response)
        return wrapped
