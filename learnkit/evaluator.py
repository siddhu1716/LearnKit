from enum import Enum
from typing import Optional
import dspy
import json

class EvaluationSignal(Enum):
    USER_FEEDBACK = "user_feedback"
    LLM_JUDGE = "llm_judge"
    NLI_CONSISTENCY = "nli_consistency"

class EvaluationResult:
    def __init__(self, score: float, signal: EvaluationSignal, reasoning: str):
        self.score = score                    # 0.0 – 5.0
        self.signal = signal
        self.reasoning = reasoning
        self.passes_threshold = score >= 3.5  # default threshold

class Evaluator:
    """
    Quality gate before any record enters the memory store.
    
    Priority order (most reliable first):
    1. USER_FEEDBACK — explicit thumbs up/down or rating
    2. LLM_JUDGE — separate model reads task + response, scores 0-5
    3. NLI_CONSISTENCY — factual consistency check (cheapest, least reliable)
    
    Failure records skip this gate entirely (they already failed — store immediately).
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
        LLM-as-judge evaluation. Separate model from the one that ran the task.
        ReaComp equivalent: reward signal for whether solver succeeded.
        """
        if lm is None:
            lm = dspy.LM("anthropic/claude-3-5-haiku-20241022")

        judge_prompt = f"""
You are evaluating an AI agent's response quality. Score from 0-5.

TASK: {task}

RESPONSE: {response}

{f"AGENT REASONING: {reasoning_trace}" if reasoning_trace else ""}

Score 0-5 where:
5 = Excellent: accurate, complete, well-structured, no hallucinations
4 = Good: accurate, mostly complete, minor gaps
3 = Acceptable: basically correct, some important omissions
2 = Poor: significant errors or omissions
1 = Bad: mostly wrong or misleading
0 = Harmful: incorrect information presented as fact

Respond with JSON only: {{"score": <number>, "reasoning": "<one sentence>"}}
"""
        with dspy.context(lm=lm):
            response_text = lm(judge_prompt)[0]

        try:
            # We strip any markdown formatting around json just in case
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            data = json.loads(response_text)
            return EvaluationResult(
                score=float(data["score"]),
                signal=EvaluationSignal.LLM_JUDGE,
                reasoning=data.get("reasoning", "")
            )
        except Exception:
            # If judge fails to parse, default conservative score
            return EvaluationResult(
                score=2.0,
                signal=EvaluationSignal.LLM_JUDGE,
                reasoning="Judge response unparseable — conservative score applied"
            )

    def evaluate_from_user_feedback(self, rating: int) -> EvaluationResult:
        """Direct user feedback (1-5 stars or thumbs up = 4.5)."""
        return EvaluationResult(
            score=float(rating),
            signal=EvaluationSignal.USER_FEEDBACK,
            reasoning=f"Direct user rating: {rating}/5"
        )
