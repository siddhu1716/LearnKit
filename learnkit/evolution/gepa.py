"""
GEPA (Genetic-Pareto Prompt Evolution) for LearnKit skill library.

Adapted from hermes-agent-self-evolution (MIT License, ICLR 2026 Oral).
Original: github.com/NousResearch/hermes-agent-self-evolution

Key changes from original:
- Operates on LearnKit SkillRecord JSON schema instead of Hermes SKILL.md
- Uses LearnKit Evaluator for quality scoring instead of Hermes benchmarks
- Ensemble policy: runs 3 parallel trials, ensembles results (ReaComp finding)
- Outputs to LearnKit memory backend, not ~/.hermes/skills/
"""

from concurrent.futures import ThreadPoolExecutor

import dspy

from ..backends.base import BaseBackend
from ..evaluator import Evaluator
from ..schemas.skill import SkillRecord

GEPA_SYSTEM = """
You are evolving an AI agent skill to improve its success rate.

Current skill:
{skill_json}

Recent execution traces where this skill was used:
{traces_summary}

Success rate: {success_rate:.0%}

Propose 3 mutations to this skill (modify steps, add constraints, clarify failure modes).
Each mutation should target a different failure pattern observed in the traces.

Respond with JSON: {{"mutations": [{{ "steps": [...], "constraints": [...], "failure_modes": [...] }}]}}
"""


class GEPAEvolver:

    def __init__(self, backend: BaseBackend, evaluator: Evaluator, lm=None):
        self.backend = backend
        self.evaluator = evaluator
        self.lm = lm or dspy.LM("anthropic/claude-sonnet-4-20250514")

    def evolve_skill(
        self,
        skill: SkillRecord,
        traces: list,
        n_trials: int = 3,  # ReaComp: ensemble diversity — minimum 3 runs
    ) -> list[SkillRecord]:
        """
        Runs n_trials parallel evolution trials and returns all variants.
        Caller ensembles and picks the best per task (ReaComp ensemble pattern).
        Never overwrites existing skill — creates new evolution_gen variants.
        """
        import json
        import uuid

        traces_summary = "\n".join(
            [
                f"- Task: {t.task[:100]}, Quality: {t.quality_score}/5"
                for t in traces[:10]
            ]
        )

        prompt = GEPA_SYSTEM.format(
            skill_json=skill.model_dump_json(indent=2),
            traces_summary=traces_summary,
            success_rate=skill.success_rate or 0.5,
        )

        def run_trial(_):
            with dspy.context(lm=self.lm):
                # DSPy 3.x LM returns a list
                raw = self.lm(prompt)[0]

            if raw.startswith("```json"):
                raw = raw[7:-3]

            try:
                data = json.loads(raw)
            except Exception:
                data = {}

            variants = []
            for mutation in data.get("mutations", [])[:3]:
                new_skill = skill.model_copy(deep=True)
                new_skill.id = str(uuid.uuid4())
                new_skill.content.update(mutation)
                new_skill.confidence = 0.5  # starts fresh, builds with use
                new_skill.evolution_gen = skill.evolution_gen + 1
                new_skill.status = "quarantine"
                variants.append(new_skill)
            return variants

        # Run trials in parallel — ensemble for diversity (ReaComp finding)
        all_variants = []
        with ThreadPoolExecutor(max_workers=n_trials) as executor:
            for result in executor.map(run_trial, range(n_trials)):
                all_variants.extend(result)

        # Store all variants — retriever will surface the best per task over time
        for variant in all_variants:
            self.backend.add(variant)

        return all_variants
