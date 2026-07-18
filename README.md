# LearnKit

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/siddhu1716/LearnKit)

> **🚀 Live Pre-Release on PyPI!**
> LearnKit is installable via PyPI as `learnkit-ai`. It provides the complete experience-distillation layer for Python AI agents. Let your agents compound knowledge dynamically!

---

# Stop Re-Planning the Same Task

LearnKit is an **agent-agnostic SDK** that makes tool-using AI agents **learn from experience**. It captures the tool-call *procedure* an agent uses to solve a task, then:

- **replays it on exact repeats with zero planning/LLM calls**, and
- **guides sibling tasks with a distilled playbook** so the model follows the proven shape instead of re-exploring.

The expensive, compressible part of a tool-using agent isn't the answer text — it's the **planning loop** (the back-and-forth LLM calls to decide which tools to call in what order). That plan is normally thrown away after every task. LearnKit keeps it, quality-gates it on the **real tool outcome** (not a fragile LLM judge), and reuses it.

**Reproducible result (agentic matrix, 3/3 models PASS, equal task success):**

> **+2.25 best quality lift · −38.4% pooled LLM planning calls** on Qwen2.5-14B/32B and Llama-3.3-70B.

Memory is **typed**, **quality-gated**, **attributed** (help/harm/reuse per record), and **lifecycle-managed** (confidence decay, quarantine → promote, TTL) — auditable, deletable JSON, no model retraining.

---

## Where this fits — procedural memory, not caching or hand-written skills

LearnKit adds **procedural memory** (how to do a task) — distinct from the
semantic/episodic memory that Mem0, Zep, and vector stores provide (facts and past
conversations).

- **Not plan caching.** Plan caching keys a whole plan and trades accuracy for cost.
  LearnKit does *workflow induction*: hard-replay only on an **exact** match (zero
  LLM), and *guide* sibling tasks (the model still plans) — never a fuzzy replay
  that could silently produce the wrong result. Success holds; it doesn't degrade.
- **Not hand-written Skills.** LangChain / Deep Agents Skills are procedural memory
  too, but you author and maintain each one by hand. LearnKit **auto-induces**
  procedures from real successful runs, quality-gates them on the tool outcome,
  tracks help/harm, and decays the stale ones — and it's framework-agnostic. It
  even exports a Deep Agents-compatible library:
  `learnkit skills export --format deepagents`.

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

To install from PyPI (recommended):

```bash
pip install learnkit-ai
# Or with integration extras:
pip install "learnkit-ai[langchain]"
```

To install from local repo root:

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
python examples/agent_learn_demo.py
```

A runnable, **offline** (no API key) demo of the cold→warm capture-and-replay
loop: on first exposure the agent explores and LearnKit captures the productive
tool procedure; on repeats it replays that procedure with zero planning calls.

---

# Wrap your agent — the agent path (`@memory.agent_learn`)

```python
import learnkit as lk

memory = lk.LearnKit(memory_backend="sqlite", scope="team")

@memory.agent_learn(domain="pipeline")
def my_tool_agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
    # Record every tool call so LearnKit can learn / replay the productive procedure.
    rows = _learnkit_tools.record("query", {"table": "users"}, run_query("users"))
    _learnkit_tools.record("format", {"fmt": "csv"}, to_csv(rows))
    return "report ready"

# Same task, called twice — run 2 replays run 1's captured procedure (zero planning calls).
my_tool_agent("Build an active-user CSV report")
my_tool_agent("Build an active-user CSV report")
```

Valid `scope` values: `"user"`, `"team"`, `"public"` (see `learnkit/schemas/base.py`).

## Auto-replay — zero-wiring reuse (`run_react_agent`)

Don't want to hand-check `has_plan`/`plan_steps`? Use the built-in ReAct runner.
It prepares the run, retrieves any matching procedure, **auto-replays exact
matches with zero planning calls**, and otherwise drives your planner while
capturing the trajectory:

```python
from learnkit import run_react_agent, LLMStep, ToolCall

def planner(task, context, history):
    # One planning turn. Return tool calls to make, and/or a final answer.
    # `context` already contains playbook guidance for sibling tasks.
    ...
    return LLMStep(tool_calls=[ToolCall("query", {"table": "users"})], final=None)

result = run_react_agent(memory, task, tools, planner, exploration_tools={"list_tables"})
print(result.replayed, result.llm_calls, result.tool_calls)  # True 0 3  on an exact repeat
```

This path supports exact replay (zero-LLM for exact re-encounters) and guided
sibling reuse. A runnable, offline demo (no API key) lives at
[`examples/agent_learn_demo.py`](examples/agent_learn_demo.py). See
`benchmarks/injection_ablation.py` for a quality-focused ablation that isolates
the effect of playbook injection on novel sibling tasks.

---

# Integrate with LangChain (and others)

LangChain, LangGraph, AutoGen, CrewAI, LlamaIndex, and the OpenAI Agents SDK are
all supported through the universal adapter contract described in **Framework
integrations** below. Each adapter captures tool calls onto the run so the agent
path learns and replays procedures with no change to your agent logic.

---

# Framework integrations

LearnKit is framework-agnostic. Every integration subclasses one universal
contract (`learnkit.adapters.BaseAdapter`), so they all expose the same
two-path API — `start_run` → inject memory, `complete_run` → distill the
outcome — and an exception-safe `session()` / `asession()` lifecycle.

| Framework | Adapter | Install | Native hook |
|---|---|---|---|
| LangChain | `LangChainAdapter` | `learnkit-ai[langchain]` | `LearnKitCallbackHandler` (`BaseCallbackHandler`) |
| LangGraph | `LangGraphAdapter` | `learnkit-ai[langgraph]` | `as_node()` graph node |
| AutoGen / AG2 | `AutoGenAdapter` | `learnkit-ai[autogen]` | `inject()` system-message + `ChatResult` capture |
| CrewAI | `CrewAIAdapter` | `learnkit-ai[crewai]` | `step_callback()` (`AgentAction`) |
| LlamaIndex | `LlamaIndexAdapter` | `learnkit-ai[llamaindex]` | `LearnKitLlamaHandler` (`FUNCTION_CALL` events) |
| OpenAI Agents SDK | `OpenAIAgentsAdapter` | `learnkit-ai[openai-agents]` | `LearnKitRunHooks` (`RunHooks`) |
| Raw OpenAI / Anthropic | `OpenAIRawAdapter` | core | wraps the chat call |

```python
from learnkit import LearnKit
from learnkit.adapters import get_adapter

lk = LearnKit(memory_backend="sqlite")
adapter = get_adapter("crewai")(lk)        # resolve any adapter by name

with adapter.session(task) as run:          # exception-safe lifecycle
    tools = adapter.wrap_tools(run, tools)  # agent path: capture tool calls
    run.response = my_agent(run.context, tools)
```

Any third-party package can register its own adapter without a PR — declare a
`learnkit.adapters` entry point and LearnKit discovers it lazily via
`get_adapter(name)` / `available_adapters()`.

### Offline mode (no API key)

When no LLM provider key is set, LearnKit runs **keyless**: task classification
falls back to a deterministic heuristic instead of a network call, so the agent
path and the deterministic benchmarks run with zero credentials and zero
latency. Force it explicitly with `LEARNKIT_OFFLINE=1`; it is auto-detected
otherwise (no provider key and no `LEARNKIT_CLASSIFIER_MODEL` override).

---

# How it works — the 8-step loop

The agent function never changes. The decorator orchestrates everything around it.

1. User calls your wrapped agent with a task.
2. **Classify** — `TaskClassifier` returns a domain vector, e.g. `{"Python": 0.9, "Concurrency": 0.7}`.
3. **Retrieve** — `SemanticRetriever` pulls relevant records (FTS5 lexical + optional dense rerank), filtered by `domain` and `scope`.
4. **Compose** — `compose_context` formats records into a bounded prompt block (≤ 8 records, ≤ 1,200 tokens, inference mode = `PRESCRIPTIVE` / `GUIDED` / `EXPLORATORY` based on top-record confidence).
5. **Run** — your function executes with `_learnkit_context` injected as a kwarg.
6. **Evaluate** — on the agent path the outcome is gated on the **real tool success** (`ToolTracker.outcome_score()`), not a fragile LLM judge; an optional judge scores 0–5 when no tool signal is available.
7. **Distill** — a passing run captures the cleaned productive tool sequence into a procedural `SkillRecord` (`procedure` / `tool_sequence` / `trigger`) for replay, plus optional facts/failures. Below threshold, a `FailureRecord` is stored directly so future runs avoid the same path.
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
| [`Docs/learnkit_architecture.md`](Docs/learnkit_architecture.md) | …you need the full mechanism diagrams and the agent-path runtime flow. |
| [`architecture/`](architecture/) | …you want the Mermaid diagrams (product map, agent runtime flow, storage lifecycle, benchmark flow). |

Run the test suite:

```bash
pytest tests/ -q       # 167 passed, 1 xfailed
```

Pre-commit hooks (black / ruff / isort / whitespace / yaml / debug-statements) are enforced on commit:

```bash
pip install pre-commit
pre-commit install
```

---

# Status

**v0.0.2 — MVP handover-ready (2026-06-27).** The full ingest / query / maintain
loop runs end-to-end with SQLite + FTS5 + DSPy classifier + LLM-judge
evaluator + structured distiller, and includes an agentic procedural-learning
path (`@memory.agent_learn`) with replay and guided sibling reuse. Published
and installable from PyPI as `learnkit-ai`.

Supported MVP lane (verified end-to-end): self-hosted Qwen via sglang —
`Qwen/Qwen2.5-Coder-32B-Instruct`, `Qwen/Qwen2.5-32B-Instruct`,
`Qwen/Qwen2.5-14B-Instruct`. See
[`improvements.md` → MVP Handover Snapshot](improvements.md) for the
supported environment table, known limitations, and the handover checklist.

Latest published benchmark numbers (Qwen2.5-7B-Instruct reference,
2026-06-21):

- Live ReAct ([`benchmarks/react_live.py`](benchmarks/react_live.py)): LLM
  planning calls 21 → 8 (~62% reduction), success preserved 6/6 → 6/6.
- Evolution ([`benchmarks/evolution_live.py`](benchmarks/evolution_live.py)):
  LLM calls 58 → 20 (~66% reduction), success preserved 16/16 → 16/16,
  evolved=true.
- Injection ablation
  ([`benchmarks/injection_ablation.py`](benchmarks/injection_ablation.py)):
  `playbook_effect = +2.625`, `pass^k(full) = 1.0`; the agentic suite gate
  (`min_playbook_effect >= 0.5`) PASSES.

Cross-model matrix (same seed/tasks):
[`Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`](Docs/FINAL_MODEL_MATRIX_2026-06-21.txt).
Single-model published numbers:
[`Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt`](Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt).

See [`benchmarks/README.md`](benchmarks/README.md) for benchmark coverage,
run commands, and how to point benchmark runs at the live observability
dashboard via `LEARNKIT_DB_PATH`.
