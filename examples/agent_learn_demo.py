"""
LearnKit agent-path example — `@lk.agent_learn` (procedure capture & replay)
============================================================================

The model path (`@lk.learn`) treats an agent as a black box: a task goes in, an
answer comes out, and only that final answer is judged and distilled. It cannot
learn *how* the agent got there.

The agent path (`@lk.agent_learn`) learns the **procedure** — the sequence of
tool calls — not just the answer. On the first exposure to a task the agent
explores (and may hit dead ends); LearnKit captures the *cleaned* successful
tool sequence as a reusable procedural skill. On the next exposure it recognises
the task, attaches the stored procedure, and the agent **replays** it directly —
no re-derivation, far fewer tool calls. This is the tool-calls-per-task
reduction the agent path is measured on.

This demo is fully offline and deterministic: the "tools" are plain Python
functions and distillation is stubbed, so it needs **no API key** and runs in
CI as a smoke test. Expected output:

    RUN 1 — cold:  6 tool calls  (2 dead-end + 4 productive, procedure captured)
    RUN 2 — warm:  4 tool calls  (procedure replayed, 0 dead ends)

Run:
    python examples/agent_learn_demo.py
"""

import logging
import sys

import learnkit as lk
from learnkit.replay import replay_plan

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Quiet library logs so the demo output stays readable. Offline, the task
# classifier can't reach an LLM and logs a benign fallback warning — silence
# WARNING/INFO chatter from LearnKit, dspy and litellm; procedure matching
# works from the task signature regardless of classification.
logging.disable(logging.WARNING)


# ── Deterministic "tools" ────────────────────────────────────────────────
# Stand-ins for real side-effecting tools (DB lookups, API calls, ...). Each
# returns a canned value so the demo is reproducible without a network.
def find_user(email: str) -> str:
    return "user_42"


def list_orders(user_id: str) -> list[str]:
    return ["order_1001"]


def get_order(order_id: str) -> dict:
    return {"id": order_id, "total": 49.0, "status": "delivered"}


def issue_refund(order_id: str, amount: float) -> str:
    return f"refunded ${amount:.2f} on {order_id}"


TOOLS = {
    "find_user": find_user,
    "list_orders": list_orders,
    "get_order": get_order,
    "issue_refund": issue_refund,
}

# The correct 4-step procedure for this task family.
CORRECT_SEQUENCE = [
    ("find_user", {"email": "ada@example.com"}),
    ("list_orders", {"user_id": "user_42"}),
    ("get_order", {"order_id": "order_1001"}),
    ("issue_refund", {"order_id": "order_1001", "amount": 49.0}),
]

# Dead ends the agent wanders into before finding the right path. Recorded as
# unproductive so they are EXCLUDED from the stored procedure — replay follows
# only the cleaned successful path.
DEAD_ENDS = ["search_faq", "open_ticket"]


class StubDistiller:
    """No LLM prose distillation — the offline procedural builder captures the
    tool sequence on its own, so the demo never needs an API key."""

    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *args, **kwargs):
        return None


def build_memory() -> lk.LearnKit:
    return lk.LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        background_postprocess=False,  # synchronous: run 2 sees run 1's capture
        auto_promote=True,             # learned procedure is retrievable at once
        distiller=StubDistiller(),
    )


def run_task(memory: lk.LearnKit, task: str, label: str) -> int:
    """Run the agent once and return the number of tool calls it made."""

    @memory.agent_learn(domain="support")
    def agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
        # Warm path: an exact procedure was retrieved → replay it directly.
        if _learnkit_tools.plan_kind == "exact":
            replay_plan(_learnkit_tools, TOOLS)  # zero re-derivation
            return "done (replayed stored procedure)"

        # Cold path: explore (dead ends marked unproductive), then run the
        # correct sequence. `record` logs each call with its flat kwargs so the
        # captured arg_template can be re-bound and replayed verbatim later.
        for noise in DEAD_ENDS:
            _learnkit_tools.record(noise, {}, f"{noise}: no help", productive=False)

        for name, kwargs in CORRECT_SEQUENCE:
            output = TOOLS[name](**kwargs)
            _learnkit_tools.record(name, kwargs, output)

        _learnkit_tools.mark_outcome(True)  # tool-success gate → capture skill
        return "done (explored and captured procedure)"

    result = agent(task)
    traj = memory.last_trajectory
    calls = sum(1 for s in traj.steps if s.role == "tool")
    print(f"  {label}: {calls} tool calls — {result}")
    return calls


def main() -> None:
    memory = build_memory()
    task = "Refund the most recent delivered order for ada@example.com"

    print("=" * 72)
    print("RUN 1 — cold (no stored procedure yet)")
    print("=" * 72)
    cold = run_task(memory, task, "cold")

    print("\n" + "=" * 72)
    print("RUN 2 — warm (procedure captured in run 1 is replayed)")
    print("=" * 72)
    warm = run_task(memory, task, "warm")

    memory.shutdown(wait=True)

    print("\n" + "=" * 72)
    print(f"Tool calls: {cold} (cold) -> {warm} (warm)")
    if warm < cold:
        print("Procedure replay cut tool calls by "
              f"{cold - warm} ({100 * (cold - warm) // cold}%).")
    else:
        print("No reduction — check that the procedure was captured and matched.")
    print("=" * 72)

    # Make the smoke test fail loudly in CI if the value loop regresses.
    assert warm <= cold, "warm run must not use more tool calls than the cold run"


if __name__ == "__main__":
    main()
