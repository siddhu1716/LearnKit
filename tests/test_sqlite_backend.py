"""Unit tests for LearnKit Phase 1 components."""

from datetime import datetime, timedelta, timezone

import pytest

from learnkit.backends.registry import get_backend
from learnkit.backends.sqlite import SQLiteBackend
from learnkit.composer import compose_context
from learnkit.compressor import compress_context
from learnkit.inference_mode import InferenceMode
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.failure import FailureRecord
from learnkit.schemas.skill import SkillRecord
from learnkit.trajectory import Trajectory


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
    assert (
        loaded.steps[1].reasoning
        == "CoT reasoning trace here is mandatory per ReaComp."
    )
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
    past_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
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
            },
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


def test_sqlite_memory_backend_operations():
    """Verify documented ':memory:' backend usage keeps data for the backend lifetime."""
    backend = SQLiteBackend(db_path=":memory:")
    skill = SkillRecord(
        domains={"legal": 0.9},
        task_type="contract_summarization",
        content={"steps": ["extract obligations"]},
    )

    backend.add(skill)
    results = backend.search("contract summarization", domain="legal")

    assert len(results) == 1
    assert results[0].id == skill.id


def test_update_confidence_persists_full_record(tmp_path):
    """Confidence updates must round-trip through full_record, not only SQL columns."""
    backend = SQLiteBackend(db_path=str(tmp_path / "memory.db"))
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["inspect traceback"]},
        confidence=0.8,
    )

    backend.add(skill)
    backend.update_confidence(skill.id, 0.42)

    read_rec = backend.read(skill.id)
    assert read_rec.confidence == 0.42


def test_sqlite_confidence_decay(tmp_path):
    """Verify Phase 3 maintenance: confidence decays 2 percent per week."""
    backend = SQLiteBackend(db_path=str(tmp_path / "memory.db"))
    active = SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["inspect traceback"]},
        confidence=0.5,
    )
    quarantined = SkillRecord(
        domains={"coding": 0.9},
        task_type="draft_skill",
        content={"steps": ["wait for review"]},
        confidence=0.5,
        status="quarantine",
    )

    backend.add(active)
    backend.add(quarantined)

    count = backend.decay_confidence(weeks=2)

    assert count == 1
    assert backend.read(active.id).confidence == pytest.approx(0.46)
    assert backend.read(quarantined.id).confidence == 0.5


def test_sqlite_scope_filtering(tmp_path):
    """Verify team registry records can be queried separately from user records."""
    backend = SQLiteBackend(db_path=str(tmp_path / "memory.db"))
    team_skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["team pattern"]},
        confidence=0.8,
        scope="team",
    )
    user_skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["personal pattern"]},
        confidence=0.9,
        scope="user",
    )

    backend.add(team_skill)
    backend.add(user_skill)

    team_results = backend.search("debug python error", domain="coding", scope="team")
    team_list = backend.list_by_scope("team")

    assert [r.id for r in team_results] == [team_skill.id]
    assert [r.id for r in team_list] == [team_skill.id]


def test_sqlite_replace_promote_and_stale_lifecycle(tmp_path):
    backend = SQLiteBackend(db_path=str(tmp_path / "memory.db"))
    old_quarantined = SkillRecord(
        domains={"coding": 0.9},
        task_type="draft_skill",
        content={"steps": ["draft"]},
        status="quarantine",
        created_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)).isoformat(),
    )
    expired = SkillRecord(
        domains={"coding": 0.9},
        task_type="expired_skill",
        content={"steps": ["old"]},
        expires_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)).isoformat(),
    )

    backend.add(old_quarantined)
    backend.add(expired)

    old_quarantined.content["steps"] = ["replaced"]
    backend.replace(old_quarantined)

    assert backend.read(old_quarantined.id).content["steps"] == ["replaced"]
    assert backend.promote_quarantined(min_age_hours=24) == 1
    assert backend.read(old_quarantined.id).status == "active"
    assert backend.mark_expired_stale() == 1
    assert backend.read(expired.id).status == "stale"


def test_sqlite_export_import_json(tmp_path):
    source = SQLiteBackend(db_path=str(tmp_path / "source.db"))
    record = SkillRecord(
        domains={"legal": 0.9},
        task_type="contract_summarization",
        content={"steps": ["extract obligations"]},
        confidence=0.77,
    )
    source.add(record)
    export_path = tmp_path / "export.json"

    assert source.export_json(export_path) == 1

    target = SQLiteBackend(db_path=str(tmp_path / "target.db"))
    assert target.import_json(export_path) == 1

    imported = target.read(record.id)
    assert isinstance(imported, SkillRecord)
    assert imported.task_type == "contract_summarization"
    assert imported.confidence == 0.77


def test_optional_backends_have_explicit_dependency_errors():
    for name in ("mem0", "zep", "qdrant"):
        with pytest.raises(ImportError, match=name):
            get_backend(name)


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
            content={
                "description": "fork context hanging",
                "what_to_avoid": "avoid fork on macos",
            },
        ),
        FactRecord(
            domains={"coding": 0.9},
            content={
                "statement": "macOS default start method is spawn since python 3.8",
                "source": "docs",
            },
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
    assert (
        "[Context truncated — additional records available in memory store]"
        in compressed_context
    )


def test_context_compressor_direct_use():
    text = "header\n" + "\n".join("line " + str(i) for i in range(100))

    compressed = compress_context(text, max_tokens=20, chars_per_token=4)

    assert len(compressed) <= 80
    assert compressed.startswith("header")
    assert (
        "[Context truncated — additional records available in memory store]"
        in compressed
    )


def test_sqlite_native_hybrid_search():
    def embedder(text):
        if "deadlock" in text or "spawn" in text:
            return [1.0, 0.0, 0.0]
        if "contract" in text:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    backend = SQLiteBackend(db_path=":memory:", embedder=embedder)

    target = SkillRecord(
        domains={"coding": 0.9},
        task_type="multiprocessing_fix",
        content={"steps": ["set spawn start method"]},
        confidence=0.8,
    )
    distractor = SkillRecord(
        domains={"coding": 0.9},
        task_type="contract_summary",
        content={"steps": ["extract contract terms"]},
        confidence=0.9,
    )
    backend.add(target)
    backend.add(distractor)

    # Hybrid search with pure dense similarity
    results = backend.hybrid_search("thread deadlock", alpha=1.0)
    assert len(results) >= 1
    assert results[0].id == target.id


def test_sqlite_native_hybrid_search_with_bm25_contribution():
    def embedder(text):
        if "spawn" in text:
            return [1.0, 0.0, 0.0]
        if "lock" in text:
            return [0.0, 1.0, 0.0]
        return [0.5, 0.5, 0.0]

    backend = SQLiteBackend(db_path=":memory:", embedder=embedder)

    target = SkillRecord(
        domains={"coding": 0.9},
        task_type="spawn_fix",
        content={"steps": ["use spawn"]},
        confidence=0.8,
    )
    distractor = SkillRecord(
        domains={"coding": 0.9},
        task_type="lock_fix",
        content={"steps": ["avoid lock"]},
        confidence=0.8,
    )
    backend.add(target)
    backend.add(distractor)

    results = backend.hybrid_search("spawn", alpha=0.5)
    assert len(results) == 2
    assert results[0].id == target.id
    assert results[0]._bm25_score > 0.0
    assert results[1]._bm25_score == 0.0


def test_sqlite_passes_contract(tmp_path):
    """Verify that SQLiteBackend satisfies the BaseBackend contract."""
    from tests.test_backend_contract import run_backend_contract_suite

    backend = SQLiteBackend(db_path=str(tmp_path / "contract_memory.db"))
    run_backend_contract_suite(backend, tmp_path)
