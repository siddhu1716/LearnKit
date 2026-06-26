"""Framework adapters for integrating LearnKit with any agent framework.

LearnKit ships adapters for a few popular frameworks, but the architecture is
pluggable: any open-source package can register its own adapter — either
in-process via :func:`register_adapter` / :func:`adapter`, or as an installed
package via a ``learnkit.adapters`` entry point. Use :func:`get_adapter` /
:func:`available_adapters` to resolve adapters by name, including third-party
plugins discovered lazily.

Every adapter subclasses :class:`BaseAdapter`, so all of them expose the same
two-path contract (``start_run`` / ``complete_run``) and get both the model and
agent learning paths for free.
"""

from .base import BaseAdapter, RunHandle
from .registry import (
    adapter,
    available_adapters,
    get_adapter,
    register_adapter,
)
from .autogen import AutoGenAdapter
from .crewai import CrewAIAdapter
from .langchain import LangChainAdapter, LearnKitCallbackHandler
from .langgraph import LangGraphAdapter
from .llamaindex import LlamaIndexAdapter, LearnKitLlamaHandler
from .openai_agents import OpenAIAgentsAdapter, LearnKitRunHooks
from .openai_raw import OpenAIRawAdapter

__all__ = [
    # Base contract
    "BaseAdapter",
    "RunHandle",
    # Registry / plugin discovery
    "register_adapter",
    "adapter",
    "get_adapter",
    "available_adapters",
    # Built-in adapters
    "LangChainAdapter",
    "LearnKitCallbackHandler",
    "LangGraphAdapter",
    "AutoGenAdapter",
    "CrewAIAdapter",
    "LlamaIndexAdapter",
    "LearnKitLlamaHandler",
    "OpenAIAgentsAdapter",
    "LearnKitRunHooks",
    "OpenAIRawAdapter",
]
