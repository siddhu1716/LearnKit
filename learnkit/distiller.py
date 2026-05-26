"""Task H7 — Harden Distiller (Contrastive failures, trace records).

Schema validation, TraceRecord emission, and contrastive failure extraction.
"""

import json
import dspy
from typing import Optional, Tuple, List

from .trajectory import Trajectory
from .schemas.skill import SkillRecord
from .schemas.failure import FailureRecord
from .schemas.fact import FactRecord
from .schemas.trace import TraceRecord
from .logging import get_logger

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

class MemoryDistiller:
    """
    Converts successful execution traces into typed memory records.
    """

    def __init__(self, lm=None):
        self.lm = lm or dspy.LM("anthropic/claude-haiku-4-5-20251001")

    def distill(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float
    ) -> Tuple[Optional[SkillRecord], List[FactRecord], List[FailureRecord], Optional[TraceRecord]]:
        """
        Distill trajectory into Skill, Fact, Failure, and Trace records.
        """
        if quality_score < 3.5:
            raise ValueError("Distillation called on low-quality trace. Evaluator should have gated this.")

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
            output=final_output[:500]
        )

        try:
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)[0]
        except Exception as e:
            logger.warning(
                "Distillation model call failed",
                extra={"event": "distill_model_fail", "error": str(e)}
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
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                data = json.loads(cleaned.replace("'", '"'))
            except json.JSONDecodeError as e:
                logger.warning(
                    "Distillation JSON parsing failed, returning empty records",
                    extra={"event": "distillation_parse_fail", "error_type": type(e).__name__, "error": str(e)}
                )
                data = {"skill": None, "facts": [], "failures": []}

        if not isinstance(data, dict):
            logger.warning("Distillation output is not a JSON object, returning empty records")
            data = {"skill": None, "facts": [], "failures": []}

        # Build records
        skill = None
        if data.get("skill"):
            try:
                skill = SkillRecord(
                    domains=domain_vector,
                    task_type=trajectory.task[:80],
                    content=data["skill"],
                    status="quarantine"   # 24h quarantine before becoming active
                )
            except Exception as e:
                logger.warning("Failed to validate skill schema", extra={"error": str(e)})

        facts = []
        for f in data.get("facts", []):
            if isinstance(f, dict) and "statement" in f:
                try:
                    facts.append(FactRecord(
                        domains=domain_vector,
                        content={"statement": f["statement"], "source": f.get("source", "agent trace")},
                        status="quarantine"
                    ))
                except Exception as e:
                    logger.warning("Failed to validate fact schema", extra={"error": str(e)})

        # Failure records activate IMMEDIATELY — no quarantine
        failures = []
        for f in data.get("failures", []):
            if isinstance(f, dict):
                try:
                    failures.append(FailureRecord(
                        domains=domain_vector,
                        content={"description": f.get("description", ""), "what_to_avoid": f.get("what_to_avoid", "")},
                        status="active"   # immediately active
                    ))
                except Exception as e:
                    logger.warning("Failed to validate failure schema", extra={"error": str(e)})

        # TraceRecord emission (active immediately)
        trace_steps = []
        for step in trajectory.steps:
            trace_steps.append({
                "step": step.step,
                "role": step.role,
                "content": step.content,
                "tool_name": step.tool_name,
                "tool_input": step.tool_input,
                "reasoning": step.reasoning,
                "timestamp": step.timestamp
            })

        try:
            trace_record = TraceRecord(
                domains=domain_vector,
                task_type=trajectory.task[:80],
                content={
                    "trajectory_id": trajectory.id,
                    "task": trajectory.task,
                    "summary": f"Distilled trace of {trajectory.task} with quality {quality_score}",
                    "steps": trace_steps
                },
                status="active"
            )
        except Exception as e:
            logger.warning("Failed to validate trace record schema", extra={"error": str(e)})
            trace_record = None

        return skill, facts, failures, trace_record
