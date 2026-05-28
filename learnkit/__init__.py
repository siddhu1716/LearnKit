"""
LearnKit — agent-agnostic self-improving memory SDK.

Public surface:
    LearnKit          — main class + @lk.agent decorator (Phase 3)
    Trajectory        — trajectory capture
    MemoryRecord      — base record type
    SkillRecord       — skill memory type
    FactRecord        — fact memory type
    FailureRecord     — failure memory type (activates immediately)
    StrategyRecord    — strategy memory type
    PreferenceRecord  — preference memory type
    TraceRecord       — execution trace memory type
    HeuristicRecord   — domain heuristic memory type
    SQLiteBackend     — default storage backend
    compose_context   — context composer (formats records → prompt block)
    seed_bundled_skills — load bundled SKILL.md + metadata.json into a backend
"""

from .backends.sqlite import SQLiteBackend
from .composer import compose_context
from .compressor import compress_context
from .core import LearnKit
from .inference_mode import InferenceMode, determine_inference_mode
from .schemas.base import MemoryRecord
from .schemas.fact import FactRecord
from .schemas.failure import FailureRecord
from .schemas.heuristic import HeuristicRecord
from .schemas.preference import PreferenceRecord
from .schemas.skill import SkillRecord
from .schemas.strategy import StrategyRecord
from .schemas.trace import TraceRecord
from .skills_loader import seed_bundled_skills
from .trajectory import Trajectory, TrajectoryStep

__all__ = [
    "LearnKit",
    "Trajectory",
    "TrajectoryStep",
    "MemoryRecord",
    "SkillRecord",
    "FactRecord",
    "FailureRecord",
    "StrategyRecord",
    "PreferenceRecord",
    "TraceRecord",
    "HeuristicRecord",
    "SQLiteBackend",
    "compose_context",
    "compress_context",
    "InferenceMode",
    "determine_inference_mode",
    "seed_bundled_skills",
]
