"""
LearnKit -- Quick Start Demo
============================

Run this script to see LearnKit's components in action.
No API key required for the offline components (Parts 1-4).
An ANTHROPIC_API_KEY is required for the full loop (Part 5).

Usage:
    python examples/quick_start.py
"""

from pathlib import Path

import learnkit as lk


def part1_memory_store():
    """Part 1: Store and search memory records (fully offline)."""
    print("\n" + "=" * 60)
    print("PART 1 -- Memory Store (SQLite + FTS5)")
    print("=" * 60)

    # Create an in-memory backend (use a file path for persistence)
    backend = lk.SQLiteBackend(db_path=":memory:")

    # Store a skill learned from past agent runs
    skill = lk.SkillRecord(
        domains={"legal": 0.9, "finance": 0.3},
        task_type="contract_summarization",
        content={
            "steps": [
                "Extract all obligations per party",
                "Extract termination clauses",
                "Flag indemnity clauses separately",
                "Simplify to plain English",
            ],
            "tools_used": ["pdf_reader"],
            "constraints": ["under 500 words", "no legal jargon"],
            "failure_modes": ["hallucinated clause references"],
        },
        confidence=0.87,
    )
    backend.add(skill)
    print(f"  [OK] Stored skill: {skill.task_type} (id: {skill.id[:8]}...)")

    # Store a failure record (activates immediately -- no quarantine)
    failure = lk.FailureRecord(
        domains={"legal": 0.9},
        content={
            "description": "Merged obligations from different parties into one list",
            "what_to_avoid": "Always separate obligations by party name",
        },
        status="active",
    )
    backend.add(failure)
    print(f"  [OK] Stored failure: {failure.content['description'][:50]}...")

    # Search -- BM25 full-text search via FTS5
    results = backend.search("contract obligations", domain="legal")
    print(f"  [SEARCH] 'contract obligations' -> {len(results)} result(s)")
    for r in results:
        print(f"     [{r.type}] {r.task_type or r.content.get('description', '')[:40]}")

    return backend, skill


def part2_context_composition(backend, skill):
    """Part 2: Compose memory into a prompt context block."""
    print("\n" + "=" * 60)
    print("PART 2 -- Context Composer")
    print("=" * 60)

    # Retrieve records and compose them into a context block
    records = backend.search("summarize contract", domain="legal")
    mode = lk.determine_inference_mode(records)
    context = lk.compose_context(records, "Summarize this vendor agreement", mode)

    print(f"  Inference mode: {mode.value}")
    print(f"  Context length: {len(context)} chars")
    print("  Preview:")
    for line in context.split("\n")[:8]:
        print(f"    {line}")
    print("    ...")


def part3_trajectory_capture():
    """Part 3: Capture an execution trace (the learning signal)."""
    print("\n" + "=" * 60)
    print("PART 3 -- Trajectory Capture")
    print("=" * 60)

    traj = lk.Trajectory(task="Debug Python multiprocessing hang")
    traj.add_step("user", "My pool.map() hangs on macOS")
    traj.add_step(
        "assistant",
        "The default start method on macOS is 'spawn' since Python 3.8, "
        "but if you're using fork, it can deadlock with threads.",
        reasoning="Checked Python docs: fork is unsafe with threads on macOS. "
        "The multiprocessing module documentation recommends spawn.",
    )
    traj.add_step(
        "tool",
        "mp.set_start_method('spawn') -- pool now completes successfully",
        tool_name="python_executor",
    )
    traj.outcome = "success"
    traj.quality_score = 4.5

    # Save and reload
    save_path = Path("examples/demo_trajectory.jsonl")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    traj.save(save_path)
    loaded = lk.Trajectory.load(save_path)

    print(f"  [OK] Saved trajectory: {save_path}")
    print(f"  Steps: {len(loaded.steps)}")
    print(f"  Has CoT reasoning: {loaded.steps[1].reasoning is not None}")
    print(f"  Outcome: {loaded.outcome} (quality: {loaded.quality_score}/5)")

    # Clean up
    save_path.unlink()


def part4_skill_generation():
    """Part 4: Generate a SKILL.md from a SkillRecord."""
    print("\n" + "=" * 60)
    print("PART 4 -- Skill Document Generation")
    print("=" * 60)

    skill = lk.SkillRecord(
        domains={"coding": 0.95},
        task_type="debug_python_error",
        content={
            "steps": [
                "Read traceback bottom to top",
                "Reproduce with minimal test case",
                "Apply minimal fix",
                "Add regression test",
            ],
            "tools_used": ["pdb", "pytest"],
            "constraints": ["reproduce before fixing"],
            "failure_modes": ["fixing symptom not root cause"],
            "examples": {
                "good": "Root cause: fork on macOS. Fix: use spawn.",
                "bad": "Added try/except to suppress the error.",
            },
        },
        confidence=0.82,
    )

    md = skill.to_skill_md()
    print(md[:400])


def part5_full_loop():
    """Part 5: The full @lk.agent decorator loop (requires ANTHROPIC_API_KEY)."""
    import os

    print("\n" + "=" * 60)
    print("PART 5 -- Full Agent Loop (@lk.agent decorator)")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [SKIP] Set ANTHROPIC_API_KEY to run the full loop.")
        print("  Example:")
        print('    $env:ANTHROPIC_API_KEY = "sk-ant-..."')
        print("    python examples/quick_start.py")
        return

    # Initialize LearnKit with in-memory SQLite
    memory = lk.LearnKit(memory_backend="sqlite", db_path=":memory:")

    # Wrap any function as a learning agent
    @memory.agent(domain="coding")
    def my_agent(task: str, _learnkit_context: str = "") -> str:
        # In real usage, this calls your LLM (LangChain, OpenAI, etc.)
        # The _learnkit_context is injected automatically by LearnKit
        print(f"  Context injected: {len(_learnkit_context)} chars")
        return f"Agent solved: {task}"

    result = my_agent("Fix a Python multiprocessing deadlock on macOS")
    import time

    time.sleep(1)  # let background thread finish
    print(f"  Result: {result}")
    print(
        "  [OK] Full loop executed (classify -> retrieve -> compose -> run -> evaluate -> distill)"
    )


if __name__ == "__main__":
    print("LearnKit Quick Start Demo")
    print("=" * 60)

    backend, skill = part1_memory_store()
    part2_context_composition(backend, skill)
    part3_trajectory_capture()
    part4_skill_generation()
    part5_full_loop()

    print("\n" + "=" * 60)
    print("[DONE] Demo complete!")
    print()
    print("Next steps:")
    print("  * Run tests:       python -m pytest tests/ -v")
    print("  * Read the blueprint: agents.md")
    print("  * Browse skills:   skills/legal/ and skills/coding/")
    print("=" * 60)
