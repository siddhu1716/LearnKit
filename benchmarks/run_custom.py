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

import argparse
import datetime as dt
import json
import os
import random
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
from benchmarks.graders import grade_contract_task, grade_python_task, grade_sql_task

# Agent + distiller default to the same self-hosted Qwen (vLLM, OpenAI-compatible
# endpoint), matching run_slr_bench.py / run_pbebench.py. Override via env:
#   LEARNKIT_AGENT_MODEL, LEARNKIT_API_BASE, LEARNKIT_DISTILLER_MODEL.
AGENT_MODEL = os.environ.get("LEARNKIT_AGENT_MODEL", "openai/Qwen/Qwen2.5-72B-Instruct")
API_BASE = os.environ.get("LEARNKIT_API_BASE", "http://localhost:8001/v1")

# Pass api_base/api_key only for local OpenAI-compatible endpoints (vLLM). A
# hosted model id (e.g. "gemini/...") routes through litellm's own credentials.
_USE_LOCAL_ENDPOINT = AGENT_MODEL.startswith("openai/") or bool(
    os.environ.get("LEARNKIT_API_BASE")
)

# Route every LearnKit model slot (distiller, evaluator, classifier) to the same
# local Qwen endpoint. The distiller/agent get an explicit api_base, but the
# Evaluator and classifier build dspy.LM(...) without one — so we export the
# OpenAI-compatible base/key env vars that litellm honors, and point their model
# envs at the Qwen id. This makes a fully self-hosted, no-cloud run work.
if _USE_LOCAL_ENDPOINT:
    os.environ.setdefault("OPENAI_API_BASE", API_BASE)
    os.environ.setdefault("OPENAI_API_KEY", "anything")
    os.environ.setdefault("LEARNKIT_EVALUATOR_MODEL", AGENT_MODEL)
    os.environ.setdefault("LEARNKIT_CLASSIFIER_MODEL", AGENT_MODEL)


def _judge():
    """Lazily build the LLM judge (only used by non-deterministic domains)."""
    return Evaluator()


def _build_distiller():
    """Distiller on the same model/endpoint as the agent (matches SLR/PBE runners).

    Honors LEARNKIT_DISTILLER_MODEL when set, else uses the agent model. For a
    local vLLM endpoint the api_base/api_key are passed through; otherwise the
    distiller falls back to LearnKit's default credential routing.
    """
    import dspy
    from learnkit.distiller import MemoryDistiller

    distill_model = os.environ.get("LEARNKIT_DISTILLER_MODEL", AGENT_MODEL)
    if _USE_LOCAL_ENDPOINT:
        lm = dspy.LM(distill_model, api_base=API_BASE, api_key="anything", temperature=0.0)
    else:
        lm = dspy.LM(distill_model)
    return MemoryDistiller(lm=lm)


_EMBEDDER_SINGLETON = None


def _build_embedder():
    """Local sentence-transformers embedder, cached as a singleton.

    Returns a Callable[[str], list[float]] or None when embeddings are disabled
    (LEARNKIT_USE_EMBEDDER unset/0) or sentence-transformers is unavailable.
    The embedder enables hybrid retrieval AND the query-time relevance gate
    (LEARNKIT_RELEVANCE_FLOOR), which both need vectors.
    """
    if os.environ.get("LEARNKIT_USE_EMBEDDER", "0") not in ("1", "true", "True"):
        return None
    global _EMBEDDER_SINGLETON
    if _EMBEDDER_SINGLETON is not None:
        return _EMBEDDER_SINGLETON
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("  [embedder] sentence-transformers not installed; running lexical-only")
        return None
    model_name = os.environ.get("LEARNKIT_EMBED_MODEL", "all-MiniLM-L6-v2")
    model = SentenceTransformer(model_name)

    def _embed(text: str) -> list[float]:
        return model.encode(text, normalize_embeddings=True).tolist()

    _EMBEDDER_SINGLETON = _embed
    return _embed



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


_last_call_time = 0.0


def call_agent(
    system: str, user: str, *, max_retries: int = 5
) -> tuple[str, dict, float]:
    """Single LLM call with retry/backoff. Returns (text, usage_dict, latency_s)."""
    global _last_call_time
    # Inter-call throttle guards cloud rate limits (e.g. Gemini 503s). A local
    # vLLM/sglang endpoint needs no such gap, so make it env-configurable.
    min_interval = float(os.environ.get("LEARNKIT_MIN_CALL_INTERVAL", "4.2"))
    elapsed = time.time() - _last_call_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
        
    last_err: Optional[Exception] = None
    completion_kwargs: dict = (
        {"api_base": API_BASE, "api_key": "anything", "temperature": 0.0}
        if _USE_LOCAL_ENDPOINT
        else {}
    )
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
                **completion_kwargs,
            )
            latency = time.perf_counter() - t0
            _last_call_time = time.time()
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
            wait = 5.0 * (attempt + 1)
            print(
                f"    [retry] attempt {attempt + 1}/{max_retries} failed "
                f"({type(e).__name__}); sleeping {wait}s"
            )
            time.sleep(wait)
            _last_call_time = time.time()
    print(f"    [give-up] {type(last_err).__name__}: {str(last_err)[:140]}")
    return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, 0.0


def load_tasks(domain: str, splits: Optional[set[str]] = None) -> list[dict]:
    """Load tasks for a domain, optionally filtered to specific splits.

    ``splits=None`` excludes the contamination split so the default reuse run
    (train + eval) is unchanged. Pass an explicit set (e.g. {"contamination"})
    to select a split for transfer/contamination experiments. Tasks without a
    ``split`` field are always included (back-compat).
    """
    p = HERE / "tasks" / f"{domain}.jsonl"
    tasks = [
        json.loads(line)
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if splits is None:
        return [t for t in tasks if t.get("split") != "contamination"]
    return [t for t in tasks if t.get("split") in splits or "split" not in t]


def score(
    domain: str, task_id: str, task_prompt: str, response: str, pattern: Optional[str] = None
) -> tuple[float, str]:
    if not response.strip():
        return 0.0, "empty response"
    try:
        if domain == "contract_summarization":
            s = grade_contract_task(task_prompt, response)
            return s, f"Deterministic recall facts score: {s}/5"
        elif domain == "python_debugging":
            s = grade_python_task(task_id, task_prompt, response, pattern=pattern)
            return s, f"Deterministic python syntax score: {s}/5"
        elif domain == "sql_authoring":
            s = grade_sql_task(task_id, task_prompt, response)
            return s, f"Deterministic SQL execution score: {s}/5"
        else:
            result = _judge().evaluate_with_llm_judge(task=task_prompt, response=response)
            return result.score, result.reasoning
    except Exception as e:
        return 0.0, f"grader error: {type(e).__name__}: {str(e)[:80]}"


def run_control(domain: str, tasks: list[dict], seed: int = 0) -> list[dict]:
    system = DOMAIN_SYSTEM_PROMPTS[domain]
    out = []
    print(f"\n  [CONTROL] {domain} (seed {seed})")
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} {t['id']}", end="", flush=True)
        resp, usage, latency = call_agent(system, t["prompt"])
        s, reason = score(domain, t["id"], t["prompt"], resp, pattern=t.get("pattern"))
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
                "seed": seed,
                "split": t.get("split"),
                "contaminant": t.get("contaminant"),
            }
        )
    return out


def run_treatment(
    domain: str,
    tasks: list[dict],
    db_path: Path,
    seed: int = 0,
    warm_tasks: Optional[list[dict]] = None,
) -> list[dict]:
    system_base = DOMAIN_SYSTEM_PROMPTS[domain]
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=str(db_path),
        scope="user",
        background_postprocess=False,  # sync so task N+1 sees task N's distillation
        auto_promote=True,  # bypass 24h quarantine for online benchmark learning
        distiller=_build_distiller(),
        embedder=_build_embedder(),
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
    print(f"\n  [TREATMENT] {domain}  (db: {db_path.name}, seed {seed})")
    # Warm phase: pre-populate the store with prior-split skills (unscored) so a
    # contamination/transfer eval has a learned pattern to be retrieved/baited by.
    if warm_tasks:
        print(f"    [warm] seeding {len(warm_tasks)} tasks into memory")
        for wt in warm_tasks:
            ask(wt["prompt"])
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} {t['id']}", end="", flush=True)
        resp = ask(t["prompt"])
        s, reason = score(domain, t["id"], t["prompt"], resp, pattern=t.get("pattern"))
        # When utility is sourced externally, feed the deterministic grader score
        # (the true objective, a production analog of a real test/accept signal)
        # into the retrieved records' utility EMA so the utility gate is driven by
        # ground truth rather than the model's own (harm-blind) LLM judge.
        if os.environ.get("LEARNKIT_UTILITY_EXTERNAL", "").lower() in ("1", "true", "yes"):
            memory.apply_external_outcome(s)
        ctx = context_holder.get("chars", 0)
        usage = context_holder.get(
            "usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )
        latency = context_holder.get("latency_s", 0.0)
        attribution = memory.last_attribution or {}
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
                "seed": seed,
                "split": t.get("split"),
                "contaminant": t.get("contaminant"),
                "attribution": attribution,
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
        # Group by seed
        by_seed: dict[int, list[dict]] = {}
        for r in rs:
            by_seed.setdefault(r.get("seed", 0), []).append(r)
            
        seed_means = []
        for seed_val, seed_rs in by_seed.items():
            seed_means.append(statistics.mean([r["score"] for r in seed_rs]))
            
        overall_mean = statistics.mean(seed_means) if seed_means else 0.0
        if len(seed_means) > 1:
            stdev_val = statistics.stdev(seed_means)
            se_val = stdev_val / (len(seed_means) ** 0.5)
        else:
            stdev_val = 0.0
            se_val = 0.0
            
        tokens = [r["usage"]["total_tokens"] for r in rs]
        latencies = [r["latency_s"] for r in rs]
        ctx = [r["learnkit_context_chars"] for r in rs]
        
        rows.append(
            {
                "arm": arm,
                "domain": domain,
                "n_tasks": len(rs) // len(by_seed) if by_seed else len(rs),
                "n_seeds": len(by_seed),
                "mean_score": overall_mean,
                "stdev_score": stdev_val,
                "se_score": se_val,
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
    lines.append("Deterministic Custom Rubric Graders (No LLM Judge)")
    lines.append("")
    lines.append("## Aggregate per domain × arm")
    lines.append("")
    lines.append(
        "| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in summary["rows"]:
        lines.append(
            f"| {r['arm']} | {r['domain']} | {r['n_tasks']} | {r['n_seeds']} | {r['mean_score']:.2f} | "
            f"{r['se_score']:.2f} | {r['mean_tokens']:.0f} | "
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
            f"| {d} | {c['mean_score']:.2f} ± {c['se_score']:.2f} | {t['mean_score']:.2f} ± {t['se_score']:.2f} | "
            f"{delta:+.2f} | {rel:+.1f}% |"
        )
    lines.append("")

    # Compounding curve: treatment score by task index per domain
    max_idx = max((r["task_index"] for r in records), default=10)
    
    lines.append("## Compounding curve (treatment score by task index)")
    lines.append("")
    headers = [f"t{i}" for i in range(1, max_idx + 1)]
    lines.append(f"| Domain | {' | '.join(headers)} |")
    lines.append(f"|---|{'---|' * max_idx}")
    
    treatment_by_domain: dict[str, list[float]] = {}
    for r in records:
        if r["arm"] == "treatment":
            treatment_by_domain.setdefault(r["domain"], [0.0] * max_idx)
            idx = r["task_index"] - 1
            if idx < len(treatment_by_domain[r["domain"]]):
                treatment_by_domain[r["domain"]][idx] = r["score"]
                
    for d in sorted(treatment_by_domain):
        scores = treatment_by_domain[d]
        cells = " | ".join(f"{s:.1f}" for s in scores)
        lines.append(f"| {d} | {cells} |")
    lines.append("")

    # Context growth: how many chars LearnKit injected on each task index
    lines.append("## LearnKit context size by task index (treatment)")
    lines.append("")
    lines.append(f"| Domain | {' | '.join(headers)} |")
    lines.append(f"|---|{'---|' * max_idx}")
    
    ctx_by_domain: dict[str, list[int]] = {}
    for r in records:
        if r["arm"] == "treatment":
            ctx_by_domain.setdefault(r["domain"], [0] * max_idx)
            idx = r["task_index"] - 1
            if idx < len(ctx_by_domain[r["domain"]]):
                ctx_by_domain[r["domain"]][idx] = r["learnkit_context_chars"]
                
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
    # Require credentials for the chosen backend: a local vLLM endpoint needs no
    # cloud key; otherwise fall back to expecting GEMINI_API_KEY.
    if not _USE_LOCAL_ENDPOINT and not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit(
            "ERROR: no model endpoint configured. Set LEARNKIT_API_BASE for a "
            "local Qwen/vLLM endpoint, or GEMINI_API_KEY (check benchmarks/.env)."
        )

    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=3, help="Number of seeds to run")
    parser.add_argument("--tasks", type=int, default=50, help="Number of tasks per domain")
    parser.add_argument(
        "--splits",
        type=str,
        default="train,eval",
        help="Comma-separated splits to RUN and score (e.g. 'contamination' or 'train,eval').",
    )
    parser.add_argument(
        "--warm-splits",
        type=str,
        default="",
        help="Comma-separated splits used ONLY to pre-populate the treatment store "
        "before the scored run (e.g. 'train' for a contamination experiment).",
    )
    args = parser.parse_args()

    run_splits = {s.strip() for s in args.splits.split(",") if s.strip()}
    warm_splits = {s.strip() for s in args.warm_splits.split(",") if s.strip()}

    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "results" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run id: {run_id}")
    print(f"Output: {out_dir}")
    print(f"Agent:  {AGENT_MODEL}")
    print(f"Seeds:  {args.seeds}")
    print(f"Tasks:  {args.tasks} per domain")
    print(f"Splits: run={sorted(run_splits)} warm={sorted(warm_splits) or 'none'}")

    domains = ["python_debugging", "contract_summarization", "sql_authoring"]
    all_records: list[dict] = []

    for domain in domains:
        all_tasks = load_tasks(domain, splits=run_splits)[:args.tasks]
        warm_all = load_tasks(domain, splits=warm_splits) if warm_splits else []
        print(f"\n{'=' * 72}\nDOMAIN: {domain}  ({len(all_tasks)} tasks)\n{'=' * 72}")
        
        for s in range(args.seeds):
            # Shuffle tasks deterministically per seed
            shuffled_tasks = list(all_tasks)
            random.seed(s)
            random.shuffle(shuffled_tasks)
            
            # Control run
            all_records.extend(run_control(domain, shuffled_tasks, seed=s))
            
            # Treatment run
            db_path = out_dir / f"learnkit_{domain}_seed_{s}.db"
            if db_path.exists():
                db_path.unlink()
            all_records.extend(
                run_treatment(
                    domain, shuffled_tasks, db_path, seed=s, warm_tasks=warm_all
                )
            )

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
