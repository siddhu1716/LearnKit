"""Tests for the skill consolidation (umbrella-merge) maintenance pass.

Mirrors the Hermes curator invariants we adapted:
  - overlapping active skills merge into one canonical umbrella
  - merged skills are archived (status -> "deprecated"), never deleted
  - pinned skills are exempt
  - distinct skills are left untouched
"""

from __future__ import annotations

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.consolidation import (
    MAX_MERGED_LIST_ITEMS,
    consolidate_skills,
)
from learnkit.schemas.skill import SkillRecord


def _backend() -> SQLiteBackend:
    return SQLiteBackend(db_path=":memory:")


def _skill(
    task_type: str,
    steps: list[str],
    confidence: float = 0.7,
    reuse_count: int = 0,
    pinned: bool = False,
    tools: list[str] | None = None,
) -> SkillRecord:
    content: dict = {"steps": steps, "tools_used": tools or []}
    if pinned:
        content["pinned"] = True
    return SkillRecord(
        domains={"coding": confidence},
        task_type=task_type,
        content=content,
        confidence=confidence,
        reuse_count=reuse_count,
    )


def test_overlapping_skills_merge_into_umbrella():
    backend = _backend()
    a = _skill(
        "deploy fastapi to aws",
        ["build docker image", "push to ecr", "update ecs service"],
        confidence=0.85,
        reuse_count=5,
        tools=["docker", "aws-cli"],
    )
    b = _skill(
        "deploy fastapi app to aws",
        ["build docker image", "push to ecr", "run smoke test"],
        confidence=0.7,
        reuse_count=2,
        tools=["docker", "pytest"],
    )
    backend.add(a)
    backend.add(b)

    stats = consolidate_skills(backend, threshold=0.5)

    assert stats["clusters"] == 1
    assert stats["archived"] == 1

    canonical = backend.read(a.id)  # higher confidence -> canonical
    loser = backend.read(b.id)
    assert canonical.status == "active"
    assert loser.status == "deprecated"
    # Union of steps, deduped, canonical-first.
    assert "run smoke test" in canonical.content["steps"]
    assert canonical.content["steps"].count("build docker image") == 1
    # Reuse counts are summed onto the umbrella.
    assert canonical.reuse_count == 7
    # Back-references both directions.
    assert loser.id in canonical.content["consolidated_from"]
    assert loser.content["consolidated_into"] == canonical.id
    # Tools unioned too.
    assert set(canonical.content["tools_used"]) == {"docker", "aws-cli", "pytest"}


def test_distinct_skills_not_merged():
    backend = _backend()
    a = _skill("parse pdf invoices", ["open pdf", "extract tables", "map fields"])
    b = _skill("train sentiment classifier", ["load dataset", "tokenize", "fit model"])
    backend.add(a)
    backend.add(b)

    stats = consolidate_skills(backend, threshold=0.5)

    assert stats["clusters"] == 0
    assert stats["archived"] == 0
    assert backend.read(a.id).status == "active"
    assert backend.read(b.id).status == "active"


def test_pinned_skill_is_exempt():
    backend = _backend()
    pinned = _skill(
        "deploy fastapi to aws",
        ["build docker image", "push to ecr"],
        confidence=0.9,
        pinned=True,
    )
    dup = _skill(
        "deploy fastapi to aws",
        ["build docker image", "push to ecr"],
        confidence=0.6,
    )
    backend.add(pinned)
    backend.add(dup)

    stats = consolidate_skills(backend, threshold=0.5)

    # Pinned skill never participates, so there is no 2-member cluster.
    assert stats["archived"] == 0
    assert backend.read(pinned.id).status == "active"
    assert backend.read(dup.id).status == "active"


def test_archived_skills_are_recoverable_not_deleted():
    backend = _backend()
    a = _skill("scrape product prices", ["fetch page", "parse html", "store row"], confidence=0.8)
    b = _skill("scrape product prices", ["fetch page", "parse html", "dedup rows"], confidence=0.5)
    backend.add(a)
    backend.add(b)

    consolidate_skills(backend, threshold=0.5)

    loser = backend.read(b.id)
    assert loser is not None  # still present, just deprecated
    assert loser.status == "deprecated"


def test_merge_respects_list_cap():
    backend = _backend()
    a = _skill("bulk task", [f"step a{i}" for i in range(40)], confidence=0.9)
    b = _skill("bulk task", [f"step b{i}" for i in range(40)], confidence=0.5)
    backend.add(a)
    backend.add(b)

    consolidate_skills(backend, threshold=0.3)

    canonical = backend.read(a.id)
    assert len(canonical.content["steps"]) <= MAX_MERGED_LIST_ITEMS


def test_empty_or_single_skill_is_noop():
    backend = _backend()
    assert consolidate_skills(backend)["clusters"] == 0
    backend.add(_skill("solo skill", ["only step"]))
    stats = consolidate_skills(backend)
    assert stats["skills_scanned"] == 1
    assert stats["clusters"] == 0
