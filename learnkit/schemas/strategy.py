"""StrategyRecord — high-level planning strategies or reasoning pathways."""

from .base import MemoryRecord


class StrategyRecord(MemoryRecord):
    type: str = "strategy"

    # Expected content keys:
    #   goal: str            — high-level goal
    #   phases: list[str]    — structured execution phases
    #   why: str             — reasoning behind strategy
