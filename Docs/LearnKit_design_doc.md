# LearnKit SDK — Design Document
## Incorporating Hermes Agent + ReaComp

**Version:** 1.0 | **Date:** May 2026
**For:** ML engineers and SDK contributors

---

## Executive Summary

This document maps the exact components, patterns, and concepts from two research projects — **Hermes Agent** (NousResearch, Feb 2026) and **ReaComp** (CMU, May 2026) — that LearnKit should incorporate. Both solve adjacent problems to ours. Neither is what we are building. This document identifies what is worth borrowing, what needs to be modified, and what we deliberately leave out.

---

## The Two Sources — What Each Does

### Hermes Agent (NousResearch)
**Repo:** github.com/NousResearch/hermes-agent
**Stars:** 163K (fastest-growing open-source agent framework of 2026)
**Tagline:** "The agent that grows with you"

Hermes is a **complete agent framework** — not just a memory system. It solves the persistence problem for one specific runtime (its own). It cannot be used as a library. Its key internals are:

- `MemoryStore` in `tools/memory_tool.py` — add/replace/remove/read ops on a curated markdown file
- `skills/` system — SKILL.md procedure documents stored under `~/.hermes/skills/`
- `session_search` — SQLite FTS5 full-text search across all past session transcripts
- `ContextCompressor` in `agent/context_compressor.py` — manages what enters the context window
- `agent/trajectory.py` — saves JSONL trajectory files per run
- `agent/prompt_builder.py` — structured prompt construction with memory injection
- GEPA (`hermes-agent-self-evolution`, ICLR 2026) — DSPy + genetic evolution of skills and prompts
- `BatchRunner` — parallel trajectory generation for RL training
- RL environments — Atropos integration

**What Hermes does NOT have:**
Multi-backend memory adapters, typed memory (facts vs skills vs failures), confidence scoring, TTL/expiry, cross-agent skill sharing, privacy scoping, or a public API. All learning is locked to its own runtime.

---

### ReaComp (Carnegie Mellon University)
**Repo:** github.com/cmu-llab/ReaComp
**Paper:** arXiv 2605.05485
**Tagline:** "Compiling LLM reasoning into symbolic solvers"

ReaComp is a **research paper** demonstrating that ~100 LLM reasoning traces can be compiled by a coding agent into a standalone Python solver that runs at zero LLM cost. Key results:

- Symbolic solver ensemble: 84.7% accuracy on hard tasks, zero per-task LLM calls
- 78% token reduction via hybrid (solver first, LLM fallback on failure)
- **Critical finding:** Removing CoT traces from induction collapses accuracy from 74.7% to 24.8% — a 50 percentage point drop. The reasoning trace IS the learning signal.
- Solvers transfer zero-shot to new domains (e.g., trained on ASCII → works on Unicode IPA linguistics data)
- Build cost amortizes over runs: a $0.85 solver recoups cost in 9 tasks; savings compound over 1,000+ tasks

**What ReaComp does NOT have:**
It's a research pipeline for program synthesis, not a general memory/learning SDK. The "solver" is Python code, not a memory record. But its core insight — compile traces into reusable logic, run that logic at zero LLM cost, fall back only on failure — is the most important thing we take from it.

---

## Mapping: What Goes Into LearnKit

### From Hermes — Exact Components to Borrow

#### 1. Memory tool operations pattern
**Source:** `tools/memory_tool.py`
**Hermes implementation:** Four atomic ops: `add`, `replace`, `remove`, `read` on a markdown file. The agent calls these as tools.

**What we take:** The four-operation interface is correct. Every memory backend (SQLite, Mem0, Qdrant) exposes the same four operations through a common adapter. Developers get a consistent interface regardless of backend.

```python
# LearnKit memory interface (borrowed from Hermes ops pattern)
memory.add(record)        # store new experience
memory.replace(id, record) # update existing record
memory.remove(id)         # delete (GDPR, TTL, manual)
memory.read(query)        # retrieve relevant records
```

**What we modify:** Hermes stores raw text in markdown. We store typed JSON records with confidence scores, TTL, and scope. The operation interface is the same; the data model is richer.

---

#### 2. Skills system — SKILL.md format
**Source:** `skills/` directory, `skills_list` and `skill_view` tools
**Hermes implementation:** Each skill is a structured markdown file with sections for what the skill does, when to use it, steps, and notes. 118 bundled skills. Stored under `~/.hermes/skills/`.

**What we take:** The skill document format is solid. We adopt the structured markdown schema and add JSON metadata alongside it:

```
skill_name/
  SKILL.md        # human-readable procedure (borrowed from Hermes)
  metadata.json   # machine-readable: confidence, reuse_count, TTL, domains
```

The markdown format means skills are readable and editable by humans. The JSON metadata enables automated scoring, retrieval ranking, and decay. Both files travel together.

**What we modify:** Hermes skills are private to one user's `~/.hermes/` directory. LearnKit skills have a `scope` field (`user | team | public`) and can be shared through the team registry. We also add `failure_modes` and `constraints` sections to the SKILL.md template.

---

#### 3. Session search — SQLite FTS5
**Source:** `gateway/session.py` (SessionStore), `session_search` toolset
**Hermes implementation:** SQLite database with FTS5 full-text search across all past session transcripts. The agent can explicitly search previous conversations with `session_search` tool.

**What we take:** FTS5 is exactly right for our execution trace store. Cheap, zero dependencies, works offline, full-text search across any text field. We use it as the backend for our Trace memory type.

```python
# SQLite FTS5 for trace retrieval (borrowed from Hermes session_search)
CREATE VIRTUAL TABLE traces USING fts5(
    task_type, strategy, tools_used, outcome_summary,
    failure_modes, created_at UNINDEXED
);
```

**What we add:** Hermes stores raw transcripts. We store distilled traces — compressed structured summaries, not raw messages. FTS5 on our trace schema retrieves relevant past strategies, not conversation history.

---

#### 4. Context compression
**Source:** `agent/context_compressor.py`
**Hermes implementation:** Hermes compresses conversation history when it approaches context limits. Uses LLM summarization to maintain key context while reducing token count.

**What we take:** The ContextCompressor pattern — periodically summarize and compress memory rather than truncating raw. We apply this to our context injection step: when retrieved records would exceed the token budget, the Context Composer summarizes them into a compact block rather than truncating arbitrarily.

**What we modify:** Hermes compresses conversation history. We compress the memory context block. Different target, same technique.

---

#### 5. Trajectory saving
**Source:** `agent/trajectory.py`, `save_trajectories` parameter
**Hermes implementation:** Saves JSONL trajectory files per agent run when `save_trajectories=True`. Used for RL training and batch generation.

**What we take:** The trajectory format and the `save_trajectories` opt-in pattern. Our Memory Distiller reads these JSONL files as its primary input. The format maps directly:

```jsonl
{"step": 1, "role": "user", "content": "..."}
{"step": 2, "role": "assistant", "content": "...", "tool_calls": [...]}
{"step": 3, "role": "tool", "content": "...", "tool_name": "web_search"}
{"outcome": "success", "quality": 4.2, "timestamp": "..."}
```

**What we add:** Hermes saves trajectories for RL training. We also use them for skill distillation. The trajectory is the raw material that our Memory Distiller processes into typed records.

---

#### 6. Prompt builder structure
**Source:** `agent/prompt_builder.py`
**Hermes implementation:** Builds the system prompt by assembling: base instructions + MEMORY.md content + USER.md content + relevant skills + session context.

**What we take:** The layered prompt construction pattern. Our Context Composer follows the same structure:

```
[Base agent instructions]
[LearnKit context block]
  → relevant skills (from Skill memory type)
  → known failures (from Failure memory type)
  → domain facts (from Fact memory type)
  → user preferences (from Preference memory type)
[Original task]
```

**What we modify:** Hermes injects memory before every prompt. We inject only relevant memory — retrieved by domain and task type. Our Memory Router gates what goes in.

---

#### 7. GEPA — self-evolution loop
**Source:** `hermes-agent-self-evolution` (separate MIT-licensed repo)
**What it does:** DSPy + Genetic-Pareto Prompt Evolution. Reads execution traces, understands WHY things fail, mutates skills and prompts, evaluates against benchmarks, keeps improvements. No GPU needed — all via API calls. ICLR 2026 Oral.

**What we take:** The full GEPA loop, as a periodic scheduled job on our skill library. Not inline during agent runs — run weekly or on-demand.

```bash
# Borrowed from hermes-agent-self-evolution, adapted for LearnKit
python -m learnkit.evolution.evolve_skills \
    --domain legal \
    --iterations 10 \
    --eval-source session_traces
```

**What we modify:** Hermes-GEPA evolves skills for the Hermes runtime. We evolve skills in our portable JSON schema that any agent can consume. The evolution target is the LearnKit skill registry, not a Hermes-specific skills directory.

---

#### 8. Toolset registration pattern
**Source:** `toolsets.py`, `tools/registry.py`
**Hermes implementation:** Named toolsets (groups of tools). `toolsets.py` defines presets. A central `registry.py` manages all tool definitions. Clean separation between "what tools exist" and "which tools are active for this run."

**What we take:** The same pattern for our memory backends. A central backend registry, named backend presets:

```python
# LearnKit backend registry (inspired by Hermes toolset registry)
BACKENDS = {
    "sqlite": SQLiteBackend,
    "mem0": Mem0Backend,
    "zep": ZepBackend,
    "qdrant": QdrantBackend,
    "supermemory": SupermemoryBackend,
}
```

---

### From ReaComp — Concepts to Borrow

#### 9. Two-stage inference: solver first, LLM fallback
**ReaComp insight:** Run the compiled symbolic solver first (zero LLM cost). If it succeeds (reward = 1.0), return immediately. Only fall back to the LLM if the solver fails or returns low-confidence output.

**What we take:** The exact same pattern, applied to memory-based context. Before calling the LLM:

1. Check if an existing skill has `success_rate > 0.90` for this exact task type → inject it directly and let the agent follow it mechanically (minimal LLM reasoning needed)
2. Check if a partial skill covers this task → inject + let LLM extend it
3. No relevant skill → full LLM reasoning, trace captured for future distillation

This is ReaComp's Pareto efficiency applied to memory: high-confidence skills amortize their creation cost over many future runs.

```python
# Two-stage inference (ReaComp pattern applied to LearnKit skills)
def compose_context(task, domain):
    exact_skill = memory.read(task_type=task, confidence_min=0.90)
    if exact_skill:
        return ContextMode.PRESCRIPTIVE   # follow the skill, minimal LLM reasoning
    partial_skill = memory.read(domain=domain, confidence_min=0.70)
    if partial_skill:
        return ContextMode.GUIDED         # skill as scaffold, LLM fills gaps
    return ContextMode.EXPLORATORY        # no skill, full LLM reasoning, capture trace
```

---

#### 10. Balanced trace collection — success AND failure
**ReaComp insight:** Sample traces balanced across difficulty and outcome (success and failure). Do not train only on successes.

**What we take:** Our Memory Distiller collects from both successful and failed runs. Failure traces produce Failure memory records — explicit warnings about dead ends. ReaComp proved this is load-bearing: removing failure context collapses performance.

Our quarantine policy also applies differently: successful traces distill immediately (after quality gate). Failed traces are stored as Failure records immediately — you want to know what failed as soon as possible.

---

#### 11. CoT traces are the learning signal
**ReaComp finding:** Removing chain-of-thought reasoning traces from solver induction drops accuracy from 74.7% to 24.8% on hard tasks — a 50 percentage point collapse. The reasoning trace is what the agent uses to understand the problem structure.

**What we take:** We must capture reasoning traces, not just tool calls and outputs. If the underlying model supports extended thinking (Claude, o3, Gemini 2.0 Flash Thinking), we capture the thinking trace, not just the final output.

For models without extended thinking, we instruct the agent to reason step-by-step in a `<reasoning>` block before responding. This reasoning block is captured in the trajectory and feeds the Memory Distiller.

```python
# Reasoning trace capture — critical per ReaComp finding
@lk.agent(capture_reasoning=True)
def my_agent(task):
    return agent.run(task)
# trajectory.reasoning_steps = [...] — always populated
```

---

#### 12. Ensemble diversity — multiple distillation runs
**ReaComp finding:** Three 100-example CoT runs span 51.8–74.7% accuracy on hard tasks — a 22.9 percentage point range. Ensembling diverse runs recovers most of this variance. Solver induction is a search over algorithmic space, not a data-scaling problem.

**What we take:** When GEPA evolves our skill library, run multiple evolution trials (3+) and ensemble the results. Different runs produce different skill variants. The skill registry stores all variants; the retriever scores and selects the best for each specific task.

This is why our skill schema has `evolution_gen` and versioning — each evolution run produces a new variant, not an overwrite.

---

#### 13. Zero-shot domain transfer
**ReaComp finding:** Solvers induced on ASCII program synthesis tasks transfer zero-shot to Unicode IPA historical linguistics data. The underlying reasoning structure generalizes.

**What we take:** Skills distilled in one domain may transfer to adjacent domains. Our multi-label domain scoring already enables this — a skill tagged `{"legal": 0.9}` can be retrieved at partial weight for a task tagged `{"legal": 0.6, "compliance": 0.8}`. The overlap drives retrieval; transfer happens automatically.

We also add a `transfer_domains` field to skills that have been successfully applied outside their primary domain, as a signal for future retrieval:

```json
{
  "domains": {"legal": 0.9},
  "transfer_domains": ["compliance", "finance"],
  "transfer_confidence": 0.65
}
```

---

#### 14. Build cost amortization framing
**ReaComp framing:** A $0.85 solver recoups its build cost after just 9 tasks. At 1,000 tasks, build cost is under 1% of total inference savings.

**What we take:** This is our pricing and positioning argument. Every skill extraction costs a few cents in API calls (Haiku-class model reading a trace). That skill then reduces LLM reasoning cost on every future similar task — potentially thousands of times.

```
Skill extraction cost:   ~$0.02 (one Haiku call on a trace)
Tasks before breakeven:  1 (if skill saves even one full LLM call)
Tasks at 1,000 runs:     build cost = 0.002% of savings
```

This is the quantitative case for why LearnKit pays for itself.

---

## What We Do NOT Take From Either

### From Hermes — deliberately excluded:
- **MEMORY.md / USER.md as primary store** — markdown flat files do not scale, cannot be queried semantically, have no TTL, and are not multi-backend. We replace this with typed JSON records in a queryable store.
- **CLI runtime binding** — Hermes SKILL.md files live at `~/.hermes/skills/`. LearnKit skills live in the memory backend, wherever that is. No filesystem coupling.
- **RL training harness** — BatchRunner, Atropos integration, trajectory-for-RL — these are Hermes-specific research infrastructure. LearnKit uses trajectories for memory distillation only, not RL training.
- **Messaging gateway** — Telegram, Discord, Slack adapters. Not our concern. LearnKit is middleware, not a user-facing product.
- **`skip_memory` as a flag** — Hermes disables memory for batch runs. In LearnKit, memory is always active but can be scoped. The design decision is different.

### From ReaComp — deliberately excluded:
- **Symbolic solver induction** — ReaComp compiles traces into actual Python code. That's a research capability for constrained DSLs (program synthesis, linguistics). Our use cases (legal, research, coding copilots) don't operate over constrained formal languages. We distill to structured JSON skill records, not code.
- **PBEBench / SLR-Bench benchmarks** — These are program synthesis benchmarks. We need domain-specific evals (legal, finance, code). We build our own per the VertexEval concept.
- **Prolog rule induction** — SLR-Bench specific. Out of scope.

---

## Combined Architecture — Hermes + ReaComp → LearnKit

```
                         ┌──────────────────────────────────┐
                         │         LEARNKIT SDK             │
                         └──────────────────────────────────┘

USER TASK
    │
    ▼
[Task Classifier]                     ← DSPy (from GEPA/hermes-self-evolution)
    │  multi-label domain vector
    ▼
[Memory Router]                       ← hard cap pattern (from Hermes bounded memory)
    │  retrieval plan, token budget
    ▼
[Semantic Retriever]                  ← SQLite FTS5 (from Hermes session_search)
    │  BM25 + dense vectors           ← hybrid retrieval
    │
    ├── confidence ≥ 0.90 → PRESCRIPTIVE mode ──────┐
    ├── confidence ≥ 0.70 → GUIDED mode ────────────┤   ← Two-stage (ReaComp)
    └── no match         → EXPLORATORY mode ─────────┤
                                                      │
                                                      ▼
[Context Composer]                    ← prompt_builder.py (Hermes)
    │  structured context block       ← layered injection (Hermes)
    ▼
[LLM Agent]     (any framework)
    │  +reasoning_steps captured      ← CoT capture (ReaComp finding)
    │
    ├──────────────────────────────┐
    ▼                              ▼
Response → User         [Trajectory Capture]   ← trajectory.py (Hermes)
                                   │            ← JSONL format (Hermes)
                                   ▼
                          [Evaluator]           ← quality gate, never bool
                                   │
                         quality ≥ threshold?
                                   │
                    ┌──────────────┴─────────────────┐
                    │ YES                             │ NO
                    ▼                                 ▼
           [Memory Distiller]              [Failure Records]  ← first-class (ReaComp)
           (DSPy, Haiku-class)             stored immediately
                    │
         ┌──────────┴──────────┐
         │                     │
      Skill                  Fact
      record                 record
     (SKILL.md               (JSON)
      + metadata)
         │
         └──────────────────────────────────────────────────┐
                                                            ▼
                                               [Memory Store]
                                               SQLite FTS5 (Hermes)
                                               + vector index
                                               + skill files (Hermes format)
                                               + typed records (our addition)
                                                            │
                                               [GEPA Evolution]  ← hermes-self-evolution
                                               scheduled weekly
                                               multiple runs → ensemble
                                               ← ensemble diversity (ReaComp)
```

---

## Implementation File Map

This maps each LearnKit module to its source inspiration:

| LearnKit file | Inspired by | Key borrowing |
|---|---|---|
| `learnkit/classifier.py` | GEPA / DSPy | DSPy typed Predict for multi-label classification |
| `learnkit/router.py` | Hermes bounded memory | Hard token cap, retrieval plan construction |
| `learnkit/retriever.py` | Hermes session_search | SQLite FTS5 + dense vector hybrid |
| `learnkit/composer.py` | Hermes prompt_builder.py | Layered prompt injection, per-type formatting |
| `learnkit/adapters/langchain.py` | Hermes toolsets.py | Toolset registration pattern |
| `learnkit/adapters/langgraph.py` | Hermes toolsets.py | Same pattern, LangGraph variant |
| `learnkit/trajectory.py` | Hermes trajectory.py | JSONL format, `save_trajectories` opt-in |
| `learnkit/evaluator.py` | New | Quality gate — no direct equivalent exists |
| `learnkit/distiller.py` | ReaComp solver induction | Trace → reusable artifact (concept only, impl differs) |
| `learnkit/distiller.py` | Hermes skills format | SKILL.md output format + metadata.json |
| `learnkit/compressor.py` | Hermes context_compressor.py | LLM summarization of memory block |
| `learnkit/evolution/gepa.py` | hermes-agent-self-evolution | DSPy + GEPA, MIT licensed |
| `learnkit/backends/sqlite.py` | Hermes session_search | SQLite FTS5 implementation |
| `learnkit/inference_mode.py` | ReaComp two-stage inference | PRESCRIPTIVE / GUIDED / EXPLORATORY |
| `learnkit/schemas/skill.py` | Hermes SKILL.md format | Extended with metadata.json fields |
| `learnkit/schemas/failure.py` | ReaComp balanced trace collection | Failure records as first-class citizens |

---

## Key Design Decisions Driven By This Research

### Decision 1 — Reasoning traces are mandatory, not optional
**Source:** ReaComp 50pp accuracy collapse without CoT traces.
**Decision:** LearnKit always captures reasoning steps if available. For models without native CoT, inject a reasoning prompt before the task. The `capture_reasoning=True` default is non-negotiable.

### Decision 2 — Skill format stays human-readable
**Source:** Hermes SKILL.md format.
**Decision:** Skills are stored as structured markdown + JSON sidecar. Markdown for humans to read and edit. JSON sidecar for automated scoring and retrieval. Both files are required.

### Decision 3 — Two-stage inference over single-mode retrieval
**Source:** ReaComp hybrid (solver first, LLM fallback).
**Decision:** Context injection mode is determined by skill confidence, not hardcoded. High-confidence skills trigger PRESCRIPTIVE mode (minimal LLM reasoning required). This reduces token cost and latency for well-learned task types.

### Decision 4 — Failure records stored immediately, no quarantine
**Source:** ReaComp balanced trace collection; Hermes failure analysis.
**Decision:** Successful skill records quarantine for 24 hours before becoming active. Failure records are stored and active immediately — you want agents to know what not to do as fast as possible. There is no quality gate on failure records (by definition they already failed).

### Decision 5 — Evolution is async and ensembled, never inline
**Source:** ReaComp run-to-run variance (22.9pp range across runs); GEPA architecture.
**Decision:** GEPA evolution runs weekly as a background job, never inline during agent execution. Multiple runs are launched in parallel; results are ensembled. Inline evolution would add latency and variance to agent responses.

---

## Priority Build Order

### Sprint 1 (weeks 1–4): Hermes-derived core
1. `trajectory.py` — JSONL capture, borrowing Hermes format exactly
2. `backends/sqlite.py` — FTS5 store, borrowing from Hermes session_search
3. `schemas/skill.py` — SKILL.md + metadata.json, extending Hermes format
4. `composer.py` — prompt injection, borrowing from Hermes prompt_builder pattern
5. `adapters/langchain.py` — toolset registration pattern from Hermes

### Sprint 2 (weeks 5–8): ReaComp-derived intelligence
6. `inference_mode.py` — two-stage (PRESCRIPTIVE / GUIDED / EXPLORATORY)
7. `classifier.py` — multi-label domain classification via DSPy
8. `distiller.py` — trace → typed records (ReaComp concept, our implementation)
9. `evaluator.py` — quality gate (new, no equivalent in either source)
10. `schemas/failure.py` — failure records, immediate activation

### Sprint 3 (weeks 9–12): Evolution + team
11. `evolution/gepa.py` — GEPA from hermes-self-evolution, MIT licensed
12. `router.py` — hard cap, retrieval plan
13. `compressor.py` — context compression from Hermes pattern
14. Team skill registry, scope enforcement, TTL

---

## References

- Hermes Agent: github.com/NousResearch/hermes-agent (MIT, 163K stars)
- GEPA / Self-evolution: github.com/NousResearch/hermes-agent-self-evolution (MIT, ICLR 2026 Oral)
- ReaComp: arxiv.org/abs/2605.05485 (CMU, May 2026)
- SkillClaw: companion project for auto-evolving Hermes skill libraries (MIT, 705 stars)
- MemSkill: arxiv.org/pdf/2602.02474 — evolving memory skills via RL (Feb 2026)

---

*LearnKit Design Document v1.0 — May 2026*
