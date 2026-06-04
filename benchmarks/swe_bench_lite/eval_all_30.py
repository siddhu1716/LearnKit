import json
from pathlib import Path
from datasets import load_dataset
import litellm

AGENT_MODEL = "openai/qwen-72b-instruct"
# Setup api base to match local server
litellm.api_base = "http://localhost:8001/v1"

def evaluate_patch_llm(problem: str, rel_path: str, agent_patch: str, gold_patch: str) -> float:
    """Score the agent patch against the gold patch using local Qwen as judge."""
    system = (
        "You are an expert code reviewer. Compare the agent's proposed patch with the gold patch. "
        "Give a score 1.0–5.0: 5.0 = semantically equivalent and correct, 1.0 = completely wrong. "
        "Reply with a single number only."
    )
    user = (
        f"ISSUE:\n{problem}\n\n"
        f"FILE: {rel_path}\n\n"
        f"GOLD PATCH:\n{gold_patch}\n\n"
        f"AGENT PATCH:\n{agent_patch if agent_patch else '(empty — no change made)'}\n\n"
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
        val = r.choices[0].message.content.strip()
        # Parse first float/int found in response
        import re
        m = re.search(r"\d+(\.\d+)?", val)
        if m:
            return float(m.group(0))
        return 1.0
    except Exception as e:
        print(f"  Error calling judge: {e}")
        return 1.0

def main():
    print("Loading SWE-bench Lite dataset...")
    dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
    pytest_tasks = {t["instance_id"]: t for t in dataset if t["repo"] == "pytest-dev/pytest"}

    pred_path = Path("benchmarks/swe_bench_lite/predictions_treatment.jsonl")
    if not pred_path.exists():
        print(f"Error: {pred_path} does not exist.")
        return

    print("Reading predictions...")
    predictions = []
    with open(pred_path, "r") as f:
        for line in f:
            if line.strip():
                predictions.append(json.loads(line.strip()))

    print(f"Found {len(predictions)} predictions. Starting evaluation...")
    scores = []
    
    # We ran 3 tasks repeated 10 times:
    # pytest-7432, pytest-7490, pytest-8906
    for idx, pred in enumerate(predictions):
        inst_id = pred["instance_id"]
        patch = pred["model_patch"]
        task_data = pytest_tasks[inst_id]
        
        # Get patch info
        gold_patch = task_data["patch"]
        # Find target file
        import re
        m = re.findall(r"a/(\S+)", gold_patch)
        rel_path = m[0] if m else "unknown"
        
        score = evaluate_patch_llm(task_data["problem_statement"], rel_path, patch, gold_patch)
        scores.append(score)
        print(f"Task {idx+1:2d} ({inst_id}): judge score = {score}/5.0")

    # Group scores by iteration (groups of 3)
    print("\n=== Continuous Evolution Summary ===")
    print("| Iteration | pytest-7432 | pytest-7490 | pytest-8906 | Average Score |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    for i in range(10):
        it_scores = scores[i*3:(i+1)*3]
        avg = sum(it_scores) / len(it_scores) if it_scores else 0.0
        print(f"| Iteration {i+1:2d} | {it_scores[0]:.1f}/5.0 | {it_scores[1]:.1f}/5.0 | {it_scores[2]:.1f}/5.0 | **{avg:.3f}/5.0** |")

if __name__ == "__main__":
    main()
