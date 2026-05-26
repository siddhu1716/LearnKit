"""Shared test fixtures for LearnKit test suite."""

import pytest

from learnkit.trajectory import Trajectory
from learnkit.schemas.skill import SkillRecord
from learnkit.schemas.fact import FactRecord
from learnkit.schemas.failure import FailureRecord
from learnkit.backends.sqlite import SQLiteBackend


def _make_mock_lm(response: str):
    """Create a MockLM instance. Requires dspy to be installed."""
    import dspy

    class MockLM(dspy.LM):
        def __init__(self, resp: str):
            super().__init__("mock")
            self.response_text = resp
            self.history = []

        def __call__(self, messages=None, **kwargs):
            self.history.append(messages)
            return [self.response_text]

        def copy(self, **kwargs):
            return self

    return MockLM(response)


@pytest.fixture
def memory_backend():
    """In-memory SQLite backend for fast tests."""
    return SQLiteBackend(db_path=":memory:")


@pytest.fixture
def sample_skill():
    """A representative SkillRecord for testing."""
    return SkillRecord(
        domains={"legal": 0.9, "finance": 0.3},
        task_type="contract_summarization",
        content={
            "steps": [
                "Extract all obligations per party",
                "Extract termination clauses",
                "Flag indemnity clauses separately",
                "Simplify to plain English",
                "Structure as bullet summary",
            ],
            "tools_used": ["pdf_reader", "clause_extractor"],
            "constraints": ["under 500 words", "no legal jargon"],
            "failure_modes": ["hallucinated clause references"],
            "examples": {
                "good": "Party A must deliver by Q3. Liability capped at $500K.",
                "bad": "The contract has some clauses about things.",
            },
        },
        confidence=0.87,
    )


@pytest.fixture
def sample_failure():
    """A representative FailureRecord for testing."""
    return FailureRecord(
        domains={"coding": 0.9},
        content={
            "description": "Used fork start method on macOS causing hang",
            "what_to_avoid": "Never use fork on macOS with multiprocessing",
        },
        status="active",
    )


@pytest.fixture
def sample_fact():
    """A representative FactRecord for testing."""
    return FactRecord(
        domains={"coding": 0.9},
        content={
            "statement": "macOS default multiprocessing start method is spawn since Python 3.8",
            "source": "Python docs",
        },
    )


@pytest.fixture
def sample_trajectory():
    """A trajectory with reasoning steps for distillation testing."""
    t = Trajectory(task="Summarize the NDA between ACME Corp and Widget Inc")
    t.add_step(
        role="user",
        content="Summarize the NDA between ACME Corp and Widget Inc",
    )
    t.add_step(
        role="tool",
        content="Extracted 12 pages of text from NDA.pdf",
        tool_name="pdf_reader",
    )
    t.add_step(
        role="assistant",
        content="The NDA requires both parties to maintain confidentiality for 3 years...",
        reasoning="I identified the key obligations: confidentiality period is 3 years, "
                  "mutual NDA so both parties have equal obligations, no carve-outs for "
                  "publicly available information which is unusual.",
    )
    t.outcome = "success"
    t.quality_score = 4.5
    return t
