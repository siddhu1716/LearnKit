"""Quality ablation: does *injecting accumulated knowledge* actually make the
live model better — not just cheaper?

Replay and the tool-procedure scaffold reduce calls/tokens, but that is caching,
not learning. The honest test of learning is: on tasks the agent has NEVER
replayed, does the accumulated natural-language *playbook* raise the QUALITY of
the output? This benchmark isolates that with a 3-arm ablation over a stream of
novel sibling tasks (distinct tables, none ever replayed):

    cold       — BASE_SYSTEM only. No memory.
    procedure  — inject the bare tool-sequence scaffold (tool NAMES only, no
                 convention arguments). This is the pre-fix behavior: the model
                 learns the SHAPE of the task but none of the know-how.
    playbook   — inject the scaffold PLUS the accumulated natural-language
                 playbook (the post-fix behavior, via the real compose_context
                 path the agent uses live).

The task prompt is deliberately vague. Success depends on three domain
conventions that are stated ONLY in the playbook, never in the prompt or the
scaffold:

    1. filter to active records      -> filter(active='true')
    2. include a record count        -> aggregate(op='count')
    3. emit TSV for the ingest system-> format(fmt='tsv')

The verifier inspects the ACTUAL tool arguments and scores each task 0..3.

    cold vs procedure  -> value of the bare scaffold (shape only)
    procedure vs playbook -> value of the accumulated KNOW-HOW (the real question)

A flat line from procedure->playbook is an honest negative: injection did not
help. A rising line means the model genuinely applied knowledge it was given.

Run:
    python -m benchmarks.injection_ablation
"""

from benchmarks.react_live import (
    BASE_SYSTEM,
    GUIDED_SUFFIX,
    MODEL,
    react_loop,
)
from learnkit.composer import compose_context
from learnkit.inference_mode import InferenceMode
from learnkit.schemas.skill import SkillRecord
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory

# ── Novel sibling tasks (distinct tables, never replayed) ─────────────────────
# Vague on purpose: it does NOT reveal the compliance conventions.
TABLES = ["users", "orders", "products", "items",
          "customers", "invoices", "payments", "accounts"]
TASK = "Prepare the compliance export for the {t} table."

# ── The three hidden conventions, checked against real tool arguments ─────────
CONVENTIONS = ("filter_active", "record_count", "tsv_output")


def _compliance(tracker: ToolTracker) -> tuple[int, dict]:
    """Score 0..3: how many compliance conventions the agent actually satisfied."""
    def used(tool: str, key: str, value: str) -> bool:
        for c in tracker.calls:
            if c["tool"] != tool:
                continue
            arg = (c.get("input") or {}).get(key, "")
            if str(arg).strip().lower() == value:
                return True
        return False

    hits = {
        "filter_active": used("filter", "active", "true"),
        "record_count": used("aggregate", "op", "count"),
        "tsv_output": used("format", "fmt", "tsv"),
    }
    return sum(hits.values()), hits


# ── Memory records that get injected (the only difference between arms) ────────
def _skill(with_playbook: bool) -> SkillRecord:
    """A proven procedure for the compliance-export family. The scaffold lists
    tool NAMES only (no convention args). When ``with_playbook`` is set, the
    accumulated know-how — the conventions — is attached as the playbook."""
    rec = SkillRecord(
        domains={"pipeline": 1.0},
        task_type="compliance-export",
        content={
            "procedure": [{"tool": "query"}, {"tool": "filter"},
                          {"tool": "aggregate"}, {"tool": "format"}],
            "tool_sequence": ["query", "filter", "aggregate", "format"],
            "tools_used": ["query", "filter", "aggregate", "format"],
        },
        status="active",
    )
    rec.confidence = 0.9
    rec.reuse_count = 12
    if with_playbook:
        rec.content["playbook"] = [
            "Compliance exports must be filtered to active records only via filter active='true'",
            "Every compliance export must include a record count via aggregate op='count'",
            "The compliance ingest system requires TSV output via format fmt='tsv'",
            "Read the table first, then filter, then count, then format",
        ]
        rec.content["pitfalls"] = [
            "Never emit CSV or JSON for a compliance export; the ingest system rejects them",
        ]
    return rec


def _system_for(arm: str, task: str) -> str:
    if arm == "cold":
        return BASE_SYSTEM
    rec = _skill(with_playbook=(arm == "playbook"))
    context = compose_context([rec], task=task, inference_mode=InferenceMode.GUIDED)
    return BASE_SYSTEM + GUIDED_SUFFIX + context


def run_arm(arm: str) -> dict:
    s = {"score": 0, "full": 0, "tool_calls": 0, "llm_calls": 0, "tasks": 0,
         "filter_active": 0, "record_count": 0, "tsv_output": 0, "rows": []}
    for t in TABLES:
        task = TASK.format(t=t)
        tracker = ToolTracker(Trajectory(task=task))
        system = _system_for(arm, task)
        _final, llm = react_loop(task, system, tracker)
        score, hits = _compliance(tracker)
        s["score"] += score
        s["full"] += 1 if score == 3 else 0
        s["tool_calls"] += sum(1 for c in tracker.calls if c["productive"])
        s["llm_calls"] += llm
        s["tasks"] += 1
        for k in CONVENTIONS:
            s[k] += 1 if hits[k] else 0
        s["rows"].append((t, score, hits))
    return s


def main() -> None:
    print(f"model: {MODEL}   novel sibling tasks: {len(TABLES)}   "
          f"(none replayed; conventions live only in the playbook)\n")

    arms = ["cold", "procedure", "playbook"]
    results = {a: run_arm(a) for a in arms}

    n = len(TABLES)
    print("  arm       | avg score /3 | full 3/3 | filter | count |  tsv | tool/ta | llm")
    print("  " + "-" * 78)
    for a in arms:
        r = results[a]
        print(f"  {a:<9} | {r['score']/n:>11.2f}  | {r['full']:>4}/{n:<3} | "
              f"{r['filter_active']:>4}/{n} | {r['record_count']:>3}/{n} | "
              f"{r['tsv_output']:>3}/{n} | {r['tool_calls']/n:>6.2f}  | {r['llm_calls']}")
    print("  " + "-" * 78)

    cold, proc, pb = results["cold"], results["procedure"], results["playbook"]
    d_scaffold = (proc["score"] - cold["score"]) / n
    d_playbook = (pb["score"] - proc["score"]) / n
    print(f"\n  scaffold effect  (procedure - cold):     {d_scaffold:+.2f} avg compliance points")
    print(f"  PLAYBOOK effect  (playbook - procedure): {d_playbook:+.2f} avg compliance points")
    print(f"  full-compliance: cold {cold['full']}/{n} -> procedure {proc['full']}/{n} "
          f"-> playbook {pb['full']}/{n}")

    if d_playbook > 0.25:
        print("\n  VERDICT: the agent applied accumulated know-how it could not have")
        print("           inferred from the prompt or scaffold. Injection genuinely helped.")
    elif d_playbook <= 0.0:
        print("\n  VERDICT: injecting the playbook did NOT improve quality. Honest negative —")
        print("           the loop is wired but the model is not using the knowledge here.")
    else:
        print("\n  VERDICT: marginal/mixed. The playbook moved quality a little; not decisive.")


if __name__ == "__main__":
    main()
