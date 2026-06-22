"""Edge case tests for MemoryRecord base behaviours and backend operations
not covered by the main test suite.

Covers: reinforce() cap and side-effects, decay() status transition,
empty queries, confidence boundaries, stale filtering, quarantine timing,
list_all limit, and error paths.
"""

from datetime import datetime, timedelta, timezone

import pytest

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.skill import SkillRecord


# ---------------------------------------------------------------------------
# reinforce()
# ---------------------------------------------------------------------------


def test_reinforce_increments_reuse_count():
    r = SkillRecord(domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]})
    r.reinforce(quality=4.0)
    assert r.reuse_count == 1


def test_reinforce_called_multiple_times_accumulates_reuse_count():
    r = SkillRecord(domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]})
    for _ in range(5):
        r.reinforce(quality=4.0)
    assert r.reuse_count == 5


def test_reinforce_confidence_is_capped_at_095():
    r = SkillRecord(
        domains={"coding": 0.9},
        task_type="t",
        content={"steps": ["s"]},
        confidence=0.94,
    )
    for _ in range(20):
        r.reinforce(quality=5.0)
    assert r.confidence == pytest.approx(0.95)


def test_reinforce_sets_success_rate_on_first_call():
    r = SkillRecord(domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]})
    assert r.success_rate is None
    r.reinforce(quality=4.0)
    assert r.success_rate == pytest.approx(4.0 / 5.0)


def test_reinforce_rolls_success_rate_as_weighted_average():
    r = SkillRecord(domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]})
    r.reinforce(quality=5.0)   # success_rate = 1.0
    r.reinforce(quality=0.0)   # success_rate = 0.8 * 1.0 + 0.2 * 0.0 = 0.8
    assert r.success_rate == pytest.approx(0.8)


def test_reinforce_sets_last_reinforced_timestamp():
    r = SkillRecord(domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]})
    assert r.last_reinforced is None
    r.reinforce(quality=3.0)
    assert r.last_reinforced is not None
    # Timestamp must be parseable and recent
    ts = datetime.fromisoformat(r.last_reinforced)
    assert (datetime.now() - ts).total_seconds() < 5


# ---------------------------------------------------------------------------
# decay()
# ---------------------------------------------------------------------------


def test_decay_reduces_confidence_by_decay_rate():
    r = SkillRecord(
        domains={"coding": 0.9},
        task_type="t",
        content={"steps": ["s"]},
        confidence=0.5,
    )
    r.decay(decay_rate=0.02)
    assert r.confidence == pytest.approx(0.48)


def test_decay_does_not_go_below_zero():
    r = SkillRecord(
        domains={"coding": 0.9},
        task_type="t",
        content={"steps": ["s"]},
        confidence=0.01,
    )
    r.decay(decay_rate=0.05)
    assert r.confidence == pytest.approx(0.0)


def test_decay_below_03_threshold_sets_status_to_stale():
    r = SkillRecord(
        domains={"coding": 0.9},
        task_type="t",
        content={"steps": ["s"]},
        confidence=0.31,
    )
    r.decay(decay_rate=0.02)
    # confidence is now 0.29, which is < 0.3
    assert r.status == "stale"


def test_decay_above_threshold_preserves_active_status():
    r = SkillRecord(
        domains={"coding": 0.9},
        task_type="t",
        content={"steps": ["s"]},
        confidence=0.5,
    )
    r.decay(decay_rate=0.02)
    assert r.status == "active"


# ---------------------------------------------------------------------------
# Backend: empty / zero-result queries
# ---------------------------------------------------------------------------


def test_empty_search_query_does_not_raise():
    """Empty query falls back to non-FTS LIKE path — must not raise."""
    backend = SQLiteBackend(db_path=":memory:")
    backend.add(SkillRecord(domains={"coding": 0.9}, task_type="debug", content={"steps": ["s"]}))
    results = backend.search("")
    assert isinstance(results, list)


def test_search_with_no_matching_records_returns_empty_list():
    backend = SQLiteBackend(db_path=":memory:")
    results = backend.search("xyznonexistentquery99999")
    assert results == []


def test_read_nonexistent_id_returns_none():
    backend = SQLiteBackend(db_path=":memory:")
    assert backend.read("does-not-exist-1234") is None


# ---------------------------------------------------------------------------
# Backend: confidence boundary values
# ---------------------------------------------------------------------------


def test_confidence_zero_is_storable_and_retrievable():
    backend = SQLiteBackend(db_path=":memory:")
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="lowconf",
        content={"steps": ["s"]},
        confidence=0.0,
    )
    backend.add(skill)
    retrieved = backend.read(skill.id)
    assert retrieved.confidence == pytest.approx(0.0)


def test_confidence_one_is_storable_and_retrievable():
    backend = SQLiteBackend(db_path=":memory:")
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="highconf",
        content={"steps": ["s"]},
        confidence=1.0,
    )
    backend.add(skill)
    retrieved = backend.read(skill.id)
    assert retrieved.confidence == pytest.approx(1.0)


def test_search_excludes_records_below_min_confidence():
    backend = SQLiteBackend(db_path=":memory:")
    low = SkillRecord(
        domains={"coding": 0.9},
        task_type="lowconfskill",
        content={"steps": ["s"]},
        confidence=0.3,
    )
    backend.add(low)
    results = backend.search("lowconfskill", min_confidence=0.5)
    assert all(r.id != low.id for r in results)


# ---------------------------------------------------------------------------
# Backend: stale record filtering
# ---------------------------------------------------------------------------


def test_search_excludes_stale_records_by_default():
    backend = SQLiteBackend(db_path=":memory:")
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="stalefindme",
        content={"steps": ["s"]},
        status="stale",
    )
    backend.add(skill)
    results = backend.search("stalefindme")
    assert all(r.id != skill.id for r in results)


def test_search_includes_stale_records_when_exclude_stale_false():
    backend = SQLiteBackend(db_path=":memory:")
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="includemestale",
        content={"steps": ["s"]},
        status="stale",
    )
    backend.add(skill)
    results = backend.search("includemestale", exclude_stale=False)
    assert any(r.id == skill.id for r in results)


# ---------------------------------------------------------------------------
# Backend: quarantine promotion timing
# ---------------------------------------------------------------------------


def test_promote_quarantined_skips_records_younger_than_threshold():
    """A record created moments ago must NOT be promoted even if its status is quarantine."""
    backend = SQLiteBackend(db_path=":memory:")
    recent = SkillRecord(
        domains={"coding": 0.9},
        task_type="newdraft",
        content={"steps": ["s"]},
        status="quarantine",
        # created_at defaults to now — well within the 24-hour window
    )
    backend.add(recent)
    promoted = backend.promote_quarantined(min_age_hours=24)
    assert promoted == 0
    assert backend.read(recent.id).status == "quarantine"


def test_promote_quarantined_promotes_old_records():
    """A record created 25 hours ago must be promoted."""
    backend = SQLiteBackend(db_path=":memory:")
    old = SkillRecord(
        domains={"coding": 0.9},
        task_type="olddraft",
        content={"steps": ["s"]},
        status="quarantine",
        created_at=(
            datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)
        ).isoformat(),
    )
    backend.add(old)
    promoted = backend.promote_quarantined(min_age_hours=24)
    assert promoted == 1
    assert backend.read(old.id).status == "active"


# ---------------------------------------------------------------------------
# Backend: list_all with limit
# ---------------------------------------------------------------------------


def test_list_all_with_limit_returns_correct_count():
    backend = SQLiteBackend(db_path=":memory:")
    for i in range(5):
        backend.add(
            SkillRecord(
                domains={"coding": 0.9},
                task_type=f"skill{i}",
                content={"steps": ["s"]},
            )
        )
    results = backend.list_all(limit=3)
    assert len(results) == 3


def test_list_all_without_limit_returns_all_records():
    backend = SQLiteBackend(db_path=":memory:")
    for i in range(4):
        backend.add(
            SkillRecord(
                domains={"coding": 0.9},
                task_type=f"allskill{i}",
                content={"steps": ["s"]},
            )
        )
    results = backend.list_all()
    assert len(results) == 4


def test_list_all_is_ordered_by_created_at_ascending():
    backend = SQLiteBackend(db_path=":memory:")
    first = SkillRecord(
        domains={"coding": 0.9},
        task_type="first",
        content={"steps": ["s"]},
        created_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)).isoformat(),
    )
    second = SkillRecord(
        domains={"coding": 0.9},
        task_type="second",
        content={"steps": ["s"]},
        created_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)).isoformat(),
    )
    backend.add(second)
    backend.add(first)
    results = backend.list_all()
    assert results[0].id == first.id
    assert results[1].id == second.id


# ---------------------------------------------------------------------------
# Backend: error paths
# ---------------------------------------------------------------------------


def test_update_confidence_on_missing_id_does_not_raise():
    """Silent no-op for a non-existent record ID."""
    backend = SQLiteBackend(db_path=":memory:")
    backend.update_confidence("nonexistent-id-9999", 0.9)


def test_import_json_from_missing_path_raises(tmp_path):
    backend = SQLiteBackend(db_path=":memory:")
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(Exception):
        backend.import_json(missing)


def test_remove_nonexistent_id_does_not_raise():
    """Removing a record that was never added must be a silent no-op."""
    backend = SQLiteBackend(db_path=":memory:")
    backend.remove("nonexistent-id-0000")
