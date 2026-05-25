"""Unit tests for LearnKit Phase 1 components."""

import os
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from learnkit.trajectory import Trajectory
from learnkit.schemas.base import MemoryRecord
from learnkit.schemas.skill import SkillRecord
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.failure import FailureRecord
from learnkit.backends.sqlite import SQLiteBackend
from learnkit.composer import compose_context
from learnkit.inference_mode import InferenceMode


def test_trajectory_roundtrip(tmp_path):
    """Verify Task 1.2: Trajectory can save and load cleanly with CoT reasoning."""
    t = Trajectory(task="Multiprocessing debug")
    t.add_step(
        role="user",
        content="Fix python multiprocessing pool error",
    )
    t.add_step(
        role="assistant",
        content="Use spawn start method",
        reasoning="CoT reasoning trace here is mandatory per ReaComp.",
    )
    
    file_path = tmp_path / "trajectory.jsonl"
    t.save(file_path)
    
    loaded = Trajectory.load(file_path)
    assert loaded.task == "Multiprocessing debug"
    assert len(loaded.steps) == 2
    assert loaded.steps[1].reasoning == "CoT reasoning trace here is mandatory per ReaComp."
    assert loaded.steps[0].role == "user"


def test_memory_record_expiration():
    """Verify Task 1.3: expires_at defaults and is_expired function."""
    # Default expires_at auto-populated (e.g. 180 days for skill)
    rec = SkillRecord(
        domains={"coding": 1.0},
        task_type="debug_multiprocessing",
        content={"steps": ["Use spawn"]},
    )
    assert rec.expires_at is not None
    assert not rec.is_expired()

    # Explicit past expiration
    past_date = datetime.utcnow() - timedelta(days=1)
    rec_expired = SkillRecord(
        domains={"coding": 1.0},
        task_type="debug_multiprocessing",
        content={"steps": ["Use spawn"]},
        expires_at=past_date.isoformat(),
    )
    assert rec_expired.is_expired()


def test_skill_to_md():
    """Verify SkillRecord to_skill_md returns non-empty structured markdown."""
    rec = SkillRecord(
        domains={"coding": 0.9, "ops": 0.5},
        task_type="debug_python_error",
        content={
            "steps": ["Step one to try", "Step two to check"],
            "tools_used": ["pytest", "pdb"],
            "constraints": ["Keep logs minimal"],
            "failure_modes": ["Using fork on macOS"],
            "examples": {
                "good": "Use spawn",
                "bad": "Use fork",
            }
        },
    )
    md = rec.to_skill_md()
    assert "# debug_python_error" in md
    assert "Use spawn" in md
    assert "Using fork on macOS" in md
    assert "Tools used" in md


def test_sqlite_backend_operations(tmp_path):
    """Verify Task 1.4: SQLite Backend add, read, search, list, remove."""
    db_file = str(tmp_path / "memory.db")
    backend = SQLiteBackend(db_path=db_file)

    # Add a SkillRecord
    skill = SkillRecord(
        domains={"legal": 0.9, "compliance": 0.8},
        task_type="nda_review",
        content={
            "steps": ["Review indemnification limit", "Check governing law"],
            "tools_used": ["pdf_extractor"],
        },
        confidence=0.85,
    )
    skill_id = backend.add(skill)
    assert skill_id == skill.id

    # Read back and ensure subclass type is preserved
    read_rec = backend.read(skill_id)
    assert isinstance(read_rec, SkillRecord)
    assert read_rec.task_type == "nda_review"
    assert read_rec.confidence == 0.85
    assert read_rec.content["tools_used"] == ["pdf_extractor"]

    # FTS5 / Search
    search_res = backend.search("indemnification limit", domain="legal")
    assert len(search_res) == 1
    assert search_res[0].id == skill.id

    # List by domain
    list_res = backend.list_by_domain("legal")
    assert len(list_res) == 1
    assert list_res[0].id == skill.id

    # Remove and confirm gone
    backend.remove(skill_id)
    assert backend.read(skill_id) is None


def test_context_composer():
    """Verify Task 1.5: Context Composer formats typed records and obeys hard token limit."""
    # Compose with various record types
    records = [
        SkillRecord(
            domains={"coding": 0.9},
            task_type="multiprocessing_fix",
            content={"steps": ["Check start method"], "tools_used": ["sys"]},
            confidence=0.95,
            reuse_count=4,
        ),
        FailureRecord(
            domains={"coding": 0.9},
            content={"description": "fork context hanging", "what_to_avoid": "avoid fork on macos"},
        ),
        FactRecord(
            domains={"coding": 0.9},
            content={"statement": "macOS default start method is spawn since python 3.8", "source": "docs"},
        ),
    ]

    context = compose_context(
        records=records,
        task="fix hang in python multiprocess pool",
        inference_mode=InferenceMode.PRESCRIPTIVE,
    )

    assert "=== LearnKit Context [prescriptive mode] ===" in context
    assert "SKILL — multiprocessing_fix" in context
    assert "KNOWN FAILURE in this domain" in context
    assert "FACT (verified docs)" in context
    assert "=== End Context ===" in context

    # Test compression limit: Create 10 massive skills to exceed 4800 characters
    many_records = []
    for i in range(15):
        many_records.append(
            SkillRecord(
                domains={"coding": 0.9},
                task_type=f"massive_skill_{i}",
                content={"steps": ["Step extremely long " * 40]},
                confidence=0.8,
            )
        )
    
    compressed_context = compose_context(
        records=many_records,
        task="some general task",
        inference_mode=InferenceMode.GUIDED,
    )
    
    assert len(compressed_context) <= 4800
    assert "[Context truncated — additional records available in memory store]" in compressed_context
