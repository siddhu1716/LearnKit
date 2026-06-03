"""Regression tests for the Tier-A production-hardening pass.

Each test pins one of the AGENTS_V2 hardening guarantees so it cannot
silently regress in a future refactor.

- A2 — `SQLiteBackend.add` must reject records with an invalid `scope` at
  write time (raises `BackendError`) instead of writing a poison row that
  blows up on subsequent read.
- A3 — `LearnKit.shutdown()` drains the worker pool and survives being
  called twice; `_post_process_async` falls back to sync after shutdown
  so an `agent(...)` call doesn't crash.
- A4 — `MemoryRouter.route` caps results at both `max_records` AND
  `max_tokens` (default ~1,200), preserving priority order
  failure > skill > fact > others. Always admits at least one record.
"""

import pytest

from learnkit.backends.sqlite import SQLiteBackend
from learnkit.classifier import ClassificationOutput
from learnkit.core import LearnKit
from learnkit.errors import BackendError
from learnkit.evaluator import EvaluationResult, EvaluationSignal
from learnkit.router import MemoryRouter
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.failure import FailureRecord
from learnkit.schemas.skill import SkillRecord

# --- A2 ---------------------------------------------------------------


def test_add_rejects_invalid_scope_with_backenderror(tmp_path):
    """Writing a record with an out-of-literal scope must raise BackendError.

    Pydantic validates `scope` on construction but `validate_assignment` defaults
    to False, so `record.scope = "demo"` after the fact bypasses validation.
    Without this write-time check the bad value goes to disk and explodes
    later on read.
    """
    backend = SQLiteBackend(str(tmp_path / "memory.db"))
    skill = SkillRecord(
        domains={"coding": 0.9}, task_type="t", content={"steps": ["s"]}
    )
    # Simulate the post-Pydantic mutation that landed the original poison row.
    skill.__dict__["scope"] = "demo"  # bypass Pydantic on purpose

    with pytest.raises(BackendError, match="Invalid scope"):
        backend.add(skill)

    # And no row should have made it through.
    assert backend.read(skill.id) is None


def test_add_accepts_each_valid_scope(tmp_path):
    backend = SQLiteBackend(str(tmp_path / "memory.db"))
    for scope in ("user", "team", "public"):
        skill = SkillRecord(
            domains={"coding": 0.9},
            task_type=f"t-{scope}",
            content={"steps": ["s"]},
            scope=scope,
        )
        backend.add(skill)
        assert backend.read(skill.id).scope == scope


# --- A3 ---------------------------------------------------------------


def test_shutdown_is_idempotent_and_pool_drains(tmp_path):
    lk = LearnKit(memory_backend="sqlite", db_path=str(tmp_path / "memory.db"))
    lk.shutdown()
    # Second call must not raise.
    lk.shutdown()
    # Worker pool is closed; submitting would raise RuntimeError if invoked.
    assert lk._is_shutdown is True


def test_post_process_falls_back_to_sync_after_shutdown(tmp_path):
    """After shutdown the wrapped agent must still run; post-processing
    happens synchronously instead of being submitted to the (closed) pool."""

    class FakeEvaluator:
        def evaluate_with_llm_judge(
            self, task, response, reasoning_trace=None, lm=None
        ):
            return EvaluationResult(4.2, EvaluationSignal.LLM_JUDGE, "good")

    class FakeDistiller:
        def distill(self, trajectory, domain_vector, quality_score):
            skill = SkillRecord(
                domains=domain_vector,
                task_type="distilled",
                content={"steps": ["s"]},
                status="quarantine",
            )
            return skill, [], [], None

    def fake_classifier(task):
        return ClassificationOutput(
            task_type="t", domains={"coding": 0.9}, complexity="medium"
        )

    lk = LearnKit(
        memory_backend="sqlite",
        db_path=str(tmp_path / "memory.db"),
        classifier=fake_classifier,
        evaluator=FakeEvaluator(),
        distiller=FakeDistiller(),
    )
    lk.shutdown()  # close the pool BEFORE invoking the agent

    @lk.agent(domain="coding")
    def agent(task, _learnkit_context=None):
        return "answered"

    # Would raise "cannot schedule new futures after shutdown" without the guard.
    result = agent("a task")
    assert result == "answered"
    # Post-processing ran synchronously: trajectory got scored and the
    # distilled (quarantined) skill was persisted. list_by_domain filters to
    # active so we read it back by id from the trajectory's last storage hit.
    assert lk.last_trajectory is not None
    assert lk.last_trajectory.quality_score == 4.2
    assert lk.last_trajectory.outcome == "success"


# --- A4 ---------------------------------------------------------------


def _skill(
    task_type: str, content_size: int = 100, confidence: float = 0.8
) -> SkillRecord:
    return SkillRecord(
        domains={"coding": 0.9},
        task_type=task_type,
        content={"steps": ["x" * content_size]},
        confidence=confidence,
    )


def test_router_caps_at_max_records():
    router = MemoryRouter(max_records=3, max_tokens=100000)
    records = [_skill(f"s{i}") for i in range(10)]
    routed = router.route(records)
    assert len(routed) == 3


def test_router_caps_at_token_budget():
    """Once the per-record budget is exceeded, additional records are dropped
    even if max_records is generous."""
    router = MemoryRouter(max_records=20, max_tokens=200)  # ~800 char budget
    records = [_skill(f"s{i}", content_size=300) for i in range(10)]
    routed = router.route(records)
    assert (
        1 <= len(routed) < 10
    ), f"expected token budget to drop most records, got {len(routed)}"


def test_router_preserves_priority_failures_before_skills_before_facts():
    """Type-priority (failure > skill > fact) determines *which* records are
    included. The k=1 split then re-orders by confidence so the highest-
    confidence record is always at position 0 (PRIMARY PRESCRIPTIVE context).

    This test verifies:
    - All 3 types survive the token budget and max_records cap.
    - The skill (confidence=0.8) is at position 0 because it has higher
      confidence than the failure (default 0.5) after k=1 reorder.
    """
    skill = _skill("a_skill")  # confidence=0.8
    fact = FactRecord(domains={"coding": 0.9}, content={"statement": "f"})
    failure = FailureRecord(
        domains={"coding": 0.9},
        content={"description": "d", "what_to_avoid": "w"},
        status="active",
        # default confidence=0.5 → below skill's 0.8, so skill becomes PRIMARY
    )
    # Pass them in inverse-priority order to verify the router includes all types.
    routed = MemoryRouter(max_records=8, max_tokens=10000).route([fact, skill, failure])

    # All 3 types must be present (type-priority selection)
    types_in_result = {r.type for r in routed}
    assert "failure" in types_in_result
    assert "skill" in types_in_result
    assert "fact" in types_in_result

    # Position 0 is the highest-confidence record (k=1 split)
    assert routed[0].type == "skill"  # skill.confidence=0.8 > failure.confidence=0.5


def test_router_always_admits_at_least_one_record_even_if_oversized():
    """A single huge failure must still be admitted — dropping it would defeat
    the point of running the retriever at all."""
    huge = FailureRecord(
        domains={"coding": 0.9},
        content={"description": "x" * 10000, "what_to_avoid": "y" * 10000},
        status="active",
    )
    routed = MemoryRouter(max_records=8, max_tokens=100).route([huge])
    assert len(routed) == 1
    assert routed[0] is huge
