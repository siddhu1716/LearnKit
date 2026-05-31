"""
examples/multi_iteration_benchmark.py

Highly targeted, multi-iteration E2E benchmark demonstrating:
1. Continuous learning (Cold Start -> Immediate failure avoidance -> Reinforcement)
2. Dynamic key rotation for free-tier rate limits (utilizing 5 API keys)
3. Transparent error & rate limit handling via a custom patched RobustLM

We contrast a stateless bare Gemini LLM against a LearnKit-enabled Gemini agent
over 5 consecutive runs on the exact same complex platform task.
"""

import os
import re
import time
import json
import sqlite3
from typing import Any
import dspy
import learnkit as lk
from learnkit.evaluator import Evaluator

# ─────────────────────────────────────────────────────────────────────────────
# 1. API KEYS & GLOBAL ROUND-ROBIN ROTATION (5 Keys total)
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
    global _key_idx
    key = API_KEYS[_key_idx % len(API_KEYS)]
    _key_idx += 1
    return key

# ─────────────────────────────────────────────────────────────────────────────
# 2. MONKEY-PATCH DSPY FOR ROBUST RATE-LIMIT TRANSPARENCY
# ─────────────────────────────────────────────────────────────────────────────

class RobustLM(dspy.LM):
    def __init__(self, *args, **kwargs):
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
                    print(f"    ⏳ Rate limit, waiting {wait}s... rotating key (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    self.kwargs["api_key"] = get_next_key()
                else:
                    if attempt == max_retries - 1:
                        raise e
                    print(f"    ⚠️ API Error, waiting 5s... ({str(e)[:60]})")
                    time.sleep(5)
        raise Exception("Max retries exceeded")

dspy.LM = RobustLM

def get_next_lm():
    return dspy.LM(MODEL)

# Configure default DSPy LM
dspy.configure(lm=get_next_lm())

# ─────────────────────────────────────────────────────────────────────────────
# 3. BENCHMARK SUITE CONFIGURATION & STATE
# ─────────────────────────────────────────────────────────────────────────────

TASK = (
    "How do I fix Python multiprocessing deadlocks on macOS? "
    "Provide a minimal code snippet illustrating how to set the correct start method, "
    "and explain the root cause in exactly one paragraph. Keep it extremely concise."
)

DB_PATH = "/tmp/multi_iter_benchmark.db"

# Reset DB for a clean test
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
if os.path.exists(DB_PATH + "-wal"):
    os.remove(DB_PATH + "-wal")
if os.path.exists(DB_PATH + "-shm"):
    os.remove(DB_PATH + "-shm")

# Initialize LearnKit in production sync mode
memory = lk.LearnKit(
    memory_backend="sqlite",
    db_path=DB_PATH,
    evaluation="llm_judge",
    quality_threshold=3.0,
    background_postprocess=False,  # sync distillation for testing
    scope="team",
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. RUNNERS (Control vs Experimental)
# ─────────────────────────────────────────────────────────────────────────────

def call_bare_agent(task: str) -> str:
    """Bare Gemini Agent (Stateless)"""
    prompt = (
        "You are a helpful expert software engineer.\n\n"
        f"USER TASK: {task}\n\n"
        "Provide a direct, step-by-step answer. Write minimal code, NO conversational intro/outro. "
        "Explain the macOS platform issue concisely."
    )
    lm = get_next_lm()
    res = lm(prompt)
    return res[0] if isinstance(res, list) else str(res)

@memory.agent(domain="coding", task_type="python_debugging")
def call_learnkit_agent(task: str, _learnkit_context: str = "") -> str:
    """LearnKit-driven Gemini Agent (Stateful)"""
    system = (
        "You are a helpful expert software engineer. "
        "Provide a direct, step-by-step answer. Write minimal code, NO conversational intro/outro. "
        "Explain the macOS platform issue concisely."
    )
    if _learnkit_context:
        system += f"\n\n{_learnkit_context}"
    
    prompt = f"{system}\n\nUSER TASK: {task}"
    lm = get_next_lm()
    res = lm(prompt)
    return res[0] if isinstance(res, list) else str(res)

def evaluate_response(task: str, response: str) -> float:
    evaluator = Evaluator()
    for attempt in range(3):
        try:
            lm = get_next_lm()
            result = evaluator.evaluate_with_llm_judge(task=task, response=response, lm=lm)
            return result.score
        except Exception as e:
            print(f"    ⚠️ Eval error: {e}, retrying...")
            time.sleep(3)
    return 2.0

# ─────────────────────────────────────────────────────────────────────────────
# 5. EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n🔬 " + "═"*70 + " 🔬")
    print("  LEARNKIT MULTI-ITERATION CONTINUOUS LEARNING BENCHMARK")
    print("  Task: macOS Multiprocessing Deadlocks (5 Sequential Iterations)")
    print("🔬 " + "═"*70 + " 🔬\n")

    control_scores = []
    learnkit_scores = []
    modes = []
    retrieved_counts = []
    
    # ── CONTROL GROUP: Stateless Bare LLM ─────────────────────────────────────
    print("══════════════════════════════════════════════════════════════════════")
    print("  RUNNING CONTROL GROUP (Stateless Raw LLM)")
    print("══════════════════════════════════════════════════════════════════════")
    for i in range(5):
        print(f"\n👉 [Control Iteration {i+1}/5]")
        t0 = time.time()
        response = call_bare_agent(TASK)
        score = evaluate_response(TASK, response)
        control_scores.append(score)
        print(f"   Score: {score:.1f}/5.0  |  Time: {time.time()-t0:.1f}s")
        time.sleep(5)  # cool down

    # ── EXPERIMENTAL GROUP: LearnKit ──────────────────────────────────────────
    print("\n══════════════════════════════════════════════════════════════════════")
    print("  RUNNING EXPERIMENTAL GROUP (LearnKit-enabled)")
    print("══════════════════════════════════════════════════════════════════════")
    for i in range(5):
        print(f"\n👉 [LearnKit Iteration {i+1}/5]")
        t0 = time.time()
        
        # Prepare run (retrieval + mode logic)
        run_ctx = memory.prepare_run(TASK)
        mode = run_ctx["mode"]
        records = run_ctx["records"]
        context = run_ctx["context"]
        
        modes.append(mode.value.upper())
        retrieved_counts.append(len(records))
        
        print(f"   Inference Mode   : {mode.value.upper()}")
        print(f"   Retrieved Records: {len(records)}")
        
        # Call agent
        response = call_learnkit_agent(TASK)
        
        # Score and finalize
        score = evaluate_response(TASK, response)
        learnkit_scores.append(score)
        
        # distills trajectory + updates database
        memory.finalize_run(run_ctx, response)
        
        # Promote quarantined skills/facts instantly for E2E testing
        promoted = memory.backend.promote_quarantined(min_age_hours=0.0)
        
        print(f"   Score: {score:.1f}/5.0  |  Promoted: {promoted}  |  Time: {time.time()-t0:.1f}s")
        time.sleep(5)  # cool down

    # ── FINAL COMPARISON DISPLAY ──────────────────────────────────────────────
    print("\n" + "═"*74)
    print("  MULTI-ITERATION BENCHMARK RESULTS")
    print("═"*74)
    print(f"  {'Iteration':10s} | {'Bare Score':10s} | {'LearnKit':10s} | {'Inference Mode':15s} | {'Retrieved':10s}")
    print("-" * 74)
    for i in range(5):
        print(f"  {i+1:9d}  |  {control_scores[i]:8.1f}  |  {learnkit_scores[i]:8.1f}  |  {modes[i]:15s}  |  {retrieved_counts[i]:9d}")
    print("-" * 74)
    
    avg_control = sum(control_scores) / len(control_scores)
    avg_lk = sum(learnkit_scores) / len(learnkit_scores)
    print(f"  {'Average':10s} |  {avg_control:8.1f}  |  {avg_lk:8.1f}  |")
    print("═"*74)
    
    total_mem = len(memory.backend.list_all())
    print(f"  🎉 Total persistent records in SQLite database: {total_mem}")
    
    # Save results to a dedicated file
    results = {
        "control_scores": control_scores,
        "learnkit_scores": learnkit_scores,
        "modes": modes,
        "retrieved_counts": retrieved_counts,
        "avg_control": avg_control,
        "avg_lk": avg_lk,
        "total_records": total_mem
    }
    with open("examples/multi_iteration_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("  💾 Saved results to examples/multi_iteration_results.json")
    print("═"*74 + "\n")

if __name__ == "__main__":
    main()
