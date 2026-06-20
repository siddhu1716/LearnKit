"""Agentic benchmark for the agent path (`@lk.agent_learn`) — AP7.

The model-path benchmarks (BENCHMARK_SPEC.md) score *answer quality*. They
cannot measure what the agent path is for: doing the same work in fewer tool
calls. This benchmark measures that directly, with two arms over an identical
task stream:

    cold_start   — a fresh, never-learning agent. Always explores. The baseline.
    warmed_start — a LearnKit agent that captures a procedure on first exposure
                   and replays it (auto-short-circuit) on repeats and on
                   *sibling* tasks via parameterized argument binding.

The stream deliberately mixes:
    • exact repeats        — tests plain replay (AP3/AP4)
    • parameterized siblings — same task family, different slot values; tests the
      task-signature gate (AP5) + argument templating (AP6)
    • an unrelated task    — tests that the signature gate does NOT misfire and
      replay the wrong procedure.

Metrics (per arm): total tool calls, tool-calls/task, success rate, and the
reduction the warmed arm achieves over cold. No LLM — the tool world is
deterministic so the numbers are a clean measurement of the replay mechanism.

Run:
    python -m benchmarks.agentic_bench
"""

import learnkit as lk
from learnkit.replay import replay_plan

# ── A deterministic tool world ────────────────────────────────────────────────
ALL_TOOLS = [
    "list_tables", "describe_schema", "query", "filter",
    "aggregate", "rank", "format",
]
# Dead-end calls a naive agent makes while searching for the right approach.
EXPLORATION_NOISE = ["list_tables", "describe_schema"]


def make_tools():
    """Plain tool callables: name -> f(**kwargs) -> result string."""
    def make(name):
        def _tool(**kwargs):
            return f"{name}_result"
        return _tool
    return {name: make(name) for name in ALL_TOOLS}


# ── Task families ─────────────────────────────────────────────────────────────
# Each builder maps a task string -> the correct (tool, kwargs) sequence. Args
# that come from the task text (entity, fmt, limit) are the slots LearnKit will
# parameterize, so a sibling task replays the same procedure with new values.

def report_seq(entity: str, fmt: str):
    return [
        ("query", {"table": entity}),
        ("filter", {"active": "true"}),
        ("format", {"fmt": fmt}),
    ]


def topn_seq(entity: str, n: str, fmt: str):
    return [
        ("query", {"table": entity}),
        ("rank", {"by": "sales", "limit": n}),
        ("format", {"fmt": fmt}),
    ]


# (task string, correct sequence, slot-substitution map vs the family's first task)
# The substitution map is what a real agent derives by parsing the new task; it
# tells replay how to re-bind the stored procedure's slots.
STREAM = [
    # Family A — first exposure (explored & learned).
    ("export users report as csv", report_seq("users", "csv"), {}),
    # Family A — exact repeat (plain replay).
    ("export users report as csv", report_seq("users", "csv"), {}),
    # Family A — parameterized sibling (replay + arg binding: users->orders, csv->json).
    ("export orders report as json", report_seq("orders", "json"),
     {"users": "orders", "csv": "json"}),
    # Family B — first exposure (explored & learned).
    ("rank products by sales as csv", topn_seq("products", "10", "csv"), {}),
    # Family B — parameterized sibling (products->items, csv->json).
    ("rank items by sales as json", topn_seq("items", "10", "json"),
     {"products": "items", "csv": "json"}),
    # Unrelated task — signature gate must NOT replay a Family A/B procedure.
    ("compute monthly revenue total",
     [("query", {"table": "orders"}),
      ("aggregate", {"op": "sum", "field": "amount"})], {}),
]


class StubDistiller:
    """No prose distillation — the procedural builder does the work offline."""
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None


def build_memory() -> lk.LearnKit:
    return lk.LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        background_postprocess=False,  # synchronous so task N+1 sees task N
        auto_promote=True,             # learned skills retrievable immediately
        distiller=StubDistiller(),
    )


def run_warmed() -> dict:
    """LearnKit agent: capture on first exposure, replay on repeats/siblings."""
    memory = build_memory()
    tools = make_tools()
    stats = {"tool_calls": 0, "successes": 0, "replayed": 0, "explored": 0, "tasks": 0}

    for task, correct_seq, overrides in STREAM:
        @memory.agent_learn(domain="pipeline")
        def agent(task: str, _seq=correct_seq, _ov=overrides,
                  _learnkit_context: str = "", _learnkit_tools=None) -> str:
            if _learnkit_tools.has_plan:
                # Auto-short-circuit: execute the proven procedure directly,
                # re-binding slot args for this (possibly sibling) task.
                replay_plan(_learnkit_tools, tools, overrides=_ov)
                return "done (replayed)"
            # First exposure: explore dead ends (marked unproductive so they are
            # excluded from the stored procedure), then run the correct sequence.
            for noise in EXPLORATION_NOISE:
                _learnkit_tools.record(noise, {}, f"{noise}_result", productive=False)
            for name, kwargs in _seq:
                _learnkit_tools.record(name, kwargs, tools[name](**kwargs))
            _learnkit_tools.mark_outcome(True)
            return "done (explored)"

        had_plan = bool(
            memory._select_procedure(
                memory.retriever.retrieve(
                    task=task, domain_vector={}, scope=memory.scope, router=memory.router
                ),
                task=task,
            )[0]
        )
        agent(task)
        traj = memory.last_trajectory
        n_tool = sum(1 for s in traj.steps if s.role == "tool")
        # Correctness: the productive tool calls (the ones that count) must match
        # the task's correct sequence — tool names AND arguments. For a replayed
        # sibling this only passes if argument re-binding (AP6) produced the right
        # values, so this is the real test that parameterization works.
        productive = [
            (s.tool_name, dict(s.tool_input or {}))
            for s in traj.steps
            if s.role == "tool" and getattr(s, "productive", True)
        ]
        expected = [(name, kwargs) for name, kwargs in correct_seq]
        correct = productive == expected
        stats["tool_calls"] += n_tool
        stats["successes"] += 1 if (traj.outcome == "success" and correct) else 0
        stats["replayed"] += 1 if had_plan else 0
        stats["explored"] += 0 if had_plan else 1
        stats["tasks"] += 1

    memory.shutdown()
    return stats


def run_cold() -> dict:
    """Baseline agent: never learns, explores every single time."""
    tools = make_tools()
    stats = {"tool_calls": 0, "successes": 0, "replayed": 0, "explored": 0, "tasks": 0}
    for task, correct_seq, _ in STREAM:
        n_tool = len(EXPLORATION_NOISE) + len(correct_seq)
        for name, kwargs in correct_seq:
            tools[name](**kwargs)
        stats["tool_calls"] += n_tool
        stats["successes"] += 1
        stats["explored"] += 1
        stats["tasks"] += 1
    return stats


def _row(label, s):
    cpt = s["tool_calls"] / s["tasks"]
    return (f"{label:>12} | {s['tasks']:>5} | {s['tool_calls']:>10} | {cpt:>10.2f} | "
            f"{s['replayed']:>8} | {s['explored']:>8} | {s['successes']:>7}")


def main():
    cold = run_cold()
    warm = run_warmed()

    print(f"{'arm':>12} | {'tasks':>5} | {'tool_calls':>10} | {'calls/task':>10} | "
          f"{'replayed':>8} | {'explored':>8} | {'success':>7}")
    print("-" * 84)
    print(_row("cold_start", cold))
    print(_row("warmed", warm))
    print("-" * 84)

    cold_cpt = cold["tool_calls"] / cold["tasks"]
    warm_cpt = warm["tool_calls"] / warm["tasks"]
    reduction = (cold_cpt - warm_cpt) / cold_cpt * 100 if cold_cpt else 0.0
    print(f"\ntool-calls/task: cold = {cold_cpt:.2f}  ->  warmed = {warm_cpt:.2f}   "
          f"({reduction:+.0f}% )")
    print(f"replayed (incl. parameterized siblings): "
          f"{warm['replayed']}/{warm['tasks']}")
    print(f"success: cold {cold['successes']}/{cold['tasks']}  "
          f"warmed {warm['successes']}/{warm['tasks']}")

    # PASS: warmed reduces calls, holds success, replays >=3 (2 repeats/siblings
    # per family that should fire) and the unrelated task is NOT replayed.
    ok = (
        warm_cpt < cold_cpt
        and warm["successes"] == warm["tasks"]
        and warm["replayed"] >= 3
        and warm["replayed"] < warm["tasks"]
    )
    print("\nPASS" if ok else "\nFAIL")


if __name__ == "__main__":
    main()
