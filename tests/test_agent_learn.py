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


# ── evolution: reinforce / refine / demote (Hermes institutional knowledge) ──
from learnkit.procedure_evolution import (  # noqa: E402
    demote_procedure,
    reinforce_or_refine,
)
from learnkit.procedural import signature_fingerprint  # noqa: E402
from learnkit.schemas.skill import SkillRecord  # noqa: E402


class _FakeBackend:
    """Captures the last replaced record so tests can assert on persistence."""

    def __init__(self):
        self.replaced = []

    def replace(self, record):
        self.replaced.append(record)
        return record.id


def _proc_skill(steps):
    return SkillRecord(
        domains={},
        content={
            "procedure": [{"tool": f"t{i}", "arg_template": {}} for i in range(steps)],
            "tool_sequence": [f"t{i}" for i in range(steps)],
            "task_signature": ["export", "report"],
            "task_tokens": ["export", "report"],
        },
        status="active",
    )


def test_signature_fingerprint_is_order_independent():
    assert signature_fingerprint(["a", "b"]) == signature_fingerprint(["b", "a"])
    assert signature_fingerprint(["a"]) != signature_fingerprint(["a", "b"])


def test_reinforce_grows_confidence_and_reuse():
    backend = _FakeBackend()
    existing = _proc_skill(3)
    c0, r0 = existing.confidence, existing.reuse_count
    outcome = reinforce_or_refine(backend, existing, _proc_skill(3).content, score=5.0)
    assert outcome == "reinforced"
    assert existing.reuse_count == r0 + 1
    assert existing.confidence > c0
    assert existing.content["success_count"] == 1
    assert backend.replaced == [existing]


def test_refine_evolves_to_shorter_path():
    backend = _FakeBackend()
    existing = _proc_skill(4)
    g0 = existing.evolution_gen
    shorter = _proc_skill(2).content
    outcome = reinforce_or_refine(backend, existing, shorter, score=5.0)
    assert outcome == "refined"
    assert len(existing.content["procedure"]) == 2
    assert existing.evolution_gen == g0 + 1


def test_longer_path_does_not_replace():
    backend = _FakeBackend()
    existing = _proc_skill(2)
    outcome = reinforce_or_refine(backend, existing, _proc_skill(5).content, score=5.0)
    assert outcome == "reinforced"
    assert len(existing.content["procedure"]) == 2  # kept the shorter one


def test_reinforce_reactivates_quarantined():
    backend = _FakeBackend()
    existing = _proc_skill(3)
    existing.status = "quarantine"
    reinforce_or_refine(backend, existing, _proc_skill(3).content, score=5.0)
    assert existing.status == "active"


def test_demote_quarantines_after_repeated_failures():
    backend = _FakeBackend()
    rec = _proc_skill(3)
    q1 = demote_procedure(backend, rec, max_failures=2)
    assert q1 is False and rec.status == "active"
    assert rec.content["failure_count"] == 1
    q2 = demote_procedure(backend, rec, max_failures=2)
    assert q2 is True and rec.status == "quarantine"


def test_demote_quarantines_below_confidence_floor():
    backend = _FakeBackend()
    rec = _proc_skill(3)
    rec.confidence = 0.3
    quarantined = demote_procedure(backend, rec, max_failures=99, confidence_floor=0.25)
    assert quarantined is True  # 0.3 - 0.15 < 0.25


# ── playbook accumulation (Hermes-style growing skill body) ──────────────────
from learnkit.playbook import merge_insights  # noqa: E402


def test_merge_insights_dedups_case_insensitively_and_preserves_order():
    existing = ["Use arxiv cs.LG", "Skip survey papers"]
    new = ["skip survey papers.", "Format as bullet + link"]
    merged = merge_insights(existing, new)
    assert merged == ["Use arxiv cs.LG", "Skip survey papers", "Format as bullet + link"]


def test_merge_insights_caps_length():
    merged = merge_insights([f"durable insight number {i}" for i in range(20)], [], cap=5)
    assert len(merged) == 5


def test_merge_insights_ignores_blank_and_nonstring():
    merged = merge_insights(["keep this insight"], ["", "  ", 42, None, "add this insight"])
    assert merged == ["keep this insight", "add this insight"]


def test_merge_insights_drops_non_durable_bullets():
    durable = "Use arxiv cs.LG as the primary source"
    merged = merge_insights(
        [durable],
        [
            "ripgrep is not installed",            # environment/setup failure
            "the search tool doesn't work",        # negative tool claim
            "the request timed out, retry later",  # transient error
            "I clicked the third result this run",  # one-off narration
            "x",                                    # too short
            " ".join(["word"] * 40),               # too long
            "Prefer recent papers over surveys",   # durable -> kept
        ],
    )
    assert merged == [durable, "Prefer recent papers over surveys"]


def test_reinforce_accumulates_playbook_across_runs():
    backend = _FakeBackend()
    existing = _proc_skill(3)
    existing.content["playbook"] = ["Use arxiv cs.LG"]
    new_content = _proc_skill(3).content
    new_content["playbook"] = ["Skip survey papers"]
    new_content["pitfalls"] = ["Do not post without a link"]

    reinforce_or_refine(backend, existing, new_content, score=5.0)

    assert existing.content["playbook"] == ["Use arxiv cs.LG", "Skip survey papers"]
    assert existing.content["pitfalls"] == ["Do not post without a link"]


def test_reinforce_playbook_dedups_repeat_knowledge():
    backend = _FakeBackend()
    existing = _proc_skill(3)
    existing.content["playbook"] = ["Use arxiv cs.LG"]
    new_content = _proc_skill(3).content
    new_content["playbook"] = ["use arxiv cs.LG."]  # same insight, different casing

    reinforce_or_refine(backend, existing, new_content, score=5.0)

    assert existing.content["playbook"] == ["Use arxiv cs.LG"]


def test_procedural_skill_md_renders_playbook():
    skill = _proc_skill(2)
    skill.task_type = "weekly-arxiv-digest"
    skill.content["playbook"] = ["Use arxiv cs.LG + cs.AI", "Skip surveys"]
    skill.content["pitfalls"] = ["Do not post without a link"]
    md = skill.to_skill_md()
    assert "## Playbook (learned knowledge)" in md
    assert "Use arxiv cs.LG + cs.AI" in md
    assert "Do not post without a link" in md  # pitfalls fold into failure modes


def test_compose_context_injects_playbook_into_agent_prompt():
    """Closing the learning loop: accumulated know-how must reach the model, not
    just the exported SKILL.md. A guided/sibling task should see the playbook."""
    from learnkit.composer import compose_context
    from learnkit.inference_mode import InferenceMode

    skill = _proc_skill(2)
    skill.task_type = "weekly-arxiv-digest"
    skill.content["playbook"] = ["Prefer arxiv cs.LG as the primary source"]
    skill.content["pitfalls"] = ["Do not post a paper without a link"]

    ctx = compose_context([skill], task="build this week's digest",
                          inference_mode=InferenceMode.GUIDED)

    assert "Playbook (learned know-how)" in ctx
    assert "Prefer arxiv cs.LG as the primary source" in ctx
    assert "Do not post a paper without a link" in ctx  # pitfalls -> watch out for


# ── end-to-end: reflection authors + accumulates playbook through core ───────
import learnkit as lk  # noqa: E402


class _ReflectingDistiller:
    """Distiller that abstains on prose but authors a fixed playbook per run."""

    def __init__(self, playbooks):
        self._playbooks = list(playbooks)
        self._i = 0

    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None

    def reflect_procedure(self, trajectory, tool_sequence, domain_vector):
        pb = self._playbooks[min(self._i, len(self._playbooks) - 1)]
        self._i += 1
        return {"playbook": pb, "pitfalls": []}


def _stored_procedure(memory):
    recs = [r for r in memory.backend.list_by_scope(memory.scope, limit=100)
            if getattr(r, "type", None) == "skill" and r.content.get("procedure")]
    return recs[0] if recs else None


def test_reflection_authors_and_accumulates_playbook_end_to_end():
    memory = lk.LearnKit(
        memory_backend="sqlite", db_path=":memory:",
        background_postprocess=False, auto_promote=True,
        reflect_procedures=True,
        distiller=_ReflectingDistiller([
            ["Use arxiv cs.LG"],
            ["Skip survey papers"],
        ]),
    )

    task = "Build a report from the users table then filter then format as csv"

    @memory.agent_learn(domain="pipeline")
    def agent(task, _learnkit_context="", _learnkit_tools=None):
        _learnkit_tools.record("query", {"table": "users"}, "rows", success=True)
        _learnkit_tools.record("filter", {"active": "true"}, "filtered", success=True)
        _learnkit_tools.record("format", {"fmt": "csv"}, "csv", success=True)
        _learnkit_tools.mark_outcome(True)
        return "done"

    agent(task)
    rec = _stored_procedure(memory)
    assert rec is not None
    assert rec.content["playbook"] == ["Use arxiv cs.LG"]

    # Second exposure accumulates new knowledge into the same procedure.
    agent(task)
    rec = _stored_procedure(memory)
    assert rec.content["playbook"] == ["Use arxiv cs.LG", "Skip survey papers"]
    memory.shutdown()


def test_reflection_off_by_default():
    memory = lk.LearnKit(
        memory_backend="sqlite", db_path=":memory:",
        background_postprocess=False, auto_promote=True,
        distiller=_ReflectingDistiller([["should not appear"]]),
    )
    task = "Build a report from the orders table then filter then format as json"

    @memory.agent_learn(domain="pipeline")
    def agent(task, _learnkit_context="", _learnkit_tools=None):
        _learnkit_tools.record("query", {"table": "orders"}, "rows", success=True)
        _learnkit_tools.record("format", {"fmt": "json"}, "json", success=True)
        _learnkit_tools.mark_outcome(True)
        return "done"

    agent(task)
    rec = _stored_procedure(memory)
    assert rec is not None
    assert "playbook" not in rec.content
    memory.shutdown()


