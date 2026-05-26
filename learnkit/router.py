from typing import List

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
        Takes a raw list of records from retriever and returns a filtered,
        capped list prioritizing skills and failures over facts.
        """
        # Sort priority: failures first, then skills, then facts, then others.
        # Within type, sorted by confidence (which Retriever already did).

        failures = [r for r in records if r.type == "failure"]
        skills = [r for r in records if r.type == "skill"]
        facts = [r for r in records if r.type == "fact"]
        others = [r for r in records if r.type not in ("failure", "skill", "fact")]

        routed = []
        for r_list in (failures, skills, facts, others):
            for r in r_list:
                if len(routed) < self.max_records:
                    routed.append(r)
                else:
                    break

        return routed
