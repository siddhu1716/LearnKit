import pytest
from unittest.mock import MagicMock
from learnkit.classifier import classify_task
from learnkit.evaluator import Evaluator
from learnkit.distiller import MemoryDistiller
from learnkit.trajectory import Trajectory

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

def test_task_classifier():
    # Mock DSPy LM
    mock_response = '{"classification": {"task_type": "contract_summarization", "domains": {"legal": 0.9}, "complexity": "medium"}}'
    lm = MockLM(mock_response)
    
    result = classify_task("summarize this NDA", lm=lm)
    assert result.task_type == "contract_summarization"
    assert "legal" in result.domains
    assert result.domains["legal"] == 0.9

def test_evaluator_llm_judge():
    mock_response = '{"score": 4.5, "reasoning": "Good output"}'
    lm = MockLM(mock_response)
    
    evaluator = Evaluator()
    result = evaluator.evaluate_with_llm_judge(
        task="summarize this contract",
        response="The contract requires Party A to deliver...",
        lm=lm
    )
    
    assert result.score == 4.5
    assert result.passes_threshold is True
    assert result.reasoning == "Good output"

def test_memory_distiller():
    mock_response = '''{
      "skill": {
        "steps": ["Step 1"],
        "tools_used": ["Tool A"],
        "constraints": [],
        "failure_modes": []
      },
      "facts": [
        {"statement": "A fact", "source": "trace"}
      ],
      "failures": [
        {"description": "A failure", "what_to_avoid": "Do not do X"}
      ]
    }'''
    lm = MockLM(mock_response)
    
    distiller = MemoryDistiller(lm=lm)
    
    t = Trajectory(task="test task")
    t.add_step(role="user", content="do this")
    t.add_step(role="assistant", content="did this", reasoning="some reasoning")
    
    skill, facts, failures = distiller.distill(
        trajectory=t,
        domain_vector={"legal": 0.9},
        quality_score=4.5
    )
    
    assert skill is not None
    assert skill.status == "quarantine"
    assert len(skill.content["steps"]) == 1
    
    assert len(facts) == 1
    assert facts[0].status == "quarantine"
    
    assert len(failures) == 1
    assert failures[0].status == "active"
