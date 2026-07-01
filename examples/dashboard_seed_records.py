"""Dashboard records seeder — populates Memory Explorer + Top Skills + Overview
counts when no Anthropic/Gemini judge+distiller key is available.

The main `dashboard_seed_multi.py` produces real run telemetry by calling the
self-hosted models, but distillation requires an LLM call (judge -> distiller).
On a key-less host that call fails and the memory store stays empty, leaving
Memory Overview, Memory Explorer, and Top Performing Skills blank.

This script writes typed records (skill, fact, failure, strategy, preference,
heuristic, trace) **directly** through the SQLite backend, modeled after what
the distiller would have produced for the seeded tasks. They're tagged to the
same agents that already have run telemetry, so every dashboard page lines up
end-to-end.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import learnkit as lk  # noqa: E402
from learnkit.schemas.skill import SkillRecord  # noqa: E402
from learnkit.schemas.fact import FactRecord  # noqa: E402
from learnkit.schemas.failure import FailureRecord  # noqa: E402
from learnkit.schemas.strategy import StrategyRecord  # noqa: E402
from learnkit.schemas.preference import PreferenceRecord  # noqa: E402
from learnkit.schemas.heuristic import HeuristicRecord  # noqa: E402
from learnkit.schemas.trace import TraceRecord  # noqa: E402


DB_PATH = os.environ.get("LEARNKIT_DB_PATH") or str(Path.home() / ".learnkit" / "memory.db")


def _agent_ids() -> list[tuple[str, str]]:
    """Read the (agent_id, agent_name) pairs that already exist in `runs`."""
    if not Path(DB_PATH).exists():
        print(f"[seed_records] no DB at {DB_PATH} — run dashboard_seed_multi.py first")
        return []
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    rows = list(
        c.execute(
            "SELECT DISTINCT agent_id, agent_name FROM runs ORDER BY agent_name"
        )
    )
    c.close()
    return [(r["agent_id"], r["agent_name"]) for r in rows]


# Templates indexed by ordinal — keep dashboard varied across agents.
SKILL_TEMPLATES = [
    {
        "task_type": "asyncio_exception_handling",
        "trigger": "When wiring asyncio.gather() across multiple awaitables",
        "steps": [
            "Call asyncio.gather(*tasks) with return_exceptions=True when you need every result",
            "Inspect each returned item with isinstance(item, BaseException) before using it",
            "Re-raise or log selectively — never let an exception object flow into business logic",
        ],
        "tools_used": ["asyncio.gather", "asyncio.create_task"],
        "constraints": [
            "return_exceptions=False (default) re-raises the FIRST exception and cancels siblings",
        ],
        "failure_modes": [
            "Silently treating an exception object as a result and crashing downstream",
        ],
    },
    {
        "task_type": "multiprocessing_macos_start_method",
        "trigger": "When multiprocessing.Pool().map() hangs on macOS Python 3.12+",
        "steps": [
            "Call multiprocessing.set_start_method('spawn', force=True) at program entry",
            "Guard the entry point with `if __name__ == '__main__':` to avoid recursive spawns",
            "Verify with mp.get_start_method() before allocating the Pool",
        ],
        "tools_used": ["multiprocessing.Pool", "multiprocessing.set_start_method"],
        "constraints": [
            "macOS default 'fork' is incompatible with Objective-C frameworks loaded by Python 3.8+",
        ],
        "failure_modes": [
            "Hangs with no traceback when the child inherits an Objective-C runtime fork",
        ],
    },
]


FACT_TEMPLATES = [
    {
        "statement": "asyncio.gather(*, return_exceptions=False) cancels sibling tasks on first exception",
        "source": "agent trace",
        "verified": True,
    },
    {
        "statement": "macOS Python 3.8+ defaults multiprocessing to 'spawn' for the GUI process group but child Pools still inherit 'fork' unless set explicitly",
        "source": "agent trace",
        "verified": True,
    },
]


FAILURE_TEMPLATES = [
    {
        "description": "Treated asyncio.gather result as a list of values without checking for BaseException instances",
        "what_to_avoid": "Iterating gather(return_exceptions=True) results without isinstance(item, BaseException) guard",
        "error_message": "AttributeError: 'TimeoutError' object has no attribute 'json'",
    },
    {
        "description": "Called multiprocessing.Pool() at import time without `if __name__ == '__main__':` guard",
        "what_to_avoid": "Module-level Pool() construction on macOS — it recursively spawns the parent",
        "error_message": "Hang with no traceback; main process pegs one CPU at 100%",
    },
]


STRATEGY_TEMPLATES = [
    {
        "name": "Prefer return_exceptions=True for fire-and-forget gathers",
        "rationale": "Lets the caller decide which failures are fatal instead of cancelling siblings reflexively",
    },
]


PREFERENCE_TEMPLATES = [
    {
        "name": "Always pin multiprocessing start method on macOS",
        "value": "spawn",
        "rationale": "fork is unsafe under any Objective-C framework loaded in the parent",
    },
]


HEURISTIC_TEMPLATES = [
    {
        "rule": "If an asyncio task hangs > 30s and no logs appear, suspect a cancelled-but-awaited gather sibling",
        "confidence": 0.7,
    },
]


TRACE_TEMPLATES = [
    {
        "summary": "asyncio.gather error-handling fix: switched to return_exceptions=True + per-item isinstance check",
        "outcome": "success",
    },
]


def _domain_vector() -> dict[str, float]:
    return {"coding": 0.9, "python": 0.7}


def _make_skill(idx: int, agent_name: str) -> SkillRecord:
    t = SKILL_TEMPLATES[idx % len(SKILL_TEMPLATES)]
    return SkillRecord(
        task_type=t["task_type"],
        domains=_domain_vector(),
        content={
            "steps": t["steps"],
            "tools_used": t["tools_used"],
            "constraints": t["constraints"],
            "failure_modes": t["failure_modes"],
            "trigger": t["trigger"],
            "examples": {
                "good": "results = await asyncio.gather(*tasks, return_exceptions=True); for r in results: ...",
                "bad": "results = await asyncio.gather(*tasks)  # one exception kills the batch",
            },
            "_source_agent": agent_name,
            "_quality_score": 4.2,
        },
        confidence=0.72,
        reuse_count=3,
        success_rate=0.85,
        status="active",
    )


def _make_fact(idx: int, agent_name: str) -> FactRecord:
    t = FACT_TEMPLATES[idx % len(FACT_TEMPLATES)]
    return FactRecord(
        task_type="python_runtime_fact",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=0.65,
        status="active",
    )


def _make_failure(idx: int, agent_name: str) -> FailureRecord:
    t = FAILURE_TEMPLATES[idx % len(FAILURE_TEMPLATES)]
    return FailureRecord(
        task_type="python_runtime_pitfall",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=0.6,
        status="active",
    )


def _make_strategy(agent_name: str) -> StrategyRecord:
    t = STRATEGY_TEMPLATES[0]
    return StrategyRecord(
        task_type="error_handling_strategy",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=0.6,
        status="active",
    )


def _make_preference(agent_name: str) -> PreferenceRecord:
    t = PREFERENCE_TEMPLATES[0]
    return PreferenceRecord(
        task_type="runtime_preference",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=0.7,
        status="active",
    )


def _make_heuristic(agent_name: str) -> HeuristicRecord:
    t = HEURISTIC_TEMPLATES[0]
    return HeuristicRecord(
        task_type="debugging_heuristic",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=float(t.get("confidence") or 0.6),
        status="active",
    )


def _make_trace(agent_name: str) -> TraceRecord:
    t = TRACE_TEMPLATES[0]
    return TraceRecord(
        task_type="trace_snapshot",
        domains=_domain_vector(),
        content={**t, "_source_agent": agent_name},
        confidence=0.5,
        status="active",
    )


def main() -> int:
    pairs = _agent_ids()
    if not pairs:
        return 1

    print(f"[seed_records] DB: {DB_PATH}")
    print(f"[seed_records] agents found: {[p[1] for p in pairs]}")

    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=DB_PATH,
        scope="user",
        background_postprocess=False,
        quality_threshold=1.5,
        auto_promote=True,
    )

    added = 0
    for i, (_aid, name) in enumerate(pairs):
        memory.backend.add(_make_skill(i, name))
        memory.backend.add(_make_skill(i + 1, name))
        memory.backend.add(_make_fact(i, name))
        memory.backend.add(_make_fact(i + 1, name))
        memory.backend.add(_make_failure(i, name))
        memory.backend.add(_make_strategy(name))
        memory.backend.add(_make_preference(name))
        memory.backend.add(_make_heuristic(name))
        memory.backend.add(_make_trace(name))
        added += 9

    print(f"[seed_records] inserted {added} records across {len(pairs)} agents")

    # Verify
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    print("[seed_records] type counts:")
    for r in c.execute("SELECT type, COUNT(*) AS n FROM records GROUP BY type"):
        print(f"  {r['type']:<12} -> {r['n']}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
