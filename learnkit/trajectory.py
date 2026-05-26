"""
Task 1.2 — Trajectory capture.

Inspired by Hermes Agent agent/trajectory.py — JSONL format.
CoT reasoning field is MANDATORY per ReaComp findings (removing it
collapses distillation quality by ~50 percentage points).
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TrajectoryStep:
    step: int
    role: str  # "user" | "assistant" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    reasoning: Optional[str] = None  # CoT trace — CRITICAL per ReaComp
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


@dataclass
class Trajectory:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    domain_hint: Optional[str] = None
    steps: list = field(default_factory=list)
    outcome: Optional[str] = None  # "success" | "failure" | "partial"
    quality_score: Optional[float] = None  # 0–5, set by Evaluator
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def add_step(self, role: str, content: str, **kwargs) -> None:
        self.steps.append(
            TrajectoryStep(
                step=len(self.steps) + 1,
                role=role,
                content=content,
                **kwargs,
            )
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for step in self.steps:
                f.write(json.dumps(asdict(step)) + "\n")
            f.write(
                json.dumps(
                    {
                        "id": self.id,
                        "task": self.task,
                        "outcome": self.outcome,
                        "quality_score": self.quality_score,
                        "created_at": self.created_at,
                    }
                )
                + "\n"
            )

    @classmethod
    def load(cls, path: Path) -> "Trajectory":
        lines = path.read_text().strip().split("\n")
        meta = json.loads(lines[-1])
        steps = [TrajectoryStep(**json.loads(line)) for line in lines[:-1]]
        t = cls(id=meta["id"], task=meta["task"])
        t.steps = steps
        t.outcome = meta.get("outcome")
        t.quality_score = meta.get("quality_score")
        t.created_at = meta.get("created_at", t.created_at)
        return t
