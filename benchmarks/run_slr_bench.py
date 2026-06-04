"""
LearnKit SLR-Bench benchmark runner.

Runs Symbolic Logic Reasoning (SLR) train classification tasks in three arms:
    Control      — cold agent (no memory)
    Cold Start   — empty SQLite memory, online incremental learning
    Warmed Start — seeded with SLR skills, online incremental learning

Uses custom programmatic evaluator to verify correctness and score 0.0 or 5.0.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

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
    "You are a logic programming assistant. Output ONLY a single Prolog rule of the form "
    "'eastbound(T) :- Body.' inside a fenced code block that correctly classifies eastbound "
    "vs westbound trains. No explanation or prose."
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


def parse_slr_response(response: str) -> str:
    code_blocks = re.findall(r'```(?:prolog|logic|python)?\s*(.*?)\s*```', response, re.DOTALL)
    candidates = code_blocks if code_blocks else [response]
    for candidate in reversed(candidates):
        match = re.search(r'eastbound\([^)]*\)\s*:-\s*[^.]+\.', candidate)
        if match:
            return match.group(0)
    return ""


def parse_prolog_facts(facts_text: str) -> dict[str, set[tuple[str, ...]]]:
    relations = {}
    for line in facts_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        match = re.match(r'^([a-zA-Z0-9_]+)\(([^)]+)\)\.$', line)
        if match:
            pred = match.group(1)
            args = tuple(arg.strip() for arg in match.group(2).split(","))
            relations.setdefault(pred, set()).add(args)
    return relations


def parse_prolog_rule(rule_str: str):
    rule_str = rule_str.strip().rstrip(".")
    if ":-" not in rule_str:
        return None
    head_part, body_part = rule_str.split(":-", 1)
    
    head_match = re.match(r'^([a-zA-Z0-9_]+)\(([^)]+)\)$', head_part.strip())
    if not head_match:
        return None
    head_pred = head_match.group(1)
    head_args = [arg.strip() for arg in head_match.group(2).split(",")]
    
    literals = []
    lit_matches = re.findall(r'([a-zA-Z0-9_]+)\(([^)]+)\)', body_part)
    for pred, args_str in lit_matches:
        args = [arg.strip() for arg in args_str.split(",")]
        literals.append({"pred": pred, "args": args})
        
    return {"pred": head_pred, "args": head_args}, literals


def evaluate_rule_on_train(relations: dict[str, set[tuple[str, ...]]], rule, train_id: str) -> bool:
    if not rule:
        return False
    head, literals = rule
    if head["pred"] != "eastbound" or len(head["args"]) != 1:
        return False
    
    head_var = head["args"][0]
    vars_in_rule = set()
    for lit in literals:
        for arg in lit["args"]:
            if arg[0].isupper():
                vars_in_rule.add(arg)
    vars_in_rule.add(head_var)
    
    vars_list = list(vars_in_rule)
    assignment = {head_var: train_id}
    remaining_vars = [v for v in vars_list if v != head_var]
    
    constants = set()
    for pred, tuples in relations.items():
        for t in tuples:
            for item in t:
                constants.add(item)
                
    def backtrack(var_idx: int) -> bool:
        if var_idx == len(remaining_vars):
            for lit in literals:
                pred = lit["pred"]
                if pred not in relations:
                    return False
                ground_args = tuple(assignment.get(arg, arg) for arg in lit["args"])
                if ground_args not in relations[pred]:
                    return False
            return True
            
        var = remaining_vars[var_idx]
        for val in constants:
            assignment[var] = val
            if backtrack(var_idx + 1):
                return True
        return False
        
    return backtrack(0)


def parse_slr_prompt(prompt: str):
    positive_trains = re.findall(r'eastbound\((train\d+)\)\.', prompt)
    negative_trains = re.findall(r'westbound\((train\d+)\)\.', prompt)
    
    relations = {}
    fact_matches = re.findall(r'([a-zA-Z0-9_]+)\(([^)]+)\)\.', prompt)
    for pred, args_str in fact_matches:
        if pred in ("eastbound", "westbound"):
            continue
        args = tuple(arg.strip() for arg in args_str.split(","))
        relations.setdefault(pred, set()).add(args)
        
    return positive_trains, negative_trains, relations


class ProgrammaticSLREvaluator(Evaluator):
    def evaluate_with_llm_judge(self, task: str, response: str, reasoning_trace=None, lm=None) -> EvaluationResult:
        pos_trains, neg_trains, relations = parse_slr_prompt(task)
        rule_str = parse_slr_response(response)
        
        if not rule_str:
            return EvaluationResult(
                score=0.0,
                signal=EvaluationSignal.USER_FEEDBACK,
                reasoning="No valid Prolog rule found.",
                metadata={"rule": ""}
            )
            
        rule = parse_prolog_rule(rule_str)
        if not rule:
            return EvaluationResult(
                score=0.0,
                signal=EvaluationSignal.USER_FEEDBACK,
                reasoning=f"Failed to parse rule: {rule_str}",
                metadata={"rule": rule_str}
            )
            
        pos_correct = True
        failed_pos = []
        for t in pos_trains:
            if not evaluate_rule_on_train(relations, rule, t):
                pos_correct = False
                failed_pos.append(t)
                
        neg_correct = True
        failed_neg = []
        for t in neg_trains:
            if evaluate_rule_on_train(relations, rule, t):
                neg_correct = False
                failed_neg.append(t)
                
        matches = (pos_correct and neg_correct)
        score = 5.0 if matches else 0.0
        reasoning = "Perfect separation." if matches else f"Mismatch. Failed pos: {failed_pos}, failed neg: {failed_neg}"
        
        return EvaluationResult(
            score=score,
            signal=EvaluationSignal.USER_FEEDBACK,
            reasoning=reasoning,
            metadata={"rule": rule_str, "pos_correct": pos_correct, "neg_correct": neg_correct}
        )


def slr_classifier(task: str) -> ClassificationOutput:
    return ClassificationOutput(
        task_type="symbolic_logic_reasoning",
        domains={"coding": 1.0},
        complexity="medium"
    )


def run_control(tasks: list[dict]) -> list[dict]:
    out = []
    print("\n  [CONTROL]")
    for i, t in enumerate(tasks, 1):
        print(f"    {i:2d}/{len(tasks)} task_{t['id']}", end="", flush=True)
        resp, usage, latency = call_agent(SYSTEM_PROMPT, t["prompt"])
        
        # Grade programmatically
        pos_trains, neg_trains, relations = parse_slr_prompt(t["prompt"])
        rule_str = parse_slr_response(resp)
        s = 0.0
        if rule_str:
            rule = parse_prolog_rule(rule_str)
            if rule:
                pos_correct = all(evaluate_rule_on_train(relations, rule, pt) for pt in pos_trains)
                neg_correct = all(not evaluate_rule_on_train(relations, rule, nt) for nt in neg_trains)
                if pos_correct and neg_correct:
                    s = 5.0
                    
        print(f"  score={s:.1f}  tokens={usage['total_tokens']}  latency={latency:.1f}s")
        out.append({
            "arm": "control",
            "task_id": t["id"],
            "response": resp,
            "score": s,
            "usage": usage,
            "latency_s": latency,
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
    
    # Initialize LearnKit
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=str(db_path),
        scope="user",
        background_postprocess=False,  # sync
        classifier=slr_classifier,
        evaluator=ProgrammaticSLREvaluator(),
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
        text, usage, latency = call_agent(system, task)
        context_holder["usage"] = usage
        context_holder["latency_s"] = latency
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
    parser.add_argument("--tasks", type=str, default="slr_bench_v1_all.jsonl", help="Tasks file name")
    args = parser.parse_args()

    run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = HERE / "results" / f"slr_{run_id}"
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
        "# LearnKit SLR-Bench Benchmark Results",
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
