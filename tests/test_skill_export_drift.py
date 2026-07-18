"""Tests for the Deep Agents SKILL.md exporter (B2) and drift detector (B1)."""

import json

import learnkit as lk
from learnkit import LLMStep, ToolCall, check_drift, export_golden_suite, run_react_agent
from learnkit.classifier import ClassificationOutput
from learnkit.schemas.skill import SkillRecord


# ── B2: Deep Agents renderer (pure, no store) ────────────────────────────────


def test_to_deepagents_md_frontmatter_and_tools():
    rec = SkillRecord(
        domains={"pipeline": 0.9},
        task_type="build_report",
        content={
            "trigger": "Build an active-user CSV report",
            "tool_sequence": ["query", "filter", "format"],
            "procedure": [
                {"tool": "query", "args": {"table": "users"}},
                {"tool": "filter", "args": {"active": True}},
                {"tool": "format", "args": {"fmt": "csv"}},
            ],
        },
    )
    md = rec.to_deepagents_md()
    assert md.startswith("---\n")
    assert "name: build-report" in md
    assert 'description: "Build an active-user CSV report"' in md
    assert "allowed-tools: query, filter, format" in md
    assert "## Steps" in md
    assert "Call `query`" in md


# ── Shared offline agent-path memory (mirrors test_auto_replay) ──────────────


def _fake_classifier(task):
    return ClassificationOutput(
        task_type="pipeline", domains={"pipeline": 0.9}, complexity="medium"
    )


class _StubDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None


def _memory_with_procedure():
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        background_postprocess=False,
        auto_promote=True,
        classifier=_fake_classifier,
        distiller=_StubDistiller(),
    )

    def tools():
        return {n: (lambda **k: f"{n}_result") for n in ["list_tables", "query", "filter", "format"]}

    def planner(task, context, history):
        return LLMStep(
            tool_calls=[
                ToolCall("list_tables", {}),
                ToolCall("query", {"table": "users"}),
                ToolCall("filter", {"active": True}),
                ToolCall("format", {"fmt": "csv"}),
            ],
            final="done",
        )

    run_react_agent(
        memory, "build active-user CSV report", tools(), planner,
        exploration_tools={"list_tables"}, mark_success=True,
    )
    return memory


def test_export_deepagents_skill_library(tmp_path):
    memory = _memory_with_procedure()
    out = tmp_path / "skills"
    n = memory.export_skill_library(out, fmt="deepagents")
    assert n == 1
    md_files = list(out.glob("**/SKILL.md"))
    assert len(md_files) == 1
    text = md_files[0].read_text(encoding="utf-8")
    assert "name:" in text and "allowed-tools:" in text
    # list_tables was exploration → excluded from the captured procedure.
    assert "list_tables" not in text.split("allowed-tools:")[1].splitlines()[0]


def test_export_golden_suite(tmp_path):
    memory = _memory_with_procedure()
    path = tmp_path / "golden.json"
    count = export_golden_suite(memory, path)
    assert count == 1
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["tool_sequence"] == ["query", "filter", "format"]


# ── B1: drift detector (pure) ────────────────────────────────────────────────

GOLDEN = ["query", "filter", "format"]


def test_check_drift_exact_match():
    r = check_drift(GOLDEN, ["query", "filter", "format"], "build_report")
    assert r.ok is True
    assert r.added_call_count == 0
    assert not r.extra and not r.missing


def test_check_drift_extra_step():
    r = check_drift(GOLDEN, ["list_tables", "query", "filter", "format"])
    assert r.ok is False
    assert r.extra == ["list_tables"]
    assert r.added_call_count == 1
    assert "drift" in r.summary


def test_check_drift_reordered():
    r = check_drift(GOLDEN, ["query", "format", "filter"])
    assert r.ok is False
    assert r.reordered is True
    assert not r.extra and not r.missing


def test_check_drift_missing_step():
    r = check_drift(GOLDEN, ["query", "format"])
    assert r.ok is False
    assert r.missing == ["filter"]
    assert r.added_call_count == -1
