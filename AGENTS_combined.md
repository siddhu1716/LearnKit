# AGENTS.md — LearnKit SDK (Combined)

> This document merges the original `AGENTS.md` with the latest updates from `AGENTS_V2.md`. It follows the original structure while incorporating current implementation status, hardening tasks, and new modules.

---

## Behavioral Rules

These rules apply to every task in this document. The agent that follows them writes less code, ships faster, and produces fewer bugs.

**Rule 1 — Think before coding.**
State your assumptions before implementing. If multiple approaches exist, name them and pick one explicitly. If something is unclear, stop and ask. Never pick silently.

**Rule 2 — Simplicity first.**
Write the minimum code that solves the problem. No abstractions for single‑use code. No configurability that wasn't asked for. If you write 200 lines and it could be 50, rewrite it.

**Rule 3 — Surgical changes.**
Touch only what you must. Match existing style. Don't refactor unrelated code. Every changed line should trace directly to the task requirement.

**Rule 4 — Goal‑driven execution.**
Transform every task into a verifiable goal before starting:
- "Build the classifier" → "DSPy Predict returns multi‑label dict with domain scores. Test with 5 sample tasks. All pass."
- "Add SQLite store" → "Can write a skill record, read it back by id, list by domain. Unit tests pass."

State a plan for multi‑step tasks. Loop until verified. Don't ship until the verify step passes.

---

## What We Are Building

**LearnKit** is an agent‑agnostic SDK that gives any AI agent a self‑improving memory layer.

*The core loop, in plain English:*  
1. User asks an agent a task  
2. LearnKit classifies the task  
3. LearnKit retrieves relevant past experience from memory  
4. That experience is injected into the agent's context  
5. Agent runs and produces a response  
6. LearnKit evaluates quality of the response  
7. If quality is good enough, the trace is distilled into typed memory records  
8. Those records improve every future run on similar tasks

*This is fine‑tuning without fine‑tuning.* Every "learned" pattern is an auditable, deletable JSON record.

---

## Core Philosophy: Experience Distillation

| Naive memory | LearnKit |
|---|---|
| Stores raw chat logs | Stores distilled experience |
| "User asked X, assistant said Y" | skill: contract_summarization → steps → success_rate: 0.92 |
| Hard to reuse across tasks | Directly reusable as context |
| Grows linearly, explodes context | Stays bounded, curated, scored |
| No quality signal | Every record has a quality gate |

---

## Four Sources — Read Before Building

*Source 1 – Hermes Agent* – Bounded memory, layered memory, SQLite FTS5 retrieval, skill generation.

*Source 2 – ReaComp* – CoT traces mandatory, two‑stage inference, failure traces first‑class.

*Source 3 – Karpathy LLM Wiki* – Wiki as persistent compounding artifact.

---

## Repository Structure

```text
learnkit/
├── AGENTS.md                    ← original (now merged)
├── AGENTS_V2.md                 ← merged updates (included here)
├── README.md
├── pyproject.toml
├── learnkit/
│   ├── __init__.py
│   ├── core.py
│   ├── classifier.py
│   ├── router.py
│   ├── retriever.py
│   ├── composer.py
│   ├── evaluator.py
│   ├── distiller.py
│   ├── compressor.py
│   ├── trajectory.py
│   ├── inference_mode.py
│   ├── schemas/…
│   ├── backends/…
│   ├── adapters/…
│   └── evolution/…
├── tests/…
└── skills/…
```

---

## Updated Implementation Status (from AGENTS_V2.md)

### 1. WHAT CHANGED FROM POC (Current Status)

| module | POC state | production target | current status |
|---|---|---|---|
| `classifier.py` | DSPy predictor with fragile JSON parsing and hard‑coded model | Typed classifier with validated domain scores, retry/repair, configurable model, warning logs on fallback | **[x] Completed** |
| `evaluator.py` | LLM judge and user feedback only; NLI enum unused | Multi‑signal evaluator with user feedback, LLM judge, optional NLI, bounded prompts, schema repair | **[x] Completed** |
| `distiller.py` | JSON prompt parser with silent empty fallback | Strict schema validation, TraceRecord emission, contrastive failure extraction, bounded prompt assembly | **[x] Completed** |
| `retriever.py` | BM25 + dense reranker; loads all records in memory (`list_all()`) | SQLite FTS5 + persisted dense vectors via `sqlite‑vec`, push‑down queries | **[ ] In Progress** |
| `router.py` | Caps record count only | Enforce 8 records **and** ~1200‑token budget; prioritize failure > skill > fact | **[ ] Pending** |
| `backends/sqlite.py` | Functional SQLite store; no migrations/WAL/robust FTS errors | Schema versioning, WAL mode, safe FTS escaping, transaction boundaries, warning logs | **[x] Completed** |
| Optional backends (`mem0`, `zep`, `qdrant`) | Stubs | Real adapters implementing `BaseBackend` with contract tests | **[ ] Pending** |
| `core.py` | Sync test mode & daemon thread post‑processing | Bounded worker queue, exception capture, retry policy, per‑run trajectory ID registry | **[ ] In Progress** |
| `adapters/*` | Offline‑safe wrappers | Real integration for LangChain, LangGraph, AutoGen, OpenAI/Anthropic raw clients | **[ ] Pending** |
| `evolution/gepa.py` | Generates variants but does not evaluate or dedupe | Thread‑safe trials, mutation validation, duplicate filtering, parent IDs, evaluator‑based selection, quarantine output | **[ ] Pending** |
| `schemas/base.py` | Simple fields, mutable defaults | Default factories, schema version, provenance, parent IDs, redaction metadata, validation ranges | **[x] Completed** |
| tests | Mock‑heavy unit tests, limited integration | Contract tests, packaging tests, backend failure tests, concurrency tests, live optional smoke tests gated by env vars | **[x] Completed** |

### 2. HARDENING TASKS (Updated Status)

- **Task H1 – Stop Silent Failures** — **[x] Completed**
- **Task H2 – Harden SQLite Backend** — **[x] Completed**
- **Task H3 – Memory Pollution Controls** — **[ ] Pending** (quarantine promotion logic to be added)
- **Task H4 – Make Post‑Processing Async‑Correct** — **[ ] In Progress** (worker queue integrated, trajectory ID registry pending)
- **Task H5 – Harden Classifier** — **[x] Completed**
- **Task H6 – Harden Evaluator** — **[x] Completed**
- **Task H7 – Harden Distiller** — **[x] Completed**
- **Task H8 – Harden Router Token Budget** — **[ ] Pending**
- **Task H9 – Harden GEPA Evolution** — **[ ] Pending**
- **Task H10 – Harden Public Packaging** — **[x] Completed** (wheel build, editable install verified)

### 3. NEW MODULES TO BUILD (Status)

| Module | Description | Status |
|---|---|---|
| `learnkit/logging.py` | Structured logger with redaction helpers | **[x] Completed** |
| `learnkit/errors.py` | Typed exception hierarchy (`LearnKitError`, `BackendError`, …) | **[x] Completed** |
| `SQLite Vector Store` (`sqlite‑vec`) | Persisted dense embeddings, hybrid scoring | **[ ] In Progress** |
| Maintenance Runner | Decay, stale marking, quarantine promotion, GEPA selection | **[ ] Pending** |
| Backend Contract Test Suite | Reusable tests for any `BaseBackend` | **[x] Completed** |
| Real Optional Backends (`mem0`, `zep`, `qdrant`) | Implement adapters adhering to `BaseBackend` | **[ ] Pending** |
| Native Adapter Integrations | LangChain, LangGraph, AutoGen, OpenAI/Anthropic raw clients | **[ ] Pending** |

---

## Production Readiness Rules (unchanged)

- **Error handling** – recoverable failures log structured warnings and return degraded results; unrecoverable errors raise typed exceptions.
- **Logging** – never log raw user data, prompts, or document contents.
- **Async correctness** – bounded worker queue, no shared mutable state across runs.
- **Backend fallback** – empty context on retrieval failure, warn.
- **Memory pollution** – quarantine records excluded until promotion.
- **Security** – redaction of IDs, keys, payloads.

---

## Refactoring Targets (from original AGENTS.md)

- Replace `LearnKit.last_trajectory` with per‑run ID registry.
- Refactor `_post_process_async` to use bounded worker pool.
- Centralize FTS query escaping in `SQLiteBackend.search`.
- Move mutable defaults to `Field(default_factory=…)`.
- Strengthen `Distiller` parsing with strict schema validation.
- Harden `GEPAEvolver` separation of concerns.
- Update `retriever.py` to delegate vector store concerns to backend.

---

## Integration Test Plan (summarised)

| Scenario | Expected Outcome |
|---|---|
| SQLite full learning loop | Context injected, trajectory captured, quality scored, records stored correctly |
| Retrieval backend degraded | Agent returns response with empty context, warning logged |
| Distiller malformed output | Warning logged, no poisoned record stored, optional `FailureRecord` created |
| Quarantine enforcement | Quarantined records never injected into active context |
| Failure memory priority | Failure appears before lower‑priority records within 8‑record cap |
| Hybrid retrieval fallback | BM25 used when vector store unavailable, warning logged |
| Concurrent agent calls (50+) | Distinct trajectory IDs, no state corruption |
| Export/import portability | All records preserved across DB migrations |
| GEPA partial failure | Unique variants stored, failures logged, no crash |
| Adapter raw OpenAI path | Context injected safely, response finalized |

---

## Ship Checklist for v1.0 (current)

1. `learnkit/errors.py` – implemented and used. ✅
2. `learnkit/logging.py` – structured logger with redaction. ✅
3. SQLite hardening (WAL, migrations, safe FTS). ✅
4. Post‑processing refactor (worker queue, trajectory ID). **In Progress**
5. Router token budget enforcement. **Pending**
6. Classifier/Evaluator/Distiller hardening. ✅
7. Vector store integration. **In Progress**
8. Optional backends (Mem0, Zep, Qdrant). **Pending**
9. GEPA evolution hardening. **Pending**
10. Packaging & CI (wheel build, editable install). ✅
11. Security & redaction verification. ✅

---

*This combined document supersedes the original `AGENTS.md`. It should be used for all ongoing planning, implementation, and documentation tasks.*
