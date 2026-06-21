# improvements.md — LearnKit Enhancement Tracking

Last updated: 2026-06-21

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
| Agent-path quality ablation (3-arm) | `benchmarks/injection_ablation.py` | Added `cold` vs `procedure` vs `playbook` with novel sibling tasks; now supports multi-trial + pass^k + persisted detailed/summary artifacts. Confirms quality gain from playbook injection (not just replay savings). |
| Agentic suite orchestrator + regression gate | `benchmarks/run_agentic_suite.py` | One-command runner for `react_live` + `evolution_live` + `injection_ablation`, merged artifacts, and first hard gate (`playbook_effect >= threshold`). Enables repeatable benchmark-driven iteration loops. |
| Playbook injected into live context | `learnkit/composer.py` | Closed write-only learning gap: playbook/pitfalls are now rendered into composed context for sibling/guided tasks. |
| Deterministic playbook capture guardrails | `learnkit/playbook.py` | Enforced do-not-capture filters in code (env/setup failures, negative tool claims, transient errors, one-off narration), plus length bounds and dedup cap. |

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
| Optional backends (`mem0`, `zep`, `qdrant`) | Hermes toolset pattern | Keep stubs / export adapters unless strong evidence a real second backend is needed; otherwise maintain contract tests only |
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

---

## 🆕 Proposed (added 2026-06-21 — Phase 3 production hardening)

These are the next concrete improvements to move from "good mechanism" to
production-grade benchmark evidence and operational reliability.

### Benchmark rigor and standards

| Item | Why now | Notes |
|---|---|---|
| **Multi-model benchmark matrix** | Current strong numbers are single-model (`Qwen2.5-7B`) and can hide model-specific behavior | Add nightly/weekly suite runs across at least 3 model families (Qwen, GPT-4.1-mini/4.1, Claude Sonnet/Haiku) with identical seeds/tasks and per-model gate dashboards. For an open-source host, start with **Meta-Llama-3.1-8B-Instruct** as the general baseline; if you can host a second model, add **Qwen2.5-Coder-7B-Instruct** for a stronger tool/JSON-following comparison point. |
| **Standard benchmark adapters for agent-path** | Internal synthetic tasks are useful but insufficient for external credibility | Add adapters for TAU-bench style task suites (pass^k), SWE-bench Lite subset for coding agent path, and one retrieval-heavy benchmark (LongMemEval-style) for memory quality. |
| **Confidence intervals + significance in suite summary** | Mean-only deltas are easy to overinterpret | Compute bootstrap CI or stderr across trials/seeds and store in `agentic_suite_*_summary.json`. Gate on lower bound (e.g., playbook effect LB > 0). |
| **Benchmark run registry + trend report** | Hard to reason about drift from one-off files | Add run index table (timestamp/model/seed/gates/pass-fail) + trend script to compare latest N runs and alert on regressions. |

### Pain-point mitigation toward production

| Item | Pain point addressed | Notes |
|---|---|---|
| **Reflection quality scorecard** | Loop works, but authored playbook quality is uneven/generic on thin traces | Add an evaluator pass for reflected bullets: specificity, non-contradiction, de-dup (semantic), actionable utility. Demote low-quality playbook updates. |
| **Semantic playbook dedup** | Lexical dedup still keeps paraphrase duplicates | Add embedding-based near-duplicate collapse before merge (`cosine > threshold`) with deterministic fallback. |
| **Replay safety/precondition checks** | Signature matches can still over-generalize in edge tasks | Require precondition predicates (tool availability + schema/key arg constraints) before replay; otherwise force guided mode. |
| **Offline gold-task harness for CI** | Live-model variance can cause noisy CI signals | Add small deterministic gold harness with fixed mock model/tool outputs for fast PR gating; keep live runs for nightly. |
| **Prod-readiness scorecard** | Hard to answer "are we production-ready?" consistently | Add explicit scorecard in docs: reliability, observability, benchmark confidence, rollback safety, oncall ergonomics; require minimum score to promote. |

---

## 🏁 Finalization snapshot (2026-06-21)

This is the publishable state of the repo as of 2026-06-21. Numbers are
copied from suite artifacts under `benchmarks/results/`; matrix doc is
`Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`; single-model standard numbers
are `Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt`.

### What's working end-to-end

- Two learning paths live and exercised:
  - `@lk.learn` (model path): mature; v0.1.0 benchmark + improvements row above.
  - `@lk.agent_learn` (agent path): functional with reflective playbook,
    deterministic playbook guardrails, and playbook injected into composed
    context (write-only gap is closed).
- Agentic suite (`benchmarks/run_agentic_suite.py`) combines `react_live` +
  `evolution_live` + `injection_ablation`, writes merged JSON artifacts, and
  enforces a `min_playbook_effect` regression gate.
- Cross-model matrix runner (`benchmarks/run_agentic_matrix.py`) supports
  per-target endpoints, per-model and per-benchmark timeouts, and
  `--continue-on-fail`. Default targets now point at the 7B/14B/33B lineup.
- Live-model harness is robust to runaway content via `LK_MAX_OUTPUT_TOKENS`
  (default 256), preventing the previous indefinite hangs on models that
  emit pseudo-tool text.

### Standard published numbers (Qwen2.5-7B-Instruct, the reference model)

- react_live: success 6/6 → 6/6, LLM calls 21 → 8 (~62% reduction).
- evolution_live: success 16/16 → 16/16, LLM calls 58 → 20 (~66%), evolved=true.
- injection_ablation: playbook effect +2.625, playbook pass^k(full) = 1.0.
- Suite gate (`min_playbook_effect >= 0.5`): PASS.

### Cross-model portability finding (matrix, same seed/tasks)

- `qwen2.5-7b-instruct` (PASS): all three benchmarks green, playbook gate
  PASS, large cost/quality deltas.
- `qwen2.5-14b-instruct` (FAIL on gate, but learning signal visible):
  react cold 3/6 → warmed 5/6, evolution cold 10/16 → warmed 15/16,
  evolved=true. Injection ablation scored zero because the endpoint's
  tool-call parser does not extract this model's multi-call hermes-style
  output consistently; fix is endpoint-side (`--tool-call-parser hermes`).
- `deepseek-coder-33b-instruct` (FAIL on capability): does not emit
  structured tool_calls (emits Python code). Not a framework issue;
  replace with a tool-calling coder model in the coder lane.
- Three failure classes are now distinguishable in artifacts: gate pass,
  parser/harness gap, and model capability gap.

### Production readiness — current honest read

- Ready to ship: the model path (`@lk.learn`) end-to-end; the agent path on
  models that emit structured tool calls (Qwen2.5-7B-Instruct verified end
  to end with a regression gate).
- Not yet ready: multi-model gating without a parser-config audit per
  endpoint; long-tail tool-calling reliability for non-Hermes models; CI
  signal stability (suite is live-model only, see "Offline gold-task
  harness" item above).

### Top remaining improvements (ordered for next sprint)

1. Bootstrap per-model parser/health audit before each matrix run; record
   `parses_tool_calls=true/false` in the matrix detailed JSON.
2. Bootstrap confidence intervals on `playbook_effect` (≥3 seeds, ≥3 trials)
   and gate on the lower bound, not the mean.
3. Offline deterministic gold-task harness for CI; keep the live matrix for
   nightly.
4. Reflection quality scorecard + semantic playbook dedup to push playbook
   precision up under thin traces.
5. Standard adapters (`TAU-bench`-style, SWE-bench Lite subset) to add
   external credibility on top of the internal suite.


### 2026-06-21 update — third lineup, two new models PASS

Lineup pass 3 swapped in `NousResearch/Hermes-3-Llama-3.1-8B` (port 8000),
`Qwen/Qwen2.5-32B-Instruct` (port 8001), and kept `Qwen/Qwen2.5-14B-Instruct`
(port 8002). Two of three are now PASSING the regression gate:

- `Qwen/Qwen2.5-32B-Instruct`  PASS, playbook_effect=+1.75, pass^k=1.0,
  react 6/6→6/6 (LLM 12→8), evolution 16/16→16/16 (LLM 32→20, evolved=true),
  injection procedure=1.25 → playbook=3.0.
- `Qwen/Qwen2.5-14B-Instruct`  PASS, playbook_effect=+1.875, pass^k=1.0,
  react 6/6→6/6 (LLM 15→9), evolution 16/16→16/16 (LLM 38→21, evolved=true),
  injection procedure=1.125 → playbook=3.0.
- `NousResearch/Hermes-3-Llama-3.1-8B`  FAIL — endpoint configuration gap
  (does not surface the OpenAI tools schema to the model; needs sglang
  `--tool-call-parser hermes` + tools-aware chat template). Not a
  framework gap.

Framework change that unlocked the 14B PASS:
`benchmarks/react_live.py:react_loop` now contains a small inline
fallback that lifts Hermes-style `<tool_call>{...}</tool_call>` blocks
out of the `content` field when the endpoint parser misses them. Shared
by all three benchmarks. Without this, the 14B (Qwen "parallel call"
pattern) scored 0 on injection_ablation despite clearly applying the
playbook on react and evolution.

Framework portability evidence: three Qwen sizes (7B, 14B, 32B) and two
different generation regimes (single-call and parallel-call) now PASS the
gate with no per-model code changes. The reference 7B numbers remain
published in `Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt`; the full
cross-model table is in `Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`.
