"""Tests for the auto-replay ReAct runner (``learnkit.run_react_agent``).

Deterministic, no LLM: a stub planner drives the cold run, and the warm run must
auto-short-circuit into procedure replay with zero planning calls.
"""

import learnkit as lk
from learnkit import LLMStep, Observation, ToolCall, run_react_agent
from learnkit.classifier import ClassificationOutput


def _fake_classifier(task):
    return ClassificationOutput(
        task_type="pipeline", domains={"pipeline": 0.9}, complexity="medium"
    )


class _StubDistiller:
    """No prose distillation — the procedural builder captures the plan offline."""

    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None


def _build_memory():
    return lk.LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        background_postprocess=False,  # synchronous so the warm run sees the cold run
        auto_promote=True,             # learned procedure retrievable immediately
        classifier=_fake_classifier,
        distiller=_StubDistiller(),
    )


def _tools():
    def make(name):
        def _tool(**kwargs):
            return f"{name}_result"

        return _tool

    return {n: make(n) for n in ["list_tables", "query", "filter", "format"]}


TASK = "build active-user CSV report"


def _cold_planner(task, context, history):
    # One planning turn: explore once (unproductive) then run the real sequence.
    return LLMStep(
        tool_calls=[
            ToolCall("list_tables", {}),
            ToolCall("query", {"table": "users"}),
            ToolCall("filter", {"active": True}),
            ToolCall("format", {"fmt": "csv"}),
        ],
        final="done",
    )


def _forbidden_planner(task, context, history):
    raise AssertionError("planner must not be called on an exact procedure replay")


def test_auto_replay_short_circuits_exact_match():
    memory = _build_memory()

    # ── Cold run: the planner explores; the productive path is captured. ──
    cold = run_react_agent(
        memory,
        TASK,
        _tools(),
        _cold_planner,
        exploration_tools={"list_tables"},
        mark_success=True,
    )
    assert cold.replayed is False
    assert cold.llm_calls == 1
    # list_tables was flagged as exploration → excluded from the stored procedure.
    assert cold.tool_calls == 4

    # ── Warm run: identical task must auto-replay with zero planning calls. ──
    warm = run_react_agent(
        memory,
        TASK,
        _tools(),
        _forbidden_planner,  # would raise if the loop ran the model
        mark_success=True,
    )
    assert warm.replayed is True
    assert warm.plan_kind == "exact"
    assert warm.llm_calls == 0
    # Only the 3 productive steps (query → filter → format) are replayed.
    assert warm.tool_calls == 3


def test_observation_dataclass_roundtrip():
    obs = Observation("query", {"table": "users"}, "rows", True)
    assert obs.name == "query"
    assert obs.success is True
