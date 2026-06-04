"""Task H7 — Harden Distiller (Contrastive failures, trace records).

Schema validation, TraceRecord emission, and contrastive failure extraction.
"""

import json
from typing import List, Optional, Tuple

import dspy

from .logging import get_logger
from .schemas.fact import FactRecord
from .schemas.failure import FailureRecord
from .schemas.skill import SkillRecord
from .schemas.trace import TraceRecord
from .trajectory import Trajectory

logger = get_logger("distiller")

DISTILL_PROMPT = """
You are reading an AI agent's execution trace to extract reusable knowledge.

TASK: {task}
DOMAINS: {domains}
QUALITY SCORE: {quality}/5

REASONING TRACE:
{reasoning}

EXECUTION STEPS:
{steps}

FINAL OUTPUT:
{output}

Extract reusable knowledge. Respond with JSON only:
{{
  "skill": {{
    "steps": ["step 1", "step 2"],
    "tools_used": ["tool_name"],
    "constraints": ["constraint"],
    "failure_modes": ["what almost went wrong"]
  }},
  "facts": [
    {{"statement": "...", "source": "from trace"}}
  ],
  "failures": [
    {{"description": "...", "what_to_avoid": "..."}}
  ]
}}

If no reusable skill can be extracted (task was one-off), set skill to null.
Focus on the APPROACH, not the specific content. The skill must generalize.
"""

# ReasoningBank (ICLR 2026) Finding 4 — dual-pass contrastive failure extraction.
# "ReasoningBank explicitly extracts 'preventative lessons' from failures in a
# dual-prompt extraction step."
# Used by distill_failure() when quality_score < quality_threshold.
FAILURE_CONTRASTIVE_PROMPT = """
You are analyzing a failed AI agent execution to extract a preventative lesson.

TASK: {task}
DOMAINS: {domains}
QUALITY SCORE: {quality}/5 (below passing threshold)

FAILED OUTPUT:
{output}

EXECUTION STEPS:
{steps}

Extract a concise preventative lesson. Respond with JSON only:
{{
  "lesson_title": "one-line title for this failure pattern",
  "root_cause": "why the agent failed on this task",
  "corrective_strategy": "what a successful agent should do instead",
  "trigger_pattern": "describe the task pattern that triggers this failure",
  "what_to_avoid": "specific action or reasoning the agent must NOT repeat"
}}

Be specific and actionable. The lesson must generalize to similar future tasks.
"""


def robust_json_loads(text: str) -> dict:
    """Safely loads JSON from string, falling back to json_repair if available."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import json_repair
            res = json_repair.loads(text)
            if isinstance(res, dict):
                return res
        except Exception:
            pass
        return json.loads(text.replace("'", '"'))


class MemoryDistiller:
    """
    Converts successful execution traces into typed memory records.
    """

    def __init__(self, lm=None):
        import os
        if lm is None:
            model = os.environ.get("LEARNKIT_DISTILLER_MODEL")
            if not model:
                if os.environ.get("ANTHROPIC_API_KEY"):
                    model = "anthropic/claude-haiku-4-5-20251001"
                elif os.environ.get("GEMINI_API_KEY"):
                    model = "gemini/gemini-2.5-flash"
                else:
                    model = "anthropic/claude-haiku-4-5-20251001"
            self.lm = dspy.LM(model)
        else:
            self.lm = dspy.LM(lm) if isinstance(lm, str) else lm

    def distill(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float,
    ) -> Tuple[
        Optional[SkillRecord],
        List[FactRecord],
        List[FailureRecord],
        Optional[TraceRecord],
    ]:
        """
        Distill trajectory into Skill, Fact, Failure, and Trace records.

        Returns (None, [], [], None) with a warning when quality_score is below
        threshold. Callers should call distill_failure() separately for low-quality
        traces to extract a contrastive FailureRecord.
        """
        if quality_score < 3.5:
            logger.warning(
                "Distillation skipped — quality below threshold",
                extra={
                    "event": "distill_quality_gate",
                    "quality_score": quality_score,
                    "threshold": 3.5,
                },
            )
            return None, [], [], None

        # Flatten trajectory for the prompt
        reasoning_steps = []
        execution_steps = []
        final_output = ""

        for step in trajectory.steps:
            if step.reasoning:
                reasoning_steps.append(step.reasoning)
            if step.role == "assistant":
                execution_steps.append(f"Agent: {step.content[:300]}")
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        prompt = DISTILL_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            quality=quality_score,
            reasoning="\n".join(reasoning_steps) or "No reasoning trace captured",
            steps="\n".join(execution_steps),
            output=final_output[:500],
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
        except Exception as e:
            logger.warning(
                "Distillation model call failed",
                extra={"event": "distill_model_fail", "error": str(e)},
            )
            # Safe degradation: don't pollute memory, return empty tuple
            return None, [], [], None

        # Basic json extraction
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```json") or lines[0] == "```":
                cleaned = "\n".join(lines[1:-1])
        cleaned = cleaned.strip()

        try:
            data = robust_json_loads(cleaned)
        except Exception as e:
            logger.warning(
                "Distillation JSON parsing failed, returning empty records",
                extra={
                    "event": "distillation_parse_fail",
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            data = {"skill": None, "facts": [], "failures": []}

        if not isinstance(data, dict):
            logger.warning(
                "Distillation output is not a JSON object, returning empty records"
            )
            data = {"skill": None, "facts": [], "failures": []}

        # Build records
        skill = None
        if data.get("skill"):
            try:
                skill = SkillRecord(
                    domains=domain_vector,
                    task_type=trajectory.task[:80],
                    content=data["skill"],
                    confidence=0.75,  # above CONFIDENCE_FLOOR + distilled-failure default (0.7)
                    status="quarantine",  # 24h quarantine before becoming active
                )
            except Exception as e:
                logger.warning(
                    "Failed to validate skill schema", extra={"error": str(e)}
                )

        facts = []
        for f in data.get("facts", []):
            if isinstance(f, dict) and "statement" in f:
                try:
                    facts.append(
                        FactRecord(
                            domains=domain_vector,
                            content={
                                "statement": f["statement"],
                                "source": f.get("source", "agent trace"),
                            },
                            status="quarantine",
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to validate fact schema", extra={"error": str(e)}
                    )

        # Failure records activate IMMEDIATELY — no quarantine
        failures = []
        for f in data.get("failures", []):
            if isinstance(f, dict):
                try:
                    failures.append(
                        FailureRecord(
                            domains=domain_vector,
                            content={
                                "description": f.get("description", ""),
                                "what_to_avoid": f.get("what_to_avoid", ""),
                            },
                            status="active",  # immediately active
                        )
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to validate failure schema", extra={"error": str(e)}
                    )

        # TraceRecord emission (active immediately)
        trace_steps = []
        for step in trajectory.steps:
            trace_steps.append(
                {
                    "step": step.step,
                    "role": step.role,
                    "content": step.content,
                    "tool_name": step.tool_name,
                    "tool_input": step.tool_input,
                    "reasoning": step.reasoning,
                    "timestamp": step.timestamp,
                }
            )

        try:
            trace_record = TraceRecord(
                domains=domain_vector,
                task_type=trajectory.task[:80],
                content={
                    "trajectory_id": trajectory.id,
                    "task": trajectory.task,
                    "summary": f"Distilled trace of {trajectory.task} with quality {quality_score}",
                    "steps": trace_steps,
                },
                status="active",
            )
        except Exception as e:
            logger.warning(
                "Failed to validate trace record schema", extra={"error": str(e)}
            )
            trace_record = None

        return skill, facts, failures, trace_record

    def distill_failure(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float,
    ) -> Optional[FailureRecord]:
        """Contrastive failure extraction (ReasoningBank dual-pass pattern).

        Called when a trace fails the quality gate (score < threshold). Extracts
        a preventative lesson — root cause, corrective strategy, and trigger pattern
        — and returns an immediately-active FailureRecord. This record is retrieved
        on similar future tasks, blocking the agent from repeating the same mistake.

        Returns None on model call failure or JSON parse failure (safe degradation).
        """
        execution_steps = []
        final_output = ""
        for step in trajectory.steps:
            if step.role == "assistant":
                execution_steps.append(f"Agent: {step.content[:300]}")
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        prompt = FAILURE_CONTRASTIVE_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            quality=quality_score,
            output=final_output[:500],
            steps="\n".join(execution_steps),
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
        except Exception as e:
            logger.warning(
                "Contrastive failure model call failed",
                extra={"event": "distill_failure_model_fail", "error": str(e)},
            )
            return None

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```json") or lines[0] == "```":
                cleaned = "\n".join(lines[1:-1])
        cleaned = cleaned.strip()

        try:
            data = robust_json_loads(cleaned)
        except Exception as e:
            logger.warning(
                "Contrastive failure JSON parsing failed",
                extra={"event": "distill_failure_parse_fail", "error_type": type(e).__name__},
            )
            return None

        if not isinstance(data, dict):
            return None

        try:
            lesson_title = (data.get("lesson_title") or "").strip()
            failure_label = lesson_title[:80] if lesson_title else "failure_pattern"
            failure = FailureRecord(
                domains=domain_vector,
                task_type=failure_label,
                content={
                    "description": lesson_title,
                    "root_cause": data.get("root_cause", ""),
                    "corrective_strategy": data.get("corrective_strategy", ""),
                    "trigger_pattern": data.get("trigger_pattern", ""),
                    "what_to_avoid": data.get("what_to_avoid", ""),
                },
                status="active",  # immediately active — no quarantine for failures
                confidence=0.7,   # start at 0.7 so it clears the CONFIDENCE_FLOOR
            )
            logger.warning(
                "Contrastive failure record created from low-quality trace",
                extra={"event": "distill_failure_created", "task_type": failure.task_type},
            )
            return failure
        except Exception as e:
            logger.warning(
                "Failed to construct FailureRecord from contrastive extraction",
                extra={"error": str(e)},
            )
            return None
