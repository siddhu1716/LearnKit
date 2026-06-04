import os
import sys
import re
import json
import argparse
from pathlib import Path
import subprocess
import time
from datasets import load_dataset
import litellm
import learnkit as lk
from learnkit.evaluator import Evaluator, EvaluationResult, EvaluationSignal

# ── Environment configuration ──────────────────────────────────────────────────
os.environ["OPENAI_API_BASE"] = "http://localhost:8001/v1"
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["LEARNKIT_DISTILLER_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"
os.environ["LEARNKIT_EVALUATOR_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"
os.environ["LEARNKIT_CLASSIFIER_MODEL"] = "openai/Qwen/Qwen2.5-72B-Instruct"

AGENT_MODEL = "openai/Qwen/Qwen2.5-72B-Instruct"
REPO_DIR = Path(__file__).parent / "pytest_repo"

# ── Git helpers ────────────────────────────────────────────────────────────────

def run_git_cmd(args: list[str]) -> str:
    """Run a git command in the pytest repository and return stdout."""
    res = subprocess.run(
        ["git", "-C", str(REPO_DIR)] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if res.returncode != 0:
        print(f"  Git command failed: git {' '.join(args)}\n  Error: {res.stderr.strip()}")
    return res.stdout


def get_modified_file(patch: str) -> str:
    """Parse the gold patch to get the first modified file path."""
    for line in patch.splitlines():
        if line.startswith("--- a/"):
            return line[6:]
    return ""


# ── File-windowing helper ──────────────────────────────────────────────────────

def _extract_keywords(problem: str, fail_to_pass: list[str]) -> list[str]:
    """Pull candidate function / class names from the problem and test IDs."""
    keywords = []
    # From test IDs: e.g. "test_foo_bar" → ["test_foo_bar", "foo_bar"]
    for test_id in fail_to_pass:
        # last part after "::" is the test function name
        parts = test_id.split("::")
        if parts:
            keywords.append(parts[-1])
    # From problem statement: grab all snake_case and CamelCase identifiers > 4 chars
    for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{4,}\b", problem):
        keywords.append(token)
    # deduplicate, keep order
    seen: set[str] = set()
    result = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result[:20]  # cap at 20


def window_file(content: str, problem: str, fail_to_pass: list[str], window: int = 80) -> str:
    """
    Return a focused slice of the file around the most relevant lines.

    Strategy:
    1. Search for lines containing keywords derived from the failing test name
       and problem statement.
    2. Take a ±window-line window around the best match.
    3. If nothing found, return the first 150 lines with a tail note.
    """
    lines = content.splitlines()
    total = len(lines)

    keywords = _extract_keywords(problem, fail_to_pass)

    # Score each line by how many keywords it contains
    best_line = -1
    best_score = 0
    for idx, line in enumerate(lines):
        score = sum(1 for kw in keywords if kw in line)
        if score > best_score:
            best_score = score
            best_line = idx

    if best_line == -1 or best_score == 0:
        # Fallback: first 150 lines
        excerpt = "\n".join(lines[:150])
        if total > 150:
            excerpt += f"\n\n[... {total - 150} more lines omitted — show full file if needed ...]"
        return excerpt

    start = max(0, best_line - window)
    end = min(total, best_line + window)

    parts = []
    if start > 0:
        parts.append(f"[... {start} lines above omitted ...]")
    parts.append("\n".join(f"{start + i + 1}: {l}" for i, l in enumerate(lines[start:end])))
    if end < total:
        parts.append(f"[... {total - end} lines below omitted ...]")

    return "\n".join(parts)


# ── Search-and-Replace applicator ─────────────────────────────────────────────

def apply_search_replace(file_content: str, response: str) -> str:
    """
    Apply Search-and-Replace blocks from the LLM response.

    Tries four strategies in order of decreasing strictness:
      A. Exact match of stripped text
      B. Exact match including original whitespace
      C. Normalised line-endings match
      D. Fuzzy line-based match (≥70 % lines must match)
    """
    # Strip line numbers if the model echoed them ("42: def foo():")
    def strip_line_numbers(block: str) -> str:
        return re.sub(r"^\s*\d+:\s", "", block, flags=re.MULTILINE)

    pattern = re.compile(
        r"<{7}.*?\n(.*?)\n={7}\n(.*?)\n>{7}", re.DOTALL
    )
    matches = pattern.findall(response)
    if not matches:
        # Relaxed: allow optional whitespace around markers
        pattern = re.compile(
            r"<{7}[^\n]*\s*(.*?)\s*={7}\s*(.*?)\s*>{7}", re.DOTALL
        )
        matches = pattern.findall(response)

    if not matches:
        print("  WARNING: No Search-and-Replace block found in response.")
        return file_content

    new_content = file_content
    for original_raw, replacement_raw in matches:
        original = strip_line_numbers(original_raw).strip()
        replacement = strip_line_numbers(replacement_raw).strip()

        # A — exact stripped match
        if original and original in new_content:
            new_content = new_content.replace(original, replacement, 1)
            print("  Applied: exact match.")
            continue

        # B — with original whitespace
        if original_raw in new_content:
            new_content = new_content.replace(original_raw, replacement_raw, 1)
            print("  Applied: exact-whitespace match.")
            continue

        # C — normalise line endings
        orig_nl = original.replace("\r\n", "\n")
        nc_nl = new_content.replace("\r\n", "\n")
        if orig_nl and orig_nl in nc_nl:
            new_content = nc_nl.replace(orig_nl, replacement.replace("\r\n", "\n"), 1)
            print("  Applied: normalised line-endings match.")
            continue

        # D — fuzzy line-based match
        orig_lines = [l.strip() for l in original.splitlines() if l.strip()]
        if not orig_lines:
            continue

        file_lines = new_content.splitlines()
        n = len(orig_lines)
        best_start, best_hits = -1, 0

        for idx in range(len(file_lines) - n + 1):
            hits = sum(
                1 for j in range(n)
                if (
                    orig_lines[j] == file_lines[idx + j].strip()
                    or orig_lines[j] in file_lines[idx + j]
                    or file_lines[idx + j].strip() in orig_lines[j]
                )
            )
            if hits > best_hits:
                best_hits, best_start = hits, idx

        if best_hits > 0 and (best_hits / n) >= 0.70:
            print(f"  Applied: fuzzy match ({best_hits}/{n} lines).")
            new_lines = (
                file_lines[:best_start]
                + replacement.splitlines()
                + file_lines[best_start + n:]
            )
            new_content = "\n".join(new_lines)
        else:
            print("  WARNING: ORIGINAL block not found in file (fuzzy match failed).")

    return new_content


# ── LLM helpers ───────────────────────────────────────────────────────────────

# Concrete worked example kept OUT of the bracket-style to avoid the model
# copying placeholder text literally.
_FORMAT_EXAMPLE = """
Here is an example of the correct format:

<<<<<<< ORIGINAL
    return x + y
=======
    return x + y + z
>>>>>>> SUGGESTED

Rules:
- The ORIGINAL block must match the file content character-for-character (use the line numbers shown in the file excerpt to copy exact text).
- Output ONLY the search-and-replace block — no explanations, no surrounding prose.
- If you need to make multiple changes, output multiple blocks back-to-back.
""".strip()


def build_system_prompt(with_context: str = "") -> str:
    base = (
        "You are an expert Python software engineer specialising in debugging and patching open-source libraries.\n"
        "Your task: given an issue description, failing test names, and a file excerpt, produce a minimal patch "
        "that makes the failing tests pass without breaking any existing tests.\n\n"
        f"{_FORMAT_EXAMPLE}"
    )
    if with_context:
        base += f"\n\n{with_context}"
    return base


def build_user_prompt(problem: str, fail_to_pass: list[str], rel_path: str, file_excerpt: str) -> str:
    tests_block = "\n".join(f"  - {t}" for t in fail_to_pass)
    return (
        f"## Issue\n{problem}\n\n"
        f"## Tests that MUST pass after your fix\n{tests_block}\n\n"
        f"## File to patch: {rel_path}\n"
        f"(Line numbers are shown for reference — do NOT include them in the ORIGINAL block.)\n\n"
        f"{file_excerpt}\n\n"
        "Now output the search-and-replace patch:"
    )


def call_agent(system: str, user: str) -> str:
    """Call the local Qwen model."""
    try:
        r = litellm.completion(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        return r.choices[0].message.content or ""
    except Exception as e:
        print(f"  Error calling agent: {e}")
        return ""


def evaluate_patch_llm(problem: str, rel_path: str, agent_patch: str, gold_patch: str) -> float:
    """Score the agent patch against the gold patch using local Qwen as judge."""
    system = (
        "You are an expert code reviewer. Compare the agent's proposed patch with the gold patch. "
        "Give a score 1.0–5.0: 5.0 = semantically equivalent and correct, 1.0 = completely wrong. "
        "Reply with a single number only."
    )
    user = (
        f"ISSUE:\n{problem}\n\n"
        f"FILE: {rel_path}\n\n"
        f"GOLD PATCH:\n{gold_patch}\n\n"
        f"AGENT PATCH:\n{agent_patch if agent_patch else '(empty — no change made)'}\n\n"
        "Score:"
    )
    try:
        r = litellm.completion(
            model=AGENT_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.0,
            max_tokens=10,
        )
        content = r.choices[0].message.content or "1.0"
        m = re.search(r"\b([1-5](?:\.\d+)?)\b", content)
        return float(m.group(1)) if m else 1.0
    except Exception as e:
        print(f"  Error calling judge: {e}")
        return 1.0


# ── Custom LearnKit Evaluator ─────────────────────────────────────────────────

class GoldPatchEvaluator(Evaluator):
    """Evaluates agent patches against the gold patch via LLM judge."""

    def __init__(self):
        super().__init__()
        self.problem_statement: str = ""
        self.rel_path: str = ""
        self.gold_patch: str = ""
        self.agent_patch: str = ""

    def evaluate_with_llm_judge(
        self, task: str, response: str, reasoning_trace: str = None, lm=None
    ) -> EvaluationResult:
        score = evaluate_patch_llm(
            self.problem_statement, self.rel_path, self.agent_patch, self.gold_patch
        )
        return EvaluationResult(
            score=score,
            signal=EvaluationSignal.LLM_JUDGE,
            reasoning=f"LLM judge score vs gold patch: {score}/5.0",
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=["control", "treatment"], default="control")
    parser.add_argument("--limit", type=int, default=17)
    args = parser.parse_args()

    print("Loading SWE-bench Lite dataset...")
    dataset = load_dataset("swe-bench/SWE-bench_Lite", split="test")
    pytest_tasks = [t for t in dataset if t["repo"] == "pytest-dev/pytest"]
    pytest_tasks.sort(key=lambda t: t["instance_id"])
    pytest_tasks = pytest_tasks[: args.limit]
    print(f"Loaded {len(pytest_tasks)} pytest tasks  [arm={args.arm}]")

    evaluator = GoldPatchEvaluator()

    # ── Treatment arm: wrap with LearnKit memory ──────────────────────────────
    memory = None
    if args.arm == "treatment":
        db_path = Path(__file__).parent / "learnkit_swebench_pytest.db"
        if db_path.exists():
            db_path.unlink()
        memory = lk.LearnKit(
            memory_backend="sqlite",
            db_path=str(db_path),
            scope="user",
            evaluator=evaluator,
            background_postprocess=False,
        )

        @memory.agent(domain="swe_pytest")
        def ask(
            problem: str,
            fail_to_pass: list[str],
            rel_path: str,
            file_excerpt: str,
            file_path_obj: Path,
            original_content: str,
            _learnkit_context: str = "",
        ) -> str:
            system = build_system_prompt(with_context=_learnkit_context)
            user = build_user_prompt(problem, fail_to_pass, rel_path, file_excerpt)
            response = call_agent(system, user)
            new_content = apply_search_replace(original_content, response)
            file_path_obj.write_text(new_content, encoding="utf-8")
            diff = run_git_cmd(["diff", rel_path])
            memory.evaluator.agent_patch = diff
            return response

    else:
        def ask(
            problem: str,
            fail_to_pass: list[str],
            rel_path: str,
            file_excerpt: str,
            file_path_obj: Path,
            original_content: str,
        ) -> str:
            system = build_system_prompt()
            user = build_user_prompt(problem, fail_to_pass, rel_path, file_excerpt)
            response = call_agent(system, user)
            new_content = apply_search_replace(original_content, response)
            file_path_obj.write_text(new_content, encoding="utf-8")
            return run_git_cmd(["diff", rel_path])

    predictions = []

    for i, task in enumerate(pytest_tasks, 1):
        instance_id = task["instance_id"]
        base_commit = task["base_commit"]
        problem = task["problem_statement"]
        gold_patch = task["patch"]
        fail_to_pass: list[str] = json.loads(task.get("FAIL_TO_PASS", "[]"))

        rel_path = get_modified_file(gold_patch)
        if not rel_path:
            print(f"\n[{i:2d}/{len(pytest_tasks)}] SKIP {instance_id}: no file parsed from gold patch.")
            continue

        print(f"\n[{i:2d}/{len(pytest_tasks)}] {instance_id}")
        print(f"  file  : {rel_path}")
        print(f"  commit: {base_commit[:8]}")
        print(f"  tests : {fail_to_pass[:2]}{'...' if len(fail_to_pass) > 2 else ''}")

        # Checkout and reset to base commit
        run_git_cmd(["checkout", "-f", base_commit])
        run_git_cmd(["clean", "-fdx"])

        file_path = REPO_DIR / rel_path
        if not file_path.exists():
            print(f"  ERROR: {rel_path} not found at base commit.")
            continue

        original_content = file_path.read_text(encoding="utf-8", errors="ignore")

        # Window the file to keep context tight
        file_excerpt = window_file(original_content, problem, fail_to_pass, window=80)
        excerpt_lines = file_excerpt.count("\n") + 1
        total_lines = original_content.count("\n") + 1
        print(f"  context: {excerpt_lines} lines shown / {total_lines} total")

        if args.arm == "treatment":
            evaluator.problem_statement = problem
            evaluator.rel_path = rel_path
            evaluator.gold_patch = gold_patch
            ask(problem, fail_to_pass, rel_path, file_excerpt, file_path, original_content)
            agent_diff = evaluator.agent_patch
            score = memory.last_trajectory.quality_score if memory.last_trajectory else 0.0
        else:
            agent_diff = ask(problem, fail_to_pass, rel_path, file_excerpt, file_path, original_content)
            score = evaluate_patch_llm(problem, rel_path, agent_diff, gold_patch)

        print(f"  judge : {score}/5.0  |  patch lines: {len(agent_diff.splitlines())}")

        predictions.append({
            "model_name_or_path": f"learnkit_{args.arm}",
            "instance_id": instance_id,
            "model_patch": agent_diff,
        })

        # Reset the modified file
        run_git_cmd(["checkout", "-f", rel_path])

    if memory:
        memory.shutdown(wait=True)

    out_file = Path(__file__).parent / f"predictions_{args.arm}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p) + "\n")

    non_empty = sum(1 for p in predictions if p["model_patch"])
    print(f"\n{'─'*60}")
    print(f"Done [{args.arm}]  {len(predictions)} tasks  |  {non_empty} non-empty patches")
    print(f"Saved: {out_file}")


if __name__ == "__main__":
    main()
