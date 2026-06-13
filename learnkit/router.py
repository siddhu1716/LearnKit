from typing import List, Optional, Tuple

from .compressor import CHARS_PER_TOKEN
from .diversity import mmr_order
from .schemas.base import MemoryRecord

# ReasoningBank (ICLR 2026, arXiv 2509.25140) Finding 1:
# "Retrieving more memories actually hurts performance: success rate drops
# from 49.7% at k=1 to 44.4% at k=4."
# The highest-confidence record is promoted to PRIMARY and injected first with
# a PRESCRIPTIVE label. All remaining records (up to 7) are SECONDARY.
CONFIDENCE_FLOOR: float = 0.45

DOMAIN_CONFIDENCE_FLOORS: dict[str, float] = {
    # Higher-risk domains where wrong pattern retrievals can be expensive.
    "sql_authoring": 0.55,
    "database": 0.55,
    # Coding tasks often have many near-matches; modestly stricter floor.
    "coding": 0.50,
}

# Type bonus for PRIMARY-slot ranking. Prescriptive records (skills/heuristics/
# strategies) get a small additive bonus so a comparable-confidence skill
# beats a same-confidence failure. A clearly higher-confidence failure
# (e.g. 0.95 vs skill 0.75) still wins. Window ~0.1.
_TYPE_BONUS: dict[str, float] = {
    "skill": 0.10,
    "heuristic": 0.08,
    "strategy": 0.06,
    "preference": 0.04,
    "fact": 0.02,
    "trace": 0.0,
    "failure": 0.0,
}


def _injection_score(record: MemoryRecord) -> float:
    """Effective ranking score for the PRIMARY slot.

    confidence + small additive bonus by type. Skills/heuristics/strategies
    are preferred as PRIMARY when scores are within ~0.1 — a failure must
    be meaningfully more confident to win the PRESCRIPTIVE slot, since
    failures are warnings, not instructions.
    """
    return record.confidence + _TYPE_BONUS.get(record.type, 0.0)


class MemoryRouter:
    """
    Enforces the bounded memory principle.
    Filters and limits the retrieved records before injection into context.
    """

    def __init__(
        self,
        max_records: int = 8,
        max_tokens: int = 1200,
        diversity_lambda: float = 0.7,
        domain_confidence_floors: Optional[dict[str, float]] = None,
    ):
        if max_records < 1:
            raise ValueError("max_records must be >= 1")
        if max_tokens < 1:
            raise ValueError("max_tokens must be >= 1")
        if not 0.0 <= diversity_lambda <= 1.0:
            raise ValueError("diversity_lambda must be in [0.0, 1.0]")
        self.max_records = max_records
        self.max_tokens = max_tokens
        # MMR relevance/diversity trade-off applied before the bounded-budget
        # admission loop. 1.0 disables diversity (pure confidence order); lower
        # values spend the budget on less-redundant records. See diversity.py.
        self.diversity_lambda = diversity_lambda
        self.domain_confidence_floors = dict(DOMAIN_CONFIDENCE_FLOORS)
        if domain_confidence_floors:
            self.domain_confidence_floors.update(domain_confidence_floors)

    def confidence_floor_for_domain(self, domain: Optional[str]) -> float:
        """Return the confidence floor for a top domain (or global default)."""
        if not domain:
            return CONFIDENCE_FLOOR
        return self.domain_confidence_floors.get(domain, CONFIDENCE_FLOOR)

    def route(self, records: List[MemoryRecord]) -> List[MemoryRecord]:
        """
        Returns a deduplicated, score-ranked, count-capped, token-budgeted slice.

        Records are admitted in descending ``_injection_score`` order rather than
        by strict type tiers. The score already encodes the type preference
        (skills/heuristics are prescriptive; failures are warnings), so a strong
        failure still gets in first while a stack of low-confidence failures can
        no longer starve a high-confidence skill out of the budget — the
        contamination failure mode seen on SLR/PBE runs.

        We cap at both max_records and max_tokens (~1,200 by default) so the
        composer never has to truncate a record mid-way. At least the top record
        is always admitted even if it exceeds the budget on its own — losing it
        would defeat the point of running the retriever. rank_for_injection() is
        then applied so the single highest-confidence record is first (PRIMARY),
        which the composer injects as the PRESCRIPTIVE block.
        """
        # Deduplicate by id — overlapping lexical/semantic searches can surface
        # the same record more than once. Preserve first-seen order.
        seen: set[str] = set()
        unique: List[MemoryRecord] = []
        for r in records:
            rid = getattr(r, "id", None)
            if rid is not None and rid in seen:
                continue
            if rid is not None:
                seen.add(rid)
            unique.append(r)

        ranked = sorted(unique, key=_injection_score, reverse=True)

        # Diversity-aware admission (ported from ruflo SmartRetrieval / ADR-090).
        # Re-order candidates by MMR so near-duplicate records don't fill the
        # bounded budget and crowd out complementary context. The seed is still
        # the highest-_injection_score record, so the PRIMARY slot is preserved.
        if self.diversity_lambda < 1.0 and len(ranked) > 1:
            ranked = mmr_order(
                ranked,
                relevance_of=_injection_score,
                text_of=_record_text,
                lambda_=self.diversity_lambda,
            )

        max_chars = self.max_tokens * CHARS_PER_TOKEN
        routed: List[MemoryRecord] = []
        budget_used = 0

        for r in ranked:
            if len(routed) >= self.max_records:
                break
            cost = _estimated_chars(r)
            if budget_used + cost > max_chars and routed:
                # Hit token budget. Stop adding (but keep what we have).
                break
            routed.append(r)
            budget_used += cost

        return _apply_k1_split(routed)


def rank_for_injection(
    records: List[MemoryRecord],
) -> Tuple[Optional[MemoryRecord], List[MemoryRecord]]:
    """ReasoningBank k=1 ranking.

    Separates the single highest-confidence record (PRIMARY) from the rest
    (SECONDARY, capped at 7). Called by the composer to inject PRIMARY first
    with the PRESCRIPTIVE label and SECONDARY as compact guidelines.

    The PRIMARY slot uses a type-weighted score (_injection_score) so a
    distilled skill at confidence 0.75 beats a contrastive failure at 0.75 —
    failures are warnings, skills are instructions. A clearly higher-confidence
    failure (e.g. 0.95 vs skill 0.75) still wins.

    Returns (primary, secondary_list). primary is None when records is empty.
    """
    if not records:
        return None, []
    sorted_records = sorted(records, key=_injection_score, reverse=True)
    primary = sorted_records[0]
    secondary = sorted_records[1:7]  # cap at 7; total injected <= 8
    return primary, secondary


def _apply_k1_split(records: List[MemoryRecord]) -> List[MemoryRecord]:
    """Re-order a routed list so position-0 is the highest-confidence record.

    Type-priority ordering (failure > skill > fact) determines *which* records
    are included. k=1 ranking then re-orders so the highest-confidence record
    is first — regardless of its type — so the composer always injects the
    most reliable memory as PRIMARY PRESCRIPTIVE context.
    """
    if len(records) <= 1:
        return records
    primary, secondary = rank_for_injection(records)
    if primary is None:
        return records
    return [primary] + secondary


def _record_text(record: MemoryRecord) -> str:
    """Flatten a record's task type, domains and content into one string.

    Used by the MMR diversity pass to measure token-Jaccard overlap between
    candidate records. Mirrors the retriever's record-text extraction.
    """
    parts = [record.task_type or "", " ".join(record.domains.keys())]
    for value in record.content.values():
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value))
        elif isinstance(value, dict):
            parts.append(" ".join(str(item) for item in value.values()))
        else:
            parts.append(str(value))
    return " ".join(parts)


def _estimated_chars(record: MemoryRecord) -> int:
    """Rough char count approximating what the composer will render for this record.

    Mirrors the structure of compose_context — task_type + key content fields
    plus formatting overhead. Intentionally conservative (over-estimates by
    ~10%) so we under-fill rather than overflow.
    """
    overhead = 80  # header line + indent prefixes + separators
    total = overhead + len(record.task_type or "")
    for value in record.content.values():
        if isinstance(value, list):
            total += sum(len(str(item)) + 4 for item in value)
        elif isinstance(value, dict):
            total += sum(len(str(v)) + 4 for v in value.values())
        else:
            total += len(str(value))
    return total
