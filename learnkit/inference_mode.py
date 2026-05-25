"""Task 2.1 — Inference Mode.

ReaComp two-stage inference mode classification.
"""

from enum import Enum
from .schemas.base import MemoryRecord


class InferenceMode(Enum):
    PRESCRIPTIVE = "prescriptive"   # skill confidence >= 0.90 — follow closely
    GUIDED = "guided"               # skill confidence >= 0.70 — use as scaffold
    EXPLORATORY = "exploratory"     # no match — full LLM reasoning, capture trace


def determine_inference_mode(records: list[MemoryRecord]) -> InferenceMode:
    """
    ReaComp two-stage pattern:
    - High confidence → prescriptive (minimal LLM reasoning, reduced token cost)
    - Partial match → guided
    - No match → exploratory (capture trace for future distillation)
    """
    skills = [r for r in records if r.type == "skill"]
    if not skills:
        return InferenceMode.EXPLORATORY
    best = max(skills, key=lambda r: r.confidence)
    if best.confidence >= 0.90:
        return InferenceMode.PRESCRIPTIVE
    if best.confidence >= 0.70:
        return InferenceMode.GUIDED
    return InferenceMode.EXPLORATORY
