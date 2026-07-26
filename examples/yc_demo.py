"""Recording-ready LearnKit demo using an OpenAI-compatible Llama endpoint.

The same support-agent planner and tools run first without LearnKit, then with
LearnKit. The cold LearnKit run captures a successful procedure; exact repeats
replay it with zero planning LLM calls and zero planner tokens.

PowerShell:
    $env:LK_BASE_URL = "http://127.0.0.1:8000/v1"
    $env:LK_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
    $env:LK_API_KEY = "none"
    python examples/yc_demo.py --reset

Use ``--offline`` for a deterministic rehearsal without a model endpoint.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import learnkit as lk
from learnkit import LLMStep, Observation, ToolCall
from learnkit.classifier import ClassificationOutput


logging.disable(logging.INFO)


TASK = "Refund the latest delivered order for ada@example.com"
DEFAULT_DB = Path.home() / ".learnkit" / "yc_demo.db"
TOOL_SEQUENCE = ("find_customer", "list_orders", "get_order", "issue_refund")


def find_customer(email: str) -> dict[str, str]:
    return {"customer_id": "cust_42", "email": email}


def list_orders(customer_id: str) -> list[dict[str, Any]]:
    return [
        {
            "order_id": "ord_1001",
            "customer_id": customer_id,
            "status": "delivered",
            "total": 49.0,
        }
    ]


def get_order(order_id: str) -> dict[str, Any]:
    return {"order_id": order_id, "status": "delivered", "total": 49.0}


def issue_refund(order_id: str, amount: float) -> dict[str, Any]:
    return {"refund_id": "ref_9001", "order_id": order_id, "amount": amount, "status": "paid"}


TOOLS = {
    "find_customer": find_customer,
    "list_orders": list_orders,
    "get_order": get_order,
    "issue_refund": issue_refund,
}

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "find_customer",
            "description": "Find a customer by email address.",
            "parameters": {
                "type": "object",
                "properties": {"email": {"type": "string"}},
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "List orders for a customer.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get order status and total before refunding it.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Refund a delivered order for the requested amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["order_id", "amount"],
            },
        },
    },
]


class StubDistiller:
    """The deterministic procedure builder is sufficient for this demo."""

    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *args, **kwargs):
        return None


def classify_support_task(task: str) -> ClassificationOutput:
    return ClassificationOutput(
        task_type="refund_support",
        domains={"customer_support": 0.95},
        complexity="medium",
    )


def _parse_json_tool_payload(payload: Any) -> list[ToolCall]:
    if isinstance(payload, dict) and "name" in payload:
        args = payload.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        return [ToolCall(str(payload["name"]), args if isinstance(args, dict) else {})]
    if isinstance(payload, dict):
        payload = payload.get("tool_calls") or payload.get("tools") or []
    if isinstance(payload, list):
        calls: list[ToolCall] = []
        for item in payload:
            calls.extend(_parse_json_tool_payload(item))
        return calls
    return []


def extract_tool_calls(message: Any) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for raw in list(getattr(message, "tool_calls", None) or []):
        name = getattr(raw.function, "name", "")
        try:
            args = json.loads(getattr(raw.function, "arguments", "") or "{}")
        except json.JSONDecodeError:
            args = {}
        if name:
            calls.append(ToolCall(name, args))
    if calls:
        return calls

    content = (getattr(message, "content", None) or "").strip()
    blocks = re.findall(r"<(?:tool_call|tools)>\s*(.*?)\s*</(?:tool_call|tools)>", content, re.DOTALL)
    if not blocks and content.startswith(("{", "[")):
        blocks = [content]
    for block in blocks:
        try:
            calls.extend(_parse_json_tool_payload(json.loads(block)))
        except json.JSONDecodeError:
            continue
    return calls


class LlamaPlanner:
    def __init__(self, base_url: str, model: str, api_key: str) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SystemExit("Install the demo client with: pip install openai") from exc
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=120)
        self.model = model

    def __call__(self, task: str, context: str, history: list[Observation]) -> LLMStep:
        prior = "\n".join(
            f"{item.name}({json.dumps(item.args)}) -> {json.dumps(item.output)}"
            for item in history
        ) or "No tools have run yet."
        system = (
            "You are a customer-support tool agent. Complete the task using the provided tools. "
            "Use successful observations instead of repeating a tool. Refund only delivered orders. "
            "When the refund succeeds, answer briefly without calling another tool."
        )
        if context:
            system += f"\n\nLearnKit memory:\n{context}"
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=256,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": task},
                {"role": "user", "content": f"Tool observations so far:\n{prior}"},
            ],
        )
        message = response.choices[0].message
        usage = getattr(response, "usage", None)
        calls = extract_tool_calls(message)
        return LLMStep(
            tool_calls=calls,
            final=None if calls else (message.content or "Refund completed."),
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            model=self.model,
        )


class OfflinePlanner:
    model = "offline-scripted-planner"

    def __call__(self, task: str, context: str, history: list[Observation]) -> LLMStep:
        step = len(history)
        if step == 0:
            call = ToolCall("find_customer", {"email": "ada@example.com"})
        elif step == 1:
            call = ToolCall("list_orders", {"customer_id": "cust_42"})
        elif step == 2:
            call = ToolCall("get_order", {"order_id": "ord_1001"})
        elif step == 3:
            call = ToolCall("issue_refund", {"order_id": "ord_1001", "amount": 49.0})
        else:
            return LLMStep(
                final="Refund ref_9001 completed.",
                prompt_tokens=180,
                completion_tokens=12,
                model=self.model,
                usage_estimated=True,
            )
        return LLMStep(
            tool_calls=[call],
            prompt_tokens=180 + 60 * step,
            completion_tokens=18,
            model=self.model,
            usage_estimated=True,
        )


@dataclass
class PlainResult:
    llm_calls: int
    tool_calls: int
    prompt_tokens: int
    completion_tokens: int
    success: bool


def run_plain_agent(planner, max_steps: int = 8) -> PlainResult:
    history: list[Observation] = []
    llm_calls = 0
    prompt_tokens = 0
    completion_tokens = 0
    for _ in range(max_steps):
        step = planner(TASK, "", history)
        llm_calls += 1
        prompt_tokens += int(step.prompt_tokens or 0)
        completion_tokens += int(step.completion_tokens or 0)
        for call in step.tool_calls:
            tool = TOOLS.get(call.name)
            if tool is None:
                history.append(Observation(call.name, call.args, "unknown tool", False))
                continue
            try:
                output = tool(**call.args)
                history.append(Observation(call.name, call.args, output, True))
            except Exception as exc:
                history.append(Observation(call.name, call.args, f"error: {exc}", False))
        if step.final is not None:
            break
    success = any(item.name == "issue_refund" and item.success for item in history)
    return PlainResult(llm_calls, len(history), prompt_tokens, completion_tokens, success)


def reset_demo_db(path: Path) -> None:
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        candidate.unlink(missing_ok=True)


def build_memory(path: Path) -> lk.LearnKit:
    return lk.LearnKit(
        memory_backend="sqlite",
        db_path=str(path),
        scope="team",
        background_postprocess=False,
        auto_promote=True,
        record_ttl=False,
        classifier=classify_support_task,
        distiller=StubDistiller(),
        agent_id="yc-refund-agent",
        agent_name="Llama 3.3 Refund Agent",
    )


def print_result(label: str, result: Any) -> None:
    tokens = int(result.prompt_tokens) + int(result.completion_tokens)
    print(
        f"{label:<20} planning calls={result.llm_calls:<2} "
        f"planner tokens={tokens:<5} tool calls={result.tool_calls:<2} "
        f"replayed={getattr(result, 'replayed', False)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LearnKit YC demo")
    parser.add_argument("--offline", action="store_true", help="use a deterministic rehearsal planner")
    parser.add_argument("--reset", action="store_true", help="clear the isolated demo database first")
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("LEARNKIT_DB_PATH", DEFAULT_DB)))
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.reset:
        reset_demo_db(args.db)

    if args.offline:
        planner = OfflinePlanner()
        print("REHEARSAL MODE: deterministic planner with synthetic token counts\n")
    else:
        planner = LlamaPlanner(
            base_url=os.environ.get("LK_BASE_URL", "http://127.0.0.1:8000/v1"),
            model=os.environ.get("LK_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
            api_key=os.environ.get("LK_API_KEY", "none"),
        )

    print("1) EXISTING AGENT: the repeat still re-plans from scratch")
    baseline = run_plain_agent(planner)
    print_result("Without LearnKit", baseline)
    if not baseline.success:
        raise SystemExit("The planner did not complete the refund; check tool-calling support.")

    print("\n2) ATTACH LEARNKIT: same planner, same tools, one wrapper")
    print("   lk.run_react_agent(memory, task, tools, planner, mark_success=True)")
    memory = build_memory(args.db)
    try:
        cold = lk.run_react_agent(memory, TASK, TOOLS, planner, mark_success=True)
        warm_one = lk.run_react_agent(memory, TASK, TOOLS, planner, mark_success=True)
        warm_two = lk.run_react_agent(memory, TASK, TOOLS, planner, mark_success=True)
    finally:
        memory.shutdown(wait=True)

    print_result("LearnKit cold", cold)
    print_result("LearnKit replay 1", warm_one)
    print_result("LearnKit replay 2", warm_two)
    saved_calls = cold.llm_calls - warm_one.llm_calls
    cold_tokens = cold.prompt_tokens + cold.completion_tokens
    warm_tokens = warm_one.prompt_tokens + warm_one.completion_tokens
    print(
        f"\nRESULT: exact replay saved {saved_calls} planning calls and "
        f"{cold_tokens - warm_tokens} planner tokens while preserving the tool outcome."
    )
    print(f"Dashboard database: {args.db}")
    print("Open /app.html, then Agents -> Llama 3.3 Refund Agent.")


if __name__ == "__main__":
    main()
