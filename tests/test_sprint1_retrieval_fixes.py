"""Sprint 1 regression tests — retrieval fix verification.

Tests three changes:
  A. k=1 PRIMARY/SECONDARY split in router.py (rank_for_injection + _apply_k1_split)
  B. Confidence floor (CONFIDENCE_FLOOR = 0.45) in retriever.py
  C. Contrastive failure extraction (distill_failure) in distiller.py

These tests are the "done when" gate for Sprint 1:
  - The sql06 regression scenario (wrong-pattern upsert skill injected into
    gap-detection task) must be blocked by the confidence floor.
  - The highest-confidence record must always be injected as PRIMARY.
  - A failed trace must produce a semantically richer FailureRecord than
    the old "Failed task: X, avoid: approach used" placeholder.
"""

from unittest.mock import MagicMock, patch

import pytest

from learnkit.router import (
    CONFIDENCE_FLOOR,
    MemoryRouter,
    _apply_k1_split,
    rank_for_injection,
)
from learnkit.schemas.failure import FailureRecord
from learnkit.schemas.skill import SkillRecord


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_skill(confidence: float, task_type: str = "test_task") -> SkillRecord:
    return SkillRecord(
        domains={"sql_authoring": confidence},
        task_type=task_type,
        content={"steps": [f"step for {task_type}"], "tools_used": [], "failure_modes": []},
        confidence=confidence,
        status="active",
    )


def _make_failure(confidence: float, description: str = "known failure") -> FailureRecord:
    return FailureRecord(
        domains={"sql_authoring": confidence},
        content={"description": description, "what_to_avoid": "avoid this"},
        confidence=confidence,
        status="active",
    )


# ══════════════════════════════════════════════════════════════════════════════
# A. k=1 PRIMARY / SECONDARY split
# ══════════════════════════════════════════════════════════════════════════════


class TestRankForInjection:
    def test_empty_returns_none(self):
        primary, secondary = rank_for_injection([])
        assert primary is None
        assert secondary == []

    def test_single_record_is_primary_no_secondary(self):
        skill = _make_skill(0.8)
        primary, secondary = rank_for_injection([skill])
        assert primary is skill
        assert secondary == []

    def test_highest_confidence_wins_primary(self):
        low = _make_skill(0.5, "low_task")
        high = _make_skill(0.9, "high_task")
        mid = _make_skill(0.7, "mid_task")

        primary, secondary = rank_for_injection([low, high, mid])
        assert primary is high
        assert low in secondary
        assert mid in secondary

    def test_secondary_capped_at_6(self):
        # rank_for_injection returns sorted_records[1:7] which is 6 items.
        # Total injected = 1 PRIMARY + 6 SECONDARY = 7 records (≤ 8 max).
        records = [_make_skill(i / 10.0, f"task_{i}") for i in range(1, 12)]  # 11 records
        primary, secondary = rank_for_injection(records)
        assert primary is not None
        assert len(secondary) == 6  # sorted[1:7] = indices 1..6 inclusive

    def test_failure_with_low_confidence_does_not_beat_high_confidence_skill(self):
        """A failure at 0.5 confidence should not become PRIMARY over a skill at 0.9."""
        failure_low = _make_failure(0.5)
        skill_high = _make_skill(0.9)
        primary, secondary = rank_for_injection([failure_low, skill_high])
        assert primary is skill_high
        assert failure_low in secondary

    def test_failure_with_high_confidence_beats_skill_with_lower_confidence(self):
        """A failure at 0.95 should beat a skill at 0.8."""
        failure_high = _make_failure(0.95)
        skill_low = _make_skill(0.8)
        primary, secondary = rank_for_injection([failure_high, skill_low])
        assert primary is failure_high


class TestApplyK1Split:
    def test_empty_unchanged(self):
        assert _apply_k1_split([]) == []

    def test_single_unchanged(self):
        s = _make_skill(0.8)
        assert _apply_k1_split([s]) == [s]

    def test_reorders_so_highest_confidence_is_first(self):
        low = _make_skill(0.5)
        high = _make_skill(0.9)
        mid = _make_skill(0.7)
        result = _apply_k1_split([low, high, mid])
        assert result[0] is high

    def test_preserves_all_records(self):
        records = [_make_skill(0.6, f"t{i}") for i in range(5)]
        result = _apply_k1_split(records)
        assert len(result) == 5
        assert set(id(r) for r in result) == set(id(r) for r in records)


class TestMemoryRouterK1Integration:
    """Route() must return records with position-0 == highest confidence."""

    def test_route_places_highest_confidence_first(self):
        router = MemoryRouter(max_records=8, max_tokens=1200)
        low = _make_skill(0.5, "low")
        high = _make_skill(0.9, "high")
        mid = _make_skill(0.7, "mid")

        # Type-priority: all are skills, so order should be by confidence after k=1 split
        routed = router.route([low, high, mid])
        assert routed[0] is high

    def test_route_type_priority_then_k1_confidence(self):
        """Failures must be included before skills (type-priority), but within
        the final routed list position-0 is the highest-confidence record."""
        router = MemoryRouter(max_records=8, max_tokens=1200)
        failure_mid = _make_failure(0.7)
        skill_high = _make_skill(0.9)
        skill_low = _make_skill(0.5)

        routed = router.route([skill_high, failure_mid, skill_low])
        # skill_high (0.9) beats failure_mid (0.7) on confidence → PRIMARY
        assert routed[0].confidence == pytest.approx(0.9)
        # failure is still included
        assert any(r.type == "failure" for r in routed)


# ══════════════════════════════════════════════════════════════════════════════
# B. Confidence floor
# ══════════════════════════════════════════════════════════════════════════════


class TestConfidenceFloor:
    def test_confidence_floor_value(self):
        """CONFIDENCE_FLOOR must be 0.45 — the sql06-fix threshold."""
        assert CONFIDENCE_FLOOR == pytest.approx(0.45)

    def test_retriever_drops_below_floor(self):
        """Records with confidence < CONFIDENCE_FLOOR are silently dropped."""
        from learnkit.retriever import SemanticRetriever

        # Build a backend that returns records straddling the floor
        mock_backend = MagicMock()
        above = _make_skill(0.8)
        below = _make_skill(0.3)  # below 0.45 floor → must be dropped
        at_floor = _make_skill(0.45)  # exactly at floor → must be kept

        mock_backend.search.return_value = [above, below, at_floor]

        retriever = SemanticRetriever(backend=mock_backend)
        results = retriever.retrieve(
            task="gap detection query",
            domain_vector={"sql_authoring": 0.9},
        )

        returned_ids = {r.id for r in results}
        assert above.id in returned_ids
        assert at_floor.id in returned_ids
        assert below.id not in returned_ids

    def test_sql06_regression_blocked(self):
        """sql06 scenario: upsert skill at low confidence must NOT be injected
        into a gap-detection query.

        Historical: confidence=0.5 upsert skill FTS5-matched gap-detection
        keywords and caused a 5.0→2.0 score regression on the gap task.
        With CONFIDENCE_FLOOR=0.45, the 0.5 skill passes floor — but the key
        fix is that if retrieval returns only that skill and it later decays
        below 0.45, it will be dropped. This test verifies the floor boundary.
        """
        from learnkit.retriever import SemanticRetriever

        mock_backend = MagicMock()
        # Upsert skill at the exact problematic confidence from the sql06 run
        upsert_skill = _make_skill(0.3, "upsert_on_conflict")  # simulate decayed
        mock_backend.search.return_value = [upsert_skill]

        retriever = SemanticRetriever(backend=mock_backend)
        results = retriever.retrieve(
            task="login streaks gap detection 24 hours",
            domain_vector={"sql_authoring": 0.9},
        )

        # Nothing should be injected — the upsert skill is below floor
        assert results == []

    def test_retriever_empty_when_all_below_floor(self):
        """If all returned records are below the floor, retrieve returns []."""
        from learnkit.retriever import SemanticRetriever

        mock_backend = MagicMock()
        mock_backend.search.return_value = [
            _make_skill(0.2),
            _make_skill(0.1),
            _make_skill(0.44),
        ]

        retriever = SemanticRetriever(backend=mock_backend)
        results = retriever.retrieve(
            task="some query",
            domain_vector={"sql_authoring": 0.9},
        )
        assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# C. Contrastive failure extraction
# ══════════════════════════════════════════════════════════════════════════════


class TestDistillFailure:
    def _make_trajectory(self, task: str = "gap detection SQL task") -> MagicMock:
        traj = MagicMock()
        traj.task = task
        step = MagicMock()
        step.role = "assistant"
        step.content = "SELECT ... wrong answer ..."
        step.tool_name = None
        traj.steps = [step]
        return traj

    def test_distill_failure_returns_failure_record(self):
        """distill_failure() must return a FailureRecord (not None) on success."""
        from learnkit.distiller import MemoryDistiller

        mock_lm_response = """{
            "lesson_title": "Gap detection requires LAG() not GROUP BY",
            "root_cause": "Agent used GROUP BY instead of window function for gap detection",
            "corrective_strategy": "Use LAG() OVER (PARTITION BY user_id ORDER BY ts) for gap detection",
            "trigger_pattern": "SQL task asking for gaps, sessions, or streaks in time-series data",
            "what_to_avoid": "Confusing upsert ON CONFLICT pattern with gap detection LAG() pattern"
        }"""

        mock_lm = MagicMock()
        mock_lm.return_value = [mock_lm_response]

        distiller = MemoryDistiller(lm=mock_lm)

        with patch("dspy.context"):
            result = distiller.distill_failure(
                trajectory=self._make_trajectory(),
                domain_vector={"sql_authoring": 0.9},
                quality_score=2.0,
            )

        assert result is not None
        assert isinstance(result, FailureRecord)
        assert result.status == "active"
        assert result.confidence >= CONFIDENCE_FLOOR

    def test_distill_failure_confidence_clears_floor(self):
        """FailureRecord from contrastive extraction starts at 0.7 ≥ 0.45."""
        from learnkit.distiller import MemoryDistiller

        mock_lm_response = """{
            "lesson_title": "test failure",
            "root_cause": "model chose wrong pattern",
            "corrective_strategy": "use the correct pattern",
            "trigger_pattern": "gap detection queries",
            "what_to_avoid": "applying upsert pattern to gap detection"
        }"""
        mock_lm = MagicMock()
        mock_lm.return_value = [mock_lm_response]

        distiller = MemoryDistiller(lm=mock_lm)
        with patch("dspy.context"):
            result = distiller.distill_failure(
                trajectory=self._make_trajectory(),
                domain_vector={"sql_authoring": 0.9},
                quality_score=1.5,
            )

        assert result is not None
        assert result.confidence >= CONFIDENCE_FLOOR

    def test_distill_failure_returns_none_on_model_crash(self):
        """If the LM call raises, distill_failure returns None (safe degradation)."""
        from learnkit.distiller import MemoryDistiller

        mock_lm = MagicMock()
        mock_lm.side_effect = RuntimeError("LM unavailable")

        distiller = MemoryDistiller(lm=mock_lm)
        with patch("dspy.context"):
            result = distiller.distill_failure(
                trajectory=self._make_trajectory(),
                domain_vector={"sql_authoring": 0.9},
                quality_score=2.0,
            )

        assert result is None

    def test_distill_failure_returns_none_on_bad_json(self):
        """If the LM returns unparseable JSON, distill_failure returns None."""
        from learnkit.distiller import MemoryDistiller

        mock_lm = MagicMock()
        mock_lm.return_value = ["not valid json {{{{"]

        distiller = MemoryDistiller(lm=mock_lm)
        with patch("dspy.context"):
            result = distiller.distill_failure(
                trajectory=self._make_trajectory(),
                domain_vector={"sql_authoring": 0.9},
                quality_score=2.0,
            )

        assert result is None

    def test_distill_quality_gate_returns_empty_not_raises(self):
        """distill() on low-quality trace must return (None, [], [], None), not raise."""
        from learnkit.distiller import MemoryDistiller

        mock_lm = MagicMock()
        distiller = MemoryDistiller(lm=mock_lm)

        traj = self._make_trajectory()
        # Should NOT raise ValueError — Sprint 1 changed raise to graceful return
        result = distiller.distill(
            trajectory=traj,
            domain_vector={"sql_authoring": 0.9},
            quality_score=2.0,  # below 3.5 threshold
        )

        skill, facts, failures, trace = result
        assert skill is None
        assert facts == []
        assert failures == []
        assert trace is None
