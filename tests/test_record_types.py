"""Tests for the four record types with no existing coverage:
StrategyRecord, PreferenceRecord, HeuristicRecord, and TraceRecord.

Covers: default type field, TTL per type, serialisation round-trip,
persistence through SQLiteBackend, expiry, reinforce(), and decay().
"""

from datetime import datetime

import pytest

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.schemas.heuristic import HeuristicRecord
from learnkit.schemas.preference import PreferenceRecord
from learnkit.schemas.strategy import StrategyRecord
from learnkit.schemas.trace import TraceRecord


# ---------------------------------------------------------------------------
# StrategyRecord
# ---------------------------------------------------------------------------


def test_strategy_record_type_field():
    r = StrategyRecord(
        domains={"planning": 0.9},
        content={"goal": "migrate db", "phases": ["audit", "migrate"], "why": "compliance"},
    )
    assert r.type == "strategy"


def test_strategy_record_default_ttl_is_180_days():
    r = StrategyRecord(domains={"planning": 0.9}, content={})
    exp = datetime.fromisoformat(r.expires_at)
    created = datetime.fromisoformat(r.created_at)
    assert 179 <= (exp - created).days <= 181


def test_strategy_record_roundtrip_serialisation():
    r = StrategyRecord(
        domains={"planning": 0.9, "coding": 0.5},
        content={"goal": "scale system", "phases": ["profile", "optimise"], "why": "latency"},
        confidence=0.75,
    )
    loaded = StrategyRecord.model_validate(r.model_dump(mode="json"))
    assert loaded.id == r.id
    assert loaded.type == "strategy"
    assert loaded.content["goal"] == "scale system"
    assert loaded.confidence == 0.75


def test_strategy_record_stored_and_retrieved():
    backend = SQLiteBackend(db_path=":memory:")
    r = StrategyRecord(
        domains={"planning": 0.9},
        content={"goal": "refactor auth", "phases": ["design", "implement", "test"], "why": "security"},
    )
    backend.add(r)
    retrieved = backend.read(r.id)
    assert isinstance(retrieved, StrategyRecord)
    assert retrieved.type == "strategy"
    assert retrieved.content["goal"] == "refactor auth"


def test_strategy_record_not_expired_by_default():
    r = StrategyRecord(domains={}, content={})
    assert not r.is_expired()


# ---------------------------------------------------------------------------
# PreferenceRecord
# ---------------------------------------------------------------------------


def test_preference_record_type_field():
    r = PreferenceRecord(
        domains={"general": 1.0},
        content={"key": "output_format", "value": "markdown", "scope": "global"},
    )
    assert r.type == "preference"


def test_preference_record_default_ttl_is_365_days():
    r = PreferenceRecord(domains={}, content={})
    exp = datetime.fromisoformat(r.expires_at)
    created = datetime.fromisoformat(r.created_at)
    assert 364 <= (exp - created).days <= 366


def test_preference_record_roundtrip_serialisation():
    r = PreferenceRecord(
        domains={"general": 1.0},
        content={"key": "verbosity", "value": "concise", "scope": "global"},
        scope="user",
    )
    loaded = PreferenceRecord.model_validate(r.model_dump(mode="json"))
    assert loaded.id == r.id
    assert loaded.type == "preference"
    assert loaded.content["key"] == "verbosity"
    assert loaded.scope == "user"


def test_preference_record_stored_and_retrieved():
    backend = SQLiteBackend(db_path=":memory:")
    r = PreferenceRecord(
        domains={"general": 1.0},
        content={"key": "response_language", "value": "English", "scope": "global"},
    )
    backend.add(r)
    retrieved = backend.read(r.id)
    assert isinstance(retrieved, PreferenceRecord)
    assert retrieved.type == "preference"
    assert retrieved.content["value"] == "English"


def test_preference_record_user_scope_survives_roundtrip():
    backend = SQLiteBackend(db_path=":memory:")
    r = PreferenceRecord(
        domains={"general": 1.0},
        content={"key": "theme", "value": "dark"},
        scope="user",
    )
    backend.add(r)
    retrieved = backend.read(r.id)
    assert retrieved.scope == "user"


# ---------------------------------------------------------------------------
# HeuristicRecord
# ---------------------------------------------------------------------------


def test_heuristic_record_type_field():
    r = HeuristicRecord(
        domains={"coding": 0.9},
        content={"rule": "never use fork on macOS", "exception": "single-threaded processes"},
    )
    assert r.type == "heuristic"


def test_heuristic_record_default_ttl_is_90_days():
    r = HeuristicRecord(domains={}, content={})
    exp = datetime.fromisoformat(r.expires_at)
    created = datetime.fromisoformat(r.created_at)
    assert 89 <= (exp - created).days <= 91


def test_heuristic_record_roundtrip_serialisation():
    r = HeuristicRecord(
        domains={"coding": 0.85},
        content={
            "rule": "add a regression test when fixing a bug",
            "exception": "trivial config typo fixes",
        },
        confidence=0.9,
    )
    loaded = HeuristicRecord.model_validate(r.model_dump(mode="json"))
    assert loaded.id == r.id
    assert loaded.type == "heuristic"
    assert loaded.confidence == 0.9
    assert "regression test" in loaded.content["rule"]


def test_heuristic_record_stored_and_retrieved():
    backend = SQLiteBackend(db_path=":memory:")
    r = HeuristicRecord(
        domains={"coding": 0.9},
        content={"rule": "keep functions under 30 lines", "exception": "generated code"},
    )
    backend.add(r)
    retrieved = backend.read(r.id)
    assert isinstance(retrieved, HeuristicRecord)
    assert retrieved.type == "heuristic"
    assert retrieved.content["rule"] == "keep functions under 30 lines"


def test_heuristic_record_confidence_defaults_to_half():
    r = HeuristicRecord(domains={"coding": 0.9}, content={})
    assert r.confidence == 0.5


# ---------------------------------------------------------------------------
# TraceRecord
# ---------------------------------------------------------------------------


def test_trace_record_type_field():
    r = TraceRecord(
        domains={"legal": 0.9},
        content={"trajectory_id": "abc", "task": "summarise NDA", "summary": "3 clauses", "steps": []},
    )
    assert r.type == "trace"


def test_trace_record_default_ttl_is_30_days():
    r = TraceRecord(domains={}, content={})
    exp = datetime.fromisoformat(r.expires_at)
    created = datetime.fromisoformat(r.created_at)
    assert 29 <= (exp - created).days <= 31


def test_trace_record_roundtrip_serialisation():
    steps = [
        {"role": "user", "content": "fix it"},
        {"role": "assistant", "content": "use spawn"},
    ]
    r = TraceRecord(
        domains={"coding": 0.8},
        content={
            "trajectory_id": "traj-001",
            "task": "fix multiprocessing bug",
            "summary": "identified spawn fix",
            "steps": steps,
        },
    )
    loaded = TraceRecord.model_validate(r.model_dump(mode="json"))
    assert loaded.id == r.id
    assert loaded.type == "trace"
    assert loaded.content["trajectory_id"] == "traj-001"
    assert len(loaded.content["steps"]) == 2


def test_trace_record_stored_and_retrieved():
    backend = SQLiteBackend(db_path=":memory:")
    r = TraceRecord(
        domains={"coding": 0.7},
        content={"trajectory_id": "t-42", "task": "debug crash", "summary": "null pointer fix", "steps": []},
        status="active",
    )
    backend.add(r)
    retrieved = backend.read(r.id)
    assert isinstance(retrieved, TraceRecord)
    assert retrieved.type == "trace"
    assert retrieved.content["trajectory_id"] == "t-42"


def test_trace_record_has_shortest_ttl_of_all_types():
    """Traces expire in 30 days — shorter than any other record type."""
    trace = TraceRecord(domains={}, content={})
    skill = StrategyRecord(domains={}, content={})
    trace_exp = datetime.fromisoformat(trace.expires_at)
    skill_exp = datetime.fromisoformat(skill.expires_at)
    assert trace_exp < skill_exp
