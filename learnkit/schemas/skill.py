"""SkillRecord — reusable approach distilled from successful executions."""

from .base import MemoryRecord


class SkillRecord(MemoryRecord):
    type: str = "skill"

    # Expected content keys:
    #   steps: list[str]        — ordered approach steps (prose, model path)
    #   tools_used: list[str]   — tool names
    #   constraints: list[str]
    #   failure_modes: list[str]
    #   examples: dict          — {"good": str, "bad": str}
    #
    # Procedural keys (agent path, @lk.agent_learn) — the captured tool workflow:
    #   procedure: list[dict]   — ordered [{"tool", "args", "result_preview"}]
    #   tool_sequence: list[str]— canonical ordered tool names (dedup signature)
    #   trigger: str            — when to use this procedure (Hermes `description`)
    #   _procedure_fingerprint  — hash of tool_sequence (set on store)

    @property
    def is_procedural(self) -> bool:
        """True when this skill carries a captured tool-call procedure."""
        return bool(self.content.get("procedure"))

    def to_skill_md(self) -> str:
        """Generate a human-readable SKILL.md from this record.

        Procedural skills render the captured tool-call sequence (Hermes style);
        declarative skills fall back to the prose-steps layout.
        """
        if self.is_procedural:
            return self._to_procedural_md()
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

    def _to_procedural_md(self) -> str:
        """Render a Hermes-style SKILL.md from the captured tool procedure."""
        c = self.content
        trigger = c.get("trigger") or f"Use for {self.task_type} tasks."
        tool_seq = c.get("tool_sequence", [])
        procedure = c.get("procedure", [])
        constraints = c.get("constraints", [])
        failures = c.get("failure_modes", [])

        steps_md = []
        for i, step in enumerate(procedure):
            tool = step.get("tool", "tool")
            args = step.get("args")
            line = f"{i+1}. `{tool}`"
            if args:
                line += f" — args: {args}"
            steps_md.append(line)
        steps_block = "\n".join(steps_md) or "_No tool calls captured._"

        constraints_block = "\n".join(f"- {ct}" for ct in constraints) or "_None recorded._"
        failures_block = "\n".join(f"- {f}" for f in failures) or "_None recorded._"

        return f"""---
name: {self.task_type}
description: "{trigger}"
domains: {list(self.domains.keys())}
tool_sequence: {tool_seq}
confidence: {self.confidence:.2f}
reuse_count: {self.reuse_count}
---

# {self.task_type}

## When to use
{trigger}

## Procedure (captured tool sequence)
{steps_block}

## Constraints
{constraints_block}

## Known failure modes
{failures_block}
"""

