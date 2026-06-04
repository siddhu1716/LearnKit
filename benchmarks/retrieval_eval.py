"""LearnKit retrieval-quality benchmark.

This isolates memory quality from agent-generation quality. It asks:

    Given a task and a memory store, did LearnKit retrieve the right memory?

Run:
    python benchmarks/retrieval_eval.py
    python benchmarks/retrieval_eval.py --json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import learnkit as lk
from learnkit.classifier import ClassificationOutput
from learnkit.evaluator import EvaluationResult, EvaluationSignal
from learnkit.schemas.skill import SkillRecord


@dataclass(frozen=True)
class RetrievalCase:
    name: str
    task: str
    expected_task_type: str
    expected_type: str = "skill"
    wrong_task_type: str | None = None


class NoopDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, trajectory, domain_vector, quality_score):
        return None


class NoopEvaluator:
    def evaluate_with_llm_judge(self, task, response, reasoning_trace=None, lm=None):
        return EvaluationResult(4.0, EvaluationSignal.USER_FEEDBACK, "noop")


def classifier(task: str) -> ClassificationOutput:
    lower = task.lower()
    if "prolog" in lower or "eastbound" in lower or "train" in lower:
        return ClassificationOutput(
            task_type="symbolic_logic_reasoning",
            domains={"coding": 1.0},
            complexity="medium",
        )
    if "replace" in lower or "input/output" in lower or "string" in lower:
        return ClassificationOutput(
            task_type="pbe_string_transformation",
            domains={"coding": 1.0},
            complexity="medium",
        )
    if "sql" in lower or "upsert" in lower or "gap" in lower:
        return ClassificationOutput(
            task_type="sql_authoring",
            domains={"coding": 1.0},
            complexity="medium",
        )
    return ClassificationOutput(
        task_type="debug_python_error",
        domains={"coding": 1.0},
        complexity="medium",
    )


def build_memory() -> lk.LearnKit:
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=":memory:",
        scope="team",
        classifier=classifier,
        evaluator=NoopEvaluator(),
        distiller=NoopDistiller(),
        background_postprocess=False,
    )
    lk.seed_bundled_skills(memory.backend)

    memory.backend.add(
        SkillRecord(
            domains={"coding": 0.95},
            task_type="sql_gap_detection",
            content={
                "steps": [
                    "For gap detection, generate the expected sequence or time buckets first",
                    "Left join observed rows onto the expected sequence",
                    "Filter where the observed row is missing",
                ],
                "tools_used": ["sql"],
                "constraints": ["Do not use upsert or conflict-handling patterns"],
                "failure_modes": ["Confusing gap detection with upsert conflict resolution"],
            },
            confidence=0.9,
            status="active",
        )
    )
    memory.backend.add(
        SkillRecord(
            domains={"coding": 0.95},
            task_type="sql_upsert_on_conflict",
            content={
                "steps": [
                    "Use INSERT ... ON CONFLICT to update existing rows",
                    "Specify the conflict target and update assignment list",
                ],
                "tools_used": ["sql"],
                "constraints": ["Only apply when the task is about inserting or updating"],
                "failure_modes": ["Do not apply to gap-detection tasks"],
            },
            confidence=0.72,
            status="active",
        )
    )
    return memory


CASES = [
    RetrievalCase(
        name="pbe_overlapping_replace",
        task=(
            "Solve a programming-by-example string transformation. Inputs and outputs "
            "require overlapping str.replace operations; choose the minimal encompassing "
            "replace instead of broad replacements."
        ),
        expected_task_type="pbe_string_transformation",
    ),
    RetrievalCase(
        name="slr_train_rule",
        task=(
            "Induce a Prolog eastbound(T) rule for train examples. Use has_car, "
            "car_color, car_len, and has_wall facts to separate eastbound and westbound trains."
        ),
        expected_task_type="symbolic_logic_reasoning",
    ),
    RetrievalCase(
        name="python_traceback_debug",
        task=(
            "Debug a Python traceback where multiprocessing fails on macOS. Reproduce "
            "the error, identify the root cause, and propose a minimal pytest regression test."
        ),
        expected_task_type="debug_python_error",
    ),
    RetrievalCase(
        name="sql_gap_not_upsert",
        task=(
            "Write SQL to find missing hourly login streak rows. This is a gap detection "
            "query over expected timestamps, not an INSERT ON CONFLICT upsert."
        ),
        expected_task_type="sql_gap_detection",
        wrong_task_type="sql_upsert_on_conflict",
    ),
]


def evaluate_case(memory: lk.LearnKit, case: RetrievalCase) -> dict:
    inspected = memory.inspect(case.task)
    records = inspected["records"]
    retrieved = [
        {
            "rank": idx + 1,
            "id": record["id"],
            "type": record["type"],
            "task_type": record["task_type"],
            "confidence": record["confidence"],
        }
        for idx, record in enumerate(records)
    ]
    top = retrieved[0] if retrieved else None
    expected_ranks = [
        item["rank"]
        for item in retrieved
        if item["type"] == case.expected_type
        and item["task_type"] == case.expected_task_type
    ]
    wrong_primary = bool(
        case.wrong_task_type and top and top["task_type"] == case.wrong_task_type
    )
    return {
        "name": case.name,
        "expected_task_type": case.expected_task_type,
        "top_task_type": top["task_type"] if top else None,
        "top_type": top["type"] if top else None,
        "hit_at_1": bool(expected_ranks and expected_ranks[0] == 1),
        "hit_at_3": bool(expected_ranks and expected_ranks[0] <= 3),
        "expected_rank": expected_ranks[0] if expected_ranks else None,
        "wrong_primary": wrong_primary,
        "context_chars": inspected["context_chars"],
        "retrieved": retrieved,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    memory = build_memory()
    rows = [evaluate_case(memory, case) for case in CASES]
    summary = {
        "cases": len(rows),
        "recall_at_1": sum(row["hit_at_1"] for row in rows) / len(rows),
        "recall_at_3": sum(row["hit_at_3"] for row in rows) / len(rows),
        "wrong_primary_rate": sum(row["wrong_primary"] for row in rows) / len(rows),
    }
    payload = {"summary": summary, "rows": rows}

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("LearnKit RetrievalEval")
    print("=====================")
    print(
        f"Recall@1={summary['recall_at_1']:.2%}  "
        f"Recall@3={summary['recall_at_3']:.2%}  "
        f"WrongPrimary={summary['wrong_primary_rate']:.2%}"
    )
    print()
    print("| Case | Expected | Top | Hit@1 | Hit@3 | Wrong Primary |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        print(
            f"| {row['name']} | {row['expected_task_type']} | "
            f"{row['top_task_type']} | {row['hit_at_1']} | "
            f"{row['hit_at_3']} | {row['wrong_primary']} |"
        )
    memory.shutdown()


if __name__ == "__main__":
    main()

