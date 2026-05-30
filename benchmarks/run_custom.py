"""
LearnKit custom-clustered benchmark runner.

For each domain, runs all 10 tasks twice:
    Control     — raw Gemini Flash Lite, no memory.
    Treatment   — same model wrapped in @memory.agent, tasks in order so task N
                  has access to distilled skills/facts/failures from tasks 1..N-1.

Judge: Anthropic Claude Haiku via the existing Evaluator (different vendor from
the agent — required for independent quality scoring).

Outputs:
    results/<run_id>/raw.json           — every per-task record
    results/<run_id>/summary.md         — human-readable comparison table
    results/<run_id>/compounding.csv    — treatment score by task index per domain
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import litellm  # noqa: E402

import learnkit as lk  # noqa: E402
from learnkit.evaluator import Evaluator  # noqa: E402

AGENT_MODEL = "gemini/gemini-flash-lite-latest"
JUDGE = Evaluator()  # uses claude-haiku-4-5 by default

DOMAIN_SYSTEM_PROMPTS = {
    "python_debugging": (
        "You are a senior Python engineer. Answer in <= 5 sentences. "
        "Cite specific function names, modules, or Python versions when relevant. "
        "Lead with the root cause, then the fix."
    ),
    "contract_summarization": (
        "You are a contracts attorney. Summarize in tight bullets under these headings: "
        "Obligations, Term, Termination, Liability. Do not invent clauses absent from the text."
    ),
    "sql_authoring": (
        "You are a Postgres expert. Output a single fenced ```sql code block containing "
        "ONLY runnable Postgres SQL. Prepend a single-line comment inside the block "
        "summarising the approach. No prose outside the block."
    ),
}


def call_agent(
    system: str, user: str, *, max_retries: int = 5
) -> tuple[str, dict, float]:
    """Single LLM call with retry/backoff. Returns (text, usage_dict, latency_s)."""
    last_err: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            t0 = time.perf_counter()
            r = litellm.completion(
                model=AGENT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=600,
            )
            latency = time.perf_counter() - t0
            text = r.choices[0].message.content or ""
            u = r.usage
            usage = {
                "prompt_tokens": getattr(u, "prompt_tokens", 0),
                "completion_tokens": getattr(u, "completion_tokens", 0),
                "total_tokens": getattr(u, "total_tokens", 0),
            }
            return text, usage, latency
        except Exception as e:
            last_err = e
            wait = 2**attempt
            print(
                f"    [retry] attempt {attempt + 1}/{max_retries} failed "
                f"({type(e).__name__}); sleeping {wait}s"
            )
            time.sleep(wait)
    print(f"    [give-up] {type(last_err).__name__}: {str(last_err)[:140]}")
    return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, 0.0


def load_tasks(domain: str) -> list[dict]:
    p = HERE / "tasks" / f"{domain}.jsonl"
    return [
        json.loads(line)
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def score(task_prompt: str, response: str) -> tuple[float, str]:
    if not response.strip():
        return 0.0, "empty response"
    try:
        result = JUDGE.evaluate_with_llm_judge(task=task_prompt, response=response)
        return result.score, result.reasoning
    except Exception as e:
        return 0.0, f"judge error: {type(e).__name__}: {str(e)[:80]}"


def run_control(domain: str, tasks: list[dict]) -> list[dict]:
    system = DOMAIN_SYSTEM_PROMPTS[domain]
    out = []
    print(f"\n  [CONTROL] {domain}")
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} {t['id']}", end="", flush=True)
        resp, usage, latency = call_agent(system, t["prompt"])
        s, reason = score(t["prompt"], resp)
        print(
            f"  score={s:.1f}  tokens={usage['total_tokens']}  latency={latency:.1f}s"
        )
        out.append(
            {
                "arm": "control",
                "task_id": t["id"],
                "domain": domain,
                "pattern": t["pattern"],
                "task_index": i,
                "response": resp,
                "score": s,
                "score_reasoning": reason,
                "usage": usage,
                "latency_s": latency,
                "learnkit_context_chars": 0,
            }
        )
    return out


def run_treatment(domain: str, tasks: list[dict], db_path: Path) -> list[dict]:
    system_base = DOMAIN_SYSTEM_PROMPTS[domain]
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=str(db_path),
        scope="user",
        background_postprocess=False,  # sync so task N+1 sees task N's distillation
    )

    context_holder: dict = {"chars": 0}

    @memory.agent(domain=domain)
    def ask(task: str, _learnkit_context: str = "") -> str:
        context_holder["chars"] = len(_learnkit_context)
        system = (
            f"{system_base}\n\n{_learnkit_context}"
            if _learnkit_context
            else system_base
        )
        text, usage, latency = call_agent(system, task)
        # stash latency/usage on the closure for the outer loop to read
        context_holder["usage"] = usage
        context_holder["latency_s"] = latency
        return text

    out = []
    print(f"\n  [TREATMENT] {domain}  (db: {db_path.name})")
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} {t['id']}", end="", flush=True)
        resp = ask(t["prompt"])
        s, reason = score(t["prompt"], resp)
        ctx = context_holder.get("chars", 0)
        usage = context_holder.get(
            "usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        latency = context_holder.get("latency_s", 0.0)
        print(
            f"  score={s:.1f}  ctx={ctx}  tokens={usage['total_tokens']}  latency={latency:.1f}s"
        )
        out.append(
            {
                "arm": "treatment",
                "task_id": t["id"],
                "domain": domain,
                "pattern": t["pattern"],
                "task_index": i,
                "response": resp,
                "score": s,
                "score_reasoning": reason,
                "usage": usage,
                "latency_s": latency,
                "learnkit_context_chars": ctx,
            }
        )

    memory.shutdown(wait=True)
    return out


def summarize(records: list[dict]) -> dict:
    by_arm_domain: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        by_arm_domain.setdefault((r["arm"], r["domain"]), []).append(r)
    rows = []
    for (arm, domain), rs in sorted(by_arm_domain.items()):
        scores = [r["score"] for r in rs]
        tokens = [r["usage"]["total_tokens"] for r in rs]
        latencies = [r["latency_s"] for r in rs]
        ctx = [r["learnkit_context_chars"] for r in rs]
        rows.append(
            {
                "arm": arm,
                "domain": domain,
                "n": len(rs),
                "mean_score": statistics.mean(scores) if scores else 0,
                "stdev_score": statistics.stdev(scores) if len(scores) > 1 else 0,
                "mean_tokens": statistics.mean(tokens) if tokens else 0,
                "mean_latency_s": statistics.mean(latencies) if latencies else 0,
                "mean_ctx_chars": statistics.mean(ctx) if ctx else 0,
            }
        )
    return {"rows": rows}


def write_summary_md(summary: dict, records: list[dict], out_path: Path) -> None:
    lines = ["# LearnKit Custom-Clustered Benchmark — Results", ""]
    lines.append(f"Run: `{out_path.parent.name}`")
    lines.append(f"Agent model: `{AGENT_MODEL}`")
    lines.append("Judge: Anthropic Claude Haiku (via `learnkit.Evaluator`)")
    lines.append("")
    lines.append("## Aggregate per domain × arm")
    lines.append("")
    lines.append(
        "| Arm | Domain | n | Mean score | Stdev | Mean tokens | Mean latency (s) | Mean ctx chars |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in summary["rows"]:
        lines.append(
            f"| {r['arm']} | {r['domain']} | {r['n']} | {r['mean_score']:.2f} | "
            f"{r['stdev_score']:.2f} | {r['mean_tokens']:.0f} | "
            f"{r['mean_latency_s']:.2f} | {r['mean_ctx_chars']:.0f} |"
        )
    lines.append("")

    # Per-domain lift summary
    lines.append("## Lift: treatment − control (per domain)")
    lines.append("")
    lines.append("| Domain | Control mean | Treatment mean | Δ score | Relative |")
    lines.append("|---|---|---|---|---|")
    by_arm_domain = {(r["arm"], r["domain"]): r for r in summary["rows"]}
    domains = sorted({d for _, d in by_arm_domain})
    for d in domains:
        c = by_arm_domain.get(("control", d))
        t = by_arm_domain.get(("treatment", d))
        if not c or not t:
            continue
        delta = t["mean_score"] - c["mean_score"]
        rel = (delta / c["mean_score"] * 100) if c["mean_score"] else float("inf")
        lines.append(
            f"| {d} | {c['mean_score']:.2f} | {t['mean_score']:.2f} | "
            f"{delta:+.2f} | {rel:+.1f}% |"
        )
    lines.append("")

    # Compounding curve: treatment score by task index per domain
    lines.append("## Compounding curve (treatment score by task index)")
    lines.append("")
    lines.append("| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    treatment_by_domain: dict[str, list[float]] = {}
    for r in records:
        if r["arm"] == "treatment":
            treatment_by_domain.setdefault(r["domain"], [0.0] * 10)
            treatment_by_domain[r["domain"]][r["task_index"] - 1] = r["score"]
    for d in sorted(treatment_by_domain):
        scores = treatment_by_domain[d]
        cells = " | ".join(f"{s:.1f}" for s in scores)
        lines.append(f"| {d} | {cells} |")
    lines.append("")

    # Context growth: how many chars LearnKit injected on each task index
    lines.append("## LearnKit context size by task index (treatment)")
    lines.append("")
    lines.append("| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    ctx_by_domain: dict[str, list[int]] = {}
    for r in records:
        if r["arm"] == "treatment":
            ctx_by_domain.setdefault(r["domain"], [0] * 10)
            ctx_by_domain[r["domain"]][r["task_index"] - 1] = r[
                "learnkit_context_chars"
            ]
    for d in sorted(ctx_by_domain):
        cells = " | ".join(str(c) for c in ctx_by_domain[d])
        lines.append(f"| {d} | {cells} |")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_compounding_csv(records: list[dict], out_path: Path) -> None:
    rows = [
        "arm,domain,task_index,task_id,pattern,score,total_tokens,latency_s,ctx_chars"
    ]
    for r in records:
        rows.append(
            f"{r['arm']},{r['domain']},{r['task_index']},{r['task_id']},{r['pattern']},"
            f"{r['score']:.2f},{r['usage']['total_tokens']},{r['latency_s']:.3f},"
            f"{r['learnkit_context_chars']}"
        )
    out_path.write_text("\n".join(rows), encoding="utf-8")


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("ERROR: GEMINI_API_KEY missing (check benchmarks/.env).")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: ANTHROPIC_API_KEY missing (judge model).")

    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run id: {run_id}")
    print(f"Output: {out_dir}")
    print(f"Agent:  {AGENT_MODEL}")
    print("Judge:  claude-haiku-4-5-20251001 (via LearnKit Evaluator)")

    domains = ["python_debugging", "contract_summarization", "sql_authoring"]
    all_records: list[dict] = []

    for domain in domains:
        tasks = load_tasks(domain)
        print(f"\n{'=' * 72}\nDOMAIN: {domain}  ({len(tasks)} tasks)\n{'=' * 72}")
        all_records.extend(run_control(domain, tasks))
        db_path = out_dir / f"learnkit_{domain}.db"
        all_records.extend(run_treatment(domain, tasks, db_path))

    summary = summarize(all_records)

    (out_dir / "raw.json").write_text(
        json.dumps(all_records, indent=2), encoding="utf-8"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    write_compounding_csv(all_records, out_dir / "compounding.csv")
    write_summary_md(summary, all_records, out_dir / "summary.md")

    print(f"\n{'=' * 72}\nDONE — see {out_dir / 'summary.md'}\n{'=' * 72}")


if __name__ == "__main__":
    main()
