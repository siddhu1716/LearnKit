"""Offline LLM-judge fallback — deterministic heuristic scoring.

When no judge key is configured the evaluator must degrade to a transparent
heuristic (not a fixed sub-threshold score that silently blocks all
distillation). These tests pin that contract.
"""

import pytest

from learnkit.evaluator import (
    EvaluationSignal,
    Evaluator,
    heuristic_score,
    judge_offline,
    judge_status,
)

_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHERAI_API_KEY",
    "COHERE_API_KEY",
    "LEARNKIT_EVALUATOR_MODEL",
)


@pytest.fixture()
def offline(monkeypatch):
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("LEARNKIT_OFFLINE", "1")
    yield


def test_judge_offline_detects_no_key(offline):
    assert judge_offline() is True
    status = judge_status()
    assert status["available"] is False
    assert status["mode"] == "heuristic_offline"


def test_judge_online_when_key_present(monkeypatch):
    monkeypatch.delenv("LEARNKIT_OFFLINE", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert judge_offline() is False
    assert judge_status()["available"] is True


def test_substantive_response_passes_gate_offline(offline):
    ev = Evaluator()
    good = (
        "asyncio.gather runs awaitables concurrently and returns results in "
        "order. With return_exceptions=True it collects exceptions instead of "
        "propagating the first one. Use it to fan out I/O-bound coroutines."
    )
    r = ev.evaluate_with_llm_judge("Explain asyncio.gather", good)
    assert r.signal == EvaluationSignal.HEURISTIC
    assert r.score >= 3.5
    assert r.passes_threshold is True


def test_trivial_and_empty_fail_gate_offline(offline):
    ev = Evaluator()
    assert ev.evaluate_with_llm_judge("x", "ok").score < 3.5
    assert ev.evaluate_with_llm_judge("x", "").score < 3.5


def test_heuristic_score_is_deterministic():
    a = heuristic_score("t", "A reasonably detailed and complete answer here.")
    b = heuristic_score("t", "A reasonably detailed and complete answer here.")
    assert a == b
    assert 1.0 <= a[0] <= 4.5
