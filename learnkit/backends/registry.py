"""Registry for memory backends."""

from typing import Any
from .mem0 import Mem0Backend
from .qdrant import QdrantBackend
from .sqlite import SQLiteBackend
from .zep import ZepBackend

_BACKENDS = {
    "sqlite": SQLiteBackend,
    "mem0": Mem0Backend,
    "qdrant": QdrantBackend,
    "zep": ZepBackend,
}


def get_backend(name: str, **kwargs: Any) -> Any:
    """Get the memory backend instance by name."""
    cls = _BACKENDS.get(name.lower())
    if cls is None:
        raise ValueError(f"Backend '{name}' is not registered. Available: {list(_BACKENDS.keys())}")
    return cls(**kwargs)
