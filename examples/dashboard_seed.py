"""
Seed the LearnKit dashboard's live store with real agent runs.
==============================================================

Runs a tiny `@lk.agent_learn` loop against a self-hosted OpenAI-compatible
endpoint (default: Qwen2.5-14B-Instruct @ :8002) and writes records + runs
to ``LEARNKIT_DB_PATH`` (default ``~/.learnkit/memory.db``) — the same store
the FastAPI backend in ``Docs/server.py`` serves at ``/api/v1/*``.

Use this to verify the React dashboard under ``Docs/dashboard`` is reading
real telemetry (records, runs, per-run latency/tokens, replays) instead of
its built-in mock-data fallback.

Run:
    # 1) endpoint up at http://127.0.0.1:8002/v1
    # 2) this script:
    python examples/dashboard_seed.py
    # 3) start dashboard backend in another terminal:
    python Docs/server.py
    # 4) open http://127.0.0.1:8000/api/v1/metrics  (or the React UI)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from openai import OpenAI

import learnkit as lk

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.environ.get(
    "LEARNKIT_DB_PATH", str(Path.home() / ".learnkit" / "memory.db")
)
BASE_URL = os.environ.get("LK_BASE_URL", "http://127.0.0.1:8002/v1")
MODEL = os.environ.get("LK_MODEL", "Qwen/Qwen2.5-14B-Instruct")
API_KEY = os.environ.get("LK_API_KEY", "none")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def _llm(system: str, user: str) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=300,
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def main() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    print(f"endpoint: {BASE_URL}  model: {MODEL}")
    print(f"live store: {DB_PATH}")

    memory = lk.LearnKit(
        memory_backend="sqlite",
        db_path=DB_PATH,
        scope="user",
        background_postprocess=False,
    )

    base_system = (
        "You are a senior Python engineer. Answer in <= 4 sentences. "
        "Be specific (versions, exact function names, exact behavior)."
    )

    @memory.agent(domain="coding")
    def ask(task: str, _learnkit_context: str = "") -> str:
        sys_msg = base_system + ("\n\n" + _learnkit_context if _learnkit_context else "")
        print(f"  [LearnKit] context injected: {len(_learnkit_context):>4} chars")
        return _llm(sys_msg, task)

    tasks = [
        (
            "When does asyncio.gather() swallow exceptions vs propagate them, "
            "and what does return_exceptions=True change?"
        ),
        (
            "Why does multiprocessing.Pool().map() hang on macOS Python 3.12, "
            "and what is the recommended start method?"
        ),
    ]

    for i, t in enumerate(tasks, 1):
        for arm in ("cold", "warm"):
            print(f"\n[task {i} / {arm}] {t[:64]}...")
            t0 = time.time()
            out = ask(t)
            dt = (time.time() - t0) * 1000
            print(f"  -> {dt:.0f} ms  | answer: {out.strip()[:140]}...")

    memory.shutdown(wait=True)

    print(f"\nrecords now in store: {len(memory.backend.list_all(limit=5000))}")
    print(f"runs now in store:    {len(memory.backend.list_runs(limit=5000))}")
    print(f"\nDONE. start the dashboard backend:  python Docs/server.py")


if __name__ == "__main__":
    main()
