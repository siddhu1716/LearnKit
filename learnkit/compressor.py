"""Context compression helpers.

Keeps injected memory under LearnKit's hard bounded-memory cap.
"""

MAX_CONTEXT_TOKENS = 1200
CHARS_PER_TOKEN = 4
TRUNCATION_NOTICE = "[Context truncated — additional records available in memory store]"


def compress_context(
    text: str,
    max_tokens: int = MAX_CONTEXT_TOKENS,
    chars_per_token: int = CHARS_PER_TOKEN,
) -> str:
    """Truncate text to the approximate token budget while preserving leading context."""
    max_chars = max_tokens * chars_per_token
    if len(text) <= max_chars:
        return text

    lines = text.split("\n")
    result = []
    char_count = 0
    notice_budget = len(TRUNCATION_NOTICE) + 2

    for line in lines:
        if char_count + len(line) > max_chars - notice_budget:
            result.append("")
            result.append(TRUNCATION_NOTICE)
            break
        result.append(line)
        char_count += len(line) + 1

    return "\n".join(result)
