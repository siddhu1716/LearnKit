"""Lightweight observability helpers: model pricing, token estimation, and
cost calculation for run telemetry.

LearnKit calls LLMs through DSPy, which does not surface per-call token usage in
a stable way. Rather than couple to DSPy internals, we measure what we can
directly (wall-clock latency, context size) and produce *honest estimates* for
LLM token counts and cost from the text we control. Estimated values are flagged
so the dashboard can label them as approximations.
"""

from __future__ import annotations

import os
from typing import Optional

# Characters per token — matches the budgeting constant used by the compressor.
CHARS_PER_TOKEN = 4

# Approximate public list prices in USD per 1,000,000 tokens, as (input, output).
# Keys are matched as substrings against the normalized model name, longest
# match first, so "claude-haiku-4-5" beats a generic "claude" fallback.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-haiku": (1.00, 5.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-sonnet": (3.00, 15.00),
    "claude-opus": (15.00, 75.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "o4-mini": (1.10, 4.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini": (0.30, 2.50),
    "qwen": (0.20, 0.60),
}

_DEFAULT_PRICE = (1.00, 5.00)
_DEFAULT_MODEL = "anthropic/claude-haiku-4-5-20251001"


def normalize_model(model: Optional[str]) -> str:
    """Strip provider prefix and lowercase, e.g. ``anthropic/Claude-Haiku`` ->
    ``claude-haiku``."""
    if not model:
        return ""
    name = model.split("/", 1)[-1]
    return name.strip().lower()


def model_pricing(model: Optional[str]) -> tuple[float, float]:
    """Return (input_price, output_price) per 1M tokens for a model name."""
    name = normalize_model(model)
    best: Optional[tuple[int, tuple[float, float]]] = None
    for key, price in MODEL_PRICING.items():
        if key in name:
            if best is None or len(key) > best[0]:
                best = (len(key), price)
    return best[1] if best else _DEFAULT_PRICE


def estimate_tokens(text: Optional[str]) -> int:
    """Rough token count from character length (~4 chars/token)."""
    if not text:
        return 0
    return max(0, round(len(text) / CHARS_PER_TOKEN))


def estimate_cost(model: Optional[str], prompt_tokens: int, completion_tokens: int) -> float:
    """USD cost for a single model call given token counts."""
    in_price, out_price = model_pricing(model)
    cost = (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price
    return round(cost, 6)


def resolve_models() -> dict[str, str]:
    """Resolve the effective model names used for each LLM stage from env
    overrides, falling back to the package defaults."""
    classifier = os.environ.get("LEARNKIT_CLASSIFIER_MODEL") or _DEFAULT_MODEL
    evaluator = os.environ.get("LEARNKIT_EVALUATOR_MODEL") or _DEFAULT_MODEL
    distiller = os.environ.get("LEARNKIT_DISTILLER_MODEL") or _DEFAULT_MODEL
    return {"classifier": classifier, "evaluator": evaluator, "distiller": distiller}


def estimate_run_telemetry(
    *,
    task_chars: int,
    context_chars: int,
    response_chars: int,
    trajectory_chars: int,
    models: dict[str, str],
    replayed: bool,
    succeeded: bool,
) -> dict:
    """Produce an estimated token/cost breakdown for one learning run.

    A run triggers a few LLM stages: classification (always), LLM-judge
    evaluation (always), and distillation (only on a fresh successful run, since
    replays reuse an existing procedure). We size each stage's prompt/completion
    from the text we already have, price them per-model, and sum.
    """
    task_t = estimate_tokens_from_chars(task_chars)
    context_t = estimate_tokens_from_chars(context_chars)
    response_t = estimate_tokens_from_chars(response_chars)
    traj_t = estimate_tokens_from_chars(trajectory_chars)

    stages: list[dict] = []

    # Classification: reads the task, emits a small structured label.
    stages.append(
        {
            "stage": "classify",
            "model": models.get("classifier"),
            "prompt_tokens": task_t + 220,
            "completion_tokens": 60,
        }
    )

    # LLM-judge evaluation: reads task + injected context + the agent response.
    stages.append(
        {
            "stage": "evaluate",
            "model": models.get("evaluator"),
            "prompt_tokens": task_t + context_t + response_t + 160,
            "completion_tokens": 130,
        }
    )

    # Distillation: only on a fresh successful run (replays skip it).
    if succeeded and not replayed:
        stages.append(
            {
                "stage": "distill",
                "model": models.get("distiller"),
                "prompt_tokens": traj_t + 300,
                "completion_tokens": 220,
            }
        )

    prompt_tokens = sum(s["prompt_tokens"] for s in stages)
    completion_tokens = sum(s["completion_tokens"] for s in stages)
    cost = sum(
        estimate_cost(s["model"], s["prompt_tokens"], s["completion_tokens"]) for s in stages
    )

    return {
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(prompt_tokens + completion_tokens),
        "context_tokens": int(context_t),
        "cost_usd": round(cost, 6),
        "stages": stages,
        "estimated": True,
    }


def estimate_tokens_from_chars(chars: int) -> int:
    if not chars or chars < 0:
        return 0
    return round(chars / CHARS_PER_TOKEN)
