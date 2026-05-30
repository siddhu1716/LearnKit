"""
LearnKit minimal example — raw Anthropic SDK, no framework.
============================================================

Smallest possible @lk.agent integration. No LangChain, no LangGraph, no DSPy
in the agent itself — just `anthropic.Anthropic().messages.create`. Used to
prove LearnKit's value loop works independently of any framework.

Runs the same task twice against a fresh file-backed SQLite store and prints
how many chars of distilled context get injected on each run.

    Run 1 — cold:  Context injected:   0 chars
    Run 2 — warm:  Context injected: ~600+ chars

Requires:
    pip install anthropic
    $env:ANTHROPIC_API_KEY = "sk-ant-..."

Run:
    python examples/minimal_agent.py
"""

import os
import sys
from pathlib import Path

from anthropic import Anthropic

import learnkit as lk

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = str(Path(__file__).parent / "minimal_agent.db")
MODEL = "claude-haiku-4-5-20251001"
BASE_SYSTEM = (
    "You are a senior Python engineer. Answer in <= 4 sentences. "
    "If you cite a fact, be specific (version, function name, exact behavior)."
)

client = Anthropic()


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ERROR: set ANTHROPIC_API_KEY before running this demo.")

    # Reset BEFORE constructing LearnKit — otherwise __init__ creates the
    # schema, then we delete the file, and the next op finds an empty DB.
    Path(DB_PATH).unlink(missing_ok=True)

    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=DB_PATH,
        scope="user",
        background_postprocess=False,  # sync so run 2 sees run 1's distillation
    )

    @memory.agent(domain="coding")
    def ask(task: str, _learnkit_context: str = "") -> str:
        print(f"  [LearnKit] Context injected: {len(_learnkit_context):>4} chars")
        system = BASE_SYSTEM
        if _learnkit_context:
            system = f"{BASE_SYSTEM}\n\n{_learnkit_context}"
        msg = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": task}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")

    task = (
        "When does Python's asyncio.gather() swallow exceptions vs propagate them, "
        "and how does return_exceptions=True change the behavior?"
    )

    print("=" * 72)
    print("RUN 1 — cold memory")
    print("=" * 72)
    out1 = ask(task)
    print(f"  Answer: {out1.strip()[:280]}{'...' if len(out1) > 280 else ''}")

    print("\n" + "=" * 72)
    print("RUN 2 — warm memory (should inject what run 1 distilled)")
    print("=" * 72)
    out2 = ask(task)
    print(f"  Answer: {out2.strip()[:280]}{'...' if len(out2) > 280 else ''}")

    memory.shutdown(wait=True)

    print("\n" + "=" * 72)
    print(f"DONE. Memory store: {DB_PATH}")
    print("=" * 72)


if __name__ == "__main__":
    main()
