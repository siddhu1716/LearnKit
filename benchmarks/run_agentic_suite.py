"""Run LearnKit agentic benchmarks as one suite and enforce regression gates.

This orchestrates the three core agent-path benchmarks:

- react_live         (cost reduction on warmed vs cold)
- evolution_live     (multi-round durability and reuse trend)
- injection_ablation (quality effect of playbook injection)

Outputs:
- benchmarks/results/agentic_suite_<timestamp>_detailed.json
- benchmarks/results/agentic_suite_<timestamp>_summary.json

The first regression gate is enforced by default:
- playbook_effect = avg_score(playbook) - avg_score(procedure)
- fails if playbook_effect < --min-playbook-effect

Example:
    python -m benchmarks.run_agentic_suite
    python -m benchmarks.run_agentic_suite --trials 3 --k 3 --seed 7
    python -m benchmarks.run_agentic_suite --skip-react --skip-evolution
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


def _run(cmd: list[str], env: dict[str, str] | None = None, timeout_s: int | None = None) -> dict[str, Any]:
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


def _parse_react(stdout: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"tool-calls/task:\s*cold\s*([0-9.]+)\s*->\s*warmed\s*([0-9.]+)", stdout)
    if m:
        out["cold_tools_per_task"] = float(m.group(1))
        out["warmed_tools_per_task"] = float(m.group(2))
    m = re.search(r"llm-calls total:\s*cold\s*(\d+)\s*->\s*warmed\s*(\d+)", stdout)
    if m:
        out["cold_llm_calls"] = int(m.group(1))
        out["warmed_llm_calls"] = int(m.group(2))
    m = re.search(r"success:\s*cold\s*(\d+)/(\d+)\s*warmed\s*(\d+)/(\d+)", stdout)
    if m:
        out["cold_success"] = int(m.group(1))
        out["cold_tasks"] = int(m.group(2))
        out["warmed_success"] = int(m.group(3))
        out["warmed_tasks"] = int(m.group(4))
    out["pass"] = "PASS" in stdout
    return out


def _parse_evolution(stdout: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"llm calls:\s*cold\s*(\d+)\s*->\s*warmed\s*(\d+)", stdout)
    if m:
        out["cold_llm_calls"] = int(m.group(1))
        out["warmed_llm_calls"] = int(m.group(2))
    m = re.search(r"tool calls:\s*cold\s*(\d+)\s*->\s*warmed\s*(\d+)", stdout)
    if m:
        out["cold_tool_calls"] = int(m.group(1))
        out["warmed_tool_calls"] = int(m.group(2))
    m = re.search(r"success:\s*cold\s*(\d+)/(\d+)\s*warmed\s*(\d+)/(\d+)", stdout)
    if m:
        out["cold_success"] = int(m.group(1))
        out["cold_tasks"] = int(m.group(2))
        out["warmed_success"] = int(m.group(3))
        out["warmed_tasks"] = int(m.group(4))
    out["evolved"] = "EVOLVED" in stdout
    return out


def _extract_saved_summary_path(stdout: str) -> Path | None:
    m = re.search(r"Saved summary:\s+(.+_summary\.json)", stdout)
    if not m:
        return None
    p = Path(m.group(1).strip())
    return p if p.exists() else None


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _compute_suite_summary(detailed: dict[str, Any], min_playbook_effect: float) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "generated_at": detailed["generated_at"],
        "model": detailed.get("model"),
        "gates": {},
        "benchmarks": {},
    }

    react = detailed["benchmarks"].get("react_live")
    if react and react.get("parsed"):
        summary["benchmarks"]["react_live"] = {
            **react["parsed"],
            "timed_out": bool(react.get("run", {}).get("timed_out")),
            "returncode": react.get("run", {}).get("returncode"),
        }

    evo = detailed["benchmarks"].get("evolution_live")
    if evo and evo.get("parsed"):
        summary["benchmarks"]["evolution_live"] = {
            **evo["parsed"],
            "timed_out": bool(evo.get("run", {}).get("timed_out")),
            "returncode": evo.get("run", {}).get("returncode"),
        }

    inj = detailed["benchmarks"].get("injection_ablation")
    playbook_effect = None
    pass_k_full = None
    if inj and inj.get("summary"):
        s = inj["summary"]["arms"]
        playbook_effect = s["playbook"]["avg_score_per_task"] - s["procedure"]["avg_score_per_task"]
        pass_k_full = s["playbook"]["pass_k_full"]
        summary["benchmarks"]["injection_ablation"] = {
            "playbook_effect": playbook_effect,
            "playbook_pass_k_full": pass_k_full,
            "procedure_avg_score": s["procedure"]["avg_score_per_task"],
            "playbook_avg_score": s["playbook"]["avg_score_per_task"],
            "k": inj["summary"].get("k"),
            "trials": inj["summary"].get("trials"),
            "timed_out": bool(inj.get("run", {}).get("timed_out")),
            "returncode": inj.get("run", {}).get("returncode"),
        }

    gate = {
        "name": "min_playbook_effect",
        "threshold": min_playbook_effect,
        "observed": playbook_effect,
        "pass": (playbook_effect is not None and playbook_effect >= min_playbook_effect),
    }
    summary["gates"]["min_playbook_effect"] = gate
    summary["overall_pass"] = all(g.get("pass", False) for g in summary["gates"].values())
    summary["playbook_pass_k_full"] = pass_k_full
    return summary


def _save(detailed: dict[str, Any], summary: dict[str, Any], prefix: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    detailed_path = RESULTS_DIR / f"{prefix}_{ts}_detailed.json"
    summary_path = RESULTS_DIR / f"{prefix}_{ts}_summary.json"
    detailed_path.write_text(json.dumps(detailed, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return detailed_path, summary_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run agentic benchmark suite with gates")
    p.add_argument("--trials", type=int, default=1,
                   help="Injection ablation trials per arm")
    p.add_argument("--k", type=int, default=1,
                   help="Injection ablation pass^k parameter")
    p.add_argument("--seed", type=int, default=0,
                   help="Injection ablation base seed")
    p.add_argument("--skip-react", action="store_true",
                   help="Skip benchmarks.react_live")
    p.add_argument("--skip-evolution", action="store_true",
                   help="Skip benchmarks.evolution_live")
    p.add_argument("--skip-injection", action="store_true",
                   help="Skip benchmarks.injection_ablation")
    p.add_argument("--reflect", action="store_true",
                   help="Run evolution_live with LK_REFLECT=1")
    p.add_argument("--min-playbook-effect", type=float, default=0.5,
                   help="Regression gate threshold for playbook effect")
    p.add_argument("--react-timeout", type=int, default=420,
                   help="Timeout in seconds for benchmarks.react_live")
    p.add_argument("--evolution-timeout", type=int, default=420,
                   help="Timeout in seconds for benchmarks.evolution_live")
    p.add_argument("--injection-timeout", type=int, default=420,
                   help="Timeout in seconds for benchmarks.injection_ablation")
    p.add_argument("--save-prefix", default="agentic_suite",
                   help="Output prefix under benchmarks/results/")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    detailed: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": os.environ.get("LK_MODEL", "Qwen/Qwen2.5-7B-Instruct"),
        "benchmarks": {},
        "args": vars(args),
    }

    py = sys.executable

    if not args.skip_react:
        print("[suite] running benchmarks.react_live ...")
        r = _run([py, "-m", "benchmarks.react_live"], timeout_s=args.react_timeout)
        detailed["benchmarks"]["react_live"] = {
            "run": r,
            "parsed": _parse_react(r["stdout"]),
        }

    if not args.skip_evolution:
        print("[suite] running benchmarks.evolution_live ...")
        env = os.environ.copy()
        if args.reflect:
            env["LK_REFLECT"] = "1"
        r = _run([py, "-m", "benchmarks.evolution_live"], env=env,
                 timeout_s=args.evolution_timeout)
        detailed["benchmarks"]["evolution_live"] = {
            "run": r,
            "parsed": _parse_evolution(r["stdout"]),
        }

    if not args.skip_injection:
        print("[suite] running benchmarks.injection_ablation ...")
        cmd = [
            py,
            "-m",
            "benchmarks.injection_ablation",
            "--trials",
            str(args.trials),
            "--k",
            str(args.k),
            "--seed",
            str(args.seed),
            "--save-prefix",
            "injection_ablation",
        ]
        r = _run(cmd, timeout_s=args.injection_timeout)
        summary_path = _extract_saved_summary_path(r["stdout"])
        inj_summary = None
        if summary_path:
            inj_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        detailed["benchmarks"]["injection_ablation"] = {
            "run": r,
            "summary_path": str(summary_path) if summary_path else None,
            "summary": inj_summary,
        }

    summary = _compute_suite_summary(detailed, args.min_playbook_effect)
    detailed_path, summary_path = _save(detailed, summary, args.save_prefix)

    print("\n=== agentic suite summary ===")
    for name in ("react_live", "evolution_live", "injection_ablation"):
        bench = summary["benchmarks"].get(name)
        if bench and bench.get("timed_out"):
            print(f"{name}: TIMED OUT")
    if "injection_ablation" in summary["benchmarks"]:
        inj = summary["benchmarks"]["injection_ablation"]
        print(f"playbook effect: {inj['playbook_effect']:+.2f}  "
              f"(threshold >= {args.min_playbook_effect:.2f})")
        print(f"playbook pass^k(full): {inj['playbook_pass_k_full']:.3f}")
    gate = summary["gates"]["min_playbook_effect"]
    print("gate min_playbook_effect: PASS" if gate["pass"] else "gate min_playbook_effect: FAIL")
    print(f"saved detailed: {detailed_path}")
    print(f"saved summary:  {summary_path}")

    if not summary["overall_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
