"""
LearnKit — a self-improving learning layer for tool-using AI agents.

LearnKit captures the tool-call *procedure* an agent uses to solve a task, then
replays it on exact repeats (zero planning/LLM calls) and guides sibling tasks
with a playbook — cutting planning cost while holding success.

Public surface:
    LearnKit          — main class
                        @lk.agent_learn — the agent path (tool-call capture,
                                          procedure replay, playbook guidance)
    run_react_agent   — auto-replay ReAct runner (short-circuits exact matches)
    ToolTracker       — tool-call capture instrument for the agent path
    replay_plan       — auto-execute a captured procedure (agent-path replay)
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
from .drift import DriftReport, build_golden_suite, check_drift, export_golden_suite, golden_sequence
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
from .replay import bind_args, replay_plan
from .adapters.react import (
    LLMStep,
    Observation,
    ReActResult,
    ToolCall,
    run_react_agent,
)
from .tool_tracker import ToolTracker
from .trajectory import Trajectory, TrajectoryStep

__version__ = "1.0.0"

__all__ = [
    "__version__",
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
    "ToolTracker",
    "replay_plan",
    "bind_args",
    "run_react_agent",
    "LLMStep",
    "Observation",
    "ToolCall",
    "ReActResult",
    "check_drift",
    "DriftReport",
    "golden_sequence",
    "build_golden_suite",
    "export_golden_suite",
]
