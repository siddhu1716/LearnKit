"""Live-LLM agentic benchmark for the agent path (`@lk.agent_learn`) — AP7 live run.

This drives a real tool-calling LLM (Qwen2.5-7B-Instruct over an OpenAI-compatible
endpoint) through a ReAct loop and measures whether LearnKit's procedural memory
reduces the work the *live model* does on repeat / sibling tasks.

Two arms over an identical task stream:

    cold   — raw ReAct agent, no memory. Explores every task from scratch.
    warmed — the same agent wrapped in @lk.agent_learn. On first exposure it
             learns the productive tool procedure; on repeats and parameterized
             siblings that procedure is retrieved and injected into the model's
             context (`_learnkit_context`), so the model follows the proven plan
             instead of re-exploring.

Metrics per arm: tool calls, LLM calls (planning turns), and success — totalled
over the stream. Win condition: warmed does fewer tool + LLM calls than cold
while holding success.

Config via env (defaults target the hosted Qwen endpoint):
    LK_BASE_URL   default http://206.1.58.252:8000/v1
    LK_MODEL      default Qwen/Qwen2.5-7B-Instruct
    LK_API_KEY    default "none"

Run:
    python -m benchmarks.react_live
"""

import json
import os

from openai import OpenAI

import learnkit as lk
from learnkit.replay import replay_plan
from learnkit.tool_tracker import ToolTracker
from learnkit.trajectory import Trajectory

BASE_URL = os.environ.get("LK_BASE_URL", "http://206.1.58.252:8000/v1")
MODEL = os.environ.get("LK_MODEL", "Qwen/Qwen2.5-7B-Instruct")
API_KEY = os.environ.get("LK_API_KEY", "none")
MAX_STEPS = 8
MAX_OUTPUT_TOKENS = int(os.environ.get("LK_MAX_OUTPUT_TOKENS", "256"))

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120)

# ── Deterministic tool world ──────────────────────────────────────────────────
# Tool results are canned so the only variable being measured is how many calls
# the agent makes. Exploration tools (list_tables/describe_schema) are the
# dead-ends a naive agent uses to orient itself.
EXPLORATION_TOOLS = {"list_tables", "describe_schema"}


def _impl(name):
    def fn(**kwargs):
        if name == "list_tables":
            return "tables: users, orders, products, items"
        if name == "describe_schema":
            return "columns: id, name, active, amount, sales, category"
        if name == "query":
            return f"rows from {kwargs.get('table', '?')}"
        if name == "filter":
            return "filtered rows"
        if name == "aggregate":
            return f"{kwargs.get('op', 'agg')} of {kwargs.get('field', '?')} = 42"
        if name == "rank":
            return f"top {kwargs.get('limit', 'N')} by {kwargs.get('by', '?')}"
        if name == "format":
            return f"formatted as {kwargs.get('fmt', '?')}"
        return f"unknown tool {name}"
    return fn


TOOL_IMPLS = {
    n: _impl(n)
    for n in ["list_tables", "describe_schema", "query", "filter",
              "aggregate", "rank", "format"]
}


def _schema(name, props, required, desc):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


TOOLS_SCHEMA = [
    _schema("list_tables", {}, [], "List available database tables."),
    _schema("describe_schema", {"table": {"type": "string"}}, ["table"],
            "Describe the columns of a table."),
    _schema("query", {"table": {"type": "string"}}, ["table"],
            "Read rows from a table."),
    _schema("filter", {"active": {"type": "string"}}, [],
            "Filter the current rows by a predicate, e.g. active='true'."),
    _schema("aggregate",
            {"op": {"type": "string"}, "field": {"type": "string"}}, ["op", "field"],
            "Aggregate a field, e.g. op='sum', field='amount'."),
    _schema("rank", {"by": {"type": "string"}, "limit": {"type": "integer"}}, ["by"],
            "Rank rows by a field, optionally limited to N."),
    _schema("format", {"fmt": {"type": "string"}}, ["fmt"],
            "Format the current result, e.g. fmt='csv' or fmt='json'."),
]

BASE_SYSTEM = (
    "You are a data pipeline agent. Accomplish the user's task by calling the "
    "provided tools, one logical step at a time. Do not call exploration tools "
    "(list_tables, describe_schema) unless you genuinely need them. When the "
    "result is ready, reply with a short final message and no further tool calls."
)
GUIDED_SUFFIX = (
    "\n\nYou have successfully completed a similar task before. A proven tool "
    "procedure is provided below — follow it directly with arguments adapted to "
    "the current task, and do NOT explore.\n"
)

# ── Task stream ───────────────────────────────────────────────────────────────
# (task, required productive tools). Each family appears as a first exposure
# (the model explores/plans, then the procedure is learned) followed by an exact
# repeat (which the warmed agent hard-replays with no LLM) and a sibling.
_REPORT = ("Build a report from the {t} table: first read the {t} table, then "
           "filter to active rows, then format the result as {f}.")
_TOPN = ("Produce a ranking from the {t} table: first read the {t} table, then "
         "rank rows by sales, then format the top 10 as {f}.")

STREAM = [
    (_REPORT.format(t="users", f="CSV"), ["query", "filter", "format"]),
    (_REPORT.format(t="users", f="CSV"), ["query", "filter", "format"]),   # exact
    (_REPORT.format(t="orders", f="JSON"), ["query", "filter", "format"]),  # sibling
    (_TOPN.format(t="products", f="CSV"), ["query", "rank", "format"]),
    (_TOPN.format(t="products", f="CSV"), ["query", "rank", "format"]),     # exact
    (_TOPN.format(t="items", f="JSON"), ["query", "rank", "format"]),       # sibling
]


def react_loop(task: str, system: str, tracker: ToolTracker) -> tuple[str, int]:
    """Run a ReAct tool-calling loop. Records each tool call on ``tracker`` and
    returns ``(final_text, llm_calls)``."""
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task}]
    llm_calls = 0
    final = ""
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS_SCHEMA,
            tool_choice="auto", temperature=0, max_tokens=MAX_OUTPUT_TOKENS,
        )
        llm_calls += 1
        msg = resp.choices[0].message
        if not msg.tool_calls:
            final = msg.content or ""
            break
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name,
                              "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPLS.get(name)
            result = impl(**args) if impl else f"unknown tool {name}"
            tracker.record(
                name, args, result,
                success=impl is not None,
                productive=name not in EXPLORATION_TOOLS,
            )
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": str(result)})
    return final, llm_calls


def _verify(required: list[str], tracker: ToolTracker) -> bool:
    called = {c["tool"] for c in tracker.calls}
    return all(t in called for t in required)


class StubDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *a, **k):
        return None


def run_cold() -> dict:
    stats = {"tool_calls": 0, "llm_calls": 0, "successes": 0, "tasks": 0}
    for task, required in STREAM:
        tracker = ToolTracker(Trajectory(task=task))
        _, llm = react_loop(task, BASE_SYSTEM, tracker)
        stats["tool_calls"] += tracker.call_count
        stats["llm_calls"] += llm
        stats["successes"] += 1 if _verify(required, tracker) else 0
        stats["tasks"] += 1
    return stats


def run_warmed() -> dict:
    memory = lk.LearnKit(
        memory_backend="sqlite", db_path=":memory:",
        background_postprocess=False, auto_promote=True,
        distiller=StubDistiller(),
    )
    stats = {"tool_calls": 0, "llm_calls": 0, "successes": 0,
             "replayed": 0, "guided": 0, "tasks": 0}

    for task, required in STREAM:
        llm_box = {"n": 0}
        req_box = {"r": required}

        @memory.agent_learn(domain="pipeline")
        def agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
            # Exact re-encounter: hard-replay the proven procedure with no LLM
            # call at all (the headline agentic win — zero planning cost).
            if _learnkit_tools.plan_kind == "exact":
                replay_plan(_learnkit_tools, TOOL_IMPLS)
                llm_box["n"] = 0
                _learnkit_tools.mark_outcome(_verify(req_box["r"], _learnkit_tools))
                return "done (replayed)"
            # Otherwise run ReAct, guided by any retrieved procedure in context.
            system = BASE_SYSTEM
            if _learnkit_context and _learnkit_context.strip():
                system = BASE_SYSTEM + GUIDED_SUFFIX + _learnkit_context
            final, llm = react_loop(task, system, _learnkit_tools)
            llm_box["n"] = llm
            _learnkit_tools.mark_outcome(_verify(req_box["r"], _learnkit_tools))
            return final

        # Classify the match the SDK would make for this run (for reporting).
        records = memory.retriever.retrieve(
            task=task, domain_vector={}, scope=memory.scope, router=memory.router)
        kind, _, _ = memory._match_procedure(records, task)

        agent(task)
        traj = memory.last_trajectory
        stats["tool_calls"] += sum(1 for s in traj.steps if s.role == "tool")
        stats["llm_calls"] += llm_box["n"]
        stats["successes"] += 1 if traj.outcome == "success" else 0
        stats["replayed"] += 1 if kind == "exact" else 0
        stats["guided"] += 1 if kind == "sibling" else 0
        stats["tasks"] += 1

    memory.shutdown()
    return stats


def main():
    print(f"endpoint: {BASE_URL}  model: {MODEL}\n")
    cold = run_cold()
    warm = run_warmed()

    hdr = (f"{'arm':>8} | {'tasks':>5} | {'tool_calls':>10} | {'tools/task':>10} | "
           f"{'llm_calls':>9} | {'success':>7} | {'replay':>6} | {'guide':>5}")
    print(hdr)
    print("-" * len(hdr))
    for label, s in (("cold", cold), ("warmed", warm)):
        cpt = s["tool_calls"] / s["tasks"]
        print(f"{label:>8} | {s['tasks']:>5} | {s['tool_calls']:>10} | {cpt:>10.2f} | "
              f"{s['llm_calls']:>9} | {s['successes']:>7} | "
              f"{s.get('replayed', 0):>6} | {s.get('guided', 0):>5}")
    print("-" * len(hdr))

    c_cpt = cold["tool_calls"] / cold["tasks"]
    w_cpt = warm["tool_calls"] / warm["tasks"]
    tool_red = (c_cpt - w_cpt) / c_cpt * 100 if c_cpt else 0.0
    llm_red = ((cold["llm_calls"] - warm["llm_calls"]) / cold["llm_calls"] * 100
               if cold["llm_calls"] else 0.0)
    print(f"\ntool-calls/task: cold {c_cpt:.2f} -> warmed {w_cpt:.2f}  ({tool_red:+.0f}%)")
    print(f"llm-calls total: cold {cold['llm_calls']} -> warmed {warm['llm_calls']} "
          f"({llm_red:+.0f}%)")
    print(f"success: cold {cold['successes']}/{cold['tasks']}  "
          f"warmed {warm['successes']}/{warm['tasks']}")
    ok = w_cpt <= c_cpt and warm["successes"] >= cold["successes"]
    print("\nPASS" if ok else "\nNO IMPROVEMENT")


if __name__ == "__main__":
    main()
