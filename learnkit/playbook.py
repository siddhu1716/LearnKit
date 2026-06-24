"""Playbook accumulation for the agent path (`@lk.agent_learn`).

A captured procedure makes a *repeat* cheaper (replay the tool sequence). A
*playbook* makes the agent *smarter* about the task: the natural-language
knowledge it learns by doing the work — which sources/inputs are worth using,
how to select what matters, output conventions, and pitfalls to avoid.

This is the Hermes "the SKILL.md body grows over the week" mechanism. Where
Hermes has an LLM patch one markdown file each session, we accumulate the same
knowledge as deduped insight bullets on the procedure record, merged every time
the family is re-proven. The merge is order-preserving (older, battle-tested
insights stay first) and capped so a procedure's knowledge stays focused.
"""

import re

DEFAULT_CAP = 12
MIN_WORDS = 2
MAX_WORDS = 30
_WS_RE = re.compile(r"\s+")

# Hermes "do-not-capture" guardrails as a deterministic gate. The reflection
# prompt already asks the model to avoid these, but a small local model follows
# that unreliably, so we enforce it in code: junk that hardens into bad rules is
# dropped before it can pollute a procedure's playbook.
#
# These categories mirror Hermes' background-review filter:
#   - environment/setup failures (not a property of the task, of the machine)
#   - negative claims that a tool "doesn't work" (almost always misattribution)
#   - transient errors that resolve on retry
#   - one-off, instance-specific narration that does not generalize
_REJECT_PATTERNS = (
    # environment / setup failures
    r"not installed|isn'?t installed|missing (binary|dependency|dependencies|package|module)"
    r"|command not found|no such (file|command|directory)|permission denied"
    r"|bad credential|invalid (api )?key|api key (is )?(missing|invalid|required)"
    r"|could not connect|connection refused|connection error|env(ironment)? (variable|var) (is )?(not set|missing)",
    # negative tool claims
    r"does(n'?t| not) work|is broken|doesn'?t exist|isn'?t available|is unavailable"
    r"|always fails|never works|tool (is )?(broken|unavailable|unreliable)|unreliable tool",
    # transient errors
    r"timed out|time-?out|retry|retried|try again|temporar(y|ily)|rate limit(ed)?|flaky|intermittent",
)
_REJECT_RE = re.compile("|".join(_REJECT_PATTERNS), re.IGNORECASE)
# Instance-specific narration: a bullet that opens by narrating *this* run rather
# than stating durable, reusable knowledge.
_NARRATION_RE = re.compile(
    r"^\s*(i |we |in this (task|case|instance|run)|this time|for this (task|specific|particular)"
    r"|the user (asked|wanted|requested|said)|here (i|we) )",
    re.IGNORECASE,
)

# Generic-advice gate (SkillLens, arXiv:2605.23899). Their study found that
# surface-plausible but generic best-practice ("be systematic", "verify
# results") is INERT — it does not improve downstream utility and a reformat of
# the same platitude changes nothing (p > 0.34). What drives utility is concrete,
# domain-specific failure knowledge. So a bullet whose *entire* content is a
# generic platitude is dropped; a concrete rule that merely contains a verb like
# "verify" (e.g. "verify the order exists before issuing a refund") is kept,
# because the pattern is whole-string anchored and stays short.
_GENERIC_ADVICE_RE = re.compile(
    r"^(?:please |always |remember to |make sure to |try to |you should |be sure to )?"
    r"(?:"
    r"be (?:careful|systematic|thorough|precise|methodical|diligent|cautious|mindful|organized)"
    r"|be careful with (?:dangerous|risky) (?:operations|actions|commands)"
    r"|handle (?:errors?|exceptions?|edge cases?) (?:carefully|gracefully|properly|appropriately)"
    r"|(?:carefully )?verify (?:the |your )?(?:results?|output|work|everything)"
    r"|double[- ]check (?:your |the )?(?:work|results?|everything|output)"
    r"|decompose (?:the task )?into (?:smaller )?(?:steps|subtasks|sub-tasks)"
    r"|break (?:it|the task|the problem|things) down(?: into (?:smaller )?steps)?"
    r"|think (?:step by step|carefully|things through)"
    r"|plan (?:your approach|the work|ahead|carefully)"
    r"|proceed (?:carefully|methodically|step by step)"
    r"|follow (?:best practices|the guidelines)"
    r"|use (?:good|sound) judg?ment"
    r"|pay (?:close )?attention(?: to detail| to details)?"
    r"|test (?:your )?(?:code|work|everything) (?:thoroughly|carefully)"
    r"|make sure (?:everything )?(?:is correct|works|is right)"
    r"|check (?:your )?work"
    r"|keep it simple"
    r"|stay focused"
    r")$",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Normalise an insight for dedup: lowercased, whitespace/punctuation-trimmed."""
    return _WS_RE.sub(" ", str(text).strip().lower()).rstrip(".!,; ")


def is_durable_insight(text) -> bool:
    """Return ``True`` if ``text`` is a keepable, durable playbook insight.

    Rejects the Hermes "do-not-capture" categories (environment/setup failures,
    negative tool claims, transient errors, one-off narration), generic best-
    practice platitudes that SkillLens found inert (e.g. "be systematic"), plus
    malformed bullets (empty, too short to be meaningful, or too long to be a
    focused rule).
    """
    if not isinstance(text, str):
        return False
    clean = _WS_RE.sub(" ", text.strip())
    if not clean:
        return False
    words = clean.split(" ")
    if len(words) < MIN_WORDS or len(words) > MAX_WORDS:
        return False
    if _NARRATION_RE.search(clean):
        return False
    if _REJECT_RE.search(clean):
        return False
    if _GENERIC_ADVICE_RE.match(_normalize(clean)):
        return False
    return True


def filter_insights(bullets) -> list[str]:
    """Drop non-durable bullets from ``bullets``, preserving order."""
    return [b.strip() for b in (bullets or []) if is_durable_insight(b)]


def merge_insights(existing, new, cap: int = DEFAULT_CAP) -> list[str]:
    """Merge ``new`` insight bullets into ``existing``, deduped and capped.

    Existing insights keep their position (proven knowledge first); genuinely new
    ones are appended. Near-duplicates (same normalised text) are dropped, and
    non-durable bullets (env failures, negative tool claims, transient errors,
    one-off narration, malformed length) are gated out via :func:`is_durable_insight`.
    The result is bounded to ``cap`` so the playbook stays a focused summary, not an
    ever-growing transcript.
    """
    merged: list[str] = []
    seen: set[str] = set()
    for item in list(existing or []) + list(new or []):
        if not is_durable_insight(item):
            continue
        clean = item.strip()
        key = _normalize(clean)
        if key in seen:
            continue
        seen.add(key)
        merged.append(clean)
    return merged[:cap]
