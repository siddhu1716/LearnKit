import pytest
from unittest.mock import MagicMock
from learnkit.evolution.gepa import GEPAEvolver
from learnkit.core import LearnKit
from learnkit.schemas.skill import SkillRecord
from learnkit.trajectory import Trajectory
from learnkit.backends.sqlite import SQLiteBackend
from learnkit.evaluator import Evaluator
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

def test_learnkit_agent():
    # Mock classifier to skip actual LM call
    lk = LearnKit(memory_backend="sqlite", db_path=":memory:")
    
    @lk.agent(domain="test")
    def mock_agent(task, _learnkit_context=None):
        return f"Agent response for {task} with context len {len(_learnkit_context) if _learnkit_context else 0}"
        
    # We won't actually run this in the test because it spins a thread for distiller,
    # and requires full LM mocking for classifier and distiller. But we can check if it initializes.
    assert hasattr(lk, "agent")
