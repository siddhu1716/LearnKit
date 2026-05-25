"""PreferenceRecord — explicit user-defined styling, formatting, or behavioral preferences."""

from .base import MemoryRecord


class PreferenceRecord(MemoryRecord):
    type: str = "preference"

    # Expected content keys:
    #   key: str      — setting or style variable name
    #   value: str    — preference value
    #   scope: str    — global/local scope
