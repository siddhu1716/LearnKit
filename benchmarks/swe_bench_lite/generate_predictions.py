import os
import sys
import re
import json
import argparse
from pathlib import Path
import subprocess
import time
from datasets import load_dataset
import litellm
import learnkit as lk
from learnkit.evaluator import Evaluator, EvaluationResult, EvaluationSignal

# 1. Environment configuration
os.environ["OPENAI_API_BASE"] = "http://localhost:8001/v1"
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["LEARNKIT_DISTILLER_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"
os.environ["LEARNKIT_EVALUATOR_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"
os.environ["LEARNKIT_CLASSIFIER_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"

AGENT_MODEL = "openai/Qwen/Qwen2.5-72B-Instruct"
REPO_DIR = Path(__file__).parent / "pytest_repo"

def run_git_cmd(args: list[str]) -> str:
    """Run a git command in the pytest repository and return stdout."""
    res = subprocess.run(
        ["git", "-C", str(REPO_DIR)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    if res.returncode != 0:
        print(f"Git command failed: git {' '.join(args)}\nError: {res.stderr}")
    return res.stdout

def get_modified_file(patch: str) -> str:
    """Parse the gold patch to get the modified file path."""
    for line in patch.splitlines():
        if line.startswith("--- a/"):
            return line[6:]
    return ""

def apply_search_replace(file_content: str, response: str) -> str:
    """Apply a Search-and-Replace block to the file content with robust fuzzy and line-matching fallback."""
    # 1. Parse all blocks in format <<<<<<< ORIGINAL ... ======= ... >>>>>>> SUGGESTED
    pattern = re.compile(r"<<<<<<<.*?\n(.*?)\n=======\n(.*?)\n>>>>>>>", re.DOTALL)
    matches = pattern.findall(response)
    if not matches:
        pattern = re.compile(r"<<<<<<<[^\n]*\s*(.*?)\s*=======\s*(.*?)\s*>>>>>>>", re.DOTALL)
        matches = pattern.findall(response)
        
    if not matches:
        print("  WARNING: No Search-and-Replace block matches found in response.")
        return file_content
        
    new_content = file_content
    for original, replacement in matches:
        original_stripped = original.strip()
        replacement_stripped = replacement.strip()
        
        # Scenario A: Exact match of stripped text
        if original_stripped in new_content:
            new_content = new_content.replace(original_stripped, replacement_stripped, 1)
            print("  Successfully applied search-replace block.")
            continue
            
        # Scenario B: Match with exact original block including whitespace
        if original in new_content:
            new_content = new_content.replace(original, replacement, 1)
            print("  Successfully applied exact search-replace block.")
            continue

        # Scenario C: Normalize line endings and match
        original_normalized = original_stripped.replace("\r\n", "\n")
        new_content_normalized = new_content.replace("\r\n", "\n")
        if original_normalized in new_content_normalized:
            new_content = new_content_normalized.replace(original_normalized, replacement_stripped.replace("\r\n", "\n"), 1)
            print("  Successfully applied normalized search-replace block.")
            continue
            
        # Scenario D: Fuzzy line-based match to tolerate minor LLM typos in ORIGINAL block
        orig_lines = [line.strip() for line in original_stripped.splitlines() if line.strip()]
        if not orig_lines:
            continue
            
        file_lines = new_content.splitlines()
        n_orig = len(orig_lines)
        best_start_idx = -1
        best_match_count = 0
        
        for idx in range(len(file_lines) - n_orig + 1):
            match_count = 0
            for j in range(n_orig):
                f_line = file_lines[idx + j].strip()
                o_line = orig_lines[j]
                # Match if identical, or if one is a substring of the other (allowing minor typos/punctuation differences)
                if o_line == f_line or o_line in f_line or f_line in o_line:
                    match_count += 1
            if match_count > best_match_count:
                best_match_count = match_count
                best_start_idx = idx
                
        # If at least 70% of lines match, apply fuzzy replacement
        if best_match_count > 0 and (best_match_count / n_orig) >= 0.7:
            print(f"  Successfully applied fuzzy search-replace block (matched {best_match_count}/{n_orig} lines).")
            new_lines = file_lines[:best_start_idx] + replacement_stripped.splitlines() + file_lines[best_start_idx + n_orig:]
            new_content = "\n".join(new_lines)
        else:
            print("  WARNING: ORIGINAL block not found in file content (even with fuzzy match)!")
            
    return new_content

def call_agent(system_prompt: str, user_prompt: str) -> str:
    """Call the local Qwen model to generate predictions."""
    try:
        r = litellm.completion(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"Error calling agent: {e}")
        return ""

def evaluate_patch_llm(problem_statement: str, rel_path: str, agent_patch: str, gold_patch: str) -> float:
    """Compare agent patch with gold patch using local Qwen as a judge."""
    system = (
        "You are an expert code reviewer. Compare the agent's proposed patch with the gold (correct) patch "
        "for the given issue. Determine if the agent's patch is semantically equivalent and correctly fixes "
        "the bug. Output a score from 1.0 (completely wrong) to 5.0 (perfect fix). "
        "Reply with a single line containing only the numeric score, e.g., 5.0 or 1.0."
    )
    user = (
        f"ISSUE:\n{problem_statement}\n\n"
        f"FILE: {rel_path}\n\n"
        f"GOLD PATCH:\n{gold_patch}\n\n"
        f"AGENT PROPOSED PATCH:\n{agent_patch}\n\n"
        "Output the numeric score now:"
    )
    try:
        r = litellm.completion(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=10,
        )
        content = r.choices[0].message.content or "1.0"
        match = re.search(r"\b([1-5](?:\.\d+)?)\b", content)
        if match:
            return float(match.group(1))
        return 1.0
    except Exception as e:
        print(f"Error calling LLM judge: {e}")
        return 1.0


class GoldPatchEvaluator(Evaluator):
    """Custom Evaluator that evaluates the agent's generated patch against the gold patch."""
    def __init__(self):
        super().__init__()
        self.problem_statement = ""
        self.rel_path = ""
        self.gold_patch = ""
        self.agent_patch = ""

    def evaluate_with_llm_judge(self, task: str, response: str, reasoning_trace: str = None, lm=None) -> EvaluationResult:
        score = evaluate_patch_llm(self.problem_statement, self.rel_path, self.agent_patch, self.gold_patch)
        return EvaluationResult(
            score=score,
            signal=EvaluationSignal.LLM_JUDGE,
            reasoning=f"LLM compared generated diff against gold patch. Score: {score}/5.0"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=["control", "treatment"], default="control")
    parser.add_argument("--limit", type=int, default=17, help="Limit number of tasks to run")
    args = parser.parse_args()

    # Load dataset
    print("Loading SWE-bench Lite dataset...")
    dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
    pytest_tasks = [t for t in dataset if t["repo"] == "pytest-dev/pytest"]
    # Sort chronologically by instance_id
    pytest_tasks.sort(key=lambda t: t["instance_id"])
    pytest_tasks = pytest_tasks[:args.limit]
    print(f"Loaded {len(pytest_tasks)} pytest tasks for arm={args.arm}")

    # Set up custom evaluator
    evaluator = GoldPatchEvaluator()

    # Set up LearnKit memory if treatment arm
    memory = None
    if args.arm == "treatment":
        db_path = Path(__file__).parent / "learnkit_swebench_pytest.db"
        if db_path.exists():
            db_path.unlink()
        memory = lk.LearnKit(
            memory_backend="sqlite",
            db_path=str(db_path),
            scope="user",
            evaluator=evaluator,
            background_postprocess=False,  # sync distillation
        )

        @memory.agent(domain="pytest")
        def ask(task_prompt: str, file_context: str, file_path_obj: Path, rel_path_str: str, original_content_str: str, _learnkit_context: str = "") -> str:
            system = (
                "You are a senior Python software engineer. Your task is to fix a bug in a file.\n"
                "You are given the issue description, the path of the file, and the file's content.\n\n"
                "Propose the change using a Search-and-Replace block. Format:\n\n"
                "<<<<<<< ORIGINAL\n"
                "[lines of original code to replace]\n"
                "=======\n"
                "[lines of replacement code]\n"
                ">>>>>>> SUGGESTED\n\n"
                "Ensure the ORIGINAL block matches the file content exactly, including whitespace.\n"
                "Do not output the entire file. Output ONLY the search-and-replace block."
            )
            if _learnkit_context:
                system += f"\n\n{_learnkit_context}"
                
            response_text = call_agent(system, f"{task_prompt}\n\n{file_context}")
            new_content = apply_search_replace(original_content_str, response_text)
            
            # Write agent change
            file_path_obj.write_text(new_content, encoding="utf-8")
            
            # Generate diff using git
            agent_diff = run_git_cmd(["diff", rel_path_str])
            
            # Set diff on custom evaluator
            memory.evaluator.agent_patch = agent_diff
            
            return response_text
    else:
        def ask(task_prompt: str, file_context: str, file_path_obj: Path, rel_path_str: str, original_content_str: str) -> str:
            system = (
                "You are a senior Python software engineer. Your task is to fix a bug in a file.\n"
                "You are given the issue description, the path of the file, and the file's content.\n\n"
                "Propose the change using a Search-and-Replace block. Format:\n\n"
                "<<<<<<< ORIGINAL\n"
                "[lines of original code to replace]\n"
                "=======\n"
                "[lines of replacement code]\n"
                ">>>>>>> SUGGESTED\n\n"
                "Ensure the ORIGINAL block matches the file content exactly, including whitespace.\n"
                "Do not output the entire file. Output ONLY the search-and-replace block."
            )
            response_text = call_agent(system, f"{task_prompt}\n\n{file_context}")
            new_content = apply_search_replace(original_content_str, response_text)
            
            # Write agent change
            file_path_obj.write_text(new_content, encoding="utf-8")
            
            # Generate diff using git
            agent_diff = run_git_cmd(["diff", rel_path_str])
            
            return agent_diff

    predictions = []
    run_id = f"swebench_pytest_{args.arm}_{int(time.time())}"

    for i, task in enumerate(pytest_tasks, 1):
        instance_id = task["instance_id"]
        base_commit = task["base_commit"]
        problem = task["problem_statement"]
        gold_patch = task["patch"]
        
        rel_path = get_modified_file(gold_patch)
        if not rel_path:
            print(f"[{i:2d}/{len(pytest_tasks)}] Skipping {instance_id}: no modified file parsed from gold patch.")
            continue
            
        print(f"\n[{i:2d}/{len(pytest_tasks)}] Processing {instance_id}...")
        print(f"  File to modify: {rel_path}")
        print(f"  Checking out base commit: {base_commit[:8]}...")
        
        # Reset and checkout the repo at base commit
        run_git_cmd(["checkout", "-f", base_commit])
        run_git_cmd(["clean", "-fdx"])
        
        file_path = REPO_DIR / rel_path
        if not file_path.exists():
            print(f"  ERROR: File {rel_path} does not exist at base commit!")
            continue
            
        original_content = file_path.read_text(encoding="utf-8", errors="ignore")
        
        file_context = f"FILE: {rel_path}\nORIGINAL CONTENT:\n{original_content}"
        task_prompt = f"ISSUE:\n{problem}"
        
        # Call agent
        if args.arm == "treatment":
            # Set up inputs for custom evaluator
            evaluator.problem_statement = problem
            evaluator.rel_path = rel_path
            evaluator.gold_patch = gold_patch
            
            # Call wrapped agent function
            ask(task_prompt, file_context, file_path, rel_path, original_content)
            
            agent_diff = evaluator.agent_patch
            print(f"  LLM Judge Score: {memory.last_trajectory.quality_score if memory.last_trajectory else 0.0}/5.0")
        else:
            agent_diff = ask(task_prompt, file_context, file_path, rel_path, original_content)
            score = evaluate_patch_llm(problem, rel_path, agent_diff, gold_patch)
            print(f"  LLM Judge Score: {score}/5.0")

        # Record prediction
        predictions.append({
            "model_name_or_path": f"learnkit_{args.arm}",
            "instance_id": instance_id,
            "model_patch": agent_diff
        })
        
        # Reset the git repo
        run_git_cmd(["checkout", "-f", rel_path])

    if memory:
        memory.shutdown(wait=True)

    # Save predictions file
    out_file = Path(__file__).parent / f"predictions_{args.arm}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")
            
    print(f"\nCompleted run! Predictions saved to: {out_file}")

if __name__ == "__main__":
    main()
