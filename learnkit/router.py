from typing import List

from .compressor import CHARS_PER_TOKEN
from .schemas.base import MemoryRecord


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
                    return routed
                cost = _estimated_chars(r)
                if budget_used + cost > max_chars and routed:
                    # Hit token budget. Stop adding (but keep what we have).
                    return routed
                routed.append(r)
                budget_used += cost

        return routed


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
