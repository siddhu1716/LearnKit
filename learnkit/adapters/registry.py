"""Adapter registry + plugin discovery.

LearnKit ships adapters for a few popular frameworks, but the goal is for
*any* open-source framework to be pluggable. Third parties register their own
adapter without modifying LearnKit in two ways:

1. **In-process** — call :func:`register_adapter` (or use the
   :func:`adapter` decorator) at import time.
2. **As an installed package** — declare an entry point in the
   ``learnkit.adapters`` group::

       # pyproject.toml of a third-party package
       [project.entry-points."learnkit.adapters"]
       my_framework = "my_pkg.learnkit_adapter:MyFrameworkAdapter"

   :func:`get_adapter` / :func:`available_adapters` discover these lazily.

Lookup resolves a name to a :class:`~learnkit.adapters.base.BaseAdapter`
subclass::

    from learnkit import LearnKit
    from learnkit.adapters import get_adapter

    AdapterCls = get_adapter("langchain")
    adapter = AdapterCls(LearnKit(memory_backend="sqlite"))
"""

from __future__ import annotations

from typing import Dict, List, Type

from ..logging import get_logger
from .base import BaseAdapter

logger = get_logger("adapters.registry")

_REGISTRY: Dict[str, Type[BaseAdapter]] = {}
_ENTRY_POINTS_LOADED = False
_ENTRY_POINT_GROUP = "learnkit.adapters"


def register_adapter(name: str, cls: Type[BaseAdapter]) -> Type[BaseAdapter]:
    """Register an adapter class under ``name`` (case-insensitive).

    Returns the class so it can be used as a decorator factory if desired.
    Raises ``TypeError`` if ``cls`` is not a :class:`BaseAdapter` subclass.
    """
    if not (isinstance(cls, type) and issubclass(cls, BaseAdapter)):
        raise TypeError(f"{cls!r} is not a BaseAdapter subclass")
    key = name.lower()
    existing = _REGISTRY.get(key)
    if existing is not None and existing is not cls:
        logger.warning(
            "Overriding existing LearnKit adapter",
            extra={"event": "adapter_override", "name": key},
        )
    _REGISTRY[key] = cls
    return cls


def adapter(name: str):
    """Class decorator that registers an adapter under ``name``::

    @adapter("my_framework")
    class MyFrameworkAdapter(BaseAdapter):
        name = "my_framework"
    """

    def decorator(cls: Type[BaseAdapter]) -> Type[BaseAdapter]:
        return register_adapter(name, cls)

    return decorator


def get_adapter(name: str) -> Type[BaseAdapter]:
    """Resolve ``name`` to a registered adapter class.

    Loads installed ``learnkit.adapters`` entry points on first miss. Raises
    ``KeyError`` listing the available names if unknown.
    """
    key = name.lower()
    cls = _REGISTRY.get(key)
    if cls is None:
        _load_entry_points()
        cls = _REGISTRY.get(key)
    if cls is None:
        raise KeyError(
            f"No LearnKit adapter named {name!r}. Available: {available_adapters()}"
        )
    return cls


def available_adapters() -> List[str]:
    """Return all registered adapter names (built-in + discovered plugins)."""
    _load_entry_points()
    return sorted(_REGISTRY)


def _load_entry_points() -> None:
    """Discover third-party adapters declared via the ``learnkit.adapters``
    entry-point group. Runs at most once; failures are logged, not fatal.
    """
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return
    _ENTRY_POINTS_LOADED = True

    try:
        from importlib.metadata import entry_points
    except Exception:  # pragma: no cover - importlib.metadata always present on 3.11+
        return

    try:
        eps = entry_points(group=_ENTRY_POINT_GROUP)
    except TypeError:  # pragma: no cover - very old importlib.metadata API
        eps = entry_points().get(_ENTRY_POINT_GROUP, [])  # type: ignore[attr-defined]
    except Exception as e:  # pragma: no cover - defensive
        logger.warning(
            "Failed to enumerate adapter entry points",
            extra={"event": "adapter_ep_enumerate_failed", "error": str(e)},
        )
        return

    for ep in eps:
        try:
            cls = ep.load()
            register_adapter(ep.name, cls)
        except Exception as e:
            logger.warning(
                "Failed to load adapter entry point",
                extra={"event": "adapter_ep_load_failed", "name": ep.name, "error": str(e)},
            )
