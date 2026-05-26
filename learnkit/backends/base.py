"""Base class for all storage backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from ..schemas.base import MemoryRecord, MemoryType


class BaseBackend(ABC):
    """Abstract Base Class for LearnKit Memory Backends."""

    @abstractmethod
    def add(self, record: MemoryRecord) -> str:
        """Add or update a record."""
        pass

    def replace(self, record: MemoryRecord) -> str:
        """Replace a record by ID. Defaults to add/upsert semantics."""
        return self.add(record)

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

    @abstractmethod
    def promote_quarantined(self, min_age_hours: float = 24.0) -> int:
        """Promote quarantined records to active after the review window. Returns count."""
        pass

    @abstractmethod
    def mark_expired_stale(self) -> int:
        """Mark expired active records stale. Returns count."""
        pass

    @abstractmethod
    def export_json(self, path: str | Path) -> int:
        """Export all records as portable JSON. Returns count."""
        pass

    @abstractmethod
    def import_json(self, path: str | Path) -> int:
        """Import records from portable JSON. Returns count."""
        pass
