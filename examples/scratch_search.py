# examples/scratch_search.py
import learnkit as lk

# 1. Initialize
backend = lk.SQLiteBackend(db_path=":memory:")

# 2. Add records
skill = lk.SkillRecord(
    domains={"coding": 0.9},
    task_type="python_multiprocessing",
    content={
        "steps": [
            "Verify OS architecture context (macOS defaults to spawn)",
            "Wrap code block in 'if __name__ == \"__main__\"' gate",
            "Construct pool explicitly using 'spawn' start method"
        ]
    },
    confidence=0.9,
    status="active"
)
backend.add(skill)

failure = lk.FailureRecord(
    domains={"coding": 0.9},
    content={
        "description": "Multiprocessing deadlocks caused by 'fork' state sharing",
        "what_to_avoid": "Do not call mp.set_start_method('fork') on macOS/Windows"
    },
    status="active"
)
backend.add(failure)

# Test search
q = "Fix macOS multiprocessing issues"
res = backend.search(q, domain=None, scope="team")
print(f"Results with domain=None, scope=team: {len(res)}")
for r in res:
    print(f"  [{r.type}] {r.task_type or r.content.get('description', '')}")

res_coding = backend.search(q, domain="coding", scope="team")
print(f"Results with domain=coding, scope=team: {len(res_coding)}")
