"""Print consolidated suite numbers for the 2026-06-21 model matrix."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "benchmarks" / "results"

FILES = {
    "qwen2.5-7b": RES / "agentic_suite_qwen2.5-7b_20260620_220017_summary.json",
    "deepseek-coder-33b": RES / "agentic_suite_deepseek-coder-33b_20260620_221449_summary.json",
    "qwen2.5-14b": RES / "agentic_suite_qwen2.5-14b_20260620_223626_summary.json",
}


def main() -> None:
    for name, p in FILES.items():
        d = json.loads(p.read_text(encoding="utf-8"))
        model = d["model"]
        b = d["benchmarks"]
        g = d["gates"]["min_playbook_effect"]
        rl = b["react_live"]
        ev = b["evolution_live"]
        ij = b["injection_ablation"]
        verdict = "PASS" if g["pass"] else "FAIL"
        print(f"== {name} ({model}) ==")
        print(
            f"  gate playbook_effect: threshold {g['threshold']} | observed {g['observed']} | {verdict}"
        )
        print(
            "  react: cold {0}/{1} -> warm {2}/{3} | LLM {4}->{5} | tools/task {6}->{7} | timeout={8} pass={9}".format(
                rl["cold_success"], rl["cold_tasks"], rl["warmed_success"], rl["warmed_tasks"],
                rl["cold_llm_calls"], rl["warmed_llm_calls"],
                rl["cold_tools_per_task"], rl["warmed_tools_per_task"],
                rl["timed_out"], rl["pass"],
            )
        )
        print(
            "  evolution: cold {0}/{1} -> warm {2}/{3} | LLM {4}->{5} | tools {6}->{7} | evolved={8}".format(
                ev["cold_success"], ev["cold_tasks"], ev["warmed_success"], ev["warmed_tasks"],
                ev["cold_llm_calls"], ev["warmed_llm_calls"],
                ev["cold_tool_calls"], ev["warmed_tool_calls"],
                ev["evolved"],
            )
        )
        print(
            "  injection: procedure={0} playbook={1} effect={2} pass^k(full)={3}".format(
                ij["procedure_avg_score"], ij["playbook_avg_score"],
                ij["playbook_effect"], ij["playbook_pass_k_full"],
            )
        )
        print()


if __name__ == "__main__":
    main()
