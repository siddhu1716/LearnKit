"""Summarize attribution histograms from a benchmark raw.json."""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def summarize(raw_path: Path) -> str:
    rows = json.loads(raw_path.read_text())
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_arm[r["arm"]].append(r)

    out: list[str] = [f"# Attribution summary — {raw_path.parent.name}", ""]
    for arm, items in sorted(by_arm.items()):
        types = Counter()
        primary_types = Counter()
        ranks_when_primary_skill = []
        wins_when_skill_primary = 0
        wins_total = 0
        retrieval_present = 0
        for it in items:
            attr = it.get("attribution") or {}
            score = it.get("score", 0.0)
            wins_total += int(score > 0)
            if not attr or not attr.get("records"):
                continue
            retrieval_present += 1
            primary_type = attr.get("primary_record_type") or "none"
            primary_types[primary_type] += 1
            if primary_type == "skill":
                ranks_when_primary_skill.append(score)
                wins_when_skill_primary += int(score > 0)
            for rec in attr["records"]:
                types[rec["type"]] += 1

        out.append(f"## {arm}")
        out.append(f"- tasks: {len(items)}   wins: {wins_total}/{len(items)}   "
                   f"runs with retrieval: {retrieval_present}")
        out.append(f"- primary record type histogram: {dict(primary_types)}")
        out.append(f"- all-record type histogram: {dict(types)}")
        if ranks_when_primary_skill:
            out.append(f"- when primary=skill: wins={wins_when_skill_primary}/"
                       f"{len(ranks_when_primary_skill)} "
                       f"(scores={ranks_when_primary_skill})")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python attribution_summary.py <path-to-raw.json>", file=sys.stderr)
        sys.exit(2)
    print(summarize(Path(sys.argv[1])))
