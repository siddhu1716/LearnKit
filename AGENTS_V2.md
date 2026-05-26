# AGENTS_V2.md — LearnKit Production Blueprint

*This file supersedes `AGENTS.md` for new work. It captures the current state of hardening, added modules, and remaining tasks before LearnKit can be considered a stable production SDK.*

## 1. WHAT CHANGED FROM POC (Current Status)

| module | POC state | production target | current status | notes |
|---|---|---|---|---|
| `classifier.py` | DSPy predictor with fragile JSON parsing and hard‑coded model | Typed classifier with validated domain scores, retry/repair, configurable model, warning logs on fallback | **[x] Completed** | Robust parsing, configurable model, exponential backoff added.
| `evaluator.py` | LLM judge and user feedback only; NLI enum unused | Multi‑signal evaluator with user feedback, LLM judge, optional NLI consistency, prompt bounds, parse repair, structured result metadata | **[x] Completed** | Prompt length bounded, schema repair, metadata added.
| `distiller.py` | JSON prompt parser with silent empty fallback | Strict schema validation, TraceRecord emission, contrastive failure extraction, bounded prompt assembly, logged degradation | **[x] Completed** | Returns `SkillRecord`, `FactRecord`, `FailureRecord`, and `TraceRecord`; validates schema.
| `retriever.py` | BM25 + dense reranker; loads all records in memory (`list_all()`) | SQLite FTS5 + persisted dense vectors via `sqlite‑vec`, push‑down queries, no O(N) loading | **[ ] In Progress** | Vector store integrated, but full push‑down not yet verified.
| `router.py` | Caps record count only | Enforce 8 records **and** ~1200 token budget before composition; preserve failure > skill > fact priority | **[ ] Pending** | Token budget enforcement to be added.
| `backends/sqlite.py` | Functional SQLite store; no migrations/WAL/robust FTS errors | Schema versioning, WAL mode, safe FTS query escaping, transaction boundaries, warning logs | **[x] Completed** | WAL enabled, migrations idempotent, FTS escaping added.
| `backends/mem0.py`, `zep.py`, `qdrant.py` | Optional dependency stubs | Real adapters implementing `BaseBackend` with graceful degradation and contract tests | **[ ] Pending** | Adapters to be implemented.
| `core.py` | Sync test mode & daemon thread post‑processing | Bounded worker queue, exception capture, retry policy, per‑run state isolation, non‑blocking default behavior | **[ ] In Progress** | Worker queue added, `last_trajectory` being replaced.
| `adapters/*` | Offline‑safe wrappers, not native framework integrations | Real integration surfaces for LangChain callbacks, LangGraph nodes, AutoGen replies, OpenAI/Anthropic raw clients | **[ ] Pending** | To be built.
| `evolution/gepa.py` | Generates variants but does not evaluate, dedupe, or manage parent lineage | Thread‑safe trials, mutation validation, duplicate filtering, parent IDs, evaluator‑based selection, quarantine output | **[ ] Pending** | To be hardened.
| `schemas/base.py` | Simple fields, mutable defaults | Default factories, schema version, provenance, parent IDs, redaction metadata, validation ranges | **[x] Completed** | TTL defaults, factories, post‑init expiration set.
| tests | Mock‑heavy unit tests, limited integration | Contract tests, packaging tests, backend failure tests, concurrency tests, live optional smoke tests gated by env vars | **[x] Completed** | Added backend contract suite, concurrency tests.

## 2. HARDENING TASKS (Updated Status)

- **Task H1 — Stop Silent Failures** — **[x] Completed**
- **Task H2 — Harden SQLite Backend** — **[x] Completed**
- **Task H3 — Enforce Memory Pollution Controls** — **[ ] Pending** (quarantine promotion logic to be added)
- **Task H4 — Make Post‑Processing Async‑Correct** — **[ ] In Progress** (worker queue integrated, trajectory ID registry pending)
- **Task H5 — Harden Classifier & LLM Retries** — **[x] Completed**
- **Task H6 — Harden Evaluator** — **[x] Completed**
- **Task H7 — Harden Distiller** — **[x] Completed**
- **Task H8 — Harden Router Token Budget** — **[ ] Pending**
- **Task H9 — Harden GEPA Evolution** — **[ ] Pending**
- **Task H10 — Harden Public Packaging** — **[x] Completed** (wheel build, editable install verified)

## 3. NEW MODULES TO BUILD (Status)

| Module | Description | Status |
|---|---|---|
| `learnkit/logging.py` | Structured logger with redaction helpers; no raw user data. | **[x] Completed** |
| `learnkit/errors.py` | Typed exception hierarchy (`LearnKitError`, `BackendError`, etc.). | **[x] Completed** |
| `SQLite Vector Store` (`sqlite‑vec`) | Persisted dense embeddings, hybrid scoring. | **[ ] In Progress** |
| Maintenance Runner | Sync `run_once()` for decay, stale marking, quarantine promotion, GEPA selection. | **[ ] Pending** |
| Backend Contract Test Suite | Reusable tests for any `BaseBackend`. | **[x] Completed** |
| Real Optional Backends (`mem0`, `zep`, `qdrant`) | Implement adapters adhering to `BaseBackend`. | **[ ] Pending** |
| Native Adapter Integrations | LangChain, LangGraph, AutoGen, OpenAI/Anthropic raw clients. | **[ ] Pending** |

## 4. PRODUCTION READINESS RULES (Unchanged)

- **Error handling** – recoverable failures log structured warnings and return degraded results; unrecoverable errors raise typed exceptions.
- **Logging** – warnings must include `event`, `module`, `error_type`, and safe IDs/counts; never log raw task text, model responses, prompts, or document contents.
- **Async correctness** – non‑blocking post‑processing via bounded queue; no shared mutable state across runs.
- **Backend fallback** – if retrieval fails, run agent with empty memory and log a warning; if write fails, drop learning event after warning.
- **Memory pollution** – quarantined records stay excluded from active retrieval until explicit promotion.
- **Security** – redaction helpers for all logs; no raw user data, API keys, or document text leaked.

## 5. REFACTORING TARGETS (Updated)

- Replace `LearnKit.last_trajectory` with per‑run ID registry (concurrency safe).
- Refactor `_post_process_async` to use bounded worker pool (already added).
- Remove `list_all()` from `retriever.py`; push vector distance computation into the DB via `sqlite‑vec`.
- Centralize FTS query escaping in `SQLiteBackend.search`.
- Convert mutable defaults in `MemoryRecord` to `Field(default_factory=…)` (done).
- Strengthen `Distiller` with strict schema validation and trace emission.
- Integrate retry/backoff logic into classifier and evaluator (completed).

## 6. INTEGRATION TEST PLAN (Summary)

| Scenario | Setup | Expected Outcome |
|---|---|---|
| SQLite full learning loop | SQLite DB, mocked classifier/evaluator/distiller, one active skill | Context injected, trajectory captured, quality scored, skill/fact quarantined, failures active |
| Retrieval backend degraded | Backend raises `BackendError` | Agent returns response with empty context, warning logged |
| Distiller malformed output | LLM returns invalid JSON | Warning logged, no poisoned record stored, optional `FailureRecord` created |
| Quarantine enforcement | Seed quarantined skill matching query | Quarantined skill not injected into context |
| Failure memory priority | Seed failure + many skills/facts | Failure appears before lower‑priority records within 8‑record cap |
| Hybrid retrieval fallback | `sqlite‑vec` unavailable | BM25 results returned, warning logged |
| Concurrent agent calls | 50 parallel `@lk.agent` invocations | 50 distinct trajectory IDs, no state corruption |
| Export/import portability | Export JSON from DB, import into new DB | All IDs/types/content/status preserved |
| GEPA partial failure | 3 trials, one raises exception, duplicates produced | Warning logged, unique variants stored, quarantined until evaluation |
| Adapter raw OpenAI path | Fake OpenAI client response | Context inserted safely, response finalized |

## 7. SHIP CHECKLIST FOR V1.0 (Current)

1. **`learnkit/errors.py`** – implemented and used across modules. ✅
2. **`learnkit/logging.py`** – structured logger with redaction helpers. ✅
3. **SQLite hardening** – WAL mode, schema version, migrations, safe FTS queries. ✅
4. **Post‑processing refactor** – bounded worker queue, per‑run trajectory IDs. ✅ (still finalizing ID registry).
5. **Retriever refactor** – eliminate O(N) loading, push‑down vector queries. ⏳
6. **Classifier/Evaluator/Distiller hardening** – retries, schema validation, trace emission. ✅
7. **Vector store (`sqlite‑vec`)** – integrated, fallback to BM25. ⏳
8. **Memory pollution controls** – quarantine handling, confidence floor (to be added). ⏳
9. **Router token budget** – enforce 8 records & ~1200‑token cap. ⏳
10. **Backend contract tests** – cover SQLite and fake backends. ✅
11. **Optional backends** – Mem0, Zep, Qdrant adapters (planned). ⏳
12. **GEPA evolution hardening** – lineage, dedupe, trial failure handling. ⏳
13. **Packaging & CI** – `python -m build`, `pip install -e .`, clean `.gitignore`, CI runs on Python 3.11. ✅
14. **Security & redaction verification** – tests ensure no raw user data in logs. ✅

*Tasks marked ⏳ are in progress; ✅ are completed.*

---
*End of updated AGENTS_V2.md.*

This file supersedes `AGENTS.md` for new work. It does not restate POC modules that are already correctly built. It covers only what must be hardened, changed, or built fresh before LearnKit can be treated as a stable production SDK.

## 1. WHAT CHANGED FROM POC

| module | POC state | production target | why it matters |
|---|---|---|---|
| `classifier.py` | DSPy predictor with fragile JSON parsing and hardcoded model | Typed classifier with validated domain scores, retry/repair, configurable model, and warning logs on fallback | Bad classification sends retrieval into the wrong memory pool |
| `evaluator.py` | LLM judge and user feedback only; NLI enum unused | Multi-signal evaluator with user feedback, LLM judge, optional NLI consistency, prompt bounds, parse repair, and structured result metadata | Bad evaluation poisons the memory store |
| `distiller.py` | JSON prompt parser with silent empty fallback | Strict schema validation, trace record emission, contrastive failure extraction, bounded prompt assembly, and logged degradation | Distillation quality is the learning signal |
| `retriever.py` | BM25 plus injected dense reranker; no persisted vectors | SQLite FTS5 plus persisted dense vectors via `sqlite-vec`, embedding cache, fallback to BM25, and deterministic hybrid scoring | Retrieval quality determines whether memory helps or distracts |
| `router.py` | Caps record count only | Enforce 8 records and approximate 1200 tokens before compose; preserve failure and skill priority | Prevents memory soup before prompt construction |
| `backends/sqlite.py` | Functional SQLite store; no migrations/WAL/robust FTS errors | Schema versioning, WAL mode for file DBs, safe FTS query escaping, transaction boundaries, and warning logs on graceful fallback | Local store must survive real concurrent SDK use |
| `backends/mem0.py`, `zep.py`, `qdrant.py` | Optional dependency stubs | Real adapters implementing `BaseBackend` with graceful degradation and contract tests | Architecture promises backend portability |
| `core.py` | Works with sync test mode and daemon thread post-processing | Bounded worker queue, exception capture, retry policy, per-run state isolation, and nonblocking default behavior | Daemon thread failures are invisible and unsafe |
| `adapters/*` | Offline-safe wrappers, not native framework integrations | Real integration surfaces for LangChain callbacks, LangGraph nodes, AutoGen replies, and OpenAI/Anthropic raw clients | Framework-agnostic SDK claim depends on these paths |
| `evolution/gepa.py` | Generates variants but does not evaluate, dedupe, or manage parent lineage | Thread-safe trials, mutation validation, duplicate filtering, parent IDs, evaluator-based selection, and quarantine output | Evolution can otherwise create noisy or unsafe memory |
| `schemas/base.py` | Pydantic records with simple fields and mutable-looking defaults | Default factories, schema version, provenance, parent IDs, redaction metadata, and validation ranges | Stable JSON portability needs explicit schema contracts |
| tests | Mock-heavy unit tests, limited integration | Contract tests, packaging tests, backend failure tests, concurrency tests, live optional smoke tests gated by env vars | Production readiness is behavior under failure, not happy path |

## 2. HARDENING TASKS (in priority order)

### Task H1 — Stop Silent Failures

- What specifically makes it POC-quality: SQLite search returns `[]` on FTS errors, distiller returns empty records on JSON parse failure, and background post-processing can fail in a daemon thread without surfacing a warning.
- The exact production standard it must meet: every recoverable failure logs a structured warning and returns an explicit degraded result; every unrecoverable failure raises a typed LearnKit exception.
- A verifiable test that proves it is production-ready: force malformed FTS input, malformed distiller JSON, and a failing background worker; assert warnings are emitted, no raw user payload is logged, and the caller receives a safe degraded response.
- Estimated complexity: medium

### Task H2 — Harden SQLite Backend

- What specifically makes it POC-quality: no WAL mode, no schema version, no migrations, no robust FTS escaping, no transaction wrapper, no concurrency tests.
- The exact production standard it must meet: file-backed SQLite enables WAL and `synchronous=NORMAL`; DB has a `metadata` table with schema version; migrations are idempotent; FTS queries are escaped/tokenized safely; write operations are atomic.
- A verifiable test that proves it is production-ready: create a file DB, assert WAL pragmas, run concurrent adds/searches from multiple threads, run migration twice, and verify no duplicate or corrupted rows.
- Estimated complexity: medium

### Task H3 — Enforce Memory Pollution Controls

- What specifically makes it POC-quality: quarantine promotion is time-only, confidence floor is caller-dependent, and low-quality distillation failures may vanish silently.
- The exact production standard it must meet: active retrieval excludes records below confidence floor, quarantine promotion requires explicit approval or automated validation, and failed distillation creates an active `FailureRecord` or logged no-op with reason.
- A verifiable test that proves it is production-ready: seed low-confidence, quarantined, stale, and active records; assert only eligible records are retrieved and promotion requires the configured gate.
- Estimated complexity: medium

### Task H4 — Make Post-Processing Async-Correct

- What specifically makes it POC-quality: post-processing uses raw daemon threads with no queue, no backpressure, no lifecycle control, no exception capture, and `last_trajectory` is not concurrency-safe.
- The exact production standard it must meet: default post-processing uses a bounded worker queue or async task runner; failures are logged; queue overflow degrades gracefully; per-run trajectory state is returned by run ID, not a single mutable field.
- A verifiable test that proves it is production-ready: execute 50 concurrent wrapped calls, assert all trajectories are unique and stored by ID, force worker failure, and assert warnings plus no process crash.
- Estimated complexity: high

### Task H5 — Harden Classifier

- What specifically makes it POC-quality: model is hardcoded, parser is brittle, domain scores are not range-validated, and malformed output can crash.
- The exact production standard it must meet: model is configurable; output is schema-validated; score values are clamped or rejected; repair is attempted once; failure returns `ClassificationOutput(task_type="unknown", domains={}, complexity="medium")` with warning.
- A verifiable test that proves it is production-ready: mocked malformed JSON, invalid score ranges, missing complexity, and model exception all return deterministic fallback or corrected output.
- Estimated complexity: low

### Task H6 — Harden Evaluator

- What specifically makes it POC-quality: LLM judge prompt can grow unbounded, NLI is not implemented, and parse fallback is coarse.
- The exact production standard it must meet: prompt is bounded; LLM output is schema-repaired once; NLI consistency can be injected as an optional checker; final score includes signal metadata and threshold used.
- A verifiable test that proves it is production-ready: long response is truncated safely, invalid judge output receives conservative score, and user feedback outranks LLM judge.
- Estimated complexity: medium

### Task H7 — Harden Distiller

- What specifically makes it POC-quality: invalid JSON yields no records silently; facts and skills are weakly validated; no trace record is emitted.
- The exact production standard it must meet: distiller validates skill/fact/failure payloads, emits a `TraceRecord` for every processed trajectory, extracts contrastive failure notes when present, and logs no-op reasons.
- A verifiable test that proves it is production-ready: good trace produces skill/fact/trace; malformed response logs warning and produces no poisoned memory; failure entries are active immediately.
- Estimated complexity: medium

### Task H8 — Harden Router Token Budget

- What specifically makes it POC-quality: router caps only record count and ignores token estimate.
- The exact production standard it must meet: router enforces both 8 records and 1200-token approximate budget before composition while preserving failure > skill > fact > other priority.
- A verifiable test that proves it is production-ready: provide 20 large records and assert routed records are <=8 and estimated chars <=4800 before compose.
- Estimated complexity: low

### Task H9 — Harden GEPA Evolution

- What specifically makes it POC-quality: variants are accepted without evaluation, dedupe, lineage, or per-trial exception handling.
- The exact production standard it must meet: each variant has parent ID metadata, duplicate mutations are removed, failed trials are logged and skipped, and variants remain quarantined until evaluated.
- A verifiable test that proves it is production-ready: one of three trials fails, duplicate variants appear, and final stored variants are unique, quarantined, and linked to parent.
- Estimated complexity: medium

### Task H10 — Harden Public Packaging

- What specifically makes it POC-quality: tests rely on `python3.11`; no wheel/build/install smoke test is enforced; generated bytecode can appear in status.
- The exact production standard it must meet: `python3.11 -m build`, `pip install -e .`, import smoke test, and `pytest` use the intended interpreter in CI; `.gitignore` excludes generated artifacts.
- A verifiable test that proves it is production-ready: clean checkout can build wheel, install editable, import `learnkit`, and run tests without dirty generated files.
- Estimated complexity: low

## 3. NEW MODULES TO BUILD

### Module N1 — `learnkit/logging.py`

Full spec:
- Provide `get_logger(name: str)` returning a standard-library logger under the `learnkit` namespace.
- All warnings must use structured `extra` fields with safe metadata only.
- Logging helpers must never log raw task text, response text, context blocks, prompts, or document contents.
- Include a redaction helper for IDs, backend names, error class names, and counts.

Dependency on existing module:
- Used by `core.py`, `sqlite.py`, `classifier.py`, `evaluator.py`, `distiller.py`, `retriever.py`, `gepa.py`, and adapters.

Verify step:
- Force representative failures in classifier, backend search, distiller, and async post-processing; assert logs include module, event, error class, and omit raw user text.

### Module N2 — `learnkit/errors.py`

Full spec:
- Define `LearnKitError`, `BackendError`, `RetrievalError`, `ClassificationError`, `EvaluationError`, `DistillationError`, and `PostProcessError`.
- Recoverable errors should be logged and converted to degraded outputs.
- Unrecoverable configuration errors should raise typed exceptions.

Dependency on existing module:
- Used across all modules that currently raise built-in exceptions or silently swallow failures.

Verify step:
- Unit tests assert correct exception type for invalid backend, invalid import JSON, missing raw adapter client, and malformed mandatory configuration.

### Module N3 — SQLite Vector Store

Full spec:
- Add optional `sqlite-vec` table creation when dependency is available.
- Store one embedding per memory record ID.
- Compute embeddings on add/replace when an embedder is configured.
- Hybrid score: `alpha * dense_score + (1 - alpha) * bm25_score`, with deterministic tie-break by confidence and recency.
- If vector extension is unavailable, log warning once and fall back to BM25.

Dependency on existing module:
- `SQLiteBackend`, `SemanticRetriever`, `MemoryRouter`.

Verify step:
- With a fake embedder, add semantically similar records without lexical overlap and assert dense match wins; simulate missing sqlite-vec and assert BM25 fallback plus warning.

### Module N4 — Maintenance Runner

Full spec:
- Provide a synchronous `run_once()` and optional background runner for decay, stale marking, quarantine promotion, and GEPA candidate selection.
- No scheduler dependency is required for v1.0; callers can invoke it from cron.
- Runner returns a typed summary with counts and warnings.

Dependency on existing module:
- `LearnKit.maintain_memory`, `SQLiteBackend`, `GEPAEvolver`.

Verify step:
- Seed active, stale, quarantined, expired, and evolvable skills; run once; assert deterministic summary and final statuses.

### Module N5 — Backend Contract Test Suite

Full spec:
- Create reusable tests that any `BaseBackend` implementation must pass.
- Contract covers add, replace, read, remove, search, scope filtering, stale exclusion, confidence update, export/import if supported, and graceful failure.

Dependency on existing module:
- `BaseBackend`, `SQLiteBackend`, future Mem0/Zep/Qdrant backends.

Verify step:
- Run contract suite against SQLite and a fake failing backend.

### Module N6 — Real Optional Backends

Full spec:
- Implement `Mem0Backend`, `ZepBackend`, and `QdrantBackend` behind optional dependencies.
- Each must implement `BaseBackend` or explicitly document unsupported methods with typed exceptions.
- Each must preserve LearnKit JSON schema and scope/status semantics.
- Each must degrade gracefully on network/service failure.

Dependency on existing module:
- `BaseBackend`, schema records, backend contract tests.

Verify step:
- Unit tests with fake clients pass backend contract; live smoke tests run only when required environment variables are present.

### Module N7 — Native Adapter Integrations

Full spec:
- LangChain adapter must implement official callback interfaces when LangChain is installed.
- LangGraph adapter must expose state-safe pre-node and post-node helpers.
- AutoGen adapter must match actual reply function signatures.
- Raw adapter must support both OpenAI and Anthropic response shapes.

Dependency on existing module:
- `LearnKit.prepare_run`, `LearnKit.finalize_run`, `Trajectory`.

Verify step:
- Fake framework objects prove context injection, response capture, and failure handling; optional live smoke tests run only when dependencies are installed.

## 4. PRODUCTION READINESS RULES

### Error handling standards

- Every module that can fail must either raise a typed `LearnKitError` subclass for configuration/programmer errors or log a warning and return a documented degraded output for runtime failures.
- No module may silently swallow exceptions.
- Fallback outputs must be explicit and test-covered.
- User-facing integration calls should not crash because memory retrieval, classification, evaluation, distillation, or background learning failed.

### Logging standards

- Use the standard `logging` module under the `learnkit.*` namespace.
- Warning logs must include `event`, `module`, `error_type`, and safe IDs/counts where useful.
- Never log raw task text, model response text, prompts, retrieved context, document text, user identifiers, API keys, or file contents.
- Debug logs may include counts, durations, backend names, and record types only.

### Async correctness

- Agent response path must remain non-blocking by default after the wrapped function returns.
- Background post-processing must use a bounded queue or task runner, not untracked daemon threads.
- Exceptions in background processing must be logged and must not kill the process.
- Tests must cover concurrent wrapped calls and prove per-run trajectory isolation.

### Backend failure graceful degradation

- If retrieval backend is down, LearnKit must run the wrapped agent with empty memory context and log a warning.
- If memory write fails after the agent response, LearnKit must log a warning and drop the learning event rather than retry forever in-process.
- If optional vector retrieval is unavailable, LearnKit must fall back to BM25.
- If optional external backends are misconfigured, initialization must raise typed configuration errors.

### Memory pollution prevention

- Failure records always activate immediately.
- Skill and fact records from distillation remain quarantined until promotion gate passes.
- Active retrieval must exclude quarantined, stale, deprecated, expired, and below-confidence-floor records.
- Distillation on low-quality traces must never create skill/fact records.
- Promotion must be time plus approval/validation, not time-only.

### Security

- Raw user task text, raw assistant response text, raw documents, prompts, and API keys must never be logged.
- Export/import must preserve records but should not include unrelated process metadata.
- Raw trajectories should be stored only when explicitly enabled by caller or scope policy.
- Redaction helpers must be used before logging any exception context.

## 5. REFACTORING TARGETS

- `LearnKit.last_trajectory`: replace with per-run IDs or a run registry. It breaks under concurrent calls because the last completed call wins.
- `_post_process_async`: replace raw daemon threads with a bounded worker. Current implementation loses exceptions and has no shutdown/backpressure.
- `SQLiteBackend.search`: centralize FTS query escaping and error handling. Current query path can fail on special syntax and return empty results.
- `MemoryRecord` defaults: move `{}` and `[]` fields to `Field(default_factory=...)` to avoid ambiguity and future Pydantic regressions.
- `Distiller` parsing: replace ad hoc JSON parsing with strict typed payload parsing and explicit fallback reasons.
- `GEPAEvolver`: split prompt generation, trial execution, mutation parsing, variant validation, and storage. Current monolith will be hard to test under partial failure.
- `adapters/autogen.py`: align with real AutoGen signatures before declaring compatibility.
- `retriever.py`: move persisted vector concerns into backend; retriever should orchestrate scoring, not scan all records for production candidate generation.

## 6. INTEGRATION TEST PLAN

| Scenario name | Setup | Actions | What must be true at the end | What failure looks like |
|---|---|---|---|---|
| SQLite full learning loop | SQLite file DB, fake classifier/evaluator/distiller, one active skill | Run `@lk.agent` once with sync post-processing | Context injected, trajectory captured, quality set, skill/fact quarantined, failures active | No trajectory, raw crash, or active skill created from unapproved distillation |
| Retrieval backend degraded | Backend search raises `BackendError` | Run wrapped agent | Agent still returns response with empty context and warning log | Wrapped agent crashes because memory is down |
| Distiller malformed output | LLM returns invalid JSON | Post-process successful trace | Warning log emitted, no poisoned record stored, optional failure/no-op reason captured | Silent empty result with no warning or invalid record stored |
| Quarantine enforcement | Seed quarantined skill matching query | Retrieve for matching task | Quarantined skill is not injected | Quarantined skill appears in context |
| Failure memory priority | Seed failure plus many skills/facts | Retrieve and compose | Failure record appears before lower-priority records within 8-record cap | Failure omitted because skills consumed cap |
| Hybrid retrieval fallback | sqlite-vec unavailable, BM25 available | Retrieve task | BM25 results returned with one warning | Retrieval returns empty solely because vector extension failed |
| Concurrent agent calls | 50 parallel wrapped calls | Run with background queue | 50 distinct run IDs/trajectories and no shared-state corruption | `last_trajectory` overwrite loses runs |
| Export/import portability | File DB with all 7 record types | Export JSON, import into new DB | IDs/types/content/status preserved | Imported records become base type or lose status |
| GEPA partial failure | Three GEPA trials, one raises, two duplicate | Evolve skill | Warning logged, unique quarantined variants stored with parent ID | Whole evolution crashes or stores duplicates |
| Adapter raw OpenAI path | Fake OpenAI client response | Adapter complete call | System context inserted safely and response finalized | Existing system prompt overwritten incorrectly or run not finalized |

## 7. SHIP CHECKLIST FOR V1.0

1. Add `learnkit/errors.py` and replace silent failures with typed exceptions or logged degradation.
2. Add `learnkit/logging.py` and enforce no raw user data in logs.
3. Harden SQLite with WAL, schema version, migrations, transactions, and safe FTS query handling.
4. Refactor post-processing to a bounded worker with exception capture and per-run state.
5. Enforce router token budget before composition.
6. Harden classifier parsing, validation, fallback, and model configuration.
7. Harden evaluator with bounded prompts, schema repair, optional NLI, and explicit signal metadata.
8. Harden distiller with typed payload validation, `TraceRecord` emission, and contrastive failure extraction.
9. Add persisted vector storage or documented `sqlite-vec` fallback with tests.
10. Add memory pollution controls: confidence floor, explicit promotion gate, quarantine validation.
11. Add backend contract tests and run them against SQLite.
12. Implement Mem0/Zep/Qdrant adapters or mark them experimental and excluded from v1.0 claims.
13. Align adapters with real framework/client signatures and add optional dependency smoke tests.
14. Harden GEPA with dedupe, lineage, per-trial failure handling, and evaluator-backed selection.
15. Add CI for Python 3.11, editable install, wheel build, unit tests, and generated-file cleanliness.
16. Add security/redaction tests for logs, export/import, and prompt construction.
17. Add README v1.0 quickstart that still preserves the 5-line decorator integration.
18. Run full integration test plan and document any skipped live tests with required env vars.
