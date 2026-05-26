"""Task H5 — Harden Classifier & LLM Retries.

Configurable models, DSPy retries/backoff, schema-validated clamping, and deterministic fallback.
"""

import os
import json
import time
import dspy
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from .logging import get_logger

logger = get_logger("classifier")

class ClassificationOutput(BaseModel):
    task_type: str = Field(..., description="The type of the task")
    domains: dict[str, float] = Field(default_factory=dict, description="Multi-label domains and their confidence scores")
    complexity: str = Field("medium", description="The complexity level: low, medium, or high")

    @field_validator("domains", mode="after")
    @classmethod
    def clamp_domains(cls, v: dict[str, float]) -> dict[str, float]:
        """Clamp all domain scores to [0.0, 1.0]."""
        return {domain: max(0.0, min(1.0, score)) for domain, score in v.items()}

class TaskClassificationSignature(dspy.Signature):
    """Classify the user's task into domain, task_type and complexity."""
    task = dspy.InputField(desc="The user's task description")
    classification: ClassificationOutput = dspy.OutputField(
        desc="Classified task information"
    )

class TaskClassifier(dspy.Module):
    """
    Multi-label domain classifier.
    DSPy Predict with typed output — single cheap LLM call per task.
    """

    def __init__(self):
        super().__init__()
        self.classify = dspy.Predict(TaskClassificationSignature)

    def forward(self, task: str) -> ClassificationOutput:
        try:
            result = self.classify(task=task)
            
            # Extract raw output
            raw = getattr(result, "classification", result)

            if isinstance(raw, ClassificationOutput):
                return raw
            elif isinstance(raw, dict):
                return ClassificationOutput(**raw)
            elif isinstance(raw, str):
                cleaned = raw.strip()
                # Remove markdown json code blocks
                if cleaned.startswith("```"):
                    lines = cleaned.splitlines()
                    if lines[0].startswith("```json") or lines[0] == "```":
                        cleaned = "\n".join(lines[1:-1])
                try:
                    data = json.loads(cleaned)
                except json.JSONDecodeError:
                    # Simple recovery replacement
                    data = json.loads(cleaned.replace("'", '"'))
                return ClassificationOutput(**data)
            
            return ClassificationOutput.model_validate(raw)
        except Exception as e:
            logger.warning(
                "Classification parsing failed, using fallback",
                extra={"event": "classification_parse_fail", "error_type": type(e).__name__, "error": str(e)}
            )
            return FALLBACK_CLASSIFICATION

# Deterministic safe fallback
FALLBACK_CLASSIFICATION = ClassificationOutput(
    task_type="general",
    domains={"general": 1.0},
    complexity="medium"
)

def classify_task(task: str, lm=None, retries: int = 3, backoff_factor: float = 1.5) -> ClassificationOutput:
    """Classify task with model config, exponential backoff retries, and fallback."""
    if lm is None:
        model_name = os.environ.get("LEARNKIT_CLASSIFIER_MODEL", "anthropic/claude-haiku-4-5-20251001")
        try:
            lm = dspy.LM(model_name)
        except Exception as e:
            logger.warning(
                "Failed to initialize default classifier model, using fallback",
                extra={"event": "classifier_init_fail", "model_name": model_name, "error": str(e)}
            )
            return FALLBACK_CLASSIFICATION
    elif isinstance(lm, str):
        try:
            lm = dspy.LM(lm)
        except Exception as e:
            logger.warning(
                "Failed to initialize classifier model, using fallback",
                extra={"event": "classifier_init_fail", "model_name": lm, "error": str(e)}
            )
            return FALLBACK_CLASSIFICATION

    delay = 1.0
    for attempt in range(retries):
        try:
            with dspy.context(lm=lm):
                classifier = TaskClassifier()
                return classifier(task=task)
        except Exception as e:
            logger.warning(
                f"Classification model call failed (attempt {attempt + 1}/{retries})",
                extra={
                    "event": "classification_attempt_fail",
                    "attempt": attempt + 1,
                    "error_type": type(e).__name__,
                    "error": str(e),
                }
            )
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.warning(
                    "All classification retries failed, returning general fallback",
                    extra={"event": "classification_all_retries_failed", "error_type": type(e).__name__}
                )
                return FALLBACK_CLASSIFICATION
