import dspy

from learnkit.classifier import classify_task
from learnkit.distiller import MemoryDistiller
from learnkit.evaluator import Evaluator
from learnkit.trajectory import Trajectory


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
        lm=lm,
    )

    assert result.score == 4.5
    assert result.passes_threshold is True
    assert result.reasoning == "Good output"


def test_memory_distiller():
    mock_response = """{
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
    }"""
    lm = MockLM(mock_response)

    distiller = MemoryDistiller(lm=lm)

    t = Trajectory(task="test task")
    t.add_step(role="user", content="do this")
    t.add_step(role="assistant", content="did this", reasoning="some reasoning")

    skill, facts, failures, trace_rec = distiller.distill(
        trajectory=t, domain_vector={"legal": 0.9}, quality_score=4.5
    )

    assert skill is not None
    assert skill.status == "quarantine"
    assert len(skill.content["steps"]) == 1

    assert len(facts) == 1
    assert facts[0].status == "quarantine"

    assert len(failures) == 1
    assert failures[0].status == "active"

    assert trace_rec is not None
    assert trace_rec.status == "active"
    assert trace_rec.content["trajectory_id"] == t.id


class FailingMockLM(dspy.LM):
    def __init__(self):
        super().__init__("mock")
        self.call_count = 0

    def __call__(self, messages=None, **kwargs):
        self.call_count += 1
        raise RuntimeError("API failure")

    def copy(self, **kwargs):
        return self


def test_task_classifier_retry_and_fallback():
    lm = FailingMockLM()
    result = classify_task("summarize this NDA", lm=lm, retries=2, backoff_factor=0.1)

    assert lm.call_count == 2
    assert result.task_type == "general"
    assert result.domains == {"general": 1.0}
    assert result.complexity == "medium"


def test_evaluator_bounds_and_repair():
    evaluator = Evaluator()

    # 1. Bounded inputs truncation
    mock_response = '{"score": 4.5, "reasoning": "Truncation test passed"}'
    lm = MockLM(mock_response)

    long_task = "A" * 5000
    long_response = "B" * 6000

    result = evaluator.evaluate_with_llm_judge(
        task=long_task, response=long_response, reasoning_trace="Reasoning info", lm=lm
    )

    assert result.score == 4.5
    assert result.metadata["task_len"] == 5000
    assert result.metadata["response_len"] == 6000

    # 2. JSON Repair - Single quotes
    lm_single_quotes = MockLM("{'score': 3.8, 'reasoning': 'Single quotes work'}")
    result_sq = evaluator.evaluate_with_llm_judge(
        "task", "response", lm=lm_single_quotes
    )
    assert result_sq.score == 3.8
    assert result_sq.metadata["parse_method"] == "json_replace_quotes"

    # 3. JSON Repair - Regex Recovery
    lm_malformed = MockLM(
        'Some prefix text { "score": 4.2, "reasoning": "Indeed corrected" } some suffix text'
    )
    result_malformed = evaluator.evaluate_with_llm_judge(
        "task", "response", lm=lm_malformed
    )
    assert result_malformed.score == 4.2
    assert result_malformed.metadata["parse_method"] == "regex_recovery"
