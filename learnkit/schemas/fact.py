"""FactRecord — a verified factual statement extracted from an execution trace."""

from .base import MemoryRecord


class FactRecord(MemoryRecord):
    type: str = "fact"

    # Expected content keys:
    #   statement: str   — the fact itself
    #   source: str      — where it came from ("agent trace", "user", etc.)
    #   verified: bool   — whether manually confirmed
