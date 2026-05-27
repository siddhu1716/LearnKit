"""
LearnKit + LangChain Integration Demo
=====================================

Wraps a real LangChain 1.x tool-calling agent (`create_agent`, backed by
langgraph) with LearnKit's `@memory.agent` decorator. Runs the same task
twice against a file-backed SQLite memory store and prints how many
characters of distilled context get injected on each run.

Expected behaviour:
    - Run 1: cold memory, `Context injected: 0 chars`.
    - Run 2: warm memory, `Context injected: N chars` (N > 0) — the skill
      distilled from run 1 is retrieved and injected into the system prompt.

Requires:
    pip install langchain langchain-anthropic
    $env:ANTHROPIC_API_KEY = "sk-ant-..."

Run:
    python examples/langchain_demo.py
"""

import os
import platform
from pathlib import Path

from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

import learnkit as lk


@tool
def lookup_python_doc(symbol: str) -> str:
    """Look up a Python standard-library symbol. Returns a one-line summary."""
    docs = {
        "multiprocessing.set_start_method": (
            "Sets the method used to start child processes. "
            "Values: 'fork' (Unix default pre-3.14), 'spawn' (macOS/Windows default), 'forkserver'."
        ),
        "multiprocessing.Pool": (
            "Process pool. On macOS, the default start method is 'spawn' since Python 3.8 "
            "to avoid fork+threads deadlocks."
        ),
        "asyncio.run": "Executes a coroutine and returns the result. Creates a new event loop.",
        "threading.Lock": "Primitive lock object for thread synchronization.",
    }
    return docs.get(symbol, f"No docs for '{symbol}'")


@tool
def check_platform() -> str:
    """Return the current operating system name (e.g. 'Darwin', 'Linux', 'Windows')."""
    return platform.system()


BASE_SYSTEM_PROMPT = (
    "You are an expert Python debugging assistant. "
    "Use the tools to verify facts before answering. Keep answers under 4 sentences."
)

LLM = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
TOOLS = [lookup_python_doc, check_platform]


def build_agent(learnkit_context: str):
    """Rebuild the langgraph agent with LearnKit memory baked into the system prompt."""
    system_prompt = BASE_SYSTEM_PROMPT
    if learnkit_context:
        system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{learnkit_context}"
    return create_agent(model=LLM, tools=TOOLS, system_prompt=system_prompt)


# File-backed SQLite store so memory survives across runs of this script.
DB_PATH = str(Path(__file__).parent / "langchain_demo.db")

memory = lk.LearnKit(
    memory_backend="sqlite",
    db_path=DB_PATH,
    # Valid values: "user", "team", "public" (defined in schemas/base.py).
    scope="user",
    # Sync post-processing so run 2 deterministically sees run 1's distilled skill.
    background_postprocess=False,
)


@memory.agent(domain="coding")
def debug_agent(task: str, _learnkit_context: str = "") -> str:
    print(f"  [LearnKit] Context injected: {len(_learnkit_context)} chars")
    agent = build_agent(_learnkit_context)
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    final = result["messages"][-1]
    # AIMessage.content can be str or list[dict]; normalise.
    if isinstance(final.content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in final.content
        )
    return final.content


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: set ANTHROPIC_API_KEY before running this demo.")

    task = (
        "My multiprocessing.Pool().map() hangs forever when I call it from a script on macOS. "
        "What is the root cause and how do I fix it?"
    )

    print("=" * 72)
    print("LearnKit + LangChain — RUN 1 (cold memory)")
    print("=" * 72)
    out1 = debug_agent(task)
    print(f"  Answer: {out1.strip()[:300]}{'...' if len(out1) > 300 else ''}")

    print("\n" + "=" * 72)
    print("LearnKit + LangChain — RUN 2 (warm memory — should inject distilled skill)")
    print("=" * 72)
    out2 = debug_agent(task)
    print(f"  Answer: {out2.strip()[:300]}{'...' if len(out2) > 300 else ''}")

    print("\n" + "=" * 72)
    print("DONE — compare 'Context injected:' counts above.")
    print(f"Memory store: {DB_PATH}  (delete the file to reset)")
    print("=" * 72)


if __name__ == "__main__":
    main()
