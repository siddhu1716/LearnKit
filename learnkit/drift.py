"""Procedure drift detection for the agent path (``@lk.agent_learn``).

A captured procedure's tool sequence is a *golden* sequence — the proven,
minimal path that solved a task family. This module turns those goldens into
lightweight regression checks so you can catch **slow drift**: the failure mode
where a live agent silently starts taking extra or reordered steps over time
(more tool calls, higher cost) even though the task hasn't changed.

Two pieces:

- :func:`check_drift` compares an observed tool sequence against a golden one and
  returns a structured :class:`DriftReport` (extra / missing / reordered / added
  call count).
- :func:`build_golden_suite` / :func:`export_golden_suite` snapshot every stored
  procedure's golden sequence to JSON, so the suite can be committed and diffed
  in CI.

Exact-match discipline is deliberate: this is a *drift alarm*, not a fuzzy
matcher. A sequence either reproduces the golden path or it doesn't.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .logging import get_logger

logger = get_logger("drift")


@dataclass
class DriftReport:
    """Result of comparing an observed tool sequence to a golden one."""

    task_type: str
    golden: list[str]
    observed: list[str]
    ok: bool                       # observed reproduces golden exactly (order + membership)
    extra: list[str] = field(default_factory=list)      # tools present beyond the golden path
    missing: list[str] = field(default_factory=list)    # golden tools the run skipped
    reordered: bool = False        # same multiset, different order
    added_call_count: int = 0      # len(observed) - len(golden)
    summary: str = ""

    def as_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "golden": self.golden,
            "observed": self.observed,
            "ok": self.ok,
            "extra": self.extra,
            "missing": self.missing,
            "reordered": self.reordered,
            "added_call_count": self.added_call_count,
            "summary": self.summary,
        }


def _multiset_diff(a: list[str], b: list[str]) -> list[str]:
    """Elements of ``a`` not accounted for by ``b`` (multiset difference)."""
    remaining = list(b)
    out: list[str] = []
    for item in a:
        if item in remaining:
            remaining.remove(item)
        else:
            out.append(item)
    return out


def golden_sequence(record) -> list[str]:
    """The stored golden tool sequence for a procedural skill record."""
    return list(record.content.get("tool_sequence") or [])


def check_drift(golden: list[str], observed: list[str], task_type: str = "") -> DriftReport:
    """Compare an ``observed`` tool sequence against the ``golden`` one.

    ``ok`` is True only on an exact match (same tools, same order). ``extra`` /
    ``missing`` are multiset differences; ``reordered`` is True when the two share
    the same multiset but differ in order. ``added_call_count`` is the raw growth
    in tool calls — the primary slow-drift signal.
    """
    golden = list(golden)
    observed = list(observed)
    ok = observed == golden
    extra = _multiset_diff(observed, golden)
    missing = _multiset_diff(golden, observed)
    reordered = (not ok) and sorted(observed) == sorted(golden)
    added = len(observed) - len(golden)

    if ok:
        summary = "no drift — reproduced the golden procedure"
    elif reordered:
        summary = "drift — same tools, different order"
    else:
        bits = []
        if extra:
            bits.append(f"+{len(extra)} extra ({', '.join(extra)})")
        if missing:
            bits.append(f"-{len(missing)} missing ({', '.join(missing)})")
        summary = "drift — " + "; ".join(bits) if bits else "drift"

    return DriftReport(
        task_type=task_type,
        golden=golden,
        observed=observed,
        ok=ok,
        extra=extra,
        missing=missing,
        reordered=reordered,
        added_call_count=added,
        summary=summary,
    )


def build_golden_suite(records) -> list[dict]:
    """Collect golden sequences from procedural skill records into a suite."""
    suite: list[dict] = []
    for r in records:
        if getattr(r, "type", None) != "skill":
            continue
        seq = r.content.get("tool_sequence")
        if not seq:
            continue
        suite.append(
            {
                "skill_id": r.id,
                "task_type": r.task_type,
                "trigger": r.content.get("trigger"),
                "tool_sequence": list(seq),
                "confidence": round(float(getattr(r, "confidence", 0.0)), 3),
                "reuse_count": int(getattr(r, "reuse_count", 0) or 0),
            }
        )
    return suite


def export_golden_suite(memory, path, scope: Optional[str] = None) -> int:
    """Snapshot every stored procedure's golden sequence to a JSON file.

    The file is a committable regression fixture: diff it in CI to catch when a
    procedure's proven path changes, and replay each entry against a live agent
    to detect step drift. Returns the number of goldens written.
    """
    records = memory.backend.list_by_scope(scope or memory.scope, limit=1000)
    suite = build_golden_suite(records)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(suite, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Exported golden test suite",
        extra={"event": "golden_suite_export", "count": len(suite), "path": str(out)},
    )
    return len(suite)
