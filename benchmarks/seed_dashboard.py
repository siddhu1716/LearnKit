"""Seed the dashboard store with the PUBLISHED benchmark results.

The dashboard's Agents / Task History / Overview / Memory pages should show the
real, published agentic-matrix numbers (the same ones on the landing page and
`benchmarks/RESULTS.json`) — not mock data. This script materializes the three
pinned benchmark runs (Qwen2.5-14B, Qwen2.5-32B, Llama-3.3-70B) into the live
SQLite store as `agent_learn`-mode runs plus the procedural skills they distilled.

After seeding, the user's OWN agents (any new `@memory.agent_learn` runs) append
naturally alongside these, so "from the next run you see your own results."

Idempotent: uses fixed agent/run/record ids and purges the prior ad-hoc seed
agents first. Backs up the DB before writing.

Run:
    python -m benchmarks.seed_dashboard            # seed published results
    python -m benchmarks.seed_dashboard --keep-old # don't purge prior seed agents
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Published benchmark memory should never expire from the dashboard.
os.environ.setdefault("LEARNKIT_PERSIST_FOREVER", "1")

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT))

import learnkit as lk  # noqa: E402
from learnkit.schemas.base import MemoryRecord  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.environ.get("LEARNKIT_DB_PATH", str(Path.home() / ".learnkit" / "memory.db"))
MANIFEST = ROOT / "matrix_manifest.json"

# Prior ad-hoc seed agents to clear so only the published benchmark shows.
LEGACY_SEED_NAMES = ("llama-3.3-70b", "qwen2.5-32b", "qwen2.5-14b", "qwen2.5-coder-32b")

# Rough per-token price for self-hosted endpoints (telemetry is estimated).
PRICE_PER_1K = 0.0004


def _q5(numer: float, denom: float) -> float:
    """Scale a /denom score onto the dashboard's 0–5 quality scale."""
    if not denom:
        return 0.0
    return round(5.0 * numer / denom, 2)


def _telemetry(llm_calls: int, model: str, latency_ms: float) -> dict:
    total = max(1, llm_calls) * 180
    prompt = int(total * 0.7)
    completion = total - prompt
    return {
        "latency_ms": latency_ms,
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "context_tokens": int(prompt * 0.4),
        "cost_usd": round(total / 1000.0 * PRICE_PER_1K, 6),
        "models": {"evaluator": model, "classifier": model},
        "estimated": True,
    }


def _mk_run(agent_id, agent_name, model, run_id, task, task_type, *, when,
            tool_calls, baseline, calls_reduced, replayed, outcome, quality,
            record_ids, latency_ms) -> dict:
    run = {
        "run_id": run_id,
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task": task,
        "task_type": task_type,
        "domains": {"agentic": 1.0, task_type: 1.0},
        "mode": "agent_learn",
        "tool_calls": tool_calls,
        "baseline_calls": baseline,
        "calls_reduced": calls_reduced,
        "replayed": replayed,
        "outcome": outcome,
        "quality_score": quality,
        "record_ids": record_ids,
        "signature_fp": f"{agent_id}:{task_type}",
        "steps": [],
        "created_at": when.replace(tzinfo=None).isoformat() + "Z",
    }
    run.update(_telemetry(tool_calls or baseline or 4, model, latency_ms))
    return run


def _skill(rec_id, model_slug, task_type, title, steps, *, quality, reuse) -> MemoryRecord:
    return MemoryRecord(
        id=rec_id,
        type="skill",
        task_type=task_type,
        domains={"agentic": 1.0, task_type: 1.0},
        content={
            "title": title,
            "steps": steps,
            "success_count": reuse,
            "_quality_score": quality,
            "generality": 0.7,
            "source": "benchmark",
            "model": model_slug,
        },
        confidence=0.9,
        reuse_count=reuse,
        success_rate=quality / 5.0,
        scope="user",
        status="active",
    )


def _runs_for_model(entry: dict, raw: dict, when0: datetime) -> tuple[list[dict], list[MemoryRecord]]:
    name = entry["name"]
    display = entry["display"]
    model = entry["model"]
    agent_id = f"bench-{name}"
    b = raw["benchmarks"]
    rl, ev, ij = b["react_live"], b["evolution_live"], b["injection_ablation"]

    # Procedural skills distilled by this model's benchmark run.
    recs = [
        _skill(
            f"bench-{name}-react", name, "react",
            f"ReAct tool procedure ({display})",
            ["classify request", "call filter tool (active=true)",
             "aggregate (op=count)", "format result (fmt=tsv)"],
            quality=5.0, reuse=int(rl["warmed_tasks"]),
        ),
        _skill(
            f"bench-{name}-evolution", name, "evolution",
            f"Evolution-refined workflow ({display})",
            ["retrieve prior procedure", "adapt to new sibling task",
             "execute tools", "consolidate into canonical skill"],
            quality=4.8, reuse=int(ev["warmed_tasks"]),
        ),
    ]
    rec_ids = [r.id for r in recs]

    react_cut = int(rl["cold_llm_calls"]) - int(rl["warmed_llm_calls"])
    evo_cut = int(ev["cold_llm_calls"]) - int(ev["warmed_llm_calls"])

    runs = [
        _mk_run(
            agent_id, display, model, f"{agent_id}-react-cold",
            "ReAct suite — cold start (6 tool-use tasks, no memory)", "react",
            when=when0,
            tool_calls=int(rl["cold_llm_calls"]), baseline=None, calls_reduced=0,
            replayed=False,
            outcome="success" if rl["cold_success"] == rl["cold_tasks"] else "failure",
            quality=_q5(rl["cold_success"], rl["cold_tasks"]),
            record_ids=[rec_ids[0]], latency_ms=2600,
        ),
        _mk_run(
            agent_id, display, model, f"{agent_id}-react-warm",
            "ReAct suite — warmed (procedure replay, fewer LLM calls)", "react",
            when=when0 + timedelta(minutes=5),
            tool_calls=int(rl["warmed_llm_calls"]), baseline=int(rl["cold_llm_calls"]),
            calls_reduced=react_cut, replayed=True,
            outcome="success" if rl["warmed_success"] == rl["warmed_tasks"] else "failure",
            quality=_q5(rl["warmed_success"], rl["warmed_tasks"]),
            record_ids=[rec_ids[0]], latency_ms=1500,
        ),
        _mk_run(
            agent_id, display, model, f"{agent_id}-evolution-cold",
            "Evolution suite — cold start (16 tasks, 4 rounds)", "evolution",
            when=when0 + timedelta(minutes=10),
            tool_calls=int(ev["cold_llm_calls"]), baseline=None, calls_reduced=0,
            replayed=False,
            outcome="success" if ev["cold_success"] == ev["cold_tasks"] else "failure",
            quality=_q5(ev["cold_success"], ev["cold_tasks"]),
            record_ids=[rec_ids[1]], latency_ms=3200,
        ),
        _mk_run(
            agent_id, display, model, f"{agent_id}-evolution-warm",
            "Evolution suite — warmed (multi-round durability)", "evolution",
            when=when0 + timedelta(minutes=15),
            tool_calls=int(ev["warmed_llm_calls"]), baseline=int(ev["cold_llm_calls"]),
            calls_reduced=evo_cut, replayed=True,
            outcome="success" if ev["warmed_success"] == ev["warmed_tasks"] else "failure",
            quality=_q5(ev["warmed_success"], ev["warmed_tasks"]),
            record_ids=[rec_ids[1]], latency_ms=1900,
        ),
        _mk_run(
            agent_id, display, model, f"{agent_id}-injection-playbook",
            "Injection ablation — playbook injected (quality lift on novel siblings)", "injection",
            when=when0 + timedelta(minutes=25),
            tool_calls=0, baseline=None, calls_reduced=0, replayed=False,
            outcome="success",
            quality=_q5(ij["playbook_avg_score"], 3.0),
            record_ids=[rec_ids[0]], latency_ms=2000,
        ),
    ]
    return runs, recs


def _purge_legacy(mem, keep_old: bool) -> None:
    if keep_old:
        return
    backend = mem.backend
    conn = backend._conn()
    try:
        with conn:
            # Clear prior ad-hoc seed agents (by name) and any earlier bench-* seed.
            qmarks = ",".join("?" for _ in LEGACY_SEED_NAMES)
            conn.execute(
                f"DELETE FROM runs WHERE agent_name IN ({qmarks}) OR agent_id LIKE 'bench-%'",
                tuple(LEGACY_SEED_NAMES),
            )
            conn.execute("DELETE FROM records WHERE id LIKE 'bench-%'")
    finally:
        backend._close(conn)


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed dashboard with published benchmark results")
    ap.add_argument("--keep-old", action="store_true",
                    help="Do not purge prior ad-hoc seed agents")
    args = ap.parse_args()

    db = Path(DB_PATH)
    if db.exists():
        backup = db.with_name(f"{db.stem}.pre-benchseed-{datetime.now():%Y%m%d-%H%M%S}.bak")
        shutil.copy2(db, backup)
        print(f"Backup: {backup}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mem = lk.LearnKit(memory_backend="sqlite", db_path=str(db), scope="user",
                      background_postprocess=False, record_ttl=False)

    _purge_legacy(mem, args.keep_old)

    base = datetime.now(timezone.utc) - timedelta(days=len(manifest["models"]))
    total_runs = total_recs = 0
    for i, entry in enumerate(manifest["models"]):
        src = ROOT / entry["source"]
        raw = json.loads(src.read_text(encoding="utf-8"))
        when0 = base + timedelta(days=i)
        runs, recs = _runs_for_model(entry, raw, when0)
        for r in recs:
            mem.backend.add(r)
            total_recs += 1
        for run in runs:
            mem.backend.insert_run(run)
            total_runs += 1
        print(f"  {entry['display']}: {len(runs)} runs, {len(recs)} skills")

    mem.shutdown(wait=True)
    print(f"Seeded {total_runs} runs + {total_recs} skills from published benchmark → {db}")


if __name__ == "__main__":
    main()
