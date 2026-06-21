import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
raw = json.loads((run_dir / "raw.json").read_text(encoding="utf-8"))

ctrl = {}
for r in raw:
    if r["arm"] == "control":
        ctrl[(r["domain"], r["seed"], r["task_id"])] = r["score"]

help_n = hurt_n = neutral = injected = noctx = 0
hurt_cases = []
for r in raw:
    if r["arm"] != "treatment":
        continue
    c = ctrl.get((r["domain"], r["seed"], r["task_id"]))
    if c is None:
        continue
    if r["learnkit_context_chars"] > 0:
        injected += 1
        d = r["score"] - c
        if d > 0.001:
            help_n += 1
        elif d < -0.001:
            hurt_n += 1
            hurt_cases.append((r["domain"], r["task_id"], r["seed"], c, r["score"]))
        else:
            neutral += 1
    else:
        noctx += 1

total_t = sum(1 for r in raw if r["arm"] == "treatment")
print(f"Treatment tasks total: {total_t}")
print(f"  with context injected: {injected}   (no-context / retrieval-empty: {noctx})")
print(f"  Of injected -> HELPED: {help_n}   HURT: {hurt_n}   NEUTRAL(same): {neutral}")
if injected:
    print(f"  harmful_retrieval_rate (hurt / injected): {hurt_n / injected:.3f}")
    print(f"  help_rate (helped / injected): {help_n / injected:.3f}")
print()
print("HURT cases (domain, task, seed, control -> treatment):")
for hc in hurt_cases:
    print("  ", hc)
