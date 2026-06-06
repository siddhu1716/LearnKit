"""Tests for the bundled skills loader (MVP — Hermes skills/ directory pattern)."""

from pathlib import Path

import pytest

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.skills_loader import seed_bundled_skills


def test_seed_bundled_skills_loads_all_starter_skills():
    """seed_bundled_skills should load all bundled starter skills into the backend."""
    backend = SQLiteBackend(db_path=":memory:")
    count = seed_bundled_skills(backend)

    assert count == 9, f"Expected 9 starter skills, got {count}"
    results = backend.list_all()
    task_types = {r.task_type for r in results}
    # Original skills
    assert "contract_summarization" in task_types
    assert "debug_python_error" in task_types
    # New coding skills
    assert "write_unit_test" in task_types
    assert "code_review_checklist" in task_types
    assert "refactor_for_readability" in task_types
    # New legal skills
    assert "gdpr_clause_check" in task_types
    assert "liability_clause_extraction" in task_types
    # New general skills
    assert "api_integration_debugging" in task_types
    assert "data_cleaning_pipeline" in task_types


def test_seed_bundled_skills_is_idempotent():
    """Calling seed twice should not duplicate records (overwrite=False default)."""
    backend = SQLiteBackend(db_path=":memory:")
    seed_bundled_skills(backend)
    count_second = seed_bundled_skills(backend)

    assert count_second == 0, "Second seed should skip already-present records"
    assert len(backend.list_all()) == 9


def test_seed_bundled_skills_overwrite_replaces():
    """overwrite=True should replace existing records."""
    backend = SQLiteBackend(db_path=":memory:")
    seed_bundled_skills(backend)
    count = seed_bundled_skills(backend, overwrite=True)
    assert count == 9


def test_seed_bundled_skills_records_are_active_with_correct_schema():
    """Seeded skills must be status=active with correct domains and content."""
    backend = SQLiteBackend(db_path=":memory:")
    seed_bundled_skills(backend)

    contract_results = backend.search("contract summarization", domain="legal")
    assert len(contract_results) >= 1
    record = contract_results[0]
    assert record.status == "active"
    assert "legal" in record.domains
    assert "steps" in record.content
    assert len(record.content["steps"]) > 0
    # SKILL.md text should be embedded
    assert "skill_md" in record.content


def test_seed_bundled_skills_handles_missing_dir_gracefully():
    """Should return 0 and not raise if the skills dir doesn't exist."""
    backend = SQLiteBackend(db_path=":memory:")
    count = seed_bundled_skills(backend, skills_dir=Path("/nonexistent/skills"))
    assert count == 0
