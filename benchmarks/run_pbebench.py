"""
LearnKit PBEBench-Lite benchmark runner.

Runs Programming-by-Example string transformation tasks in three arms:
    Control      — cold agent (no memory)
    Cold Start   — empty SQLite memory, online incremental learning
    Warmed Start — seeded with PBE skills, online incremental learning

Uses custom programmatic evaluator to verify correctness and score 0.0 or 5.0.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import litellm
import learnkit as lk
from learnkit.classifier import ClassificationOutput
from learnkit.evaluator import Evaluator, EvaluationResult, EvaluationSignal
from learnkit.skills_loader import seed_bundled_skills

AGENT_MODEL = os.environ.get("LEARNKIT_AGENT_MODEL", "openai/Qwen/Qwen2.5-Coder-32B-Instruct")
API_BASE = os.environ.get("LEARNKIT_API_BASE", "http://localhost:8001/v1")

SYSTEM_PROMPT = (
    "You are a programming assistant. Given input and output corpora, your job is to output "
    "an ordered Python list of replace() statement strings that transform each input to its "
    "corresponding output. Output ONLY the code block and nothing else."
)


def call_agent(system: str, user: str, max_retries: int = 3) -> tuple[str, dict, float]:
    for attempt in range(max_retries):
        try:
            t0 = time.perf_counter()
            r = litellm.completion(
                model=AGENT_MODEL,
                api_base=API_BASE,
                api_key="anything",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.0,
                max_tokens=300,
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
            wait = 2**attempt
            print(f"    [retry] Attempt {attempt+1} failed: {e}. Sleeping {wait}s")
            time.sleep(wait)
    return "", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, 0.0


def parse_pbe_response(response: str) -> list[str]:
    # Look for python code blocks
    code_blocks = re.findall(r'```(?:python)?\s*(.*?)\s*```', response, re.DOTALL)
    candidate_strs = code_blocks if code_blocks else [response]
    for candidate in reversed(candidate_strs):
        candidate = candidate.strip()
        try:
            parsed = ast.literal_eval(candidate)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except Exception:
            pass
    # Regex fallback to find replace() calls
    matches = re.findall(r'replace\([^)]*\)', response)
    if matches:
        return matches
    return []


def run_pbe_program(replace_calls: list[str], inputs: list[str]) -> list[str]:
    current_list = list(inputs)
    for call in replace_calls:
        call = call.strip()
        if not call.startswith("replace("):
            continue
        try:
            tree = ast.parse(call)
            if (isinstance(tree, ast.Module) and 
                len(tree.body) == 1 and 
                isinstance(tree.body[0], ast.Expr) and 
                isinstance(tree.body[0].value, ast.Call) and 
                isinstance(tree.body[0].value.func, ast.Name) and 
                tree.body[0].value.func.id == "replace"):
                
                args = tree.body[0].value.args
                if len(args) == 2:
                    old_str = ast.literal_eval(args[0])
                    new_str = ast.literal_eval(args[1])
                    current_list = [s.replace(old_str, new_str) for s in current_list]
        except Exception:
            pass
    return current_list


def parse_inputs_outputs_from_prompt(prompt: str) -> tuple[list[str], list[str]]:
    inputs_matches = list(re.finditer(r"### Inputs\s*\n([^\n]+)", prompt))
    outputs_matches = list(re.finditer(r"### Outputs\s*\n([^\n]+)", prompt))
    inputs, outputs = [], []
    if inputs_matches:
        try:
            inputs = ast.literal_eval(inputs_matches[-1].group(1).strip())
        except Exception:
            pass
    if outputs_matches:
        try:
            outputs = ast.literal_eval(outputs_matches[-1].group(1).strip())
        except Exception:
            pass
    return inputs, outputs


class ProgrammaticPBEEvaluator(Evaluator):
    def evaluate_with_llm_judge(self, task: str, response: str, reasoning_trace=None, lm=None) -> EvaluationResult:
        inputs, outputs = parse_inputs_outputs_from_prompt(task)
        replace_calls = parse_pbe_response(response)
        actual = run_pbe_program(replace_calls, inputs)
        
        matches = (actual == outputs)
        score = 5.0 if matches else 0.0
        reasoning = f"Program outputs match expected." if matches else f"Mismatch: expected {outputs}, got {actual}"
        
        return EvaluationResult(
            score=score,
            signal=EvaluationSignal.USER_FEEDBACK,
            reasoning=reasoning,
            metadata={"replace_calls": replace_calls, "actual": actual, "expected": outputs}
        )


def pbe_classifier(task: str) -> ClassificationOutput:
    return ClassificationOutput(
        task_type="pbe_string_transformation",
        domains={"coding": 1.0},
        complexity="medium"
    )


def run_control(tasks: list[dict]) -> list[dict]:
    out = []
    print("\n  [CONTROL]")
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} task_{t['id']}", end="", flush=True)
        
        inputs, outputs = parse_inputs_outputs_from_prompt(t["prompt"])
        history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": t["prompt"]}
        ]
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_latency = 0.0
        
        resp = ""
        max_attempts = 4
        for attempt in range(max_attempts):
            t0 = time.perf_counter()
            try:
                r = litellm.completion(
                    model=AGENT_MODEL,
                    api_base=API_BASE,
                    api_key="anything",
                    messages=history,
                    temperature=0.0,
                    max_tokens=300,
                )
                latency = time.perf_counter() - t0
                resp = r.choices[0].message.content or ""
                u = r.usage
                total_usage["prompt_tokens"] += getattr(u, "prompt_tokens", 0)
                total_usage["completion_tokens"] += getattr(u, "completion_tokens", 0)
                total_usage["total_tokens"] += getattr(u, "total_tokens", 0)
                total_latency += latency
                
                replace_calls = parse_pbe_response(resp)
                actual = run_pbe_program(replace_calls, inputs)
                print(f"\n        [Attempt {attempt+1}] parsed: {replace_calls} -> actual: {actual}")
                if actual == outputs:
                    print(f"        [Success] Match found on attempt {attempt+1}!")
                    break
                if attempt == max_attempts - 1:
                    break
                history.append({"role": "assistant", "content": resp})
                feedback = (
                    f"Execution feedback:\n"
                    f"Applying your replace program resulted in:\n{actual}\n"
                    f"But the expected output was:\n{outputs}\n\n"
                    f"Please correct the order or values of the replace statements. "
                    f"Respond ONLY with the revised python code block containing the replace statements."
                )
                history.append({"role": "user", "content": feedback})
            except Exception as e:
                total_latency += time.perf_counter() - t0
                print(f" Error: {e}")
                break
                
        replace_calls = parse_pbe_response(resp)
        actual = run_pbe_program(replace_calls, inputs)
        s = 5.0 if actual == outputs else 0.0
        
        print(f"  score={s:.1f}  tokens={total_usage['total_tokens']}  latency={total_latency:.1f}s")
        out.append({
            "arm": "control",
            "task_id": t["id"],
            "response": resp,
            "score": s,
            "usage": total_usage,
            "latency_s": total_latency,
            "learnkit_context_chars": 0,
        })
    return out


def run_treatment(tasks: list[dict], db_path: Path, seed: bool) -> list[dict]:
    arm_name = "warmed_start" if seed else "cold_start"
    print(f"\n  [{arm_name.upper()}]  (db: {db_path.name})")

    import dspy
    from learnkit.distiller import MemoryDistiller
    distill_model = os.environ.get("LEARNKIT_DISTILLER_MODEL")
    if distill_model:
        distill_lm = dspy.LM(distill_model, api_base=API_BASE, api_key="anything")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        distill_lm = dspy.LM("anthropic/claude-haiku-4-5-20251001")
    elif os.environ.get("GEMINI_API_KEY"):
        distill_lm = dspy.LM("gemini/gemini-flash-lite-latest")
    else:
        distill_lm = dspy.LM(AGENT_MODEL, api_base=API_BASE, api_key="anything")
    distiller = MemoryDistiller(lm=distill_lm)
    
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=str(db_path),
        scope="user",
        background_postprocess=False,  # sync
        classifier=pbe_classifier,
        evaluator=ProgrammaticPBEEvaluator(),
        distiller=distiller,
        auto_promote=True,  # bypass 24h quarantine for online benchmark learning
    )
    
    if seed:
        seeded_count = seed_bundled_skills(memory.backend)
        print(f"    Seeded {seeded_count} bundled skills.")
        
    context_holder: dict = {"chars": 0}
    
    @memory.agent(domain="coding")
    def ask(task: str, _learnkit_context: str = "") -> str:
        context_holder["chars"] = len(_learnkit_context)
        system = (
            f"{SYSTEM_PROMPT}\n\n{_learnkit_context}"
            if _learnkit_context
            else SYSTEM_PROMPT
        )
        
        inputs, outputs = parse_inputs_outputs_from_prompt(task)
        history = [
            {"role": "system", "content": system},
            {"role": "user", "content": task}
        ]
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        total_latency = 0.0
        
        text = ""
        max_attempts = 4
        for attempt in range(max_attempts):
            t0 = time.perf_counter()
            try:
                r = litellm.completion(
                    model=AGENT_MODEL,
                    api_base=API_BASE,
                    api_key="anything",
                    messages=history,
                    temperature=0.0,
                    max_tokens=300,
                )
                latency = time.perf_counter() - t0
                text = r.choices[0].message.content or ""
                u = r.usage
                total_usage["prompt_tokens"] += getattr(u, "prompt_tokens", 0)
                total_usage["completion_tokens"] += getattr(u, "completion_tokens", 0)
                total_usage["total_tokens"] += getattr(u, "total_tokens", 0)
                total_latency += latency
                
                replace_calls = parse_pbe_response(text)
                actual = run_pbe_program(replace_calls, inputs)
                print(f"\n        [Attempt {attempt+1}] parsed: {replace_calls} -> actual: {actual}")
                if actual == outputs:
                    print(f"        [Success] Match found on attempt {attempt+1}!")
                    break
                if attempt == max_attempts - 1:
                    break
                history.append({"role": "assistant", "content": text})
                feedback = (
                    f"Execution feedback:\n"
                    f"Applying your replace program resulted in:\n{actual}\n"
                    f"But the expected output was:\n{outputs}\n\n"
                    f"Please correct the order or values of the replace statements. "
                    f"Respond ONLY with the revised python code block containing the replace statements."
                )
                history.append({"role": "user", "content": feedback})
            except Exception as e:
                total_latency += time.perf_counter() - t0
                print(f" Error: {e}")
                break
                
        context_holder["usage"] = total_usage
        context_holder["latency_s"] = total_latency
        return text

    out = []
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} task_{t['id']}", end="", flush=True)
        resp = ask(t["prompt"])
        
        # Retrieve score from trajectory post-processing
        traj = memory.last_trajectory
        s = traj.quality_score if traj else 0.0
        attribution = memory.last_attribution or {}
        
        ctx = context_holder.get("chars", 0)
        usage = context_holder.get("usage", {"total_tokens": 0})
        latency = context_holder.get("latency_s", 0.0)
        
        print(f"  score={s:.1f}  ctx={ctx}  tokens={usage['total_tokens']}  latency={latency:.1f}s")
        
        out.append({
            "arm": arm_name,
            "task_id": t["id"],
            "response": resp,
            "score": s,
            "usage": usage,
            "latency_s": latency,
            "learnkit_context_chars": ctx,
            "attribution": attribution,
        })
        
    memory.shutdown(wait=True)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20, help="Limit number of tasks")
    parser.add_argument("--tasks", type=str, default="pbebench_lite_pilot.jsonl", help="Tasks file name")
    args = parser.parse_args()

    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "results" / f"pbe_{run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Run ID: {run_id}")
    print(f"Output directory: {out_dir}")
    print(f"Agent Model: {AGENT_MODEL}")
    
    # Load tasks
    tasks_file = HERE / "tasks" / args.tasks
    if not tasks_file.exists():
        print(f"Error: Tasks file not found at {tasks_file}")
        sys.exit(1)
        
    with open(tasks_file, encoding="utf-8") as f:
        tasks = [json.loads(line) for line in f if line.strip()][:args.limit]
    # Assign index-based IDs if numeric ID is missing
    for idx, t in enumerate(tasks, 1):
        if "id" not in t:
            t["id"] = idx
            
    print(f"Loaded {len(tasks)} tasks.")
    
    records = []
    
    # 1. Run Control
    records.extend(run_control(tasks))
    
    # 2. Run Cold Start
    db_cold = out_dir / "learnkit_cold.db"
    records.extend(run_treatment(tasks, db_cold, seed=False))
    
    # 3. Run Warmed Start
    db_warmed = out_dir / "learnkit_warmed.db"
    records.extend(run_treatment(tasks, db_warmed, seed=True))
    
    # Save raw records
    (out_dir / "raw.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    
    # Summarize results
    arms = ["control", "cold_start", "warmed_start"]
    summary_lines = [
        "# LearnKit PBEBench-Lite Benchmark Results",
        f"\nRun: `{run_id}`",
        f"Agent Model: `{AGENT_MODEL}`",
        f"Tasks Run: {len(tasks)}",
        "\n## Summary Table",
        "\n| Arm | Pass Rate (%) | Mean Latency (s) | Mean Total Tokens |",
        "|---|---|---|---|",
    ]
    
    for arm in arms:
        arm_recs = [r for r in records if r["arm"] == arm]
        if not arm_recs:
            continue
        pass_rate = sum(1 for r in arm_recs if r["score"] > 3.5) / len(arm_recs) * 100
        mean_lat = sum(r["latency_s"] for r in arm_recs) / len(arm_recs)
        mean_tokens = sum(r["usage"]["total_tokens"] for r in arm_recs) / len(arm_recs)
        
        summary_lines.append(f"| {arm} | {pass_rate:.1f}% | {mean_lat:.2f}s | {mean_tokens:.1f} |")
        
    summary_lines.extend([
        "\n## Compounding Curve (Score per task index)",
        "\n| Arm | " + " | ".join(f"t{i}" for i in range(1, len(tasks) + 1)) + " |",
        "|---| " + " | ".join("---" for _ in range(len(tasks))) + " |",
    ])
    
    for arm in arms:
        arm_recs = [r for r in records if r["arm"] == arm]
        if not arm_recs:
            continue
        scores = [f"{r['score']:.0f}" for r in arm_recs]
        summary_lines.append(f"| {arm} | " + " | ".join(scores) + " |")
        
    (out_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\nDone! Results written to {out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
