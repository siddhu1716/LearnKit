"""Tests for the PRIMARY-slot type-weighted tiebreaker in router.rank_for_injection.

The codex review of PBE/SLR benchmark runs revealed that contrastive
FailureRecords were winning the PRIMARY slot 100% of the time, displacing
SkillRecords that should have been the prescriptive context. The fix adds
a small type-priority bonus (~0.1) so skills beat failures at comparable
confidence — but a clearly higher-confidence failure still wins.
"""

from __future__ import annotations

from learnkit.router import rank_for_injection
from learnkit.schemas.failure import FailureRecord
from learnkit.schemas.skill import SkillRecord


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


def test_skill_beats_failure_at_equal_confidence():
    """At equal confidence, the skill is prescriptive — failure is a warning."""
    failure = _failure(0.75)
    skill = _skill(0.75)
    primary, secondary = rank_for_injection([failure, skill])
    assert primary is skill
    assert failure in secondary


def test_distilled_skill_default_beats_distilled_failure_default():
    """Mirrors actual distiller defaults: skill=0.75, failure=0.70 → skill wins."""
    failure = _failure(0.70)
    skill = _skill(0.75)
    primary, secondary = rank_for_injection([failure, skill])
    assert primary is skill


def test_clearly_higher_confidence_failure_still_wins():
    """A failure that's much more reinforced (0.95) still beats a fresh skill (0.75)."""
    failure_high = _failure(0.95)
    skill_low = _skill(0.75)
    primary, _ = rank_for_injection([failure_high, skill_low])
    assert primary is failure_high


def test_low_confidence_skill_does_not_beat_strong_failure():
    """A barely-passing skill (0.5) should not displace a very reinforced failure (0.9)."""
    failure_high = _failure(0.90)
    skill_low = _skill(0.50)
    primary, _ = rank_for_injection([failure_high, skill_low])
    assert primary is failure_high


def test_skill_with_higher_confidence_obviously_wins():
    """Sanity: a clearly-better skill beats a failure."""
    failure = _failure(0.6)
    skill = _skill(0.9)
    primary, _ = rank_for_injection([failure, skill])
    assert primary is skill
