"""Robustness/efficiency regression tests for the four core building blocks.

Covers the hardening pass on:
  1. Router      — constructor validation, id dedup, failure-starvation fix.
  2. Retriever   — empty-query guard, record-embedding cache.
  3. Distiller   — generalized skill task_type (no raw-task BM25 magnet),
                   empty-steps skip.
  4. Skills loader — metadata missing ``id`` is skipped, not a crash.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from learnkit.distiller import MemoryDistiller
from learnkit.retriever import SemanticRetriever
from learnkit.router import MemoryRouter
from learnkit.schemas.failure import FailureRecord
from learnkit.schemas.skill import SkillRecord
from learnkit.skills_loader import seed_bundled_skills
from learnkit.trajectory import Trajectory


# ── Helpers ────────────────────────────────────────────────────────────────


def _skill(confidence: float, task_type: str = "skill_task") -> SkillRecord:
    return SkillRecord(
        domains={"coding": confidence},
        task_type=task_type,
        content={"steps": ["do the thing"]},
        confidence=confidence,
        status="active",
    )


def _failure(confidence: float) -> FailureRecord:
    return FailureRecord(
        domains={"coding": confidence},
        task_type="failure_pattern",
        content={"description": "x", "what_to_avoid": "y"},
        confidence=confidence,
        status="active",
    )


# ══════════════════════════════════════════════════════════════════════════
# 1. Router
# ══════════════════════════════════════════════════════════════════════════


class TestRouterHardening:
    def test_rejects_invalid_max_records(self):
        with pytest.raises(ValueError):
            MemoryRouter(max_records=0)

    def test_rejects_invalid_max_tokens(self):
        with pytest.raises(ValueError):
            MemoryRouter(max_records=8, max_tokens=0)

    def test_dedups_records_by_id(self):
        router = MemoryRouter(max_records=8, max_tokens=1200)
        skill = _skill(0.8)
        routed = router.route([skill, skill, skill])
        assert len(routed) == 1
        assert routed[0] is skill

    def test_weak_failures_do_not_starve_strong_skill(self):
        """Many low-confidence failures must not crowd a strong skill out of a
        tight budget — the SLR/PBE contamination failure mode."""
        router = MemoryRouter(max_records=2, max_tokens=1200)
        strong_skill = _skill(0.9, "strong")
        weak_failures = [_failure(0.5) for _ in range(5)]
        routed = router.route(weak_failures + [strong_skill])
        assert routed[0] is strong_skill  # admitted AND primary
        assert len(routed) == 2


# ══════════════════════════════════════════════════════════════════════════
# 2. Retriever
# ══════════════════════════════════════════════════════════════════════════


class TestRetrieverHardening:
    def test_empty_task_returns_empty(self):
        retriever = SemanticRetriever(backend=MagicMock())
        assert retriever.retrieve(task="", domain_vector={}) == []
        assert retriever.retrieve(task="   ", domain_vector={}) == []

    def test_record_embedding_is_cached(self):
        calls = {"n": 0}

        def embedder(text: str) -> list[float]:
            calls["n"] += 1
            return [float(len(text)), 1.0, 2.0]

        retriever = SemanticRetriever(backend=MagicMock(), embedder=embedder)
        record = _skill(0.8)

        v1 = retriever._embed_record(record)
        v2 = retriever._embed_record(record)
        assert v1 == v2
        assert calls["n"] == 1  # second call served from cache

    def test_embed_cache_invalidates_on_text_change(self):
        calls = {"n": 0}

        def embedder(text: str) -> list[float]:
            calls["n"] += 1
            return [float(len(text))]

        retriever = SemanticRetriever(backend=MagicMock(), embedder=embedder)
        record = _skill(0.8)
        retriever._embed_record(record)
        record.content["steps"] = ["a totally different step now"]
        retriever._embed_record(record)
        assert calls["n"] == 2  # re-embedded because text changed


# ══════════════════════════════════════════════════════════════════════════
# 3. Distiller — skill creation
# ══════════════════════════════════════════════════════════════════════════


class TestDistillerSkillHardening:
    def _trajectory(self, task: str) -> Trajectory:
        t = Trajectory(task=task)
        t.add_step(role="user", content=task)
        t.add_step(role="assistant", content="did the work", reasoning="reasoned")
        return t

    def test_skill_task_type_uses_pattern_name_not_raw_task(self):
        raw_task = "Compute the rolling 7-day retention for cohort ACME in March"
        response = json.dumps(
            {
                "skill": {
                    "pattern_name": "rolling window cohort metric",
                    "steps": ["partition by cohort", "apply window function"],
                    "tools_used": [],
                    "constraints": [],
                    "failure_modes": [],
                },
                "facts": [],
                "failures": [],
            }
        )
        mock_lm = MagicMock()
        mock_lm.return_value = [response]
        distiller = MemoryDistiller(lm=mock_lm)

        with patch("dspy.context"):
            skill, _, _, _ = distiller.distill(
                trajectory=self._trajectory(raw_task),
                domain_vector={"sql_authoring": 0.9},
                quality_score=4.5,
            )

        assert skill is not None
        assert skill.task_type == "rolling window cohort metric"
        assert raw_task[:20] not in (skill.task_type or "")

    def test_skill_with_empty_steps_is_skipped(self):
        response = json.dumps(
            {
                "skill": {"pattern_name": "noop", "steps": [], "tools_used": []},
                "facts": [],
                "failures": [],
            }
        )
        mock_lm = MagicMock()
        mock_lm.return_value = [response]
        distiller = MemoryDistiller(lm=mock_lm)

        with patch("dspy.context"):
            skill, _, _, _ = distiller.distill(
                trajectory=self._trajectory("some task"),
                domain_vector={"coding": 0.9},
                quality_score=4.5,
            )

        assert skill is None

    def test_skill_falls_back_to_domain_label_without_pattern_name(self):
        response = json.dumps(
            {
                "skill": {"steps": ["step one"], "tools_used": []},
                "facts": [],
                "failures": [],
            }
        )
        mock_lm = MagicMock()
        mock_lm.return_value = [response]
        distiller = MemoryDistiller(lm=mock_lm)

        with patch("dspy.context"):
            skill, _, _, _ = distiller.distill(
                trajectory=self._trajectory("a one-off task"),
                domain_vector={"finance": 0.9},
                quality_score=4.5,
            )

        assert skill is not None
        assert skill.task_type == "finance_skill"


# ══════════════════════════════════════════════════════════════════════════
# 4. Skills loader
# ══════════════════════════════════════════════════════════════════════════


class _FakeBackend:
    def __init__(self):
        self.added = []

    def read(self, _id):
        return None

    def add(self, record):
        self.added.append(record)


class TestSkillsLoaderHardening:
    def test_metadata_without_id_is_skipped(self, tmp_path):
        skill_dir = tmp_path / "broken_skill"
        skill_dir.mkdir()
        # Valid skill schema fields but no "id"
        (skill_dir / "metadata.json").write_text(
            json.dumps({"type": "skill", "task_type": "x", "content": {"steps": ["a"]}})
        )
        (skill_dir / "SKILL.md").write_text("# Broken skill")

        backend = _FakeBackend()
        seeded = seed_bundled_skills(backend, skills_dir=tmp_path)
        assert seeded == 0
        assert backend.added == []

    def test_valid_skill_is_seeded(self, tmp_path):
        skill_dir = tmp_path / "good_skill"
        skill_dir.mkdir()
        (skill_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "id": "good-skill-1",
                    "type": "skill",
                    "task_type": "demo",
                    "content": {"steps": ["a"]},
                }
            )
        )
        (skill_dir / "SKILL.md").write_text("# Good skill")

        backend = _FakeBackend()
        seeded = seed_bundled_skills(backend, skills_dir=tmp_path)
        assert seeded == 1
        assert backend.added[0].content.get("skill_md") == "# Good skill"
