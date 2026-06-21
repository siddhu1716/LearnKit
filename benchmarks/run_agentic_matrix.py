"""Run the agentic suite across multiple hosted models and aggregate results.

This wrapper executes benchmarks.run_agentic_suite once per model endpoint,
collects each suite summary, and writes a merged matrix report.

Default targets match the user's hosted setup:
- qwen-instruct @ :8000
- llama-3.1-8b @ :8001
- qwen-coder @ :8002

Usage:
    python -m benchmarks.run_agentic_matrix --trials 1 --k 1 --seed 7
    python -m benchmarks.run_agentic_matrix --trials 3 --k 3 --seed 7

Custom target format (repeatable):
    --target "name|base_url|model"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"

DEFAULT_TARGETS = [
    {
        "name": "qwen2.5-7b",
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
    },
    {
        "name": "deepseek-coder-33b",
        "base_url": "http://127.0.0.1:8001/v1",
        "model": "deepseek-ai/deepseek-coder-33b-instruct",
    },
    {
        "name": "qwen2.5-14b",
        "base_url": "http://127.0.0.1:8002/v1",
        "model": "Qwen/Qwen2.5-14B-Instruct",
    },
]


def _run(cmd: list[str], env: dict[str, str], timeout_s: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT.parent),
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
        )
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "cmd": cmd,
            "returncode": 124,
            "stdout": e.stdout or "",
            "stderr": (e.stderr or "") + f"\nTimed out after {timeout_s}s",
            "timed_out": True,
        }


def _extract_suite_summary_path(stdout: str) -> Path | None:
    m = re.search(r"saved summary:\s+(.+agentic_suite[^\s]+_summary\.json)", stdout, re.IGNORECASE)
    if not m:
        return None
    p = Path(m.group(1).strip())
    return p if p.exists() else None


def _parse_target(s: str) -> dict[str, str]:
    parts = [p.strip() for p in s.split("|", 2)]
    if len(parts) != 3 or not all(parts):
        raise argparse.ArgumentTypeError(
            "target must be 'name|base_url|model'"
        )
    return {"name": parts[0], "base_url": parts[1], "model": parts[2]}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run agentic suite across a model matrix")
    p.add_argument("--target", action="append", type=_parse_target,
                   help="Custom target: name|base_url|model (repeatable)")
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--k", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--reflect", action="store_true")
    p.add_argument("--min-playbook-effect", type=float, default=0.5)
    p.add_argument("--per-model-timeout", type=int, default=900,
                   help="Timeout in seconds for each model's suite run")
    p.add_argument("--react-timeout", type=int, default=None,
                   help="Forwarded as --react-timeout to the suite")
    p.add_argument("--evolution-timeout", type=int, default=None,
                   help="Forwarded as --evolution-timeout to the suite")
    p.add_argument("--injection-timeout", type=int, default=None,
                   help="Forwarded as --injection-timeout to the suite")
    p.add_argument("--continue-on-fail", action="store_true",
                   help="Continue matrix even if one model fails suite gates")
    p.add_argument("--save-prefix", default="agentic_matrix")
    return p.parse_args()


def _save(detailed: dict[str, Any], summary: dict[str, Any], prefix: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    d = RESULTS_DIR / f"{prefix}_{ts}_detailed.json"
    s = RESULTS_DIR / f"{prefix}_{ts}_summary.json"
    d.write_text(json.dumps(detailed, indent=2), encoding="utf-8")
    s.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return d, s


def main() -> None:
    args = parse_args()
    targets = args.target or DEFAULT_TARGETS

    py = sys.executable
    rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "args": vars(args),
        "targets": targets,
        "runs": [],
    }

    for t in targets:
        print(f"[matrix] running {t['name']} ({t['model']}) @ {t['base_url']} ...")
        env = os.environ.copy()
        env["LK_BASE_URL"] = t["base_url"]
        env["LK_MODEL"] = t["model"]
        env.setdefault("LK_API_KEY", "none")

        cmd = [
            py,
            "-m",
            "benchmarks.run_agentic_suite",
            "--trials", str(args.trials),
            "--k", str(args.k),
            "--seed", str(args.seed),
            "--min-playbook-effect", str(args.min_playbook_effect),
        ]
        if args.continue_on_fail:
            cmd += ["--save-prefix", f"agentic_suite_{t['name']}"]
        if args.reflect:
            cmd.append("--reflect")
        if args.react_timeout is not None:
            cmd += ["--react-timeout", str(args.react_timeout)]
        if args.evolution_timeout is not None:
            cmd += ["--evolution-timeout", str(args.evolution_timeout)]
        if args.injection_timeout is not None:
            cmd += ["--injection-timeout", str(args.injection_timeout)]

        run = _run(cmd, env, args.per_model_timeout)
        summary_path = _extract_suite_summary_path(run["stdout"])
        suite_summary = None
        if summary_path:
            suite_summary = json.loads(summary_path.read_text(encoding="utf-8"))

        details["runs"].append(
            {
                "target": t,
                "run": run,
                "suite_summary_path": str(summary_path) if summary_path else None,
                "suite_summary": suite_summary,
            }
        )

        if suite_summary:
            inj = suite_summary.get("benchmarks", {}).get("injection_ablation", {})
            react = suite_summary.get("benchmarks", {}).get("react_live", {})
            row = {
                "name": t["name"],
                "model": t["model"],
                "base_url": t["base_url"],
                "overall_pass": bool(suite_summary.get("overall_pass")),
                "timed_out": bool(run.get("timed_out")),
                "playbook_effect": inj.get("playbook_effect"),
                "playbook_pass_k_full": inj.get("playbook_pass_k_full"),
                "warmed_llm_calls": react.get("warmed_llm_calls"),
                "cold_llm_calls": react.get("cold_llm_calls"),
            }
            rows.append(row)
        else:
            rows.append(
                {
                    "name": t["name"],
                    "model": t["model"],
                    "base_url": t["base_url"],
                    "overall_pass": False,
                    "timed_out": bool(run.get("timed_out")),
                    "playbook_effect": None,
                    "playbook_pass_k_full": None,
                    "warmed_llm_calls": None,
                    "cold_llm_calls": None,
                }
            )

    summary = {
        "generated_at": details["generated_at"],
        "rows": rows,
        "all_pass": all(bool(r.get("overall_pass")) for r in rows) if rows else False,
    }

    dpath, spath = _save(details, summary, args.save_prefix)

    print("\n=== model matrix summary ===")
    print("name           | pass | timeout | playbook_effect | pass^k(full) | llm cold->warm")
    print("---------------------------------------------------------------------------------")
    for r in rows:
        c = r.get("cold_llm_calls")
        w = r.get("warmed_llm_calls")
        llm = f"{c}->{w}" if c is not None and w is not None else "n/a"
        print(
            f"{r['name']:<14} | {str(r['overall_pass']):<4} | {str(r.get('timed_out')):<7} | "
            f"{str(r.get('playbook_effect')):<15} | {str(r.get('playbook_pass_k_full')):<12} | {llm}"
        )

    print(f"\nsaved detailed: {dpath}")
    print(f"saved summary:  {spath}")

    if not summary["all_pass"] and not args.continue_on_fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
