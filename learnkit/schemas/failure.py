"""FailureRecord — a recorded failure case, dead end, or anti-pattern.

Activates immediately (no quarantine) so agents can avoid repeating mistakes.
"""

from .base import MemoryRecord


class FailureRecord(MemoryRecord):
    type: str = "failure"

    # Expected content keys:
    #   description: str    — what failed
    #   what_to_avoid: str  — action to avoid
    #   error_message: str  — actual error if code/multiprocessing
