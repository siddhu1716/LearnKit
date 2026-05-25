"""Task 1.5 — Context Composer.

Formats retrieved memory records into a structured context block for prompt injection.
Bounded memory enforcement (1,200 tokens cap) — Hermes principle.
"""

from .schemas.base import MemoryRecord
from .inference_mode import InferenceMode

MAX_CONTEXT_TOKENS = 1200   # hard cap — Hermes bounded memory principle
CHARS_PER_TOKEN = 4         # rough estimate


def compose_context(
    records: list[MemoryRecord],
    task: str,
    inference_mode: InferenceMode,
) -> str:
    """
    Formats retrieved memory records into a system prompt context block.
    """
    if not records:
        return ""

    sections = []

    # 1. Skills — most important, inject first
    skills = [r for r in records if r.type == "skill"]
    for skill in skills:
        steps = skill.content.get("steps", [])
        tools = skill.content.get("tools_used", [])
        failures = skill.content.get("failure_modes", [])
        confidence_pct = int(skill.confidence * 100)
        reuses = skill.reuse_count
        
        block = f"SKILL — {skill.task_type} (confidence {confidence_pct}%, used {reuses} times):"
        if steps:
            block += "\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        if tools:
            block += f"\n  Tools: {', '.join(tools)}"
        if failures:
            block += "\n  Watch out for: " + "; ".join(failures)
        sections.append(block)

    # 2. Failure records — inject as explicit warnings (ReaComp: failures are first-class)
    failures = [r for r in records if r.type == "failure"]
    for f in failures:
        desc = f.content.get("description", "")
        what_to_avoid = f.content.get("what_to_avoid", "")
        sections.append(f"KNOWN FAILURE in this domain:\n  {desc}\n  Avoid: {what_to_avoid}")

    # 3. Facts — grounding information
    facts = [r for r in records if r.type == "fact"]
    for fact in facts:
        statement = fact.content.get("statement", "")
        source = fact.content.get("source", "unknown")
        is_stale = fact.status == "stale"
        staleness = " ⚠️ (may be outdated — verify before relying on)" if is_stale else ""
        sections.append(f"FACT (verified {source}){staleness}:\n  {statement}")

    # 4. Preferences
    prefs = [r for r in records if r.type == "preference"]
    for pref in prefs:
        key = pref.content.get("key", "")
        value = pref.content.get("value", "")
        sections.append(f"PREFERENCE: {key} → {value}")

    # 5. Domain heuristics
    heuristics = [r for r in records if r.type == "heuristic"]
    for h in heuristics:
        rule = h.content.get("rule", "")
        sections.append(f"DOMAIN RULE: {rule}")

    if not sections:
        return ""

    mode_note = {
        InferenceMode.PRESCRIPTIVE: "Follow the skill above closely. High confidence — minimal deviation needed.",
        InferenceMode.GUIDED: "Use the skill as a scaffold. Adapt where the specific task requires it.",
        InferenceMode.EXPLORATORY: "No established skill for this task. Reason carefully and document your approach.",
    }[inference_mode]

    header = f"=== LearnKit Context [{inference_mode.value} mode] ===\n{mode_note}\n"
    body = "\n\n".join(sections)
    footer = "\n=== End Context ==="
    full = header + "\n" + body + footer

    # Enforce hard token cap (Hermes bounded memory principle)
    if len(full) > MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN:
        full = _compress_context(full, MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN)

    return full


def _compress_context(text: str, max_chars: int) -> str:
    """
    Truncate context to hard cap.
    """
    if len(text) <= max_chars:
        return text
    # Keep header + first skill/items + truncation notice
    lines = text.split("\n")
    result = []
    char_count = 0
    for line in lines:
        if char_count + len(line) > max_chars - 60:
            result.append("\n[Context truncated — additional records available in memory store]")
            break
        result.append(line)
        char_count += len(line) + 1
    return "\n".join(result)
