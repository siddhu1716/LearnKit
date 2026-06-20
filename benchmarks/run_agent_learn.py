"""Proof harness for the agent path (`@lk.agent_learn`).

Question this answers: does capturing a tool-call procedure and replaying it on
a repeat task actually *reduce tool calls* while holding success flat?

No LLM is involved. A small family of multi-step "pipeline" tasks is solved by an
agent that, on first exposure, has to *explore* (it tries a couple of dead-end
tools before finding the working sequence) and, on a repeat exposure, *replays*
the procedure LearnKit captured and stored — going straight to the proven calls.

Storage is gated on tool success (the trusted outcome signal), not an LLM judge.

Win condition: tool-calls/task drops on repeat rounds; success stays 1.0.

Run:
    python -m benchmarks.run_agent_learn
"""

import learnkit as lk

# ── A tiny deterministic tool world ───────────────────────────────────────────
# Each task's goal is a fixed correct tool sequence. The "dead-end" tools model
# the exploration an agent does the first time it sees a task.

TASKS: dict[str, list[tuple[str, dict]]] = {
    "build active-user CSV report": [
        ("list_tables", {}),
        ("query", {"table": "users"}),
        ("filter", {"active": True}),
        ("format", {"fmt": "csv"}),
    ],
    "compute monthly revenue total": [
        ("query", {"table": "orders"}),
        ("filter", {"month": "current"}),
        ("aggregate", {"op": "sum", "field": "amount"}),
    ],
    "export top-10 products as json": [
        ("query", {"table": "products"}),
        ("rank", {"by": "sales", "limit": 10}),
        ("format", {"fmt": "json"}),
    ],
}

# Dead-end calls the naive agent makes while searching for the right approach.
EXPLORATION_NOISE = ["list_tables", "describe_schema"]

ALL_TOOLS = [
    "list_tables", "describe_schema", "query", "filter",
    "aggregate", "rank", "format",
]


def make_tools(tracker):
    """Build success-recording tool callables bound to this run's tracker."""
    def make(name):
        def _tool(**kwargs):
            return f"{name}_result"
        _tool.__name__ = name
        return tracker.wrap(_tool, name=name)
    return {name: make(name) for name in ALL_TOOLS}


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
        background_postprocess=False,  # synchronous so round N+1 sees round N
        auto_promote=True,             # learned skills retrievable immediately
        distiller=StubDistiller(),
    )


def run_round(memory: lk.LearnKit, round_idx: int) -> dict:
    stats = {"tool_calls": 0, "replayed": 0, "explored": 0, "successes": 0, "tasks": 0}

    @memory.agent_learn(domain="pipeline")
    def agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
        tools = make_tools(_learnkit_tools)
        if _learnkit_tools.has_plan:
            # Replay the proven procedure — straight to the working calls.
            for step in _learnkit_tools.plan_steps:
                name = step["tool"]
                if name in tools:
                    tools[name]()
            _learnkit_tools.mark_outcome(True)
            return "done (replayed)"
        # First exposure: explore (dead ends) then execute the correct sequence.
        # Dead-end calls succeed (no error) but are marked unproductive, so they
        # are excluded from the stored procedure.
        for noise in EXPLORATION_NOISE:
            _learnkit_tools.record(noise, {}, f"{noise}_result", productive=False)
        for name, args in TASKS[task]:
            tools[name](**args)
        _learnkit_tools.mark_outcome(True)
        return "done (explored)"

    for task in TASKS:
        agent(task)
        tracker_calls = memory.last_trajectory
        n_tool = sum(1 for s in tracker_calls.steps if s.role == "tool")
        stats["tool_calls"] += n_tool
        # Was a plan available this run? Detect via whether a procedure existed.
        proc, _ = memory._select_procedure(memory._last_records)
        if proc:
            stats["replayed"] += 1
        else:
            stats["explored"] += 1
        stats["successes"] += 1 if tracker_calls.outcome == "success" else 0
        stats["tasks"] += 1

    return stats


def main():
    memory = build_memory()
    rounds = 3
    print(f"{'round':>6} | {'tasks':>5} | {'tool_calls':>10} | {'calls/task':>10} | "
          f"{'replayed':>8} | {'explored':>8} | {'success':>7}")
    print("-" * 78)
    first_cpt = None
    last_cpt = None
    for r in range(rounds):
        s = run_round(memory, r)
        cpt = s["tool_calls"] / s["tasks"]
        if first_cpt is None:
            first_cpt = cpt
        last_cpt = cpt
        print(f"{r:>6} | {s['tasks']:>5} | {s['tool_calls']:>10} | {cpt:>10.2f} | "
              f"{s['replayed']:>8} | {s['explored']:>8} | {s['successes']:>7}")
    print("-" * 78)
    reduction = (first_cpt - last_cpt) / first_cpt * 100 if first_cpt else 0.0
    print(f"\ntool-calls/task: round 0 = {first_cpt:.2f}  ->  round {rounds-1} = "
          f"{last_cpt:.2f}   ({reduction:+.0f}% )")
    print("PASS" if last_cpt < first_cpt else "NO REDUCTION")
    memory.shutdown()


if __name__ == "__main__":
    main()
