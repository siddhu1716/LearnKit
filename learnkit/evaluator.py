"""Task H6 — Harden Evaluator.

Bounded prompt inputs, JSON parse schema repair, and signal metadata inclusion.
"""

import os
import re
import json
import dspy
from enum import Enum
from typing import Optional, Any

from .logging import get_logger

logger = get_logger("evaluator")

class EvaluationSignal(str, Enum):
    USER_FEEDBACK = "user_feedback"
    LLM_JUDGE = "llm_judge"
    NLI_CONSISTENCY = "nli_consistency"

class EvaluationResult:
    def __init__(self, score: float, signal: EvaluationSignal, reasoning: str, metadata: Optional[dict[str, Any]] = None):
        self.score = max(0.0, min(5.0, score))  # Clamp to [0.0, 5.0]
        self.signal = signal
        self.reasoning = reasoning
        self.passes_threshold = self.score >= 3.5  # default threshold
        self.metadata = metadata or {}

def truncate(text: Optional[str], max_len: int = 1500) -> str:
    """Truncate input safely to prevent context overflow or massive API costs."""
    if not text:
        return ""
    if len(text) > max_len:
        return text[:max_len] + "\n[... truncated for prompt bounds ...]"
    return text

class Evaluator:
    """
    Quality gate before any record enters the memory store.
    
    Priority order (most reliable first):
    1. USER_FEEDBACK — explicit thumbs up/down or rating
    2. LLM_JUDGE — separate model reads task + response, scores 0-5
    3. NLI_CONSISTENCY — factual consistency check
    
    Failure records skip this gate entirely.
    """

    QUALITY_THRESHOLD = 3.5

    def evaluate_with_llm_judge(
        self,
        task: str,
        response: str,
        reasoning_trace: Optional[str] = None,
        lm=None
    ) -> EvaluationResult:
        """
        LLM-as-judge evaluation with input bounds, robust parsing, and metadata.
        """
        if lm is None:
            model_name = os.environ.get("LEARNKIT_EVALUATOR_MODEL", "anthropic/claude-haiku-4-5-20251001")
            try:
                lm = dspy.LM(model_name)
            except Exception as e:
                logger.warning(
                    "Failed to initialize evaluator model, using fallback score",
                    extra={"event": "evaluator_init_fail", "model_name": model_name, "error": str(e)}
                )
                return EvaluationResult(
                    score=2.0,
                    signal=EvaluationSignal.LLM_JUDGE,
                    reasoning="Failed to initialize judge model",
                    metadata={"error": str(e)}
                )
        elif isinstance(lm, str):
            try:
                lm = dspy.LM(lm)
            except Exception as e:
                logger.warning(
                    "Failed to initialize evaluator model string, using fallback score",
                    extra={"event": "evaluator_init_fail", "model_name": lm, "error": str(e)}
                )
                return EvaluationResult(
                    score=2.0,
                    signal=EvaluationSignal.LLM_JUDGE,
                    reasoning="Failed to initialize judge model string",
                    metadata={"error": str(e)}
                )

        # Enforce prompt input bounds
        bounded_task = truncate(task, max_len=1000)
        bounded_response = truncate(response, max_len=2000)
        bounded_reasoning = truncate(reasoning_trace, max_len=1000)

        judge_prompt = f"""
You are evaluating an AI agent's response quality. Score from 0-5.

TASK: {bounded_task}

RESPONSE: {bounded_response}

{f"AGENT REASONING: {bounded_reasoning}" if bounded_reasoning else ""}

Score 0-5 where:
5 = Excellent: accurate, complete, well-structured, no hallucinations
4 = Good: accurate, mostly complete, minor gaps
3 = Acceptable: basically correct, some important omissions
2 = Poor: significant errors or omissions
1 = Bad: mostly wrong or misleading
0 = Harmful: incorrect information presented as fact

Respond with JSON only: {{"score": <number>, "reasoning": "<one sentence>"}}
"""
        try:
            with dspy.context(lm=lm):
                response_text = lm(judge_prompt)[0]
        except Exception as e:
            logger.warning(
                "Judge model call failed, using fallback score",
                extra={"event": "eval_model_call_fail", "error_type": type(e).__name__, "error": str(e)}
            )
            return EvaluationResult(
                score=2.0,
                signal=EvaluationSignal.LLM_JUDGE,
                reasoning="Judge model call failed",
                metadata={"error": str(e)}
            )

        # Robust parsing & schema repair
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```json") or lines[0] == "```":
                cleaned = "\n".join(lines[1:-1])
        cleaned = cleaned.strip()

        data = {}
        parse_method = "json"
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                # Try single quotes replacement
                data = json.loads(cleaned.replace("'", '"'))
                parse_method = "json_replace_quotes"
            except json.JSONDecodeError:
                # Attempt regex recovery
                score_match = re.search(r'"score"\s*:\s*([\d\.]+)', cleaned)
                reason_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', cleaned)
                if score_match:
                    score_val = float(score_match.group(1))
                    reason_val = reason_match.group(1) if reason_match else "Extracted via regex pattern matching"
                    data = {"score": score_val, "reasoning": reason_val}
                    parse_method = "regex_recovery"
                else:
                    logger.warning(
                        "Judge response was completely unparseable",
                        extra={"event": "eval_unparseable", "raw_response": response_text}
                    )
                    return EvaluationResult(
                        score=2.0,
                        signal=EvaluationSignal.LLM_JUDGE,
                        reasoning="Judge response unparseable — conservative score applied",
                        metadata={"raw_response": response_text, "parse_failed": True}
                    )

        score = float(data.get("score", 2.0))
        reasoning = data.get("reasoning", "Faceted judgment completed")
        metadata = {
            "parse_method": parse_method,
            "raw_response": response_text,
            "task_len": len(task),
            "response_len": len(response),
            "reasoning_len": len(reasoning_trace) if reasoning_trace else 0
        }
        return EvaluationResult(
            score=score,
            signal=EvaluationSignal.LLM_JUDGE,
            reasoning=reasoning,
            metadata=metadata
        )

    def evaluate_from_user_feedback(self, rating: int) -> EvaluationResult:
        """Direct user feedback (1-5 stars)."""
        return EvaluationResult(
            score=float(rating),
            signal=EvaluationSignal.USER_FEEDBACK,
            reasoning=f"Direct user rating: {rating}/5",
            metadata={"user_rating": rating}
        )
