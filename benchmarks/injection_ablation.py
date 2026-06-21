"""Quality ablation: does injected playbook knowledge improve quality on
non-replayed sibling tasks?

This benchmark isolates learning-by-injection from memoization with 3 arms:

    cold       — no injected memory context
    procedure  — injected tool scaffold only (shape, no conventions)
    playbook   — scaffold + natural-language playbook conventions

Compared with the prior one-shot script, this version is benchmark-grade:

- Multi-trial runs for robustness
- pass^k-style reporting (fraction of tasks solved in all k sampled trials)
- Detailed + summary JSON artifacts persisted to benchmarks/results/
- Per-arm compliance breakdown for each hidden convention

Run:
    python -m benchmarks.injection_ablation
    python -m benchmarks.injection_ablation --trials 3 --k 3 --seed 7 --save-prefix qwen_ablation
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from math import comb
from pathlib import Path

from benchmarks.react_live import BASE_SYSTEM, GUIDED_SUFFIX, MODEL, react_loop
from learnkit.composer import compose_context
from learnkit.inference_mode import InferenceMode
from learnkit.schemas.skill import SkillRecord
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory

# Novel sibling tasks only. No exact replay here by design.
TABLES = [
    "users",
    "orders",
    "products",
    "items",
    "customers",
    "invoices",
    "payments",
    "accounts",
]
TASK = "Prepare the compliance export for the {t} table."
CONVENTIONS = ("filter_active", "record_count", "tsv_output")


def pass_hat_k(n: int, s: int, k: int) -> float:
    """pass^k style metric using combinations: C(s, k) / C(n, k)."""
    if k > n or k > s:
        return 0.0
    return comb(s, k) / comb(n, k)


def _compliance(tracker: ToolTracker) -> tuple[int, dict[str, bool]]:
    """Score each task 0..3 by checking actual tool arguments used."""

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


def _skill(with_playbook: bool) -> SkillRecord:
    """Base procedural scaffold; optional playbook for knowledge injection."""
    rec = SkillRecord(
        domains={"pipeline": 1.0},
        task_type="compliance-export",
        content={
            "procedure": [
                {"tool": "query"},
                {"tool": "filter"},
                {"tool": "aggregate"},
                {"tool": "format"},
            ],
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


def run_arm_trial(arm: str, tables: list[str]) -> dict:
    out = {
        "score": 0,
        "full": 0,
        "tool_calls": 0,
        "llm_calls": 0,
        "tasks": 0,
        "filter_active": 0,
        "record_count": 0,
        "tsv_output": 0,
        "rows": [],
    }
    for t in tables:
        task = TASK.format(t=t)
        tracker = ToolTracker(Trajectory(task=task))
        system = _system_for(arm, task)
        _final, llm = react_loop(task, system, tracker)
        score, hits = _compliance(tracker)

        out["score"] += score
        out["full"] += 1 if score == 3 else 0
        out["tool_calls"] += sum(1 for c in tracker.calls if c["productive"])
        out["llm_calls"] += llm
        out["tasks"] += 1
        for k in CONVENTIONS:
            out[k] += 1 if hits[k] else 0
        out["rows"].append(
            {
                "table": t,
                "score": score,
                "hits": hits,
                "tool_calls": sum(1 for c in tracker.calls if c["productive"]),
                "llm_calls": llm,
            }
        )
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def aggregate_trials(arm: str, trials: list[dict], k: int) -> dict:
    n_tasks = len(TABLES)
    full_successes = sum(1 for t in trials if t["full"] == n_tasks)

    # Per-convention all-task success count across trials.
    convention_all = {
        c: sum(1 for t in trials if t[c] == n_tasks)
        for c in CONVENTIONS
    }

    return {
        "arm": arm,
        "trials": len(trials),
        "tasks": n_tasks,
        "avg_score_per_task": _mean([t["score"] / n_tasks for t in trials]),
        "avg_full_per_trial": _mean([t["full"] for t in trials]),
        "avg_tool_calls_per_task": _mean([t["tool_calls"] / n_tasks for t in trials]),
        "avg_llm_calls_per_trial": _mean([t["llm_calls"] for t in trials]),
        "full_success_trials": full_successes,
        "pass_k_full": pass_hat_k(len(trials), full_successes, k),
        "convention_pass_k": {
            c: pass_hat_k(len(trials), convention_all[c], k)
            for c in CONVENTIONS
        },
    }


def _results_dir() -> Path:
    p = Path(__file__).resolve().parent / "results"
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_results(detailed: dict, summary: dict, prefix: str) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_prefix = f"{prefix}_{ts}"
    root = _results_dir()
    detailed_path = root / f"{out_prefix}_detailed.json"
    summary_path = root / f"{out_prefix}_summary.json"
    detailed_path.write_text(json.dumps(detailed, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return detailed_path, summary_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Injection quality ablation benchmark")
    p.add_argument("--trials", type=int, default=1,
                   help="Number of independent trials per arm (default: 1)")
    p.add_argument("--k", type=int, default=1,
                   help="k for pass^k reporting (default: 1)")
    p.add_argument("--seed", type=int, default=0,
                   help="Base random seed used for per-trial task shuffles")
    p.add_argument("--save-prefix", default="injection_ablation",
                   help="Prefix for results files under benchmarks/results/")
    p.add_argument("--no-save", action="store_true",
                   help="Disable writing detailed/summary JSON files")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.trials < 1:
        raise SystemExit("--trials must be >= 1")
    if args.k < 1:
        raise SystemExit("--k must be >= 1")

    print(
        f"model: {MODEL}   tasks: {len(TABLES)}   "
        f"trials/arm: {args.trials}   pass^k: {args.k}"
    )
    print("arms: cold | procedure | playbook\n")

    arms = ["cold", "procedure", "playbook"]
    detailed = {
        "model": MODEL,
        "task_template": TASK,
        "tables": TABLES,
        "trials": args.trials,
        "k": args.k,
        "seed": args.seed,
        "arms": {},
    }

    for arm in arms:
        arm_trials = []
        for t in range(args.trials):
            rng = random.Random(args.seed + t)
            tables = list(TABLES)
            rng.shuffle(tables)
            trial = run_arm_trial(arm, tables)
            trial["trial_index"] = t
            trial["table_order"] = tables
            arm_trials.append(trial)
        detailed["arms"][arm] = arm_trials

    summary = {
        "model": MODEL,
        "trials": args.trials,
        "k": args.k,
        "arms": {
            arm: aggregate_trials(arm, detailed["arms"][arm], args.k)
            for arm in arms
        },
    }

    n = len(TABLES)
    print("  arm       | avg score/3 | avg full | pass^k(full) | filter^k | count^k | tsv^k")
    print("  " + "-" * 84)
    for arm in arms:
        s = summary["arms"][arm]
        print(
            f"  {arm:<9} |"
            f" {s['avg_score_per_task']:>10.2f} |"
            f" {s['avg_full_per_trial']:>7.2f}/{n:<2} |"
            f" {s['pass_k_full']:>12.3f} |"
            f" {s['convention_pass_k']['filter_active']:>8.3f} |"
            f" {s['convention_pass_k']['record_count']:>7.3f} |"
            f" {s['convention_pass_k']['tsv_output']:>5.3f}"
        )
    print("  " + "-" * 84)

    cold = summary["arms"]["cold"]
    proc = summary["arms"]["procedure"]
    pb = summary["arms"]["playbook"]
    d_scaffold = proc["avg_score_per_task"] - cold["avg_score_per_task"]
    d_playbook = pb["avg_score_per_task"] - proc["avg_score_per_task"]

    print(f"\n  scaffold effect (procedure - cold):     {d_scaffold:+.2f} avg compliance points")
    print(f"  PLAYBOOK effect (playbook - procedure): {d_playbook:+.2f} avg compliance points")

    if not args.no_save:
        detailed_path, summary_path = save_results(detailed, summary, args.save_prefix)
        print(f"\nSaved detailed: {detailed_path}")
        print(f"Saved summary:  {summary_path}")


if __name__ == "__main__":
    main()
