from typing import List, Optional, Tuple

from .compressor import CHARS_PER_TOKEN
from .schemas.base import MemoryRecord

# ReasoningBank (ICLR 2026, arXiv 2509.25140) Finding 1:
# "Retrieving more memories actually hurts performance: success rate drops
# from 49.7% at k=1 to 44.4% at k=4."
# The highest-confidence record is promoted to PRIMARY and injected first with
# a PRESCRIPTIVE label. All remaining records (up to 7) are SECONDARY.
CONFIDENCE_FLOOR: float = 0.45


class MemoryRouter:
    """
    Enforces the bounded memory principle.
    Filters and limits the retrieved records before injection into context.
    """

    def __init__(self, max_records: int = 8, max_tokens: int = 1200):
        self.max_records = max_records
        self.max_tokens = max_tokens

    def route(self, records: List[MemoryRecord]) -> List[MemoryRecord]:
        """
        Returns a priority-sorted, count-capped, token-budgeted slice of records.

        Priority order (Hermes/ReaComp): failure > skill > fact > others. Within
        each tier the retriever's score order is preserved. We cap both at
        max_records and at max_tokens (~1,200 by default) so the composer never
        has to truncate a record mid-way. At least the highest-priority record
        is always admitted even if it exceeds the budget on its own — losing it
        would defeat the point of running the retriever.

        After type-priority ordering, rank_for_injection() is applied so the
        single highest-confidence record is always first (PRIMARY). The composer
        uses position-0 to inject the PRESCRIPTIVE block.
        """
        failures = [r for r in records if r.type == "failure"]
        skills = [r for r in records if r.type == "skill"]
        facts = [r for r in records if r.type == "fact"]
        others = [r for r in records if r.type not in ("failure", "skill", "fact")]

        max_chars = self.max_tokens * CHARS_PER_TOKEN
        routed: List[MemoryRecord] = []
        budget_used = 0

        for r_list in (failures, skills, facts, others):
            for r in r_list:
                if len(routed) >= self.max_records:
                    break
                cost = _estimated_chars(r)
                if budget_used + cost > max_chars and routed:
                    # Hit token budget. Stop adding (but keep what we have).
                    return _apply_k1_split(routed)
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

    Returns (primary, secondary_list). primary is None when records is empty.
    """
    if not records:
        return None, []
    sorted_records = sorted(records, key=lambda r: r.confidence, reverse=True)
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
