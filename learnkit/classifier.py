"""Task H5 — Harden Classifier & LLM Retries.

Configurable models, DSPy retries/backoff, schema-validated clamping, and deterministic fallback.
"""

import json
import os
import time

import dspy
from pydantic import BaseModel, Field, field_validator

from .logging import get_logger

logger = get_logger("classifier")


class ClassificationOutput(BaseModel):
    task_type: str = Field(..., description="The type of the task")
    domains: dict[str, float] = Field(
        default_factory=dict,
        description="Multi-label domains and their confidence scores",
    )
    complexity: str = Field(
        "medium", description="The complexity level: low, medium, or high"
    )

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
                extra={
                    "event": "classification_parse_fail",
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            return FALLBACK_CLASSIFICATION


# Deterministic safe fallback
FALLBACK_CLASSIFICATION = ClassificationOutput(
    task_type="general", domains={"general": 1.0}, complexity="medium"
)


# Provider keys litellm/dspy can use. If none is set (and no explicit model
# override), there is no LLM to call, so the classifier runs fully offline.
_PROVIDER_KEYS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "TOGETHERAI_API_KEY",
    "COHERE_API_KEY",
)


def is_offline() -> bool:
    """True when no LLM is reachable, so the classifier must stay deterministic.

    Forced on by ``LEARNKIT_OFFLINE`` (any truthy value). Otherwise inferred:
    offline when neither an explicit ``LEARNKIT_CLASSIFIER_MODEL`` override nor
    any known provider key is configured. This keeps the agent path and the
    deterministic benchmarks fast and keyless instead of burning retries on
    network calls that can only fail.
    """
    flag = os.environ.get("LEARNKIT_OFFLINE", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    if os.environ.get("LEARNKIT_CLASSIFIER_MODEL"):
        return False
    return not any(os.environ.get(k) for k in _PROVIDER_KEYS)


# Keyword → domain map for the offline heuristic. First match wins per group;
# multiple groups can fire (multi-label). Deliberately small and transparent —
# good enough to route memory by domain without an LLM.
_HEURISTIC_DOMAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("coding", ("debug", "traceback", "exception", "stack trace", "bug", "fix the",
                "refactor", "compile", "function", "class ", "import ", "syntax")),
    ("sql", ("sql", "select ", "join", "query the", "database", "schema", "table")),
    ("data_analysis", ("dataframe", "csv", "aggregate", "pivot", "plot", "chart",
                        "statistics", "mean", "median", "correlation")),
    ("writing", ("summarize", "summary", "rewrite", "draft", "email", "essay",
                 "paragraph", "contract", "clause")),
    ("math", ("calculate", "equation", "integral", "derivative", "probability",
              "theorem", "prove ")),
    ("research", ("search", "find information", "look up", "compare", "research",
                  "investigate")),
)


def heuristic_classify(task: str) -> ClassificationOutput:
    """Deterministic, LLM-free classification used in offline mode.

    Lower-cases the task and scans the keyword map. Matched groups become
    multi-label domains; complexity is a crude length heuristic. Falls back to
    ``general`` when nothing matches, so it never returns an empty label set.
    """
    text = (task or "").lower()
    domains: dict[str, float] = {}
    for domain, keywords in _HEURISTIC_DOMAINS:
        hits = sum(1 for kw in keywords if kw in text)
        if hits:
            # Confidence grows with the number of distinct signals, capped at 1.
            domains[domain] = min(1.0, 0.5 + 0.15 * hits)
    if not domains:
        return FALLBACK_CLASSIFICATION

    primary = max(domains, key=domains.get)
    n_words = len(text.split())
    complexity = "low" if n_words < 12 else "high" if n_words > 40 else "medium"
    return ClassificationOutput(
        task_type=primary, domains=domains, complexity=complexity
    )


def classify_task(
    task: str, lm=None, retries: int = 3, backoff_factor: float = 1.5
) -> ClassificationOutput:
    """Classify task with model config, exponential backoff retries, and fallback."""
    if lm is None:
        # No LLM reachable → stay deterministic instead of retrying dead calls.
        if is_offline():
            return heuristic_classify(task)
        model_name = os.environ.get("LEARNKIT_CLASSIFIER_MODEL")
        if not model_name:
            if os.environ.get("ANTHROPIC_API_KEY"):
                model_name = "anthropic/claude-haiku-4-5-20251001"
            elif os.environ.get("GEMINI_API_KEY"):
                model_name = "gemini/gemini-2.5-flash"
            else:
                model_name = "anthropic/claude-haiku-4-5-20251001"
        try:
            lm = dspy.LM(model_name)
        except Exception as e:
            logger.warning(
                "Failed to initialize default classifier model, using fallback",
                extra={
                    "event": "classifier_init_fail",
                    "model_name": model_name,
                    "error": str(e),
                },
            )
            return FALLBACK_CLASSIFICATION
    elif isinstance(lm, str):
        try:
            lm = dspy.LM(lm)
        except Exception as e:
            logger.warning(
                "Failed to initialize classifier model, using fallback",
                extra={
                    "event": "classifier_init_fail",
                    "model_name": lm,
                    "error": str(e),
                },
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
                },
            )
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= backoff_factor
            else:
                logger.warning(
                    "All classification retries failed, returning general fallback",
                    extra={
                        "event": "classification_all_retries_failed",
                        "error_type": type(e).__name__,
                    },
                )
                return FALLBACK_CLASSIFICATION
