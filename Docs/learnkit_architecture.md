# LearnKit — Operating System for Agent Experience

> **Technical Architecture Document v1.0**
> For distribution to developers and collaborators.

---

## What This Is

LearnKit is a language-agnostic SDK that gives any AI agent a **self-improving memory layer** — without changing the model, without fine-tuning, without GPU costs.

The core idea: instead of storing raw conversations, LearnKit distills successful agent runs into **reusable experience** — typed memory records that accumulate over time and make every future run meaningfully smarter.

**The one-line pitch:**
> You are not fine-tuning the model. You are fine-tuning the context it receives. The agent improves, the weights never change, and you can audit, delete, or rollback any "learning" instantly.

This is not a new agent. It is infrastructure that plugs into whatever agent you are already building.

---

## Core Philosophy: Experience Distillation

The critical distinction from naive memory systems:

| Naive memory | LearnKit |
|---|---|
| Stores raw chat logs | Stores distilled experience |
| "User asked X, assistant said Y" | skill: contract_summarization → steps → success_rate: 0.92 |
| Hard to reuse across tasks | Directly reusable as context |
| Grows linearly, explodes context | Stays bounded, curated, scored |
| No quality signal | Every record has a quality gate |

**We call this "experience distillation" not "memory storage."** That distinction matters for how you architect every component.

---

## Why This Is Better Than Fine-Tuning

Fine-tuning changes a model's weights permanently. LearnKit changes the context the model sees at inference time. The output quality improvement is comparable. The operational advantages are significant:

| Fine-tuning | LearnKit |
|---|---|
| GPU hours, $200–2000 per run | A few API calls, $0–5 |
| Hours to deploy | Instant (records stored in real time) |
| Unauditable (opaque weight update) | Fully auditable — every record is readable JSON |
| Can't "unlearn" GDPR data from weights | Delete the record, it's gone |
| Shared model affects all domains | Domain isolation per team/bucket |
| Catastrophic forgetting risk | No forgetting — records are explicit |
| Retraining for every update | New pattern available immediately after storage |

This is the pitch for enterprise buyers in legal, healthcare, and finance. They cannot accept opaque weight updates. They can accept auditable JSON records.

---

## Memory Taxonomy — 7 Types

LearnKit formally separates memory into seven distinct types. Each is stored, scored, and retrieved differently. This is the core structural innovation beyond Hermes Agent's approach.

| Type | What it stores | TTL | Scope |
|---|---|---|---|
| **Fact** | Stable domain truths | 90 days | team / public |
| **Preference** | User or system style | 365 days | user / team |
| **Skill** | Reusable workflow with steps | 180 days | team / public |
| **Failure** | Known bad patterns, dead ends | 90 days | team |
| **Strategy** | High-level reasoning approach | 180 days | team / public |
| **Execution trace** | Full debuggable task history | 30 days | user / team |
| **Domain heuristic** | Specialized domain behavior | 90 days | team / public |

### Why failure memory matters as much as skill memory

Knowing what NOT to do is often more valuable than knowing what to do. If an agent hallucinated clause references in three NDA summarizations, every future NDA summarization should receive that failure as an explicit warning in context. No existing memory system treats failure records as first-class citizens.

---

## Architecture: 7 Core Modules

### Module 1 — Task Classifier

**Role:** Understands what kind of task is incoming.

Takes the raw user task and produces a multi-label domain vector and task type classification.

```
Input:  "Summarize this software licensing agreement"
Output: {
  "task_type": "contract_summarization",
  "domains": {"legal": 0.9, "software": 0.5, "compliance": 0.3},
  "complexity": "medium"
}
```

Implementation: Single LLM call using a Haiku-class model (cheap, fast). DSPy typed Predict for structured output. Multi-label — a task can belong to multiple domains simultaneously. This is critical for cross-domain tasks (legal + finance, code + security).

---

### Module 2 — Memory Router

**Role:** Decides what to retrieve and how much.

Takes the domain vector and task type, builds a retrieval plan, and enforces a hard cap on what will enter context (5–8 records maximum, never more).

```
Retrieval plan:
  - domain: legal (weight 0.9) → retrieve skills + facts + failures
  - domain: software (weight 0.5) → retrieve domain heuristics
  - max_records: 7
  - max_tokens: 1200
```

The hard cap is non-negotiable. Context explosion is the most common production failure. This module is the gatekeeper.

---

### Module 3 — Semantic Retriever

**Role:** Finds the most relevant past experience.

Hybrid retrieval combining BM25 (keyword match) and dense vector search (semantic similarity). Records are ranked by a composite score:

```
score = semantic_similarity × confidence × recency_weight × (1 + log(reuse_count))
```

Returns ranked records up to the router's cap. Stale records (past TTL) are flagged but not excluded — they are injected with a staleness warning.

Implementation: `sentence-transformers` (all-MiniLM-L6-v2 or BGE-M3) for embeddings. `rank_bm25` for keyword scoring. `sqlite-vec` for local vector search. Upgrade path to Qdrant or Pinecone for cloud.

---

### Module 4 — Context Composer

**Role:** Formats retrieved memory into agent-ready context.

Takes the ranked records and produces a structured context block injected into the agent's system prompt. Each memory type formats differently:

```
=== LearnKit Context ===

SKILL — contract_summarization (used 14 times, success rate 91%):
  1. Extract all obligations for each party
  2. Extract termination clauses and conditions
  3. Flag indemnity clauses separately
  4. Simplify legal language to plain English
  5. Structure as bullet summary under 500 words

FAILURE — known risk in this domain:
  Hallucinated clause references in NDAs. Always cite clause numbers
  from source document only.

FACT — verified 2026-03-10:
  EU GDPR fines cap at 4% of global annual revenue or €20M,
  whichever is higher.
=== End Context ===
```

This block sits at the top of the system prompt before any agent instructions. The agent absorbs it as background knowledge.

---

### Module 5 — LLM Agent (any)

**Role:** Executes the actual task.

LearnKit is agent-agnostic. A lightweight trace hook wraps the agent's entry point. No changes to agent logic, prompts, or framework.

Supported out of the box: LangChain, LangGraph, AutoGen, CrewAI, Hermes Agent, raw Anthropic API, raw OpenAI API.

The trace hook captures: all tool calls in order, all intermediate reasoning steps (if available), token usage, wall-clock timing, and final output.

---

### Module 6 — Evaluator

**Role:** Quality gate before anything enters memory.

The most important guardrail in the system. A response must pass quality evaluation before it influences future runs. This is the difference between a self-improving system and a self-degrading one.

Quality signal sources (ranked by reliability):
1. Explicit user feedback (thumbs up/down, rating)
2. Downstream task completion (did the legal clause get approved in review?)
3. Verifier LLM call (separate model reads task + response, scores 0–5)
4. NLI-based factual consistency check

**Never use "agent responded = success" as your quality signal.** Confident wrong answers will poison the memory store and compound over time.

Quarantine policy: new records enter a 24-hour quarantine before influencing retrieval. During quarantine they are visible in the trace but not injected into context.

---

### Module 7 — Memory Distiller

**Role:** Converts successful execution traces into reusable typed records.

The most technically interesting module. Reads the full trace of a high-quality agent run and extracts structured records:

```
Input:  Full execution trace (tool calls, reasoning, outcome)
Output: [
  Skill record — the workflow that worked
  Fact record  — any stable truths referenced
  Failure record — any dead ends encountered and abandoned
]
```

Implementation: DSPy ChainOfThought module that reads the trace and outputs structured records. Each output is validated against the schema before storage. Starting confidence: 0.5. Confidence increases with each successful reuse.

**Confidence decay:** Every record's confidence score decays by approximately 2% per week unless reinforced by a new successful reuse. This prevents stale high-confidence records from misleading future runs.

---

## Complete Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│                    INFERENCE PATH                        │
│                                                          │
│  User Task                                               │
│      │                                                   │
│      ▼                                                   │
│  [Task Classifier]  ──→  domain vector + task type       │
│      │                                                   │
│      ▼                                                   │
│  [Memory Router]    ──→  retrieval plan (max 8 records)  │
│      │                                                   │
│      ▼                                                   │
│  [Semantic Retriever]  ──→  ranked memory records        │
│      │   retrieves:                                      │
│      │   • similar past tasks                            │
│      │   • matching skills                               │
│      │   • known failure modes                           │
│      │   • domain heuristics                             │
│      ▼                                                   │
│  [Context Composer] ──→  structured context block        │
│      │                                                   │
│      ▼                                                   │
│  [LLM Agent]  (any framework, any model)                 │
│      │                                                   │
│  ┌───┴────────────────────────┐                          │
│  │                            │                          │
│  ▼                            ▼                          │
│  Response → User     Execution Trace Captured            │
│                               │                          │
└───────────────────────────────┼──────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────┐
│                   LEARNING PATH                           │
│                               │                           │
│                               ▼                           │
│                      [Evaluator]                          │
│                         quality score 0–5                 │
│                               │                           │
│                   score ≥ threshold? (default 3.5)        │
│                               │                           │
│                              YES                          │
│                               │                           │
│                               ▼                           │
│                     [Memory Distiller]                    │
│                               │                           │
│              ┌────────────────┼────────────────┐          │
│              ▼                ▼                ▼          │
│           Skill            Fact           Failure         │
│          record            record          record         │
│              │                │                │          │
│              └────────────────┴────────────────┘          │
│                               │                           │
│                               ▼                           │
└─────────────────────────────────────────────────────────  │
                                │
┌───────────────────────────────┼──────────────────────────┐
│                    MEMORY STORE                           │
│                               │                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Skills  │  │  Facts   │  │ Failures │  │Strategies│ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ Prefs    │  │ Heurist. │  │   Execution Traces   │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
│                                                           │
│  Each record:  scored · confidence-weighted · TTL-bound   │
│  Scoped as:   user-private | team-shared | public         │
└───────────────────────────────────────────────────────────┘
```

---

## Memory Record Schema

Full schema for a skill record (most complex type):

```json
{
  "id": "a3f7c2d1-...",
  "type": "skill",
  "domains": {
    "legal": 0.9,
    "finance": 0.4
  },
  "task_type": "contract_summarization",
  "content": {
    "steps": [
      "Extract all obligations per party",
      "Extract termination clauses",
      "Flag indemnity clauses separately",
      "Simplify to plain English",
      "Structure as bullet summary"
    ],
    "tools_used": ["pdf_reader", "clause_extractor"],
    "constraints": ["under 500 words", "no legal jargon"]
  },
  "failure_modes": [
    "hallucinated clause references in NDAs",
    "missing cross-reference penalties"
  ],
  "outcome_quality": 4.2,
  "confidence": 0.87,
  "reuse_count": 14,
  "success_rate": 0.91,
  "scope": "team",
  "created_at": "2026-05-22T10:30:00Z",
  "expires_at": "2026-08-20T10:30:00Z",
  "last_reinforced": "2026-05-21T14:00:00Z",
  "status": "active"
}
```

Status values: `active` | `stale` (past TTL) | `quarantine` (awaiting validation) | `deprecated` (manually removed)

---

## Hierarchical Domain Structure

Flat buckets fail on cross-domain tasks. Use a hierarchy:

```
legal/
  contracts/
    nda/
    saas_agreements/
    employment/
  compliance/
    gdpr/
    hipaa/
  litigation/

coding/
  python/
    fastapi/
    async/
  cuda/
  distributed/

finance/
  reporting/
  risk/
  derivatives/
```

Retrieval walks up the hierarchy when child has insufficient memory. A task in `legal/contracts/nda` will retrieve from `legal/contracts` and `legal` if NDA-specific records are sparse.

---

## What We Borrow From Hermes Agent

Hermes Agent (Nous Research, Feb 2026, 105K stars) validated that self-improving agents work in production. Specifically:

- **Layered memory** — working memory (hot, in-session), semantic memory (warm, extracted facts), episodic memory (cold, full history). We adopt this tier model.
- **Bounded memory** — Hermes explicitly limits memory size to prevent "memory soup." We enforce this with hard token caps in the Memory Router.
- **Retrieval-based recall** — SQLite FTS5 + vector retrieval instead of full history replay. We adopt hybrid BM25 + dense retrieval.
- **Skill generation** — converting successful executions into reusable skill documents. This is the foundation of our Memory Distiller.
- **Execution trace search** — finding past traces similar to the current task. We include this as the Execution Trace memory type.

## Where LearnKit Goes Beyond Hermes

| Hermes Agent | LearnKit |
|---|---|
| Locked inside Hermes runtime | Framework-agnostic, plug in anywhere |
| Single-instance memory | Shared team skill registry |
| Implicit memory types | Formally typed (7 types), separate retrieval per type |
| Bool success signal | Continuous quality score with quarantine |
| No TTL / memory expiry | Per-type TTL with staleness flagging |
| No privacy scoping | user / team / public scope |
| No failure memory | Failure records are first-class citizens |
| Confidence not tracked | Confidence decay + reinforcement cycle |
| Memory not portable | Portable JSON schema, export/import between agents |

---

## Design Decision: Memory as Context vs Memory as Tools

This is the most important architectural choice. Two options:

### Option A — Memory as context (default, start here)

Retrieve memory records and inject them as text into the system prompt. The model reads them as background knowledge.

- Easy to integrate (5 lines of code)
- Model agnostic
- No changes to agent behavior
- Risk: context explosion at scale if the router fails

### Option B — Memory as tools (scalable, phase 2)

The agent explicitly calls memory as functions:

```python
memory.search(query="contract summarization", domain="legal")
memory.store(record)
memory.update_skill(skill_id, feedback)
```

- Controllable by the agent itself
- Scales to large memory stores without context explosion
- Agent can decide when and what to retrieve
- Requires more complex orchestration

**Recommendation:** Ship Option A for MVP. Add Option B as MCP tool integration in phase 2. Hermes is converging on this hybrid — we follow the same trajectory.

---

## Implementation Roadmap

### Phase 1 — Core SDK (weeks 1–8)

Target: working pip package, MIT license, SQLite backend

- [ ] Task Classifier — DSPy typed Predict, Claude Haiku
- [ ] SQLite memory store with 7-type schema
- [ ] BM25 + sentence-transformer retrieval
- [ ] Context Composer with type-specific formatting
- [ ] LangChain callback adapter
- [ ] LangGraph node wrapper
- [ ] Basic Evaluator (LLM-as-judge, Claude Haiku)
- [ ] CLI: `learnkit init`, `learnkit skills list`
- [ ] Publish to PyPI

### Phase 2 — Distillation + Scoring (weeks 9–16)

Target: production-ready, first paying customers

- [ ] Memory Distiller (DSPy ChainOfThought on traces)
- [ ] Confidence scoring + weekly decay job
- [ ] Failure memory recording
- [ ] Quarantine policy implementation
- [ ] Mem0 / Supermemory / Zep backend adapters
- [ ] AutoGen + CrewAI adapters
- [ ] Memory Scorer with reuse tracking
- [ ] CLI: `learnkit skills inspect`, `learnkit memory prune`

### Phase 3 — Team + Cloud (weeks 17–24)

Target: team tier, cloud registry, revenue

- [ ] Team skill registry with RBAC
- [ ] Privacy scoping (user / team / public)
- [ ] TTL enforcement + stale memory alerts
- [ ] MCP tool mode (Option B)
- [ ] Domain skill packs marketplace
- [ ] SOC 2 compliance logging
- [ ] API for skill import/export

---

## 5-Line Integration

```python
from learnkit import LearnKit

lk = LearnKit(
    memory_backend="sqlite",       # or "mem0", "zep", "qdrant"
    evaluation="llm_judge",        # or "user_feedback", "nli"
    scope="team"
)

@lk.agent(domain="legal", task_type="contract_summarization")
def my_agent(task: str) -> str:
    return langchain_agent.run(task)

# LearnKit handles everything else:
# classifies task → retrieves memories → composes context →
# captures trace → evaluates quality → distills and stores
```

---

## Use Cases

**Coding copilots** — remember your stack, conventions, and past debugging patterns. Accumulate CUDA, CI, and deployment skill records over weeks of use.

**Legal assistants** — build jurisdiction-specific skill libraries. Flag clause patterns seen in successful past reviews. Warn against known hallucination modes in specific contract types.

**Research agents** — accumulate domain expertise per field. Retrieve successful search strategies for similar past queries.

**Customer support AI** — learn resolution patterns per ticket category. Track which approaches lead to customer satisfaction vs escalation.

**Enterprise workflow agents** — shared org-level skill registry. Different teams contribute and consume specialized knowledge without overlap or leakage.

**Autonomous debugging systems** — store failure modes and their resolutions. Next time the same error pattern appears, the agent knows to skip the dead ends.

---

## The One-Paragraph Summary

LearnKit is an SDK that sits between any AI agent and its memory backend. It intercepts every agent run, classifies the task, retrieves the most relevant past experience, composes it into a structured context block, and after the run completes, distills what worked into typed records that improve future performance. It does not require model retraining, GPU infrastructure, or changes to existing agent code. Every piece of "learning" is an auditable, deletable, scopeable JSON record. It is, in the simplest terms, the experience layer that agents are currently missing.

---

## 2026-06-21 Architecture Addendum — Agentic Learning Control Plane

The original architecture above describes the infer-and-learn data path. The
current production focus adds a control plane for benchmarking and gated
improvement loops.

### New control-plane components

- `benchmarks/injection_ablation.py`
  - Multi-trial (`--trials`) quality ablation on novel sibling tasks.
  - pass^k-style metrics (`--k`) plus convention-level checks.
  - Writes detailed and summary JSON artifacts.
- `benchmarks/run_agentic_suite.py`
  - Orchestrates `react_live`, `evolution_live`, and `injection_ablation`.
  - Produces merged suite artifacts.
  - Enforces first regression gate: `playbook_effect >= threshold`.

### Control-plane flow (implemented)

1. Execute benchmark suite (`react_live`, `evolution_live`, `injection_ablation`).
2. Parse/merge metrics into one summary record.
3. Apply regression gate(s), starting with minimum playbook effect.
4. Fail build/release candidate when gate(s) fail.
5. Feed failing slices back into reflection/guardrail tuning.

This closes the loop from "learning mechanism" to "measurable quality gate".

### Standard benchmark numbers (suite run)

Source run: `benchmarks/results/agentic_suite_qwen2.5-7b_20260620_220017_summary.json`

- Model: `Qwen/Qwen2.5-7B-Instruct`
- Gate: `min_playbook_effect >= 0.5`
- Observed playbook effect: `+2.625` (PASS)

`react_live`:

- tool-calls/task: `3.5 -> 3.0` (about 14% reduction)
- llm calls: `21 -> 8` (about 62% reduction)
- success: `6/6 -> 6/6`

`evolution_live`:

- tool calls total: `58 -> 48` (about 17% reduction)
- llm calls total: `58 -> 20` (about 66% reduction)
- success: `16/16 -> 16/16`
- evolved flag: `true`

`injection_ablation` (`trials=1`, `k=1`):

- cold avg score: `0.0`
- procedure avg score: `0.375`
- playbook avg score: `3.0`
- playbook pass^k(full): `1.0`

Interpretation: cost reductions are stable in warmed mode, and the playbook arm
shows strong quality lift over procedure-only guidance on non-replayed siblings.

### Cross-model matrix (2026-06-21, revision 3)

Full numbers and per-model interpretation:
`Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`.

Current lineup under test (sglang, OpenAI-compatible):

| model                                 | gate | playbook_effect | pass^k(full) | react cold→warm | react LLM cold→warm | evolution cold→warm | evolution LLM cold→warm | evolved |
|---------------------------------------|------|-----------------|--------------|-----------------|----------------------|---------------------|--------------------------|---------|
| `Qwen/Qwen2.5-14B-Instruct`           | PASS | +1.875          | 1.0          | 6/6 → 6/6       | 15 → 9               | 16/16 → 16/16       | 38 → 21                  | yes     |
| `Qwen/Qwen2.5-32B-Instruct`           | PASS | +1.75           | 1.0          | 6/6 → 6/6       | 12 → 8               | 16/16 → 16/16       | 32 → 20                  | yes     |
| `NousResearch/Hermes-3-Llama-3.1-8B`  | FAIL | 0.0             | 0.0          | 0/6 → 0/6       | 6 → 6                | 0/16 → 0/16         | 16 → 16                  | no      |

Reference model from the previous lineup (kept for continuity):

| model                                 | gate | playbook_effect | pass^k(full) | react cold→warm | evolution cold→warm | evolved |
|---------------------------------------|------|-----------------|--------------|-----------------|---------------------|---------|
| `Qwen/Qwen2.5-7B-Instruct`            | PASS | +2.625          | 1.0          | 6/6 → 6/6       | 16/16 → 16/16       | yes     |

Three Qwen sizes now PASS the gate with no per-model code changes (7B, 14B,
32B). The 14B PASS depends on a small framework-side fix shipped on
2026-06-21: `benchmarks/react_live.py:react_loop` now contains an inline
fallback that lifts Hermes-style `<tool_call>{...}</tool_call>` blocks out
of the `content` field when the endpoint's tool-call parser misses them
(seen with sglang+hermes on Qwen "parallel call" outputs). The fallback
is shared by `react_live`, `evolution_live`, and `injection_ablation`.

`NousResearch/Hermes-3-Llama-3.1-8B` fails outside the framework: the
endpoint does not surface the OpenAI-style `tools` schema to the model,
so the model writes prose with invented function names. This requires
re-launching sglang with `--tool-call-parser hermes` and a tools-aware
chat template; the framework needs no further change to support it.

The matrix runner now records three distinguishable failure classes:
gate pass, parser/harness gap (now mitigated by the inline fallback), and
model/endpoint capability gap. This lets us gate production on class-1
results while still publishing class-2 and class-3 data points.

---

*v1.0 — May 2026*
*Architecture inspired by Hermes Agent (Nous Research), GEPA self-evolution (ICLR 2026), and Mem0 memory architecture.*
