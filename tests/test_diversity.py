"""Tests for diversity-aware re-ranking (ported from ruflo SmartRetrieval).

Covers:
  A. diversity.py primitives — tokenize / jaccard / mmr_order / RRF.
  B. MemoryRouter MMR integration — diversity spends the bounded budget on
     complementary records instead of near-duplicates, while preserving the
     highest-confidence record as PRIMARY (ReasoningBank k=1).
"""

from learnkit.diversity import (
    jaccard,
    mmr_order,
    reciprocal_rank_fusion,
    tokenize,
)
from learnkit.router import MemoryRouter, rank_for_injection
from learnkit.schemas.skill import SkillRecord


# ── Helpers ───────────────────────────────────────────────────────────────────


def _skill(confidence: float, task_type: str, steps: list[str]) -> SkillRecord:
    return SkillRecord(
        domains={"coding": confidence},
        task_type=task_type,
        content={"steps": steps, "tools_used": [], "failure_modes": []},
        confidence=confidence,
        status="active",
    )


# ══════════════════════════════════════════════════════════════════════════════
# A. diversity primitives
# ══════════════════════════════════════════════════════════════════════════════


class TestTokenize:
    def test_drops_stopwords_and_short_tokens(self):
        assert tokenize("the cat is on a mat") == {"cat", "mat"}

    def test_strips_punctuation_and_lowercases(self):
        assert tokenize("Upsert, INSERT! and merge?") == {"upsert", "insert", "merge"}

    def test_empty(self):
        assert tokenize("") == set()


class TestJaccard:
    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert jaccard(s, s) == 1.0

    def test_disjoint_sets(self):
        assert jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3

    def test_both_empty(self):
        assert jaccard(set(), set()) == 0.0


class TestMmrOrder:
    def test_lambda_one_preserves_relevance_order(self):
        items = [("a", 0.9), ("b", 0.5), ("c", 0.1)]
        out = mmr_order(items, lambda x: x[1], lambda x: x[0], lambda_=1.0)
        assert [x[0] for x in out] == ["a", "b", "c"]

    def test_diversity_demotes_near_duplicate(self):
        # Two near-identical high-relevance items + one distinct lower item.
        items = [
            ("dup1", 0.90, "insert upsert merge conflict resolution"),
            ("dup2", 0.88, "insert upsert merge conflict resolution row"),
            ("diverse", 0.70, "detect gaps in time series windows"),
        ]
        out = mmr_order(
            items,
            relevance_of=lambda x: x[1],
            text_of=lambda x: x[2],
            lambda_=0.5,
        )
        ids = [x[0] for x in out]
        # Top item still wins the seed slot; the diverse record is promoted
        # above the redundant duplicate.
        assert ids[0] == "dup1"
        assert ids.index("diverse") < ids.index("dup2")

    def test_single_item_passthrough(self):
        items = [("a", 1.0, "x")]
        out = mmr_order(items, lambda x: x[1], lambda x: x[2])
        assert out == items

    def test_returns_all_items_when_unlimited(self):
        items = [("a", 0.9, "alpha"), ("b", 0.8, "beta"), ("c", 0.7, "gamma")]
        out = mmr_order(items, lambda x: x[1], lambda x: x[2], lambda_=0.7)
        assert {x[0] for x in out} == {"a", "b", "c"}


class TestReciprocalRankFusion:
    def test_item_in_both_lists_outranks_singletons(self):
        lexical = ["x", "y", "z"]
        dense = ["y", "w", "x"]
        fused = reciprocal_rank_fusion([lexical, dense], key_of=lambda c: c)
        # 'y' appears at ranks 2 and 1; 'x' at ranks 1 and 3 → both beat singletons.
        assert fused[0] in {"x", "y"}
        assert set(fused) == {"x", "y", "z", "w"}

    def test_single_list_preserves_order(self):
        fused = reciprocal_rank_fusion([["a", "b", "c"]], key_of=lambda c: c)
        assert fused == ["a", "b", "c"]


# ══════════════════════════════════════════════════════════════════════════════
# B. Router MMR integration
# ══════════════════════════════════════════════════════════════════════════════


class TestRouterDiversity:
    def test_invalid_lambda_rejected(self):
        import pytest

        with pytest.raises(ValueError):
            MemoryRouter(diversity_lambda=1.5)

    def test_diversity_admits_complementary_record(self):
        # Three near-duplicate upsert skills (slightly different confidence) plus
        # one distinct gap-detection skill. With a 3-record budget, the diverse
        # record should be admitted instead of a third redundant duplicate.
        dup_a = _skill(0.90, "sql_upsert", ["build insert", "merge on conflict", "update row"])
        dup_b = _skill(0.88, "sql_upsert", ["build insert", "merge on conflict", "update rows"])
        dup_c = _skill(0.86, "sql_upsert", ["build insert", "merge on conflict", "update record"])
        diverse = _skill(0.80, "gap_detection", ["window time series", "detect missing buckets"])

        router = MemoryRouter(max_records=3, max_tokens=10_000, diversity_lambda=0.5)
        routed = router.route([dup_a, dup_b, dup_c, diverse])

        ids = {r.id for r in routed}
        assert len(routed) == 3
        assert diverse.id in ids
        # PRIMARY (position 0) is still the highest-confidence record.
        primary, _ = rank_for_injection(routed)
        assert primary.id == dup_a.id

    def test_lambda_one_is_pure_confidence_order(self):
        dup_a = _skill(0.90, "sql_upsert", ["build insert", "merge on conflict"])
        dup_b = _skill(0.88, "sql_upsert", ["build insert", "merge on conflict"])
        dup_c = _skill(0.86, "sql_upsert", ["build insert", "merge on conflict"])
        diverse = _skill(0.50, "gap_detection", ["window time series"])

        router = MemoryRouter(max_records=3, max_tokens=10_000, diversity_lambda=1.0)
        routed = router.route([dup_a, dup_b, dup_c, diverse])

        ids = {r.id for r in routed}
        # No diversity: the three highest-confidence (redundant) records win.
        assert ids == {dup_a.id, dup_b.id, dup_c.id}
