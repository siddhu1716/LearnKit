# LearnKit

> **Work In Progress: Pre-Release Concept**
> LearnKit is currently in active development. This repository serves as the architectural blueprint and conceptual overview of what we are building. The code is not yet released for production use.

---

# Fine-Tuning Without Fine-Tuning

LearnKit is an **agent-agnostic SDK** that gives any AI agent a **self-improving memory layer**.

Most agents today suffer from **amnesia** or rely on **naive memory** (storing endless raw chat logs). This creates:

- “Memory soup”
- Exploding context windows
- No signal on whether a past action was actually successful

LearnKit replaces raw chat logs with **Experience Distillation**.

Every time your agent runs, LearnKit:

1. Evaluates the execution trace
2. Extracts what worked (and what failed)
3. Compiles reusable structured memory artifacts

Over time, the agent builds a compounding **“wiki” of expertise** — without retraining the underlying model.

---

# Core Philosophy

LearnKit treats agent memory like a curated wiki operating across three continuous loops:

## 1. Ingest (The Distiller)

After a task completes, LearnKit analyzes the agent’s Chain-of-Thought (CoT).

- Successful traces → distilled into reusable `SkillRecord`
- Failed traces → converted into `FailureRecord`
- Prevents agents from repeating known mistakes

## 2. Query (The Retriever)

Before a task begins:

- LearnKit classifies the domain and task type
- Retrieves high-confidence relevant memories
- Injects only the most useful context

## 3. Maintain (The Evolver)

Memory is continuously optimized:

- Unused records decay over time
- High-value skills evolve automatically
- GEPA-based prompt mutation discovers better strategies

---

# Install

LearnKit targets **Python 3.11+**. From the repo root:

```bash
pip install -e .                    # core SDK
pip install -e ".[langchain]"       # adds LangChain + langchain-anthropic
pip install -e ".[dev]"             # pytest + pytest-asyncio
```

Other optional extras: `mem0`, `zep`, `qdrant`.

Set your Anthropic key once (PowerShell, persists across sessions):

```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

On bash/zsh: `export ANTHROPIC_API_KEY=sk-ant-...` in your shell rc.

---

# 60-second Quick Start

```bash
python examples/quick_start.py
```

Walks through 5 parts that exercise the whole SDK:

| Part | Demonstrates | Needs API key? |
|---|---|---|
| 1 | SQLite + FTS5 memory store: add / search / failure record | No |
| 2 | Context composer: 1,200-token bounded block, inference-mode selection | No |
| 3 | Trajectory capture: steps, CoT reasoning, quality score | No |
| 4 | `SkillRecord.to_skill_md()` document generation | No |
| 5 | Full `@lk.agent` loop: classify → retrieve → compose → run → evaluate → distill | **Yes** |

---

# Wrap your agent — 5 lines

```python
import learnkit as lk

memory = lk.LearnKit(memory_backend="sqlite", scope="user")

@memory.agent(domain="coding")
def my_agent(task: str, _learnkit_context: str = "") -> str:
    # _learnkit_context is injected by the decorator on every call.
    # Splice it into your prompt however your framework expects.
    return call_your_llm(prompt=task, system=_learnkit_context)

# Same task, called twice — run 2 sees what run 1 distilled.
my_agent("Debug a Python multiprocessing deadlock on macOS")
my_agent("Debug a Python multiprocessing deadlock on macOS")
```

Valid `scope` values: `"user"`, `"team"`, `"public"` (see `learnkit/schemas/base.py`).

---

# Integrate with LangChain

A runnable end-to-end demo lives at [`examples/langchain_demo.py`](examples/langchain_demo.py). It wraps a real LangChain 1.x tool-calling agent (`create_agent` + `ChatAnthropic` + two tools) with `@memory.agent`, then runs the same task twice against a file-backed SQLite store:

```text
RUN 1 (cold memory):    [LearnKit] Context injected:   0 chars
RUN 2 (warm memory):    [LearnKit] Context injected: 610 chars
```

Run 2's answer is qualitatively richer because the skill, facts, and failures distilled from run 1's trajectory get retrieved and spliced into the system prompt. The demo uses `background_postprocess=False` so distillation runs synchronously and the second call is guaranteed to see the first call's output — drop that flag for production.

To run it yourself:

```bash
pip install -e ".[langchain]"
python examples/langchain_demo.py
```

---

# How it works — the 8-step loop

The agent function never changes. The decorator orchestrates everything around it.

1. User calls your wrapped agent with a task.
2. **Classify** — `TaskClassifier` returns a domain vector, e.g. `{"Python": 0.9, "Concurrency": 0.7}`.
3. **Retrieve** — `SemanticRetriever` pulls relevant records (FTS5 lexical + optional dense rerank), filtered by `domain` and `scope`.
4. **Compose** — `compose_context` formats records into a bounded prompt block (≤ 8 records, ≤ 1,200 tokens, inference mode = `PRESCRIPTIVE` / `GUIDED` / `EXPLORATORY` based on top-record confidence).
5. **Run** — your function executes with `_learnkit_context` injected as a kwarg.
6. **Evaluate** — `Evaluator.evaluate_with_llm_judge` scores the response 0–5.
7. **Distill** — if score ≥ `quality_threshold` (default 3.5), `MemoryDistiller` emits new `SkillRecord` / `FactRecord` / `FailureRecord` / `TraceRecord`. Below threshold, a `FailureRecord` is stored directly so future runs avoid the same path.
8. **Persist** — records are written via the active backend; the trajectory is registered against a per-run ID for inspection.

---

# Memory model

LearnKit stores seven typed record kinds (`learnkit/schemas/`):

| Record | Activates as | Notes |
|---|---|---|
| `SkillRecord` | `quarantine` | Promoted to `active` after the configured probation window |
| `FactRecord` | `quarantine` | Same probation as skills |
| `FailureRecord` | `active` immediately | Per ReaComp — agents must avoid known dead ends as fast as possible |
| `StrategyRecord` | `quarantine` | Higher-level approaches |
| `PreferenceRecord` | `quarantine` | User / team preferences |
| `TraceRecord` | `active` | Raw execution trace for replay |
| `HeuristicRecord` | `quarantine` | Domain heuristics |

Bounded memory is enforced at retrieval: the router caps results at **8 records / ~1,200 tokens** before the composer formats them.

---

# Maintenance

Call `memory.maintain_memory()` periodically (cron, background job, etc.):

```python
memory.maintain_memory(weeks=1, decay_rate=0.02, quarantine_hours=24)
# → {"decayed": N, "stale": M, "promoted": K}
```

- **Decay**: every active/stale record loses `decay_rate` confidence per `weeks` elapsed.
- **Stale**: records past `expires_at` get marked `stale` and excluded from retrieval.
- **Promote**: quarantined records older than `quarantine_hours` are promoted to `active`.

---

# Architecture & contributing

| File | Read when… |
|---|---|
| [`agents.md`](agents.md) | …you are writing or reviewing code. It is the strict architectural blueprint and rulebook. |
| [`AGENTS_V2.md`](AGENTS_V2.md) | …you are on the production hardening branch (`lk_v0.0.1`) — lists hardening tasks, ship checklist, integration test plan. |
| [`improvements.md`](improvements.md) | …you are picking up the next pending enhancement. |

Run the test suite:

```bash
pytest tests/ -q       # 33 passing, ~1s
```

Pre-commit hooks (black / ruff / isort / whitespace / yaml / debug-statements) are enforced on commit:

```bash
pip install pre-commit
pre-commit install
```

---

# Status

**v0.1.0 — MVP.** The full ingest / query / maintain loop runs end-to-end with SQLite + FTS5 + DSPy classifier + LLM-judge evaluator + structured distiller. See [`AGENTS_V2.md`](AGENTS_V2.md) for the production hardening plan and [`improvements.md`](improvements.md) for the open backlog.
