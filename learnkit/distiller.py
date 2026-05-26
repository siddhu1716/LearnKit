import dspy
import json
from typing import Optional, Tuple, List
from .trajectory import Trajectory
from .schemas.skill import SkillRecord
from .schemas.failure import FailureRecord
from .schemas.fact import FactRecord

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
    ) -> Tuple[Optional[SkillRecord], List[FactRecord], List[FailureRecord]]:

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

        with dspy.context(lm=self.lm):
            raw = self.lm(prompt)[0]

        # Basic json extraction
        if raw.startswith("```json"):
            raw = raw[7:-3]
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback if parsing fails (in production we'd use DSPy TypedPredictor)
            data = {"skill": None, "facts": [], "failures": []}

        # Build records
        skill = None
        if data.get("skill"):
            skill = SkillRecord(
                domains=domain_vector,
                task_type=trajectory.task[:80],
                content=data["skill"],
                status="quarantine"   # 24h quarantine before becoming active
            )

        facts = [
            FactRecord(
                domains=domain_vector,
                content={"statement": f["statement"], "source": f.get("source", "agent trace")},
                status="quarantine"
            )
            for f in data.get("facts", [])
        ]

        # Failure records activate IMMEDIATELY — no quarantine
        # Per ReaComp: agents need to know what not to do as fast as possible
        failures = [
            FailureRecord(
                domains=domain_vector,
                content={"description": f.get("description", ""), "what_to_avoid": f.get("what_to_avoid", "")},
                status="active"   # immediately active
            )
            for f in data.get("failures", [])
        ]

        return skill, facts, failures
