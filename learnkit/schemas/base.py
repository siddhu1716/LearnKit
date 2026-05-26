"""
Task 1.3 — Base MemoryRecord schema.

7 memory types, TTL per type (LLM Wiki "keep current" principle),
confidence decay + reinforcement cycle (extends Hermes — which had none).
"""

import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, Field

MemoryType = Literal[
    "skill", "fact", "failure", "strategy", "preference", "trace", "heuristic"
]
MemoryScope = Literal["user", "team", "public"]
MemoryStatus = Literal["active", "stale", "quarantine", "deprecated"]

# Default TTL per type (days) — borrowed from LLM Wiki "keep current" principle
TTL_DEFAULTS: dict[str, int] = {
    "skill": 180,
    "fact": 90,
    "failure": 90,
    "strategy": 180,
    "preference": 365,
    "trace": 30,
    "heuristic": 90,
}


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    domains: dict[str, float] = {}  # multi-label: {"legal": 0.9, "finance": 0.4}
    task_type: Optional[str] = None
    content: dict = {}  # type-specific payload
    confidence: float = 0.5  # starts at 0.5, grows with reuse
    reuse_count: int = 0
    success_rate: Optional[float] = None
    scope: MemoryScope = "team"
    status: MemoryStatus = "active"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    last_reinforced: Optional[str] = None
    transfer_domains: list[str] = []
    transfer_confidence: Optional[float] = None
    evolution_gen: int = 0

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.expires_at is None:
            days = TTL_DEFAULTS.get(self.type, 90)
            exp = datetime.utcnow() + timedelta(days=days)
            self.expires_at = exp.isoformat()

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > datetime.fromisoformat(self.expires_at)

    def reinforce(self, quality: float) -> None:
        """Call after a successful retrieval that produced a good outcome."""
        self.reuse_count += 1
        self.last_reinforced = datetime.utcnow().isoformat()
        # Rolling weighted average — recent successes count more
        if self.success_rate is None:
            self.success_rate = quality / 5.0
        else:
            self.success_rate = 0.8 * self.success_rate + 0.2 * (quality / 5.0)
        # Confidence grows toward 0.95 with use, capped
        self.confidence = min(0.95, self.confidence + 0.02)

    def decay(self, decay_rate: float = 0.02) -> None:
        """Weekly confidence decay — records not reinforced become stale."""
        self.confidence = max(0.0, self.confidence - decay_rate)
        if self.confidence < 0.3:
            self.status = "stale"
