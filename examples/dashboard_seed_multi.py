"""
Seed the LearnKit dashboard's live store from MULTIPLE self-hosted models.
==========================================================================

Runs a tiny ``@lk.agent_learn`` loop against each OpenAI-compatible endpoint
in the matrix below and writes records + runs to ``LEARNKIT_DB_PATH``
(default ``~/.learnkit/memory.db``) — the same store the FastAPI backend in
``Docs/server.py`` serves at ``/api/v1/*``.

Each model gets its own ``agent_name`` so the dashboard's Agents page lists
all targets with per-model success curves, latency, tokens, and cost.

These runs use ``@lk.agent`` (the ``learn`` alias — model/answer path, no tool
calls), so every run is tagged ``mode='learn'`` and shows up under the
dashboard's Learn toggle. Two tasks per model x (cold, warm) = 4 runs per model.

Run:
    python examples/dashboard_seed_multi.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Iterable

from openai import OpenAI

import learnkit as lk

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.environ.get(
    "LEARNKIT_DB_PATH", str(Path.home() / ".learnkit" / "memory.db")
)

# Self-hosted endpoints to seed from. Qwen2.5-Coder-32B (:8000) is intentionally
# excluded — it is not a PASS on the agentic suite (sglang tool-parser config
# gap), so it would seed a misleading agent row. The verified PASS models are
# Qwen2.5-32B-Instruct (:8001) and Llama-3.3-70B (:8002).
TARGETS = [
    ("qwen2.5-32b",       "http://127.0.0.1:8001/v1", "Qwen/Qwen2.5-32B-Instruct"),
    ("llama-3.3-70b",     "http://127.0.0.1:8002/v1", "meta-llama/Llama-3.3-70B-Instruct"),
    ("gpt-oss-20b",       "http://127.0.0.1:8004/v1", "openai/gpt-oss-20b"),
]

TASKS = [
    "When does asyncio.gather() swallow exceptions vs propagate them, "
    "and what does return_exceptions=True change?",
    "Why does multiprocessing.Pool().map() hang on macOS Python 3.12, "
    "and what is the recommended start method?",
]

SYS = (
    "You are a senior Python engineer. Answer in <= 4 sentences. "
    "Be specific (versions, exact function names, exact behavior)."
)


def _run_one(db_path: str, name: str, base_url: str, model: str, tasks: Iterable[str]) -> tuple[int, int]:
    print(f"\n=== {name} :: {model} @ {base_url} ===")
    # Lower quality_threshold so the Anthropic judge's typical 2.0-2.5 score on
    # short Q&A answers still counts as success — otherwise every run lands as
    # failure and no skills get distilled, which makes the dashboard's
    # success/skills/curves all read zero. auto_promote skips the 24h
    # quarantine so distilled skills are immediately visible.
    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=db_path,
        scope="user",
        agent_name=name,
        background_postprocess=False,
        quality_threshold=1.5,
        auto_promote=True,
    )
    client = OpenAI(base_url=base_url, api_key=os.environ.get("LK_API_KEY", "none"))

    def _llm(system: str, user: str) -> str:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=300,
                temperature=0.2,
                timeout=120,
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            print(f"  [LLM ERROR] {type(exc).__name__}: {exc}")
            return ""

    @memory.agent(domain="coding")
    def ask(task: str, _learnkit_context: str = "") -> str:
        sys_msg = SYS + (("\n\n" + _learnkit_context) if _learnkit_context else "")
        print(f"  [LearnKit] context injected: {len(_learnkit_context):>4} chars")
        return _llm(sys_msg, task)

    run_count = 0
    for i, t in enumerate(tasks, 1):
        for arm in ("cold", "warm"):
            print(f"  [task {i}/{arm}] {t[:60]}...")
            t0 = time.time()
            out = ask(t)
            dt = (time.time() - t0) * 1000
            preview = (out or "").strip().splitlines()[0][:100] if out else "<empty>"
            print(f"    -> {dt:.0f} ms  | {preview}")
            run_count += 1

    rec_added = len(memory.backend.list_all(limit=5000))
    memory.shutdown(wait=True)
    return run_count, rec_added


def main() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    print(f"live store: {DB_PATH}\n")

    summary: list[tuple[str, int, int, str]] = []
    for name, base_url, model in TARGETS:
        try:
            runs, recs_seen = _run_one(DB_PATH, name, base_url, model, TASKS)
            summary.append((name, runs, recs_seen, "ok"))
        except Exception as exc:
            print(f"  [TARGET FAILED] {name}: {type(exc).__name__}: {exc}")
            summary.append((name, 0, 0, f"FAIL: {type(exc).__name__}"))
            continue

    # Final summary using a fresh read so totals reflect everything written.
    final = lk.LearnKit(memory_backend="sqlite", db_path=DB_PATH, scope="user")
    all_runs = final.backend.list_runs(limit=5000)
    all_records = final.backend.list_all(limit=5000)
    by_agent: dict[str, int] = {}
    for r in all_runs:
        a = r.get("agent_name") or r.get("agent_id") or "?"
        by_agent[a] = by_agent.get(a, 0) + 1
    final.shutdown(wait=True)

    print(f"\n=== seed complete ===")
    print(f"total records in store: {len(all_records)}")
    print(f"total runs in store:    {len(all_runs)}")
    print("per-agent run counts (in this DB, across all sessions):")
    for k, v in sorted(by_agent.items()):
        print(f"  {k:<28} -> {v} runs")
    print("\nthis-session summary:")
    for name, runs, _, status in summary:
        print(f"  {name:<28} runs_this_session={runs}  {status}")


if __name__ == "__main__":
    main()
