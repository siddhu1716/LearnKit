"""
LearnKit MVP Benchmark — Baseline vs LearnKit Comparison
=========================================================

Respects Gemini free tier limits (20 req/day/key/model) by:
  - Splitting keys: key1 for agent/evaluator, key2 for classifier/distiller
  - Auto-retry on 429 with wait
  - 5 tasks to stay within budget (~36 total API calls)

Protocol:
  Phase 1 — BASELINE:  Raw Gemini, no memory
  Phase 2 — TRAINING:  LearnKit learns from each run
  Phase 3 — WARM EVAL: Same tasks, now with populated memory
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import dspy
import learnkit as lk
from learnkit.evaluator import Evaluator

# ─────────────────────────────────────────────────────────────────────────────
# API KEYS — GLOBAL ROUND-ROBIN ROTATION
# ─────────────────────────────────────────────────────────────────────────────

# Load API keys from environment variables to prevent Github push-protection blocks
env_keys = os.environ.get("GEMINI_API_KEYS", "")
if env_keys:
    API_KEYS = [k.strip() for k in env_keys.split(",") if k.strip()]
else:
    # Look for standard numbered keys
    keys = [
        os.environ.get("GEMINI_API_KEY", ""),
        os.environ.get("GEMINI_API_KEY_1", ""),
        os.environ.get("GEMINI_API_KEY_2", ""),
        os.environ.get("GEMINI_API_KEY_3", ""),
        os.environ.get("GEMINI_API_KEY_4", ""),
        os.environ.get("GEMINI_API_KEY_5", ""),
    ]
    API_KEYS = [k for k in keys if k]

# If absolutely no keys are provided in the environment, use a dummy placeholder so it compiles
if not API_KEYS:
    API_KEYS = ["DUMMY_KEY_PLACEHOLDER"]

MODEL = "gemini/gemini-flash-latest"

os.environ["LEARNKIT_CLASSIFIER_MODEL"] = MODEL
os.environ["LEARNKIT_EVALUATOR_MODEL"]  = MODEL
os.environ["LEARNKIT_DISTILLER_MODEL"]  = MODEL

_key_idx = 0
def get_next_key():
    """Get the next API key in the round-robin."""
    global _key_idx
    key = API_KEYS[_key_idx % len(API_KEYS)]
    _key_idx += 1
    return key

def get_next_lm():
    """Get a fresh DSPy LM instance using the next key."""
    return dspy.LM(MODEL, api_key=get_next_key())

def rotate_env_key():
    """Rotate the env var for LearnKit internals."""
    key = get_next_key()
    os.environ["GEMINI_API_KEY"] = key
    return key

# Set initial default
dspy.configure(lm=get_next_lm())

DELAY_BETWEEN_TASKS = 6  # seconds
DELAY_BETWEEN_PHASES = 10

# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK TASKS (5 tasks to fit within 40 req budget)
# ─────────────────────────────────────────────────────────────────────────────

TASKS = [
    {
        "id": "coding_1",
        "domain": "coding",
        "task": "Write a Python async web scraper with rate limiting that fetches URLs concurrently but limits to 10 requests per second.",
    },
    {
        "id": "coding_2",
        "domain": "coding",
        "task": "Debug a Python process that leaks memory when processing large CSV files with pandas. Explain root causes and fixes.",
    },
    {
        "id": "data_1",
        "domain": "data",
        "task": "Explain how to handle missing data in a time-series dataset for stock price prediction. Cover imputation strategies.",
    },
    {
        "id": "design_1",
        "domain": "design",
        "task": "Design a distributed rate limiter for a multi-region API gateway handling 100K req/s. Cover algorithm, storage, failures.",
    },
    {
        "id": "coding_3",
        "domain": "coding",
        "task": "Fix Python multiprocessing deadlocks on macOS. Explain why they happen and provide a complete solution.",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TaskResult:
    task_id: str
    domain: str
    phase: str
    quality_score: float
    response_time: float
    inference_mode: str = "n/a"
    records_retrieved: int = 0
    context_chars: int = 0
    response_preview: str = ""
    judge_reasoning: str = ""


@dataclass
class BenchmarkResults:
    baseline: list = field(default_factory=list)
    training: list = field(default_factory=list)
    warm_eval: list = field(default_factory=list)
    memory_stats: dict = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# ROBUST LLM WRAPPER FOR TRANSPARENT RETRIES
# ─────────────────────────────────────────────────────────────────────────────

import re
from typing import Any

class RobustLM(dspy.LM):
    """Wrapper that intercepts calls and automatically waits on rate limits."""
    def __init__(self, *args, **kwargs):
        # Always inject the next key if not explicitly set to something else? 
        # Actually, LearnKit components will pass api_key=None, and it will pick up GEMINI_API_KEY.
        # We can just override api_key here to force rotation!
        if "api_key" not in kwargs or not kwargs["api_key"]:
            kwargs["api_key"] = get_next_key()
        super().__init__(*args, **kwargs)
        
    def __call__(self, *args, **kwargs) -> Any:
        max_retries = 8
        for attempt in range(max_retries):
            try:
                return super().__call__(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RateLimit" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    match = re.search(r'retryDelay.*?(\d+)s', err_str)
                    wait = int(match.group(1)) + 2 if match else 15
                    print(f"    ⏳ API Rate Limit Hit, waiting {wait}s... rotating key (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    # Rotate key before next attempt
                    self.kwargs["api_key"] = get_next_key()
                else:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"    ⚠️ API Error, waiting 5s... ({str(e)[:60]})")
                    time.sleep(5)
        raise Exception("Max retries exceeded")

# Monkey-patch DSPy so all internal LearnKit instantiations use RobustLM with rotation
dspy.LM = RobustLM

def get_next_lm():
    """Get a fresh RobustLM instance using the next key."""
    return dspy.LM(MODEL)

def llm_call_with_retry(lm, prompt, label=""):
    """Simple wrapper since RobustLM handles retries internally."""
    try:
        response = lm(prompt)
        return response[0] if isinstance(response, list) else str(response)
    except Exception as e:
        return f"[ERROR: {e}]"


# ─────────────────────────────────────────────────────────────────────────────
# AGENT + EVALUATOR
# ─────────────────────────────────────────────────────────────────────────────

def call_bare_agent(task: str) -> str:
    """Bare Gemini — no LearnKit."""
    prompt = (
        "You are a helpful expert software engineer.\n\n"
        f"USER TASK: {task}\n\n"
        "Provide a clear, step-by-step answer in 300-500 words. Be concise but thorough."
    )
    return llm_call_with_retry(get_next_lm(), prompt, label="bare_agent")


def call_learnkit_agent(task: str, context: str = "") -> str:
    """Agent with LearnKit context injection."""
    system = "You are a helpful expert software engineer."
    if context:
        system += f"\n\n{context}"
    prompt = (
        f"{system}\n\nUSER TASK: {task}\n\n"
        "Provide a clear, step-by-step answer in 300-500 words. Be concise but thorough."
    )
    return llm_call_with_retry(get_next_lm(), prompt, label="lk_agent")


def evaluate_response(task: str, response: str) -> tuple:
    """Score response using LLM judge with retry logic."""
    evaluator = Evaluator()
    for attempt in range(3):
        try:
            lm = get_next_lm()
            result = evaluator.evaluate_with_llm_judge(task=task, response=response, lm=lm)
            return result.score, result.reasoning
        except Exception as e:
            if "429" in str(e) or "RateLimit" in str(e):
                print(f"    ⏳ Evaluator rate limited, waiting 15s (attempt {attempt+1}/3)...")
                time.sleep(15)
            else:
                return 2.0, f"Eval failed: {e}"
    return 2.0, "Evaluator max retries exceeded"


# ─────────────────────────────────────────────────────────────────────────────
# PHASE RUNNERS
# ─────────────────────────────────────────────────────────────────────────────

def run_phase1_baseline(results: BenchmarkResults):
    """Phase 1 — Baseline: Raw Gemini, no memory."""
    print("\n" + "═" * 70)
    print("  PHASE 1 — BASELINE (no LearnKit)")
    print("  Agent calls: key1 | Evaluator: key1")
    print("═" * 70)

    for i, t in enumerate(TASKS):
        print(f"\n  [{i+1}/{len(TASKS)}] {t['id']} ({t['domain']})")
        print(f"    Task: {t['task'][:80]}...")

        t0 = time.time()
        response = call_bare_agent(t["task"])
        elapsed = time.time() - t0

        score, reasoning = evaluate_response(t["task"], response)

        results.baseline.append(TaskResult(
            task_id=t["id"], domain=t["domain"], phase="baseline",
            quality_score=score, response_time=elapsed,
            response_preview=response[:150], judge_reasoning=reasoning,
        ))
        print(f"    Score: {score:.1f}/5  |  Time: {elapsed:.1f}s  |  {reasoning[:80]}")
        time.sleep(DELAY_BETWEEN_TASKS)


def run_phase2_training(lk_inst: lk.LearnKit, results: BenchmarkResults):
    """Phase 2 — LearnKit training. Classifier/distiller use key2."""
    print("\n" + "═" * 70)
    print("  PHASE 2 — LEARNKIT TRAINING (learning runs)")
    print("  Agent: key1 | Classifier+Distiller: key2 | Evaluator: key1")
    print("═" * 70)

    for i, t in enumerate(TASKS):
        print(f"\n  [{i+1}/{len(TASKS)}] {t['id']} ({t['domain']})")
        print(f"    Task: {t['task'][:80]}...")

        t0 = time.time()
        run_ctx = lk_inst.prepare_run(t["task"])
        mode = run_ctx["mode"]
        records = run_ctx["records"]
        ctx = run_ctx["context"]

        response = call_learnkit_agent(t["task"], context=ctx)
        elapsed = time.time() - t0

        score, reasoning = evaluate_response(t["task"], response)

        try:
            rotate_env_key()
            lk_inst.finalize_run(run_ctx, response)
        except Exception as e:
            print(f"    ⚠️  Finalize: {str(e)[:60]}")

        mem = len(lk_inst.backend.list_all())
        results.training.append(TaskResult(
            task_id=t["id"], domain=t["domain"], phase="training",
            quality_score=score, response_time=elapsed,
            inference_mode=mode.value, records_retrieved=len(records),
            context_chars=len(ctx), response_preview=response[:150],
            judge_reasoning=reasoning,
        ))
        print(f"    Score: {score:.1f}/5  |  Mode: {mode.value:13s}  |  Memory: {mem} recs")
        print(f"    Time: {elapsed:.1f}s  |  {reasoning[:80]}")
        time.sleep(DELAY_BETWEEN_TASKS)


def run_phase3_warm(lk_inst: lk.LearnKit, results: BenchmarkResults):
    """Phase 3 — Warm eval with populated memory."""
    print("\n" + "═" * 70)
    print("  PHASE 3 — LEARNKIT WARM EVALUATION (memory populated)")
    print("═" * 70)

    promoted = lk_inst.backend.promote_quarantined(min_age_hours=0.0)
    print(f"\n  🔓 Promoted {promoted} quarantined record(s) to active")

    all_recs = lk_inst.backend.list_all()
    print(f"  📦 Total records in memory: {len(all_recs)}")
    for r in all_recs:
        icon = "✅" if r.status == "active" else "🔒"
        print(f"     {icon} [{r.type:10s}] {r.status:12s} conf={r.confidence:.2f}")

    for i, t in enumerate(TASKS):
        print(f"\n  [{i+1}/{len(TASKS)}] {t['id']} ({t['domain']})")
        print(f"    Task: {t['task'][:80]}...")

        t0 = time.time()
        run_ctx = lk_inst.prepare_run(t["task"])
        mode = run_ctx["mode"]
        records = run_ctx["records"]
        ctx = run_ctx["context"]

        response = call_learnkit_agent(t["task"], context=ctx)
        elapsed = time.time() - t0

        score, reasoning = evaluate_response(t["task"], response)

        results.warm_eval.append(TaskResult(
            task_id=t["id"], domain=t["domain"], phase="warm_eval",
            quality_score=score, response_time=elapsed,
            inference_mode=mode.value, records_retrieved=len(records),
            context_chars=len(ctx), response_preview=response[:150],
            judge_reasoning=reasoning,
        ))
        print(f"    Score: {score:.1f}/5  |  Mode: {mode.value:13s}  |  Ctx: {len(ctx)} chars  |  Retrieved: {len(records)}")
        print(f"    Time: {elapsed:.1f}s  |  {reasoning[:80]}")
        time.sleep(DELAY_BETWEEN_TASKS)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────────

def print_results(results: BenchmarkResults):
    print("\n" + "═" * 90)
    print("  BENCHMARK RESULTS — COMPARISON TABLE")
    print("═" * 90)

    header = f"{'Task':<12} {'Domain':<8} {'Baseline':>8} {'Train':>8} {'Warm':>8} {'Δ(W-B)':>8} {'Mode(W)':>14}"
    print(f"\n  {header}")
    print(f"  {'─' * len(header)}")

    deltas = []
    for b, t, w in zip(results.baseline, results.training, results.warm_eval):
        delta = w.quality_score - b.quality_score
        deltas.append(delta)
        d = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        print(f"  {b.task_id:<12} {b.domain:<8} {b.quality_score:>7.1f}  {t.quality_score:>7.1f}  {w.quality_score:>7.1f}  {d:>7s}  {w.inference_mode:>13s}")

    print(f"  {'─' * len(header)}")

    avg_b = sum(r.quality_score for r in results.baseline) / len(results.baseline)
    avg_t = sum(r.quality_score for r in results.training) / len(results.training)
    avg_w = sum(r.quality_score for r in results.warm_eval) / len(results.warm_eval)
    avg_d = avg_w - avg_b
    improved = sum(1 for d in deltas if d > 0)
    tied = sum(1 for d in deltas if d == 0)
    degraded = sum(1 for d in deltas if d < 0)

    print(f"\n  SUMMARY")
    print(f"  {'─'*50}")
    print(f"  Avg Baseline Quality     : {avg_b:.2f} / 5.0")
    print(f"  Avg Training Quality     : {avg_t:.2f} / 5.0")
    print(f"  Avg Warm (w/ memory)     : {avg_w:.2f} / 5.0")
    print(f"  Avg Improvement (Δ)      : {'+' if avg_d >= 0 else ''}{avg_d:.2f}")
    print(f"  Tasks improved           : {improved}/{len(TASKS)}")
    print(f"  Tasks tied               : {tied}/{len(TASKS)}")
    print(f"  Tasks degraded           : {degraded}/{len(TASKS)}")

    # Memory
    total = results.memory_stats.get("total", 0)
    by_type = results.memory_stats.get("by_type", {})
    print(f"\n  MEMORY STORE")
    print(f"  {'─'*50}")
    print(f"  Total records: {total}")
    for tp, c in sorted(by_type.items()):
        print(f"    {tp:12s} : {c}")

    # Inference modes
    modes = {}
    for r in results.warm_eval:
        modes[r.inference_mode] = modes.get(r.inference_mode, 0) + 1
    print(f"\n  INFERENCE MODES (Warm Phase)")
    print(f"  {'─'*50}")
    for m, c in sorted(modes.items()):
        print(f"    {m:15s} : {c}/{len(TASKS)}")

    # Verdict
    print(f"\n  {'═'*50}")
    if avg_d > 0.2:
        print(f"  ✅ VERDICT: LearnKit improves quality by +{avg_d:.2f}")
    elif avg_d >= 0:
        print(f"  ➡️  VERDICT: Marginal improvement (+{avg_d:.2f})")
    else:
        print(f"  ⚠️  VERDICT: No improvement ({avg_d:.2f})")
    print(f"  {'═'*50}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "🔬 " * 15)
    print("  LearnKit MVP Benchmark")
    print("  Baseline vs LearnKit · 5 tasks · 3 phases · Real Gemini API")
    print("  Key1 → agent+eval  |  Key2 → classifier+distiller")
    print("🔬 " * 15)

    db_path = "/tmp/learnkit_benchmark.db"
    for s in ["", "-wal", "-shm"]:
        p = db_path + s
        if os.path.exists(p):
            os.remove(p)

    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=db_path,
        evaluation="llm_judge",
        quality_threshold=3.0,
        background_postprocess=False,
        scope="team",
    )

    results = BenchmarkResults()

    # Phase 1
    run_phase1_baseline(results)
    print(f"\n  ⏳ Cooling down {DELAY_BETWEEN_PHASES}s...")
    time.sleep(DELAY_BETWEEN_PHASES)

    # Phase 2
    run_phase2_training(memory, results)
    print(f"\n  ⏳ Cooling down {DELAY_BETWEEN_PHASES}s...")
    time.sleep(DELAY_BETWEEN_PHASES)

    # Phase 3
    run_phase3_warm(memory, results)

    # Collect stats
    all_recs = memory.backend.list_all()
    by_type = {}
    for r in all_recs:
        by_type[r.type] = by_type.get(r.type, 0) + 1
    results.memory_stats = {"total": len(all_recs), "by_type": by_type}

    # Print
    print_results(results)

    # Save JSON
    out = Path("examples/benchmark_results.json")
    raw = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": MODEL,
        "tasks": len(TASKS),
        "baseline": [asdict(r) for r in results.baseline],
        "training": [asdict(r) for r in results.training],
        "warm_eval": [asdict(r) for r in results.warm_eval],
        "memory_stats": results.memory_stats,
    }
    out.write_text(json.dumps(raw, indent=2) + "\n")
    print(f"\n  📄 Results saved to {out}")

    memory.shutdown(wait=True)
    print("\n  Done.\n")


if __name__ == "__main__":
    main()
