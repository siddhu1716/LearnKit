"""Tests for the procedural agent path (`@lk.agent_learn`): procedure extraction,
task-signature matching (AP5), argument parameterization (AP6), and replay (AP4).
"""

from learnkit.procedural import (
    extract_procedure,
    match_kind,
    procedure_fingerprint,
    signature_coverage,
    task_signature,
)
from learnkit.replay import bind_args, replay_plan
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory


def _traj(task, calls):
    """Build a trajectory of (tool, args, productive) tuples."""
    t = Trajectory(task=task)
    t.add_step("user", task)
    for tool, args, productive in calls:
        t.add_step("tool", f"{tool}_result", tool_name=tool,
                   tool_input=args, productive=productive)
    return t


# ── extraction + productive-path cleaning ────────────────────────────────────
def test_extract_skips_unproductive_steps():
    t = _traj("export users report as csv", [
        ("list_tables", {}, False),       # dead end
        ("query", {"table": "users"}, True),
        ("format", {"fmt": "csv"}, True),
    ])
    proc = extract_procedure(t)
    assert proc is not None
    assert proc["tool_sequence"] == ["query", "format"]
    assert proc["call_count"] == 2


def test_extract_returns_none_without_tool_steps():
    t = Trajectory(task="just thinking")
    t.add_step("user", "just thinking")
    t.add_step("assistant", "an answer")
    assert extract_procedure(t) is None


# ── AP6 argument parameterization ────────────────────────────────────────────
def test_task_derived_args_become_slots():
    t = _traj("export users report as csv", [
        ("query", {"table": "users"}, True),
        ("filter", {"active": "true"}, True),   # 'true' not in task -> literal
        ("format", {"fmt": "csv"}, True),
    ])
    proc = extract_procedure(t)
    steps = {s["tool"]: s["arg_template"] for s in proc["procedure"]}
    assert steps["query"]["table"] == {"__slot__": "users"}
    assert steps["format"]["fmt"] == {"__slot__": "csv"}
    assert steps["filter"]["active"] == "true"  # untouched literal


def test_bind_args_rebinds_slots_for_sibling_task():
    template = {"table": {"__slot__": "users"}, "active": "true"}
    bound = bind_args(template, overrides={"users": "orders"})
    assert bound == {"table": "orders", "active": "true"}


def test_bind_args_falls_back_to_original_without_override():
    template = {"fmt": {"__slot__": "csv"}}
    assert bind_args(template, overrides={}) == {"fmt": "csv"}


# ── AP5 task-signature matching ──────────────────────────────────────────────
def test_signature_excludes_slot_values_and_numbers():
    t = _traj("rank top 10 products as csv", [
        ("query", {"table": "products"}, True),   # 'products' becomes a slot
        ("rank", {"by": "sales", "limit": "10"}, True),
        ("format", {"fmt": "csv"}, True),
    ])
    sig = extract_procedure(t)["task_signature"]
    # 'products' and 'csv' are slot values; '10' is numeric; 'as' is a stopword.
    assert "rank" in sig and "top" in sig
    assert "products" not in sig and "csv" not in sig and "10" not in sig


def test_signature_coverage_matches_sibling_rejects_unrelated():
    stored = ["export", "report"]
    assert signature_coverage(stored, "export orders report as json") == 1.0
    assert signature_coverage(stored, "compute monthly revenue total") == 0.0


def test_signature_coverage_empty_defers_to_retriever():
    assert signature_coverage([], "anything") == 1.0


# ── match classification (exact vs sibling vs none) ──────────────────────────
def test_match_kind_exact_sibling_none():
    t = _traj("export users report as csv", [
        ("query", {"table": "users"}, True),
        ("format", {"fmt": "csv"}, True),
    ])
    proc = extract_procedure(t)
    sig, toks = proc["task_signature"], proc["task_tokens"]

    # Same task -> exact.
    assert match_kind(sig, toks, "export users report as csv") == "exact"
    # Same family, different slot values -> sibling.
    assert match_kind(sig, toks, "export orders report as json") == "sibling"
    # Unrelated -> no match.
    assert match_kind(sig, toks, "compute monthly revenue total") is None


# ── fingerprint stability ────────────────────────────────────────────────────
def test_fingerprint_is_order_sensitive_and_case_insensitive():
    assert procedure_fingerprint(["A", "b"]) == procedure_fingerprint(["a", "B"])
    assert procedure_fingerprint(["a", "b"]) != procedure_fingerprint(["b", "a"])


# ── AP4 replay primitive ─────────────────────────────────────────────────────
def test_replay_plan_executes_and_records_calls():
    tracker = ToolTracker(Trajectory(task="export orders report as json"))
    tracker.set_plan([
        {"tool": "query", "arg_template": {"table": {"__slot__": "users"}}},
        {"tool": "format", "arg_template": {"fmt": {"__slot__": "csv"}}},
    ], source_id="skill-1")

    seen = []
    tools = {
        "query": lambda **kw: seen.append(("query", kw)) or "ok",
        "format": lambda **kw: seen.append(("format", kw)) or "ok",
    }
    n = replay_plan(tracker, tools, overrides={"users": "orders", "csv": "json"})

    assert n == 2
    assert seen == [("query", {"table": "orders"}), ("format", {"fmt": "json"})]
    assert tracker.call_count == 2
    assert tracker.outcome_score() == 5.0  # marked success


def test_replay_plan_without_plan_raises():
    tracker = ToolTracker(Trajectory(task="x"))
    try:
        replay_plan(tracker, {})
        assert False, "expected ValueError"
    except ValueError:
        pass
