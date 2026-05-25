"""SkillRecord — reusable approach distilled from successful executions."""

from .base import MemoryRecord


class SkillRecord(MemoryRecord):
    type: str = "skill"

    # Expected content keys:
    #   steps: list[str]        — ordered approach steps
    #   tools_used: list[str]   — tool names
    #   constraints: list[str]
    #   failure_modes: list[str]
    #   examples: dict          — {"good": str, "bad": str}

    def to_skill_md(self) -> str:
        """Generate a human-readable SKILL.md from this record."""
        c = self.content
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(c.get("steps", [])))
        tools = "\n".join(f"- {t}" for t in c.get("tools_used", []))
        constraints = "\n".join(f"- {ct}" for ct in c.get("constraints", []))
        failures = "\n".join(f"- {f}" for f in c.get("failure_modes", []))
        good_ex = c.get("examples", {}).get("good", "")
        bad_ex = c.get("examples", {}).get("bad", "")

        return f"""# {self.task_type}

## When to use this skill
Use for {self.task_type} tasks in {list(self.domains.keys())} domains.

## Approach
{steps}

## Tools used
{tools}

## Known constraints
{constraints}

## Known failure modes
{failures}

## Examples
### Good output pattern
{good_ex}

### Bad output pattern
{bad_ex}
"""
