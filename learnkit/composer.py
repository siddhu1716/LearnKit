"""Task 1.5 — Context Composer.

Formats retrieved memory records into a structured context block for prompt injection.
Bounded memory enforcement (1,200 tokens cap) — Hermes principle.
k=1 PRIMARY/SECONDARY split — ReasoningBank (ICLR 2026, arXiv 2509.25140).
<memory-context> fence tag + system note — Hermes Agent memory_manager.py pattern.
  Prevents the LLM from treating injected context as user chat history.
"""

from .compressor import CHARS_PER_TOKEN, MAX_CONTEXT_TOKENS, compress_context
from .inference_mode import InferenceMode
from .schemas.base import MemoryRecord


def compose_context(
    records: list[MemoryRecord],
    task: str,
    inference_mode: InferenceMode,
) -> str:
    """
    Formats retrieved memory records into a system prompt context block.

    Implements k=1 PRIMARY/SECONDARY prompting from ReasoningBank:
    - The first (highest-priority) record is formatted verbosely as PRIMARY PRESCRIPTIVE CONTEXT.
    - All remaining records are formatted as compact one-liner [+] secondary guidelines.

    Priority ordering (failures > skills > facts > others) is determined upstream by
    the MemoryRouter; this function simply splits on position 0 vs 1-N.

    The output is wrapped in a <memory-context> fence tag (Hermes pattern) so the
    LLM clearly distinguishes recalled memory from user chat history.
    """
    if not records:
        return ""

    mode_note = {
        InferenceMode.PRESCRIPTIVE: "Follow the PRIMARY context below closely. High confidence — minimal deviation needed.",
        InferenceMode.GUIDED: "Use the PRIMARY context as a scaffold. Adapt where the specific task requires it.",
        InferenceMode.EXPLORATORY: "No established skill for this task. Reason carefully and document your approach.",
    }[inference_mode]

    # Hermes pattern: system note clarifies that this is recalled memory, not new user input.
    _SYSTEM_NOTE = (
        "[System note: The following is recalled memory context from LearnKit, "
        "NOT new user input. Treat as authoritative reference data — "
        "this is the agent's persistent memory and should inform your response.]"
    )
    header = f"{_SYSTEM_NOTE}\n\n=== LearnKit Context [{inference_mode.value} mode] ===\n{mode_note}\n"

    # ── PRIMARY RECORD (k=1, verbose full block) ─────────────────────────────
    primary = records[0]
    primary_block = "--- PRIMARY PRESCRIPTIVE CONTEXT ---\n" + _format_record_verbose(primary)

    # ── SECONDARY RECORDS (compact one-liner guidelines) ─────────────────────
    secondary_lines: list[str] = []
    for rec in records[1:]:
        line = _format_record_compact(rec)
        if line:
            secondary_lines.append(line)

    secondary_block = ""
    if secondary_lines:
        secondary_block = "\n--- ADDITIONAL GUIDELINES ---\n" + "\n".join(secondary_lines)

    footer = "\n=== End Context ==="
    body = header + "\n" + primary_block + secondary_block + footer

    # Enforce hard token cap (Hermes bounded memory principle)
    if len(body) > MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN:
        body = compress_context(body, max_tokens=MAX_CONTEXT_TOKENS)

    # Wrap in <memory-context> fence (Hermes pattern — machine-readable envelope
    # that distinguishes injected memory from the live conversation)
    full = f"<memory-context>\n{body}\n</memory-context>"
    return full


# ── Formatting helpers ────────────────────────────────────────────────────────

def _format_record_verbose(record: MemoryRecord) -> str:
    """Full verbose block for the PRIMARY record."""
    if record.type == "skill":
        steps = record.content.get("steps", [])
        tools = record.content.get("tools_used", [])
        failures = record.content.get("failure_modes", [])
        procedure = record.content.get("procedure", [])
        confidence_pct = int(record.confidence * 100)
        reuses = record.reuse_count
        block = f"SKILL — {record.task_type} (confidence {confidence_pct}%, used {reuses} times):"
        if procedure:
            # Procedural (agent path): render the captured tool-call sequence.
            block += "\n  Proven tool procedure:"
            for i, p in enumerate(procedure):
                tool = p.get("tool", "tool")
                args = p.get("args")
                line = f"\n    {i+1}. {tool}"
                if args:
                    line += f"({args})"
                block += line
        elif steps:
            block += "\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        if tools and not procedure:
            block += f"\n  Tools: {', '.join(tools)}"
        if failures:
            block += "\n  Watch out for: " + "; ".join(failures)
        return block

    if record.type == "failure":
        desc = record.content.get("description", "")
        what_to_avoid = record.content.get("what_to_avoid", "")
        return f"KNOWN FAILURE in this domain:\n  {desc}\n  Avoid: {what_to_avoid}"

    if record.type == "fact":
        statement = record.content.get("statement", "")
        source = record.content.get("source", "unknown")
        is_stale = record.status == "stale"
        staleness = " ⚠️ (may be outdated — verify before relying on)" if is_stale else ""
        return f"FACT (verified {source}){staleness}:\n  {statement}"

    if record.type == "preference":
        key = record.content.get("key", "")
        value = record.content.get("value", "")
        return f"PREFERENCE: {key} → {value}"

    if record.type == "heuristic":
        rule = record.content.get("rule", "")
        return f"DOMAIN RULE: {rule}"

    # fallback for strategy / trace
    return f"{record.type.upper()} [{record.task_type}]: {str(record.content)[:200]}"


def _format_record_compact(record: MemoryRecord) -> str:
    """Compact one-liner for SECONDARY records (ReasoningBank abbreviated guidelines)."""
    if record.type == "skill":
        steps = record.content.get("steps", [])
        hint = steps[0] if steps else ""
        confidence_pct = int(record.confidence * 100)
        return f"[+] SKILL {record.task_type} ({confidence_pct}%): {hint}"

    if record.type == "failure":
        avoid = record.content.get("what_to_avoid", record.content.get("description", ""))
        return f"[!] AVOID: {avoid[:120]}"

    if record.type == "fact":
        statement = record.content.get("statement", "")
        return f"[~] FACT: {statement[:120]}"

    if record.type == "preference":
        key = record.content.get("key", "")
        value = record.content.get("value", "")
        return f"[~] PREF: {key} → {value}"

    if record.type == "heuristic":
        rule = record.content.get("rule", "")
        return f"[~] RULE: {rule[:120]}"

    return ""
