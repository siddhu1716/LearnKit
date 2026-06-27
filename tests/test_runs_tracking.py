"""Unit tests for agent-run tracking (runs table) used by the dashboard.

These cover the persistence layer added to power the live "how your agent is
learning" view: per-run rows, family baselines, calls-reduced, and per-agent
aggregate summaries. No LLM/API key is required.
"""

from learnkit.backends.sqlite import SQLiteBackend


def _make_run(run_id, agent_id, tool_calls, *, signature_fp="sig-a",
              replayed=0, outcome="success", baseline=None, calls_reduced=0.0,
              agent_name="Agent A"):
    return {
        "run_id": run_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task": f"task for {run_id}",
        "task_type": "debug",
        "domains": ["coding"],
        "tool_calls": tool_calls,
        "baseline_calls": baseline,
        "calls_reduced": calls_reduced,
        "replayed": replayed,
        "outcome": outcome,
        "quality_score": 5.0 if outcome == "success" else 1.0,
        "record_ids": ["r1", "r2"],
        "signature_fp": signature_fp,
        "steps": [{"step": 0, "role": "user", "tool_name": None, "content": "hi"}],
    }


def test_insert_and_get_run(tmp_path):
    backend = SQLiteBackend(db_path=str(tmp_path / "m.db"))
    backend.insert_run(_make_run("run-1", "agent-x", 3))

    got = backend.get_run("run-1")
    assert got is not None
    assert got["agent_id"] == "agent-x"
    assert got["tool_calls"] == 3
    assert got["domains"] == ["coding"]
    assert got["record_ids"] == ["r1", "r2"]
    assert got["steps"][0]["role"] == "user"


def test_family_baseline_average(tmp_path):
    backend = SQLiteBackend(db_path=str(tmp_path / "m.db"))
    # Two prior cold runs with the same signature: tool_calls 4 and 6 -> avg 5
    backend.insert_run(_make_run("run-1", "agent-x", 4, signature_fp="sig-a"))
    backend.insert_run(_make_run("run-2", "agent-x", 6, signature_fp="sig-a"))
    # A replayed run should be excluded from the baseline
    backend.insert_run(_make_run("run-3", "agent-x", 1, signature_fp="sig-a", replayed=1))

    assert backend.family_baseline("sig-a") == 5.0
    assert backend.family_baseline("sig-unknown") is None


def test_list_runs_filters(tmp_path):
    backend = SQLiteBackend(db_path=str(tmp_path / "m.db"))
    backend.insert_run(_make_run("run-1", "agent-x", 4, outcome="success"))
    backend.insert_run(_make_run("run-2", "agent-y", 5, outcome="failure"))
    backend.insert_run(_make_run("run-3", "agent-x", 2, outcome="failure"))

    assert len(backend.list_runs()) == 3
    assert len(backend.list_runs(agent_id="agent-x")) == 2
    assert len(backend.list_runs(outcome="failure")) == 2
    assert len(backend.list_runs(agent_id="agent-x", outcome="failure")) == 1


def test_agent_summaries_aggregates(tmp_path):
    backend = SQLiteBackend(db_path=str(tmp_path / "m.db"))
    # agent-x: 2 cold successes (skills) + 1 replayed success, calls reduced 3+2
    backend.insert_run(_make_run("r1", "agent-x", 4, replayed=0, outcome="success", calls_reduced=3.0))
    backend.insert_run(_make_run("r2", "agent-x", 2, replayed=0, outcome="success", calls_reduced=2.0))
    backend.insert_run(_make_run("r3", "agent-x", 1, replayed=1, outcome="success", calls_reduced=0.0))
    # agent-y: 1 failure
    backend.insert_run(_make_run("r4", "agent-y", 7, replayed=0, outcome="failure", calls_reduced=0.0))

    summaries = {s["agent_id"]: s for s in backend.agent_summaries()}
    assert set(summaries) == {"agent-x", "agent-y"}

    x = summaries["agent-x"]
    assert x["task_count"] == 3
    assert x["success_rate"] == 1.0
    assert x["calls_reduced"] == 5.0
    # skills_learned counts cold successes only (replayed excluded)
    assert x["skills_learned"] == 2

    y = summaries["agent-y"]
    assert y["task_count"] == 1
    assert y["success_rate"] == 0.0
    assert y["skills_learned"] == 0
