"""Live-LLM *evolution* benchmark for the agent path (`@lk.agent_learn`).

Where `react_live.py` proves a one-shot win (warmed < cold on a single stream),
this benchmark proves the Hermes thesis: the agent does not just replay — it
*evolves over time and accumulates institutional knowledge*. We run the same
task families across multiple ROUNDS against a real tool-calling LLM and watch:

    learning curve   — warmed LLM/tool calls trend DOWN round over round while
                       the cold agent stays flat (it re-explores every time).
    institutional KB — the stored procedures' confidence and reuse_count climb,
                       evolution_gen ticks up when a shorter path is found, and
                       failures quarantine bad procedures (self-healing).
    durable artifact — at the end the learned library is exported to on-disk
                       SKILL.md files (reviewable, versionable, shareable).

Persistence is a real sqlite file (not :memory:) so the library is a durable
artifact, mirroring how Hermes keeps skills on disk between sessions.

Config via env (defaults target the hosted Qwen endpoint):
    LK_BASE_URL   default http://206.1.58.252:8000/v1
    LK_MODEL      default Qwen/Qwen2.5-7B-Instruct
    LK_API_KEY    default "none"

Run:
    python -m benchmarks.evolution_live
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import learnkit as lk
from learnkit.replay import replay_plan
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory

_RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Reuse the exact tool world + ReAct loop from the one-shot live benchmark so the
# only new variable here is *time* (rounds), not the environment.
from benchmarks.react_live import (
    API_KEY,
    BASE_SYSTEM,
    BASE_URL,
    GUIDED_SUFFIX,
    MODEL,
    StubDistiller,
    TOOL_IMPLS,
    _verify,
    react_loop,
)
ROUNDS = 4

# Two families. The *canonical* task of each family is identical every round, so
# after it is learned once it is hard-replayed (zero LLM) on every later round.
# A fresh *sibling* (new table/format) appears each round — same procedure,
# different arguments — exercising guided (parameterized) reuse.
_REPORT = ("Build a report from the {t} table: first read the {t} table, then "
           "filter to active rows, then format the result as {f}.")
_TOPN = ("Produce a ranking from the {t} table: first read the {t} table, then "
         "rank rows by sales, then format the top 10 as {f}.")

CANON_REPORT = (_REPORT.format(t="users", f="CSV"), ["query", "filter", "format"])
CANON_TOPN = (_TOPN.format(t="products", f="CSV"), ["query", "rank", "format"])

# Per-round sibling slot values (different real instances of the same families).
REPORT_SIBLINGS = [
    (_REPORT.format(t="orders", f="JSON"), ["query", "filter", "format"]),
    (_REPORT.format(t="customers", f="CSV"), ["query", "filter", "format"]),
    (_REPORT.format(t="vendors", f="JSON"), ["query", "filter", "format"]),
    (_REPORT.format(t="invoices", f="CSV"), ["query", "filter", "format"]),
]
TOPN_SIBLINGS = [
    (_TOPN.format(t="items", f="JSON"), ["query", "rank", "format"]),
    (_TOPN.format(t="skus", f="CSV"), ["query", "rank", "format"]),
    (_TOPN.format(t="regions", f="JSON"), ["query", "rank", "format"]),
    (_TOPN.format(t="stores", f="CSV"), ["query", "rank", "format"]),
]


def _round_stream(r: int):
    """The 4 tasks for round ``r``: each family's canonical (repeats every round)
    plus a fresh sibling."""
    return [
        CANON_REPORT,
        REPORT_SIBLINGS[r % len(REPORT_SIBLINGS)],
        CANON_TOPN,
        TOPN_SIBLINGS[r % len(TOPN_SIBLINGS)],
    ]


def run_cold_round(r: int) -> dict:
    s = {"tool_calls": 0, "llm_calls": 0, "successes": 0, "tasks": 0}
    for task, required in _round_stream(r):
        tracker = ToolTracker(Trajectory(task=task))
        _, llm = react_loop(task, BASE_SYSTEM, tracker)
        s["tool_calls"] += tracker.call_count
        s["llm_calls"] += llm
        s["successes"] += 1 if _verify(required, tracker) else 0
        s["tasks"] += 1
    return s


def run_warmed_round(memory: lk.LearnKit, r: int) -> dict:
    s = {"tool_calls": 0, "llm_calls": 0, "successes": 0,
         "replayed": 0, "guided": 0, "tasks": 0}
    for task, required in _round_stream(r):
        llm_box = {"n": 0}
        req_box = {"r": required}

        @memory.agent_learn(domain="pipeline")
        def agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
            if _learnkit_tools.plan_kind == "exact":
                replay_plan(_learnkit_tools, TOOL_IMPLS)  # zero LLM
                llm_box["n"] = 0
                _learnkit_tools.mark_outcome(_verify(req_box["r"], _learnkit_tools))
                return "done (replayed)"
            system = BASE_SYSTEM
            if _learnkit_context and _learnkit_context.strip():
                system = BASE_SYSTEM + GUIDED_SUFFIX + _learnkit_context
            final, llm = react_loop(task, system, _learnkit_tools)
            llm_box["n"] = llm
            _learnkit_tools.mark_outcome(_verify(req_box["r"], _learnkit_tools))
            return final

        records = memory.retriever.retrieve(
            task=task, domain_vector={}, scope=memory.scope, router=memory.router)
        kind, _, _ = memory._match_procedure(records, task)

        agent(task)
        traj = memory.last_trajectory
        s["tool_calls"] += sum(1 for st in traj.steps if st.role == "tool")
        s["llm_calls"] += llm_box["n"]
        s["successes"] += 1 if traj.outcome == "success" else 0
        s["replayed"] += 1 if kind == "exact" else 0
        s["guided"] += 1 if kind == "sibling" else 0
        s["tasks"] += 1
    return s


def knowledge_snapshot(memory: lk.LearnKit) -> dict:
    """Read the stored procedures and summarise the institutional knowledge."""
    recs = [r for r in memory.backend.list_by_scope(memory.scope, limit=1000)
            if getattr(r, "type", None) == "skill" and r.content.get("procedure")]
    active = [r for r in recs if r.status == "active"]
    confs = [r.confidence for r in recs] or [0.0]
    reuse = [r.reuse_count for r in recs] or [0]
    return {
        "procedures": len(recs),
        "active": len(active),
        "quarantined": sum(1 for r in recs if r.status == "quarantine"),
        "max_reuse": max(reuse),
        "mean_conf": sum(confs) / len(confs),
        "evolution_gen": sum(r.evolution_gen for r in recs),
    }


def _build_reflecting_distiller():
    """A MemoryDistiller whose reflection LLM is the same hosted endpoint, so the
    playbook is authored by a real model. Enabled via LK_REFLECT=1."""
    import dspy
    from learnkit.distiller import MemoryDistiller

    lm = dspy.LM(f"openai/{MODEL}", api_base=BASE_URL, api_key=API_KEY,
                 temperature=0.0, max_tokens=512)
    d = MemoryDistiller(lm=lm)
    # Abstain on prose distillation; we only want the procedure + reflection here.
    d.distill = lambda trajectory, domain_vector, quality_score: (None, [], [], None)
    d.distill_failure = lambda *a, **k: None
    return d


def main():
    print(f"endpoint: {BASE_URL}  model: {MODEL}")
    reflect = os.environ.get("LK_REFLECT", "").lower() in ("1", "true", "yes")
    db_path = os.path.join(tempfile.gettempdir(), "learnkit_evolution.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    print(f"persistent store: {db_path}  reflection: {'ON' if reflect else 'OFF'}\n")

    memory = lk.LearnKit(
        memory_backend="sqlite", db_path=db_path,
        background_postprocess=False, auto_promote=True,
        reflect_procedures=reflect,
        distiller=_build_reflecting_distiller() if reflect else StubDistiller(),
    )

    hdr = (f"{'round':>5} | {'arm':>6} | {'tool':>4} | {'llm':>4} | {'ok':>3} | "
           f"{'rpl':>3} | {'gd':>3} || {'procs':>5} | {'reuse':>5} | "
           f"{'conf':>5} | {'gen':>3}")
    print(hdr)
    print("-" * len(hdr))

    totals = {"cold_tool": 0, "cold_llm": 0, "warm_tool": 0, "warm_llm": 0,
              "cold_ok": 0, "warm_ok": 0, "tasks": 0}
    curve = []
    per_round: list[dict] = []
    for r in range(ROUNDS):
        cold = run_cold_round(r)
        warm = run_warmed_round(memory, r)
        kb = knowledge_snapshot(memory)
        curve.append((warm["llm_calls"], warm["tool_calls"]))
        per_round.append({
            "round": r,
            "tasks": cold["tasks"],
            "cold": {
                "tool_calls": cold["tool_calls"],
                "llm_calls": cold["llm_calls"],
                "successes": cold["successes"],
            },
            "warmed": {
                "tool_calls": warm["tool_calls"],
                "llm_calls": warm["llm_calls"],
                "successes": warm["successes"],
                "replayed": warm["replayed"],
                "guided": warm["guided"],
            },
            "knowledge": kb,
        })

        print(f"{r:>5} | {'cold':>6} | {cold['tool_calls']:>4} | "
              f"{cold['llm_calls']:>4} | {cold['successes']:>3} | "
              f"{'-':>3} | {'-':>3} || {'':>5} | {'':>5} | {'':>5} | {'':>3}")
        print(f"{r:>5} | {'warm':>6} | {warm['tool_calls']:>4} | "
              f"{warm['llm_calls']:>4} | {warm['successes']:>3} | "
              f"{warm['replayed']:>3} | {warm['guided']:>3} || "
              f"{kb['procedures']:>5} | {kb['max_reuse']:>5} | "
              f"{kb['mean_conf']:>5.2f} | {kb['evolution_gen']:>3}")
        print("-" * len(hdr))

        totals["cold_tool"] += cold["tool_calls"]
        totals["cold_llm"] += cold["llm_calls"]
        totals["warm_tool"] += warm["tool_calls"]
        totals["warm_llm"] += warm["llm_calls"]
        totals["cold_ok"] += cold["successes"]
        totals["warm_ok"] += warm["successes"]
        totals["tasks"] += cold["tasks"]

    # Export the learned library — the durable institutional-knowledge artifact.
    lib_dir = os.path.join(tempfile.gettempdir(), "learnkit_skill_library")
    n_skills = memory.export_skill_library(lib_dir)
    memory.shutdown()

    # ── Summary ──────────────────────────────────────────────────────────────
    def red(a, b):
        return (a - b) / a * 100 if a else 0.0

    print("\n=== totals over all rounds ===")
    print(f"tool calls:  cold {totals['cold_tool']:>4} -> warmed "
          f"{totals['warm_tool']:>4}  ({red(totals['cold_tool'], totals['warm_tool']):+.0f}%)")
    print(f"llm calls:   cold {totals['cold_llm']:>4} -> warmed "
          f"{totals['warm_llm']:>4}  ({red(totals['cold_llm'], totals['warm_llm']):+.0f}%)")
    print(f"success:     cold {totals['cold_ok']}/{totals['tasks']}  "
          f"warmed {totals['warm_ok']}/{totals['tasks']}")

    print("\n=== warmed learning curve (llm calls per round) ===")
    first = curve[0][0]
    for i, (llm, tool) in enumerate(curve):
        bar = "#" * llm
        delta = f"({red(first, llm):+.0f}% vs r0)" if first else ""
        print(f"  round {i}: llm={llm:<3} tool={tool:<3} {bar} {delta}")

    final_kb = knowledge_snapshot(lk.LearnKit(
        memory_backend="sqlite", db_path=db_path,
        background_postprocess=False, distiller=StubDistiller()))
    print("\n=== institutional knowledge (final) ===")
    print(f"  durable procedures: {final_kb['procedures']} "
          f"(active {final_kb['active']}, quarantined {final_kb['quarantined']})")
    print(f"  max reuse_count:    {final_kb['max_reuse']}")
    print(f"  mean confidence:    {final_kb['mean_conf']:.2f}")
    print(f"  total evolution_gen:{final_kb['evolution_gen']}")
    print(f"  exported library:   {n_skills} SKILL.md files -> {lib_dir}")

    if reflect:
        print("\n=== accumulated playbooks (authored live by the model) ===")
        check = lk.LearnKit(memory_backend="sqlite", db_path=db_path,
                            background_postprocess=False, distiller=StubDistiller())
        for r in check.backend.list_by_scope(check.scope, limit=1000):
            pb = r.content.get("playbook") if getattr(r, "type", None) == "skill" else None
            if pb:
                print(f"  [{r.task_type[:48]}]  (reuse {r.reuse_count})")
                for bullet in pb:
                    print(f"    - {bullet}")

    improved = (curve[-1][0] < curve[0][0] and
                totals["warm_llm"] < totals["cold_llm"] and
                totals["warm_ok"] >= totals["cold_ok"])
    print("\nEVOLVED" if improved else "\nNO IMPROVEMENT")

    # ── Persist the learning curve as a JSON artifact ────────────────────────
    if os.environ.get("LK_NO_SAVE_CURVE", "").lower() not in ("1", "true", "yes"):
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        curve_path = _RESULTS_DIR / f"evolution_live_{ts}_curve.json"
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "benchmark": "evolution_live",
            "endpoint": BASE_URL,
            "model": MODEL,
            "reflect": reflect,
            "rounds": ROUNDS,
            "per_round": per_round,
            "totals": {
                "tasks": totals["tasks"],
                "cold_tool_calls": totals["cold_tool"],
                "cold_llm_calls": totals["cold_llm"],
                "warmed_tool_calls": totals["warm_tool"],
                "warmed_llm_calls": totals["warm_llm"],
                "cold_success": totals["cold_ok"],
                "warmed_success": totals["warm_ok"],
            },
            "final_knowledge": final_kb,
            "improved": improved,
        }
        curve_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Saved curve:    {curve_path}")


if __name__ == "__main__":
    main()
