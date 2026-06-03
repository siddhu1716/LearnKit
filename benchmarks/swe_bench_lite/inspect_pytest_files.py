from datasets import load_dataset
dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
pytest_tasks = [t for t in dataset if t["repo"] == "pytest-dev/pytest"]
for t in pytest_tasks:
    files = []
    for line in t["patch"].splitlines():
        if line.startswith("--- a/"):
            files.append(line[6:])
    print(f"{t['instance_id']}: {len(files)} files modified: {files}")
