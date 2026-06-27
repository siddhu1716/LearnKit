# LearnKit

> **🚀 Live Pre-Release on PyPI!**
> LearnKit is installable via PyPI as `learnkit-ai`. It provides the complete experience-distillation layer for Python AI agents. Let your agents compound knowledge dynamically!

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

LearnKit now supports two learning paths:

- `@memory.learn` / `@memory.agent` (model path): retrieves distilled context and injects `_learnkit_context`.
- `@memory.agent_learn` (tool-using path): captures tool trajectories via `_learnkit_tools`, stores procedural skills, replays exact matches, and guides sibling tasks.

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

## Tool-using agents (`@memory.agent_learn`)

For agents that call tools, use the procedural path:

```python
import learnkit as lk

memory = lk.LearnKit(memory_backend="sqlite", scope="team")

@memory.agent_learn(domain="pipeline")
def my_tool_agent(task: str, _learnkit_context: str = "", _learnkit_tools=None) -> str:
    # Record every tool call so LearnKit can learn/replay the productive procedure.
    rows = _learnkit_tools.record("query", {"table": "users"}, "rows")
    _learnkit_tools.record("format", {"fmt": "csv"}, "done")
    return "report ready"
```

This path supports exact replay (zero-LLM for exact re-encounters) and guided sibling reuse.

A runnable, offline demo of the cold→warm capture-and-replay loop (no API key) lives at [`examples/agent_learn_demo.py`](examples/agent_learn_demo.py). See `benchmarks/injection_ablation.py` for a quality-focused ablation that isolates the effect of playbook injection on novel sibling tasks.

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
| [`Docs/learnkit_architecture.md`](Docs/learnkit_architecture.md) | …you need the full mechanism diagrams and the agent-path runtime flow. |
| [`improvements.md`](improvements.md) | …you are picking up the next pending enhancement or want the MVP handover snapshot. |
| [`Docs/LEARNKIT_CONSOLIDATED_FLOW_PLAN.md`](Docs/LEARNKIT_CONSOLIDATED_FLOW_PLAN.md) | …you want the consolidated execution-flow document (roadmap, backlog, benchmark gates). |

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
