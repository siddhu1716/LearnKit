"""Tests for the generality gate and harmful-hits demotion in memory_quality."""

from __future__ import annotations

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.memory_quality import (
    HARMFUL_HITS_QUARANTINE,
    decide_storage,
    demote_existing,
    is_general,
)
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.skill import SkillRecord


def _backend() -> SQLiteBackend:
    return SQLiteBackend(db_path=":memory:")


def test_is_general_passes_when_skill_describes_approach():
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="pbe_string_transformation",
        content={
            "steps": [
                "identify the minimal encompassing substitution rather than overlapping replacements",
                "verify the candidate program reproduces every example input output pair",
            ]
        },
    )
    task = "Solve a programming-by-example transformation where ABCDE becomes AZCDE."
    general, ratio = is_general(skill, task)
    assert general is True
    assert ratio < 0.5


def test_is_general_rejects_trace_summary_skill():
    """A skill that mostly repeats identifiers from the task is not general."""
    task = (
        "Refactor the calculate_quarterly_revenue function inside revenue_dashboard.py "
        "so it handles fiscal_year_end correctly for the Acme_Corp tenant."
    )
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="refactor",
        content={
            "steps": [
                "open calculate_quarterly_revenue inside revenue_dashboard module",
                "update fiscal_year_end branch for the Acme_Corp tenant scenario",
                "rerun calculate_quarterly_revenue tests for the Acme_Corp fixture",
            ]
        },
    )
    general, ratio = is_general(skill, task)
    assert general is False
    assert ratio >= 0.5


def test_decide_storage_blocks_non_general_skill():
    backend = _backend()
    task = (
        "Patch ProcessPoolExecutor leaks in services/worker_dispatcher for tenant_xyz "
        "by handling shutdown_handlers, restart_supervisor, and worker_recycler hooks."
    )
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="patch",
        content={
            "steps": [
                "open worker_dispatcher inside services and inspect ProcessPoolExecutor lifecycle",
                "wire shutdown_handlers and restart_supervisor for tenant_xyz workers",
                "rerun worker_recycler against tenant_xyz fixtures",
            ]
        },
    )
    decision = decide_storage(skill, backend, scope="user", task_text=task)
    assert decision.should_store is False
    assert "not general" in decision.reason


def test_decide_storage_allows_general_skill():
    backend = _backend()
    task = "Refactor a Python service for cleanup leaks."
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="patch",
        content={
            "steps": [
                "identify the resource that is not released along the failure path",
                "wrap acquisition in a context manager so cleanup runs in every branch",
                "add a regression test that asserts the resource is released after exceptions",
            ]
        },
    )
    decision = decide_storage(skill, backend, scope="user", task_text=task)
    assert decision.should_store is True


def test_decide_storage_does_not_apply_generality_to_facts():
    """Facts are allowed to be specific — generality gate must not block them."""
    backend = _backend()
    task = "Note that the AcmeCorpAPI rate limit is 100 requests per minute."
    fact = FactRecord(
        domains={"docs": 0.9},
        content={"statement": "AcmeCorpAPI enforces 100 requests per minute rate limit"},
    )
    decision = decide_storage(fact, backend, scope="user", task_text=task)
    assert decision.should_store is True


def test_demote_existing_quarantines_after_repeated_harm():
    backend = _backend()
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="sql_upsert",
        content={"steps": ["use INSERT ON CONFLICT for upserts"]},
        confidence=0.8,
        status="active",
    )
    backend.add(skill)

    for _ in range(HARMFUL_HITS_QUARANTINE - 1):
        demote_existing(backend, skill)
        refreshed = backend.read(skill.id)
        assert refreshed.status == "active"

    demote_existing(backend, skill)
    final = backend.read(skill.id)
    assert final.status == "quarantine"
    assert final.content.get("_harmful_hits") == HARMFUL_HITS_QUARANTINE
    assert final.confidence < skill.confidence
