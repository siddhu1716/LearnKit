"""Base class for all storage backends."""

from abc import ABC, abstractmethod
from typing import Optional
from ..schemas.base import MemoryRecord, MemoryType


class BaseBackend(ABC):
    """Abstract Base Class for LearnKit Memory Backends."""

    @abstractmethod
    def add(self, record: MemoryRecord) -> str:
        """Add or update a record."""
        pass

    @abstractmethod
    def read(self, id: str) -> Optional[MemoryRecord]:
        """Read a record by ID."""
        pass

    @abstractmethod
    def remove(self, id: str) -> None:
        """Remove a record by ID."""
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        scope: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True
    ) -> list[MemoryRecord]:
        """Search records."""
        pass

    @abstractmethod
    def list_by_domain(self, domain: str, limit: int = 20) -> list[MemoryRecord]:
        """List active records for a given domain, ordered by confidence."""
        pass

    @abstractmethod
    def list_by_scope(self, scope: str = "team", limit: int = 20) -> list[MemoryRecord]:
        """List active records for a given scope, ordered by confidence."""
        pass

    @abstractmethod
    def update_confidence(self, id: str, new_confidence: float) -> None:
        """Update a record's confidence score."""
        pass

    @abstractmethod
    def decay_confidence(self, weeks: int = 1, decay_rate: float = 0.02) -> int:
        """Apply weekly confidence decay to active/stale records. Returns count of decayed records."""
        pass
