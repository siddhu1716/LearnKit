# improvements.md — LearnKit Enhancement Tracking

Last updated: 2026-05-29

---

## ✅ Completed (v1 → MVP hardening)

| Item | Where | Notes |
|---|---|---|
| `datetime.utcnow()` → timezone-aware | `schemas/base.py`, `backends/sqlite.py`, all tests | Eliminated all in-house deprecation warnings |
| Mutable Pydantic defaults | `schemas/base.py` | Converted `domains={}`, `content={}`, `transfer_domains=[]` to `Field(default_factory=...)` |
| FTS5 BM25 sign inversion bug | `backends/sqlite.py` | `bm25()` returns negative values; negated to fix DESC ordering |
| Hybrid search LEFT JOIN bug | `backends/sqlite.py:hybrid_search` | Was always returning 0.0 BM25; fixed via FTS5 subquery MATCH |
| Scope propagation | `core.py:_post_process_now` | All distilled records now inherit `self.scope` |
| atexit drain of worker pool | `core.py` | Eliminates "cannot schedule new futures after shutdown" |
| Router token budget enforcement | `router.py` | Dual cap: 8 records AND ~1200 tokens |
| Write-time scope validation | `backends/sqlite.py:add()` | Raises `BackendError` on invalid scope string |
| `[langchain]` install extra | `pyproject.toml` | `pip install learnkit[langchain]` works |
| `__pycache__` in .gitignore | `.gitignore` | Removed tracked pyc files from index |
| Interpreter-finalization guard in post-processing | `core.py:_post_process_now` | Added `sys.is_finalizing()` early return — prevents the evaluator from being called against an already-torn-down dspy/litellm pool, which previously fell back to score=2.0 and **wrote a synthetic FailureRecord to the DB on every default-config program exit**. Surfaced during 2026-05-29 smoke test. |
| Example mains drain the worker pool explicitly | `quick_start.py`, new `minimal_agent.py` | Call `memory.shutdown(wait=True)` before script exit so post-processing completes while infra is healthy. |
| UTF-8 stdout reconfigure in example mains | `quick_start.py`, `minimal_agent.py` | Windows cp1252 console was rendering composer em-dashes as `�` in the printed preview. LLM input was always UTF-8 — fix is cosmetic to the demo. |
| Minimal no-framework example added | `examples/minimal_agent.py` | Raw Anthropic SDK + `@lk.agent`, ~95 lines. Run 1 → 0 chars context, Run 2 → 877 chars. Proves LearnKit works without LangChain/LangGraph/DSPy in the agent path. |
| `escape_fts` reserved-word collision | `learnkit/backends/sqlite.py` | FTS5 reserved tokens (AND/OR/NOT/NEAR) in a search query produced a malformed MATCH expression and the search silently fell back to []. Surfaced during the v0.1.0 benchmark — broke retrieval on nearly every contract_summarization task (each prompt contains "and"). Fix: double-quote each token. Regression test at `tests/test_sqlite_backend.py::test_search_with_fts5_reserved_words_in_query`. |
| v0.1.0 benchmark harness | `benchmarks/run_custom.py` + `benchmarks/RESULTS.md` | 60 tasks across 3 domains, control vs treatment with Gemini Flash Lite agent + Haiku judge. Results: +0.20 / +0.30 / +0.00 lift on contract / python / sql. Compounding curve clean on contract domain. Single hurtful case (sql06 5.0 → 2.0) traced to wrong-pattern retrieval. SWE-bench Lite scaffolded under `benchmarks/swe_bench_lite/` for v0.2.0. |

---

## 🔨 MVP Changes (current sprint — agents_v2_mvp.md)

| Item | Source | Priority | Status |
|---|---|---|---|
| **k=1 PRIMARY/SECONDARY prompt split** | ReasoningBank (ICLR 2026) | HIGH | 🔨 In Progress |
| **Bundled starter skills** (`skills/legal/`, `skills/coding/`) | Hermes Agent `skills/*.md` format | HIGH | 🔨 In Progress |
| **AWM slot substitution in skill content** | Agent Workflow Memory (arXiv 2409.07429) | MEDIUM | Pending |
| **Confidence-gate on quarantine promotion** | Voyager promotion gates | MEDIUM | Pending |
| **Contrastive failure prompting** | ReasoningBank dual-pass failure extraction | MEDIUM | Pending |

---

## 📋 Future — v2 Production

| Improvement | Source | Reason / Notes |
|---|---|---|
| Native vector embeddings (`sentence-transformers` push-down) | Hermes + sqlite-vec | Vector store integration; push-down query not yet fully verified |
| Dynamic domain adaptation | ReaComp pipeline | Requires extensive tracing; scheduled for v2 |
| Time-aware exponential confidence decay | Karpathy LLM Wiki "keep current" | Linear decay sufficient for MVP |
| Auto-instrumenting AST parser | — | Invasive; will rely on explicit wrappers |
| Local dashboard / memory wiki viewer | Karpathy LLM Wiki | Developer tooling after core stability |
| GEPA evolution hardening (lineage, dedup, trial-failure handling) | Hermes GEPA | Planned after core modules stabilize |
| Optional backends (`mem0`, `zep`, `qdrant`) | Hermes toolset pattern | Implement adapters + contract tests |
| Native framework adapters (LangChain callbacks, LangGraph nodes, AutoGen reply) | — | LangChain demo exists; native integrations still to do |
| ~~Post-processing interpreter-shutdown race (narrow case)~~ | — | **Fixed 2026-05-29.** Root cause: `_post_process_now` ran during interpreter finalization, evaluator's LM call failed against a torn-down dspy/litellm pool, score=2.0 fallback triggered synthetic `FailureRecord` write. Now guarded with `sys.is_finalizing()`. |
| Memory pollution controls — explicit promotion API + confidence-floor filter | Hermes bounded memory | Quarantine exclusion from search is in place; promotion API pending |
| Ensemble reranking surface (expose per-record final_score to callers) | ReaComp ensemble diversity | Currently scored internally; expose for downstream integrations |
| Retriever `list_all()` elimination (push-down vector retrieval) | sqlite-vec push-down | Zero-lexical-overlap fallback currently does a bounded `list_all(100)` scan |

---

## 🆕 Proposed (added 2026-05-29 — sprint kickoff review)

These came out of a fresh read of the repo against `agents.md`. None are required to ship MVP, but they unblock the benchmarking + multi-backend work the user asked for today.

### Validation infrastructure (blocks "prove LearnKit is better")

| Item | Reason | Notes |
|---|---|---|
| **Benchmark harness** (`benchmarks/` dir) | We have zero apples-to-apples evidence LearnKit improves agent quality | Needed to run a task suite twice — once with `@lk.agent`, once without — and diff quality scores, token usage, and latency. Likely shape: `runner.py` + `tasks/*.jsonl` + a CSV/HTML report writer. |
| **Standard benchmark adapters** (SWE-bench Lite first, then GAIA / HumanEval) | User explicitly asked for "standard benchmarks (swp etc)" | SWE-bench full is heavy (Docker per task). Start with **SWE-bench Lite** (~300 tasks) or a 20-task subset. GAIA is cheaper and stresses retrieval more. |
| **Deterministic evaluator mode** | LLM-judge is stochastic — benchmarks need reproducibility | Add a seed + temperature=0 path on `Evaluator.evaluate_with_llm_judge`, or allow a rule-based scorer for tasks with ground truth. |
| **Memory-state snapshot/restore** | Benchmarks need a clean store between runs and reproducible warm-state runs | Add `backend.snapshot(path)` / `backend.restore(path)`. SQLite: file copy. Already trivial — just expose. |
| **Token + latency accounting** | Need to compare *cost*, not just quality | Wrap LM calls to record tokens in/out and wall time per stage (classify, retrieve, compose, run, evaluate, distill). |

### Backend pluggability — DEFERRED (2026-05-29 decision)

Original plan was to implement real Mem0 and Supermemory backends. After review:

- Hermes and ReaComp (our two architectural references) both use **local storage only** — SQLite + filesystem for Hermes, JSONL + on-disk for ReaComp. Neither uses a memory SaaS.
- Mem0/Supermemory own their own embedding, scoring, and retrieval — they *replace* LearnKit's value-add (typed records, quality gate, distillation, confidence decay), not augment it. Routing through them weakens the contract.
- The `Mem0Backend` / `ZepBackend` / `QdrantBackend` ImportError stubs are correct to keep as marketing optionality, not real architecture.
- If a user lives in Mem0, the right shape is a one-way **export adapter** (`MemoryRecord` → Mem0 dump), not a backend swap.

**Action:** keep stubs. Add `BaseBackend` ABC conformance + contract-test matrix only if/when a real second backend is justified.

### Bugs / gaps surfaced while reading

| Item | Where | Notes |
|---|---|---|
| README test count drift | `README.md` says "33 passing" — actual is **47** after 2026-05-29 work | Bump on next docs touch. Symptom of docs lagging behind code. |
| `backends/registry.py` eagerly imports all stubs | `from .mem0 import Mem0Backend` etc. run at import time | Fine while stubs are trivial. Once real Mem0/Supermemory clients land, gate behind lazy import so `import learnkit` doesn't pull httpx/mem0ai for SQLite-only users. |
| No `examples/no_learnkit_baseline.py` | Need a side-by-side to make the benchmark comparison legible | Same agent code, no `@lk.agent` wrapper — used as the control arm in benchmarks. **Done as part of `benchmarks/run_custom.py` 2026-05-29.** |
| Stricter / rubric-based scoring for benchmark judge | LLM-judge ceiling — Haiku scored 4.7–4.9 on most v0.1.0 tasks even when responses had real gaps | Either tighten the judge prompt (stricter 0-5 anchors, deduct for any imperfection), or add ground-truth rubrics for SQL/Python tasks. Without this, lift signal saturates and small wins become invisible. |
| Larger n + multi-seed benchmark runs | n=10 per cell with single seed is too noisy for statistical claims | Bump to n=50 per domain, run 3 seeds, report mean ± stderr. Cost is still <$50 with Flash Lite + Haiku judge. |
| Wrong-pattern retrieval mitigation | Surfaced as sql06 5.0 → 2.0 in v0.1.0 benchmark | Retriever returned a related-but-wrong skill (upsert pattern surfaced for a gap-detection task). Mitigations on the roadmap already: ReasoningBank PRIMARY/SECONDARY split, confidence-gated promotion, contrastive failure prompting. v0.2.0 benchmark should re-run and verify these reduce wrong-pattern hurt cases. |
