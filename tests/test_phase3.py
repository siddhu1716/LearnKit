import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from learnkit.evolution.gepa import GEPAEvolver
from learnkit.core import LearnKit
from learnkit.schemas.skill import SkillRecord
from learnkit.trajectory import Trajectory
from learnkit.backends.sqlite import SQLiteBackend
from learnkit.evaluator import EvaluationResult, EvaluationSignal, Evaluator
from learnkit.classifier import ClassificationOutput
import dspy

class MockLM(dspy.LM):
    def __init__(self, response: str):
        super().__init__("mock")
        self.response_text = response
        self.history = []

    def __call__(self, messages=None, **kwargs):
        self.history.append(messages)
        return [self.response_text]

    def copy(self, **kwargs):
        return self

def test_gepa_evolution():
    # Mock DSPy LM to return valid JSON for mutations
    mock_response = '''{
      "mutations": [
        {"steps": ["step A"], "constraints": [], "failure_modes": []},
        {"steps": ["step B"], "constraints": [], "failure_modes": []},
        {"steps": ["step C"], "constraints": [], "failure_modes": []}
      ]
    }'''
    lm = MockLM(mock_response)
    
    import tempfile
    import os
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    
    backend = SQLiteBackend(db_path)
    evaluator = Evaluator()
    evolver = GEPAEvolver(backend=backend, evaluator=evaluator, lm=lm)
    
    skill = SkillRecord(domains={"coding": 0.9}, task_type="test", content={"steps": ["orig"]})
    traces = [Trajectory(task="test task", outcome="failure", quality_score=2.0)]
    
    variants = evolver.evolve_skill(skill, traces, n_trials=1) # 1 trial returns up to 3 variants
    
    os.remove(db_path)
    
    assert len(variants) == 3
    assert variants[0].evolution_gen == 1
    assert variants[0].status == "quarantine"
    assert variants[0].content["steps"] == ["step A"]


def test_gepa_ensemble_trials_store_all_variants(tmp_path):
    mock_response = '''{
      "mutations": [
        {"steps": ["step A"], "constraints": [], "failure_modes": []},
        {"steps": ["step B"], "constraints": [], "failure_modes": []},
        {"steps": ["step C"], "constraints": [], "failure_modes": []}
      ]
    }'''
    backend = SQLiteBackend(str(tmp_path / "memory.db"))
    evolver = GEPAEvolver(
        backend=backend,
        evaluator=Evaluator(),
        lm=MockLM(mock_response),
    )
    skill = SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["orig"]},
    )
    traces = [Trajectory(task="debug task", outcome="failure", quality_score=2.0)]

    variants = evolver.evolve_skill(skill, traces, n_trials=3)

    assert len(variants) == 9
    assert all(v.evolution_gen == 1 for v in variants)
    assert all(v.status == "quarantine" for v in variants)
    assert all(backend.read(v.id) is not None for v in variants)

def test_learnkit_agent():
    # Mock classifier to skip actual LM call
    lk = LearnKit(memory_backend="sqlite", db_path=":memory:")
    
    @lk.agent(domain="test")
    def mock_agent(task, _learnkit_context=None):
        return f"Agent response for {task} with context len {len(_learnkit_context) if _learnkit_context else 0}"
        
    # We won't actually run this in the test because it spins a thread for distiller,
    # and requires full LM mocking for classifier and distiller. But we can check if it initializes.
    assert hasattr(lk, "agent")


def test_learnkit_agent_full_loop_sync():
    class FakeEvaluator:
        def evaluate_with_llm_judge(self, task, response, reasoning_trace=None, lm=None):
            return EvaluationResult(4.2, EvaluationSignal.LLM_JUDGE, "good")

    class FakeDistiller:
        def __init__(self):
            self.trajectory = None
            self.skill = None

        def distill(self, trajectory, domain_vector, quality_score):
            self.trajectory = trajectory
            self.skill = SkillRecord(
                domains=domain_vector,
                task_type="distilled_debug_skill",
                content={"steps": ["reuse the working approach"]},
                status="quarantine",
            )
            return self.skill, [], []

    def fake_classifier(task):
        return ClassificationOutput(
            task_type="debug_python_error",
            domains={"coding": 0.9},
            complexity="medium",
        )

    distiller = FakeDistiller()
    lk = LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        classifier=fake_classifier,
        evaluator=FakeEvaluator(),
        distiller=distiller,
        background_postprocess=False,
    )
    lk.backend.add(SkillRecord(
        domains={"coding": 0.9},
        task_type="debug_python_error",
        content={"steps": ["inspect the traceback first"]},
        confidence=0.92,
    ))

    seen = {}

    @lk.agent(domain="coding")
    def mock_agent(task, _learnkit_context=None):
        seen["context"] = _learnkit_context
        return "fixed"

    result = mock_agent("debug this python traceback")

    assert result == "fixed"
    assert "SKILL" in seen["context"]
    assert "inspect the traceback first" in seen["context"]
    assert lk.last_trajectory is distiller.trajectory
    assert lk.last_trajectory.outcome == "success"
    assert [step.role for step in lk.last_trajectory.steps] == ["user", "assistant"]
    stored_skill = lk.backend.read(distiller.skill.id)
    assert stored_skill.task_type == "distilled_debug_skill"
    assert stored_skill.status == "quarantine"


def test_public_api_exports_learnkit():
    import learnkit as lk

    assert lk.LearnKit is LearnKit


def test_learnkit_maintain_memory(tmp_path):
    lk = LearnKit(memory_backend="sqlite", db_path=str(tmp_path / "memory.db"))
    active = SkillRecord(
        domains={"coding": 0.9},
        task_type="active_skill",
        content={"steps": ["active"]},
        confidence=0.5,
    )
    expired = SkillRecord(
        domains={"coding": 0.9},
        task_type="expired_skill",
        content={"steps": ["expired"]},
        expires_at=(datetime.utcnow() - timedelta(days=1)).isoformat(),
    )
    quarantined = SkillRecord(
        domains={"coding": 0.9},
        task_type="reviewed_skill",
        content={"steps": ["reviewed"]},
        status="quarantine",
        created_at=(datetime.utcnow() - timedelta(hours=25)).isoformat(),
    )
    lk.backend.add(active)
    lk.backend.add(expired)
    lk.backend.add(quarantined)

    result = lk.maintain_memory()

    assert result == {"decayed": 2, "stale": 1, "promoted": 1}
    assert lk.backend.read(active.id).confidence == pytest.approx(0.48)
    assert lk.backend.read(expired.id).status == "stale"
    assert lk.backend.read(quarantined.id).status == "active"
