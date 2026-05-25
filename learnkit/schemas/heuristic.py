"""HeuristicRecord — domain-specific rules-of-thumb or implicit boundaries."""

from .base import MemoryRecord


class HeuristicRecord(MemoryRecord):
    type: str = "heuristic"

    # Expected content keys:
    #   rule: str         — the domain rule or guideline
    #   exception: str    — when this rule does not apply
