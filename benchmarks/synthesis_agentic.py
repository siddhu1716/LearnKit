"""Agentic synthesis benchmark — PBE & SLR as a tool loop (procedural path).

Motivation
----------
The original ``run_pbebench.py`` / ``run_slr_bench.py`` are *single-shot* model-path
benchmarks: one LLM call, parse, rule-grade. They have no tool trajectory, so
LearnKit's strong **agent/procedural path** (``@lk.agent_learn`` — procedure
replay + playbook guidance) never engages. They only exercise the weaker model
path, which is why they show ceiling/floor/regression rather than lift.

This benchmark reframes both task shapes as a **propose → execute → observe →
refine** tool loop, so the procedural path actually fires:

    propose_program / propose_rule   (productive tool — the candidate solution)
    show_examples                    (exploration tool — a dead-end, like
                                      list_tables in react_live)

Two arms over an identical task stream (mirrors ``react_live.py``):

    cold   — raw ReAct agent, no memory. Refines from scratch every task.
    warmed — same agent wrapped in ``@lk.agent_learn``. On first exposure it
             learns the winning productive procedure; on an exact repeat it
             hard-replays it with **zero** LLM calls; on a sibling (same latent
             transform, different surface strings) the proven procedure is
             injected as guidance so the model converges in one turn instead of
             exploring.

Each family appears as: first-exposure, exact-repeat, sibling. Families use
content-independent transforms/rules so the sibling shares the winning solution.

Win condition (per task kind): warmed does <= cold LLM calls while holding
success. ``playbook``-style value shows up as the LLM-call reduction on
exact-repeat (replay) and sibling (guidance) tasks.

Config via env (defaults target the hosted Qwen2.5-32B-Instruct endpoint):
    LK_BASE_URL   default http://127.0.0.1:8001/v1
    LK_MODEL      default Qwen/Qwen2.5-32B-Instruct
    LK_API_KEY    default "none"

Run:
    python -m benchmarks.synthesis_agentic
    python -m benchmarks.synthesis_agentic --kinds pbe slr --save-prefix final
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

import learnkit as lk
from learnkit.replay import replay_plan
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory

BASE_URL = os.environ.get("LK_BASE_URL", "http://127.0.0.1:8001/v1")
MODEL = os.environ.get("LK_MODEL", "Qwen/Qwen2.5-32B-Instruct")
API_KEY = os.environ.get("LK_API_KEY", "none")
MAX_STEPS = int(os.environ.get("LK_MAX_STEPS", "6"))
MAX_OUTPUT_TOKENS = int(os.environ.get("LK_MAX_OUTPUT_TOKENS", "256"))

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120)

EXPLORATION_TOOLS = {"show_examples"}


# ── Graders (deterministic, no LLM judge) ─────────────────────────────────────
def apply_replace_program(program: list[str], inputs: list[str]) -> list[str]:
    """Apply an ordered list of ``replace('a','b')`` call strings to inputs."""
    current = list(inputs)
    for call in program:
        call = (call or "").strip()
        try:
            tree = ast.parse(call, mode="eval")
            node = tree.body
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "replace"
                and len(node.args) == 2
            ):
                old = ast.literal_eval(node.args[0])
                new = ast.literal_eval(node.args[1])
                current = [s.replace(old, new) for s in current]
        except Exception:
            # Unparseable step is a no-op; the grader will report the mismatch.
            pass
    return current


def grade_pbe(answer: dict, task: dict) -> tuple[bool, str]:
    """answer = {"program": [...]}; compare transformed inputs to outputs."""
    program = answer.get("program") or []
    if not isinstance(program, list):
        return False, "program must be a JSON array of replace() call strings."
    actual = apply_replace_program([str(p) for p in program], task["inputs"])
    expected = task["outputs"]
    if actual == expected:
        return True, "ALL EXAMPLES PASS."
    wrong = [
        f"  input={inp!r} expected={exp!r} got={act!r}"
        for inp, exp, act in zip(task["inputs"], expected, actual)
        if exp != act
    ]
    return False, f"{len(wrong)}/{len(expected)} still wrong:\n" + "\n".join(wrong)


def grade_slr(answer: dict, task: dict) -> tuple[bool, str]:
    """answer = {"attribute": str, "value": str}; an item is labelled positive
    iff item[attribute] == value. Passes when this rule classifies every example
    in the task correctly (positive examples labelled, negatives not)."""
    attribute = str(answer.get("attribute", "")).strip()
    value = str(answer.get("value", "")).strip()
    if not attribute:
        return False, "attribute must be one of: " + ", ".join(task["attributes"])
    wrong = []
    for ex in task["examples"]:
        predicted = str(ex["features"].get(attribute, "")) == value
        if predicted != ex["label"]:
            wrong.append(
                f"  {ex['name']} (features={ex['features']}) "
                f"expected={'+' if ex['label'] else '-'} "
                f"got={'+' if predicted else '-'}"
            )
    if not wrong:
        return True, "ALL EXAMPLES PASS."
    return False, f"{len(wrong)}/{len(task['examples'])} misclassified:\n" + "\n".join(wrong)


# ── Tool schemas ──────────────────────────────────────────────────────────────
def _schema(name: str, props: dict, required: list[str], desc: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


PBE_TOOLS = [
    _schema(
        "propose_program",
        {"program": {"type": "array", "items": {"type": "string"}}},
        ["program"],
        "Test a candidate transform. program is an ordered JSON array of Python "
        "replace() call strings, e.g. [\"replace(' ', '_')\"]. Returns whether "
        "every example is transformed correctly, with the mismatches if not.",
    ),
    _schema("show_examples", {}, [], "Re-show the input/output example pairs."),
]

SLR_TOOLS = [
    _schema(
        "propose_rule",
        {"attribute": {"type": "string"}, "value": {"type": "string"}},
        ["attribute", "value"],
        "Test a candidate classification rule: an item is positive iff its "
        "attribute equals value. Returns whether the rule classifies every "
        "labelled example correctly, with the mistakes if not.",
    ),
    _schema("show_examples", {}, [], "Re-show the labelled examples and attributes."),
]

PBE_SYSTEM = (
    "You are a program-synthesis agent. Find an ordered sequence of Python "
    "replace() operations that turns every input into its matching output. Use "
    "the propose_program tool to test a candidate; read the feedback and refine "
    "until it reports ALL EXAMPLES PASS, then reply DONE with no further tool "
    "calls. Keep programs minimal."
)
SLR_SYSTEM = (
    "You are a rule-induction agent. Find a single attribute=value rule that "
    "labels every positive example and rejects every negative one. Use the "
    "propose_rule tool to test a candidate; read the feedback and refine until "
    "it reports ALL EXAMPLES PASS, then reply DONE with no further tool calls."
)
GUIDED_SUFFIX = (
    "\n\nYou solved a similar task before. A proven solution is provided below — "
    "test it directly with the current examples and do NOT explore.\n"
)


# ── Task families ─────────────────────────────────────────────────────────────
# Each family: a first-exposure task, its exact repeat, and a sibling that shares
# the latent transform/rule but uses different surface data.
def _pbe(name: str, inputs: list[str], program: list[str]) -> dict:
    return {
        "kind": "pbe",
        "name": name,
        "inputs": inputs,
        "outputs": apply_replace_program(program, inputs),
        "gold": {"program": program},
    }


def _slr(name: str, attribute: str, value: str, examples: list[dict]) -> dict:
    attrs = sorted({k for ex in examples for k in ex["features"]})
    return {
        "kind": "slr",
        "name": name,
        "attributes": attrs,
        "examples": examples,
        "gold": {"attribute": attribute, "value": value},
    }


def _ex(name: str, label: bool, **features: str) -> dict:
    return {"name": name, "label": label, "features": features}


PBE_FAMILIES = [
    (
        _pbe("space2us_a", ["hello world", "foo bar baz"], ["replace(' ', '_')"]),
        _pbe("space2us_b", ["alpha beta", "one two three"], ["replace(' ', '_')"]),
    ),
    (
        _pbe("comma2semi_a", ["a,b,c", "x,y"], ["replace(',', ';')"]),
        _pbe("comma2semi_b", ["1,2", "p,q,r"], ["replace(',', ';')"]),
    ),
    (
        _pbe("strip_proto_a", ["http://a.com", "http://b.org"], ["replace('http://', '')"]),
        _pbe("strip_proto_b", ["http://x.io", "http://y.net"], ["replace('http://', '')"]),
    ),
]

SLR_FAMILIES = [
    (
        _slr(
            "color_red_a", "color", "red",
            [
                _ex("t1", True, color="red", size="big"),
                _ex("t2", True, color="red", size="small"),
                _ex("t3", False, color="blue", size="big"),
                _ex("t4", False, color="green", size="small"),
            ],
        ),
        _slr(
            "color_red_b", "color", "red",
            [
                _ex("u1", True, color="red", shape="square"),
                _ex("u2", False, color="yellow", shape="round"),
                _ex("u3", True, color="red", shape="round"),
                _ex("u4", False, color="black", shape="square"),
            ],
        ),
    ),
    (
        _slr(
            "shape_round_a", "shape", "round",
            [
                _ex("v1", True, shape="round", color="red"),
                _ex("v2", False, shape="square", color="red"),
                _ex("v3", True, shape="round", color="blue"),
                _ex("v4", False, shape="triangle", color="green"),
            ],
        ),
        _slr(
            "shape_round_b", "shape", "round",
            [
                _ex("w1", True, shape="round", size="big"),
                _ex("w2", False, shape="square", size="small"),
                _ex("w3", True, shape="round", size="small"),
                _ex("w4", False, shape="oval", size="big"),
            ],
        ),
    ),
]


def build_stream(kind: str) -> list[dict]:
    """exposure → exact-repeat → sibling, per family."""
    families = PBE_FAMILIES if kind == "pbe" else SLR_FAMILIES
    stream: list[dict] = []
    for exposure, sibling in families:
        stream.append({**exposure, "phase": "exposure"})
        stream.append({**exposure, "phase": "exact"})
        stream.append({**sibling, "phase": "sibling"})
    return stream


GRADERS: dict[str, Callable[[dict, dict], tuple[bool, str]]] = {
    "pbe": grade_pbe,
    "slr": grade_slr,
}
PRODUCTIVE_TOOL = {"pbe": "propose_program", "slr": "propose_rule"}
TOOLS_FOR = {"pbe": PBE_TOOLS, "slr": SLR_TOOLS}
SYSTEM_FOR = {"pbe": PBE_SYSTEM, "slr": SLR_SYSTEM}


def render_task(task: dict) -> str:
    if task["kind"] == "pbe":
        lines = ["Synthesize the replace-program for these examples:"]
        for inp, out in zip(task["inputs"], task["outputs"]):
            lines.append(f"  {inp!r} -> {out!r}")
        return "\n".join(lines)
    lines = [
        "Induce the attribute=value rule. Attributes: "
        + ", ".join(task["attributes"]),
        "Examples (+ = positive, - = negative):",
    ]
    for ex in task["examples"]:
        sign = "+" if ex["label"] else "-"
        feats = ", ".join(f"{k}={v}" for k, v in ex["features"].items())
        lines.append(f"  {sign} {ex['name']}: {feats}")
    return "\n".join(lines)


# ── Per-task tool world ───────────────────────────────────────────────────────
def make_tool_impls(task: dict, solved_box: dict) -> dict[str, Callable]:
    grader = GRADERS[task["kind"]]
    productive = PRODUCTIVE_TOOL[task["kind"]]

    def _productive(**kwargs: Any) -> str:
        passed, feedback = grader(kwargs, task)
        if passed:
            solved_box["solved"] = True
            return "RESULT: " + feedback + " Reply DONE."
        return "RESULT: " + feedback

    def _show(**_: Any) -> str:
        return render_task(task)

    return {productive: _productive, "show_examples": _show}


# Endpoints without a tool-call parser leak the call as raw content. Accept the
# common Hermes/Qwen wrappers (<tool_call>...</tool_call> and <tools>...</tools>).
_TOOL_CALL_RE = re.compile(
    r"<(?:tool_call|tools)>\s*(\{.*?\})\s*</(?:tool_call|tools)>", re.DOTALL)


class _SynthToolCall:
    __slots__ = ("id", "function")

    def __init__(self, idx: int, name: str, args_str: str) -> None:
        self.id = f"synth_{idx}"
        self.function = type("F", (), {"name": name, "arguments": args_str})()


def _coerce_tool_obj(obj: Any, out: list[tuple[str, str]]) -> None:
    if not isinstance(obj, dict):
        return
    name = obj.get("name")
    if not name:
        return
    args = obj.get("arguments", obj.get("parameters", {}))
    args_str = json.dumps(args) if isinstance(args, dict) else str(args)
    out.append((name, args_str))


def _extract_inline_tool_calls(content: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in _TOOL_CALL_RE.finditer(content):
        try:
            _coerce_tool_obj(json.loads(m.group(1)), out)
        except json.JSONDecodeError:
            continue
    if out:
        return out
    # Parser-less endpoints (e.g. some Coder serving configs) emit the call as a
    # bare top-level JSON object/array in content with no wrapper at all.
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return out
        if isinstance(parsed, list):
            for item in parsed:
                _coerce_tool_obj(item, out)
        else:
            _coerce_tool_obj(parsed, out)
    return out


def react_loop(
    task: dict,
    system: str,
    tracker: ToolTracker,
    tool_impls: dict[str, Callable],
    tools_schema: list[dict],
) -> tuple[str, int]:
    """propose → execute → observe → refine loop. Records each productive tool
    call on ``tracker``; returns ``(final_text, llm_calls)``."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": render_task(task)},
    ]
    llm_calls = 0
    final = ""
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=tools_schema,
            tool_choice="auto", temperature=0, max_tokens=MAX_OUTPUT_TOKENS,
        )
        llm_calls += 1
        msg = resp.choices[0].message
        raw_calls = list(msg.tool_calls or [])
        assistant_content = msg.content or ""
        if not raw_calls and assistant_content.strip():
            extracted = _extract_inline_tool_calls(assistant_content)
            if extracted:
                raw_calls = [_SynthToolCall(i, n, a) for i, (n, a) in enumerate(extracted)]
                assistant_content = ""
        if not raw_calls:
            final = assistant_content
            break
        messages.append({
            "role": "assistant",
            "content": assistant_content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name,
                              "arguments": tc.function.arguments}}
                for tc in raw_calls
            ],
        })
        for tc in raw_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = tool_impls.get(name)
            result = impl(**args) if impl else f"unknown tool {name}"
            tracker.record(
                name, args, result,
                success=impl is not None,
                productive=name not in EXPLORATION_TOOLS,
            )
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(result)})
    return final, llm_calls


class StubDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None


def run_arm_cold(kind: str) -> dict:
    stats = {"tool_calls": 0, "llm_calls": 0, "successes": 0, "tasks": 0}
    for task in build_stream(kind):
        solved_box = {"solved": False}
        tool_impls = make_tool_impls(task, solved_box)
        tracker = ToolTracker(Trajectory(task=render_task(task)))
        _, llm = react_loop(task, SYSTEM_FOR[kind], tracker, tool_impls, TOOLS_FOR[kind])
        stats["tool_calls"] += tracker.call_count
        stats["llm_calls"] += llm
        stats["successes"] += 1 if solved_box["solved"] else 0
        stats["tasks"] += 1
    return stats


def run_arm_warmed(kind: str) -> dict:
    memory = lk.LearnKit(
        memory_backend="sqlite", db_path=":memory:",
        background_postprocess=False, auto_promote=True,
        distiller=StubDistiller(),
    )
    stats = {"tool_calls": 0, "llm_calls": 0, "successes": 0,
             "replayed": 0, "guided": 0, "tasks": 0}

    for task in build_stream(kind):
        solved_box = {"solved": False}
        tool_impls = make_tool_impls(task, solved_box)
        llm_box = {"n": 0}

        @memory.agent_learn(domain=f"synth-{kind}")
        def agent(task_text: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
            # Exact re-encounter: hard-replay the proven procedure, zero LLM.
            if _learnkit_tools.plan_kind == "exact" and _learnkit_tools.has_plan:
                replay_plan(_learnkit_tools, tool_impls, mark_success=False)
                llm_box["n"] = 0
                _learnkit_tools.mark_outcome(solved_box["solved"])
                return "done (replayed)"
            system = SYSTEM_FOR[kind]
            if _learnkit_context and _learnkit_context.strip():
                system = system + GUIDED_SUFFIX + _learnkit_context
            final, llm = react_loop(task, system, _learnkit_tools, tool_impls, TOOLS_FOR[kind])
            llm_box["n"] = llm
            _learnkit_tools.mark_outcome(solved_box["solved"])
            return final

        records = memory.retriever.retrieve(
            task=render_task(task), domain_vector={}, scope=memory.scope, router=memory.router)
        match_kind, _, _ = memory._match_procedure(records, render_task(task))

        agent(render_task(task))
        traj = memory.last_trajectory
        stats["tool_calls"] += sum(1 for s in traj.steps if s.role == "tool")
        stats["llm_calls"] += llm_box["n"]
        stats["successes"] += 1 if traj.outcome == "success" else 0
        stats["replayed"] += 1 if match_kind == "exact" else 0
        stats["guided"] += 1 if match_kind == "sibling" else 0
        stats["tasks"] += 1

    memory.shutdown()
    return stats


def _print_kind(kind: str, cold: dict, warm: dict) -> dict:
    hdr = (f"{'arm':>8} | {'tasks':>5} | {'tool_calls':>10} | {'llm_calls':>9} | "
           f"{'success':>7} | {'replay':>6} | {'guide':>5}")
    print(f"\n=== {kind.upper()} (agentic) ===")
    print(hdr)
    print("-" * len(hdr))
    for label, s in (("cold", cold), ("warmed", warm)):
        print(f"{label:>8} | {s['tasks']:>5} | {s['tool_calls']:>10} | {s['llm_calls']:>9} | "
              f"{s['successes']:>7} | {s.get('replayed', 0):>6} | {s.get('guided', 0):>5}")
    print("-" * len(hdr))
    llm_red = ((cold["llm_calls"] - warm["llm_calls"]) / cold["llm_calls"] * 100
               if cold["llm_calls"] else 0.0)
    print(f"llm-calls: cold {cold['llm_calls']} -> warmed {warm['llm_calls']} ({llm_red:+.0f}%)")
    print(f"success:   cold {cold['successes']}/{cold['tasks']}  "
          f"warmed {warm['successes']}/{warm['tasks']}")
    # A run that executed nothing (e.g. an endpoint with no tool-call parser)
    # must not register as a PASS just because 0 <= 0.
    if cold["successes"] == 0:
        ok = False
        print("NO EXECUTION (agent never solved a task — check tool-call support)")
    else:
        ok = (warm["llm_calls"] <= cold["llm_calls"]
              and warm["successes"] >= cold["successes"])
        print("PASS" if ok else "NO IMPROVEMENT")
    return {
        "kind": kind,
        "cold": cold,
        "warmed": warm,
        "llm_reduction_pct": round(llm_red, 1),
        "pass": ok,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kinds", nargs="+", default=["pbe", "slr"], choices=["pbe", "slr"])
    ap.add_argument("--save-prefix", default="synthesis_agentic")
    args = ap.parse_args()

    print(f"endpoint: {BASE_URL}  model: {MODEL}")

    results = []
    for kind in args.kinds:
        cold = run_arm_cold(kind)
        warm = run_arm_warmed(kind)
        results.append(_print_kind(kind, cold, warm))

    overall_pass = all(r["pass"] for r in results)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    RESULTS_DIR.mkdir(exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": BASE_URL,
        "model": MODEL,
        "max_steps": MAX_STEPS,
        "results": results,
        "overall_pass": overall_pass,
    }
    out = RESULTS_DIR / f"{args.save_prefix}_{ts}_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nsaved summary: {out}")
    print("\nOVERALL PASS" if overall_pass else "\nOVERALL: NO IMPROVEMENT")


if __name__ == "__main__":
    main()
