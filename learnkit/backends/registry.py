"""Registry for memory backends."""

from typing import Any
from .sqlite import SQLiteBackend

_BACKENDS = {
    "sqlite": SQLiteBackend,
}


def get_backend(name: str, **kwargs: Any) -> Any:
    """Get the memory backend instance by name."""
    cls = _BACKENDS.get(name.lower())
    if cls is None:
        raise ValueError(f"Backend '{name}' is not registered. Available: {list(_BACKENDS.keys())}")
    return cls(**kwargs)
