from datasets import load_dataset

dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
pytest_tasks = [t for t in dataset if t["repo"] == "pytest-dev/pytest"]
task = pytest_tasks[0]

print(f"Instance ID: {task['instance_id']}")
print(f"Base Commit: {task['base_commit']}")
print("\n--- GOLD PATCH ---")
print(task["patch"])
print("\n--- GOLD TEST PATCH ---")
print(task["test_patch"])
