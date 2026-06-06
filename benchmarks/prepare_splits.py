"""Deterministic train/eval split backfill for the clustered benchmark domains.

The Transfer benchmark family (BENCHMARK_SPEC.md §1.2) needs same-pattern,
disjoint-surface train/eval splits. This script assigns a stable ``split`` field
to every task in the three clustered domains so that:

  - every non-``mixed`` pattern appears in BOTH train and eval (disjoint tasks),
    enabling "learn on train, evaluate on holdout" without leakage;
  - ``mixed`` (heterogeneous) tasks are reserved entirely for eval as a
    harder holdout;
  - tasks already carrying ``split == "contamination"`` are left untouched.

The assignment is purely positional (first ~60% of each pattern's tasks in file
order -> train, remainder -> eval), so re-running is idempotent and the split is
reproducible from the committed task files alone.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

HERE = Path(__file__).parent
CLUSTERED_DOMAINS = ("sql_authoring", "python_debugging", "contract_summarization")
TRAIN_FRACTION = 0.6


def assign_splits(tasks: list[dict]) -> list[dict]:
    """Return tasks with a stable ``split`` field assigned in place."""
    # Group positional indices by pattern, preserving file order.
    by_pattern: dict[str, list[int]] = {}
    for i, t in enumerate(tasks):
        by_pattern.setdefault(t.get("pattern", "mixed"), []).append(i)

    for pattern, indices in by_pattern.items():
        if pattern == "mixed":
            for i in indices:
                if tasks[i].get("split") != "contamination":
                    tasks[i]["split"] = "eval"
            continue
        n_train = math.ceil(len(indices) * TRAIN_FRACTION)
        for rank, i in enumerate(indices):
            if tasks[i].get("split") == "contamination":
                continue
            tasks[i]["split"] = "train" if rank < n_train else "eval"
    return tasks


def main() -> None:
    for domain in CLUSTERED_DOMAINS:
        path = HERE / "tasks" / f"{domain}.jsonl"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        tasks = [json.loads(ln) for ln in lines]
        assign_splits(tasks)
        path.write_text(
            "\n".join(json.dumps(t, ensure_ascii=False) for t in tasks) + "\n",
            encoding="utf-8",
        )
        counts: dict[str, int] = {}
        for t in tasks:
            counts[t["split"]] = counts.get(t["split"], 0) + 1
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"{domain}: {len(tasks)} tasks -> {summary}")


if __name__ == "__main__":
    main()
