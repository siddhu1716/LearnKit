from datasets import load_dataset

print("Loading SWE-bench Lite dataset (test split)...")
try:
    dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
    print(f"Loaded {len(dataset)} test tasks.")
except Exception as e:
    print(f"Failed to load test split: {e}")
    print("Loading train split...")
    dataset = load_dataset("swe-bench/SWE-bench_Lite", split="train")
    print(f"Loaded {len(dataset)} train tasks.")

# Group tasks by repository
repos = {}
for task in dataset:
    repo = task["repo"]
    repos[repo] = repos.get(repo, 0) + 1

print("\nTask counts per repository:")
for repo, count in sorted(repos.items(), key=lambda x: x[1], reverse=True):
    print(f"  {repo}: {count} tasks")

# Show details of first 3 pytest tasks
pytest_tasks = [t for t in dataset if t["repo"] == "pytest-dev/pytest"]
print(f"\nTotal pytest tasks: {len(pytest_tasks)}")
print("\nSample pytest task details:")
for i, t in enumerate(pytest_tasks[:3]):
    print(f"\n--- Task {i+1} ---")
    print(f"ID: {t['instance_id']}")
    print(f"Base Commit: {t['base_commit']}")
    print(f"Problem Statement:\n{t['problem_statement'][:300]}...")
