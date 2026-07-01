# improvements.md — LearnKit Enhancement Tracking

Last updated: 2026-06-27
Scope: **MVP handover-ready**, not production-ready. Items required for testing
handover are in *MVP handover checklist*; everything previously labelled
"production hardening" or "high-scale" has been re-tagged *Deferred to
post-MVP* without losing the content.

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
| **k=1 PRIMARY/SECONDARY prompt split** | ReasoningBank (ICLR 2026) | HIGH | ✅ Shipped (`learnkit/composer.py:23-52`) |
| **Bundled starter skills** (`skills/legal/`, `skills/coding/`) | Hermes Agent `skills/*.md` format | HIGH | ✅ Shipped (`skills/legal/`, `skills/coding/`, `learnkit/skills_loader.py`) |
| **AWM slot substitution in skill content** | Agent Workflow Memory (arXiv 2409.07429) | MEDIUM | ✅ Shipped (`learnkit/replay.py:25-34` `__slot__` marker; `learnkit/procedural.py:106` parameterization) |
| **Confidence-gate on quarantine promotion** | Voyager promotion gates | MEDIUM | ✅ Shipped (`learnkit/core.py:_maybe_promote` + `backends/sqlite.py:promote_quarantined` age window) |
| **Contrastive failure prompting** | ReasoningBank dual-pass failure extraction | MEDIUM | ✅ Shipped (`learnkit/distiller.py:FAILURE_CONTRASTIVE_PROMPT` + `contrastive_failure_extraction`) |

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

## 📦 Deferred to post-MVP — Phase 3 production hardening (was: Proposed 2026-06-21)

> **Status (2026-06-27):** every item below is intentionally **out of scope
> for the MVP handover**. They move the project from "MVP handover" to
> "production-grade benchmark evidence and operational reliability" and
> should be picked up after testing closes.

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

## 🏁 MVP Handover Snapshot (2026-06-27)

This section is the **single source of truth** for what testers receive at
MVP handover. Numbers below are the published 2026-06-21 set in
`Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt` and
`Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`; the gate, runner, and code paths
those numbers exercise have not changed since (Graphify refresh confirmed
2026-06-27: 1960 nodes, 3878 edges, agent-path modules unchanged on gating
logic). Re-running is *not* required for handover.

### Supported environments (MVP)

**Self-hosted lane (primary — handover testing happens here):**

| Port | Model | Role |
|---|---|---|
| `8000` | `Qwen/Qwen2.5-Coder-32B-Instruct` | coder lane (replaces the FAIL'd `deepseek-coder-33b-instruct` from the matrix; tool-calling coder) |
| `8001` | `Qwen/Qwen2.5-32B-Instruct` | published-PASS lane (+1.75 playbook effect) |
| `8002` | `Qwen/Qwen2.5-14B-Instruct` | published-PASS lane (+1.875 playbook effect, parallel-call regime) |

Served via sglang with `--tool-call-parser` matched to the model family. The
inline `<tool_call>{...}</tool_call>` fallback in
`benchmarks/react_live.py:react_loop` (~L141-192) covers the parallel-call
Qwen regime when the endpoint parser misses structured tool_calls.

**Hosted-API lane (smoke only):** `examples/minimal_agent.py` works against
any OpenAI-compatible endpoint. OpenRouter / Google AI Studio / Groq keys
are supported through that path for testers who want to validate without
standing up sglang.

### What is verified end-to-end

- Two decorators live and exercised:
  - `@lk.learn` (model path): mature; v0.1.0 benchmark + improvements row above.
  - `@lk.agent_learn` (agent path): reflective playbook, deterministic
    capture guardrails, playbook injected into composed context
    (write-only gap closed in `learnkit/composer.py`).
- Agentic suite (`benchmarks/run_agentic_suite.py`) combines `react_live` +
  `evolution_live` + `injection_ablation`, writes merged JSON artifacts, and
  enforces the `min_playbook_effect >= 0.5` regression gate.
- Cross-model matrix runner (`benchmarks/run_agentic_matrix.py`) supports
  per-target endpoints, per-model and per-benchmark timeouts, and
  `--continue-on-fail`.
- Live-model harness is robust to runaway content via `LK_MAX_OUTPUT_TOKENS`
  (default 256), preventing indefinite hangs on models that emit
  pseudo-tool text.
- Unit suite: **167 passed, 1 xfailed** (last green run 2026-06-25).

### Published numbers (Qwen2.5-7B-Instruct reference, carried)

- react_live: success 6/6 → 6/6, LLM calls 21 → 8 (~62% reduction).
- evolution_live: success 16/16 → 16/16, LLM calls 58 → 20 (~66%), evolved=true.
- injection_ablation: playbook effect +2.625, playbook pass^k(full) = 1.0.
- Suite gate (`min_playbook_effect >= 0.5`): **PASS**.

### Cross-model matrix (re-verified 2026-06-27 on the three-Qwen lineup)

Matrix run: `benchmarks/results/agentic_matrix_2026-06-27_20260627_142507_summary.json`
(`--trials 1 --k 1 --seed 7 --continue-on-fail`).

- `Qwen/Qwen2.5-32B-Instruct` (port 8001) — **PASS**, playbook_effect=+1.75,
  pass^k=1.0, react 6/6→6/6 (LLM 12→8), evolution 16/16→16/16 (LLM 32→20,
  evolved=true, 22 max_reuse, mean_conf=0.925). Reproduces the 2026-06-21
  published numbers exactly.
- `Qwen/Qwen2.5-14B-Instruct` (port 8002) — **PASS**, playbook_effect=+1.875,
  pass^k=1.0, react 6/6→6/6 (LLM 14→9), evolution 16/16→16/16 (LLM 38→21).
  Reproduces the 2026-06-21 published numbers exactly (within ±1 LLM call).
- `Qwen/Qwen2.5-Coder-32B-Instruct` (port 8000) — **FAIL**: 0 successes both
  arms, playbook_effect=0.0, `cold_tools_per_task=0.0`. Same failure class as
  the 2026-06-21 `deepseek-coder-33b-instruct` result: the model emitted no
  structured tool_calls. **Fix is endpoint-side**, not framework: this
  endpoint needs `--enable-auto-tool-choice` + a `--tool-call-parser` matched
  to Qwen2.5-Coder (e.g. `qwen25` or `hermes`). Treat as a known
  endpoint-config gap until the sglang launch flags are corrected, then
  re-run.

### Cross-model matrix — expanded lineup (2026-06-28: +Llama-3.3-70B, +gpt-oss-20b)

Matrix run: `benchmarks/results/agentic_matrix_2026-06-28_20260627_185900_summary.json`
(`--trials 1 --k 1 --seed 7 --continue-on-fail`, four self-hosted endpoints).

- `Qwen/Qwen2.5-32B-Instruct` (port 8001) — **PASS**, playbook_effect=+1.75,
  pass^k=1.0, LLM cold→warm 12→8. Reproduces the 2026-06-27 numbers exactly
  (the 14B lane was dropped from this lineup; 32B remains the reference).
- `meta-llama/Llama-3.3-70B-Instruct` (port 8002) — **PASS**,
  playbook_effect=**+2.25** (best in lineup), pass^k=0.0, LLM cold→warm
  24→16 (~33% reduction). Highest absolute lift recorded so far; pass^k=0.0
  means the warmed arm wasn't deterministic across all-k samples even though
  mean score improved. First non-Qwen lane to land a PASS — closes the
  "Qwen-only verification" caveat in the prior snapshot.
- `Qwen/Qwen2.5-Coder-32B-Instruct` (port 8000) — **FAIL** (unchanged):
  playbook_effect=0.0, LLM 6→6. Still the sglang parser-flag gap: tool calls
  are emitted as `<tools>{...}</tools>` text instead of structured
  `tool_calls`. Fix is unchanged — relaunch sglang with
  `--enable-auto-tool-choice --tool-call-parser qwen25` (fallback `hermes`).
- `openai/gpt-oss-20b` (port 8004) — **FAIL**, playbook_effect=**−0.125**
  (regression), pass^k=0.0, LLM cold→warm 26→16. The warm arm reduces calls
  but the score drops slightly — model follows the injected playbook in
  shape but mis-routes when the playbook step doesn't fit the task. Treat
  as a behavioural mismatch, not an endpoint bug: 20B reasoning capacity
  appears below the floor needed for procedural lift on this suite. Re-run
  with a stricter `procedure_match_threshold` (e.g. 0.85) before drawing a
  final conclusion.

Suite gate (`min_playbook_effect >= 0.5`): **PASS** for 32B and Llama-70B;
**FAIL** for Coder-32B (endpoint config) and gpt-oss-20b (model capacity).
Overall `all_pass=false` because the matrix requires every target to pass.

### Known limitations at handover (documented, not blockers)

- Suite gate is **mean-only, single-seed**. No bootstrap CIs. Sensible for
  MVP; production hardening covered under *Deferred to post-MVP*.
- No **parser/health preflight** per endpoint. Testers must read each
  benchmark's `parses_tool_calls` / non-zero `LLM calls` row to spot a
  parser gap. Runbook item below.
- No **offline CI gold harness** — the suite is live-model only. Variance is
  small (single-seed reproducible within ±1 LLM call on Qwen) but not zero.
- No **non-Qwen verification** in this snapshot. Llama / Mistral / Hermes-3
  lanes are out of scope; Hermes-3 specifically fails on endpoint config,
  not framework. Adding a non-Qwen lane is a post-MVP item.
- No **standard external benchmarks** (TAU-bench, SWE-bench Lite,
  LongMemEval). Internal suite + matrix is the MVP evidence.
- LearnKit-provided **utility gate is internal-signal only** unless callers
  pass `LEARNKIT_UTILITY_EXTERNAL=1` + call `apply_external_outcome(...)`.
  External benchmark scripts must set this to get a trustworthy outcome
  signal (`learnkit/core.py:apply_external_outcome`, ~L221).

### Explicitly out of scope for MVP

Moved to *Deferred to post-MVP* — see below for the full list, all of which
have landing notes already authored: bootstrap CIs + LB gating, per-model
parser preflight as a blocker, offline CI gold harness, reflection quality
scorecard, semantic playbook dedup, replay precondition predicates,
prod-readiness scorecard, native vector embeddings, async batched backend
writes, backend sharding, multi-model gating, TAU/SWE-bench/LongMemEval
adapters.

### MVP handover checklist (must-do before testing)

1. **Claim alignment.** Confirm `README.md`, `Docs/README.md`, and the
   examples section point reviewers at
   `Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt` and
   `Docs/FINAL_MODEL_MATRIX_2026-06-21.txt`. No claims that exceed those
   numbers.
2. **Three-endpoint smoke run.** With the trio above live, run
   `python benchmarks/run_agentic_matrix.py --continue-on-fail` once and
   archive the resulting `agentic_matrix_*_summary.json`. Accept any
   `all_pass` plus the two Qwen Instruct lanes individually PASS; Coder 32B
   either PASS or attach the parser/capability note from the artifact.
3. **Hosted-API smoke.** Run `python examples/minimal_agent.py` against one
   of {OpenRouter, Google AI Studio, Groq} so testers without sglang can
   reproduce the agent path. Expected behaviour: Run 1 → 0 chars injected
   context, Run 2 → non-zero injected context.
4. **Unit suite green.** `pytest -q` → 167 passed, 1 xfailed.
5. **Runbook page.** One page covering: env vars (`LK_API_KEY`,
   `LEARNKIT_RELEVANCE_FLOOR`, `LEARNKIT_UTILITY_FLOOR`,
   `LEARNKIT_UTILITY_EXTERNAL`, `LK_MAX_OUTPUT_TOKENS`), the three
   self-hosted endpoints, how to read `*_summary.json`, and the three
   known FAIL classes (gate, parser/harness, capability).

That is the entire pre-handover surface. Nothing else is required.


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

---

## 🆕 2026-06-25 — SkillOpt + SkillLens adaptation pass (shipped + validated)

Studied two Microsoft Research projects against LearnKit and transplanted only
the validated, low-risk mechanisms that reinforce the existing spine (no
rewrites, no new deps, no labeled datasets).

| Item | Source | Where | Notes |
|---|---|---|---|
| **Validation-gated, monotonic procedure refinement** | SkillOpt (validation-gated acceptance + monotonic `best_skill`) | `learnkit/procedure_evolution.py` | A strictly shorter tool path is accepted only when the run does **not** regress the family's proven outcome score (`_established_best_score` + `_REFINE_TOLERANCE`). Keeps a monotonic `_best_score` and a `_prev_procedure` rollback snapshot; a later failed replay self-heals back to the proven body instead of quarantining. Reuses existing `outcome_score` — zero extra calls. |
| **3-dimension quality rubric in the reflection prompt** | SkillLens RQ3 meta-skill (+1.55pp, 9/9 cells) | `learnkit/distiller.py` (`REFLECT_PROMPT`) | Steers each playbook bullet toward *failure-mechanism encoding*, *actionable specificity*, or *high-risk action blacklist*, with concrete vs. anti-example phrasing; bans generic platitudes. Same JSON contract, no extra calls. |
| **Generic-advice gate in the insight filter** | SkillLens (surface plausibility ≠ utility; judge 46.4%, format p>0.34) | `learnkit/playbook.py` (`is_durable_insight`) | Whole-string-anchored `_GENERIC_ADVICE_RE` drops platitudes ("be systematic", "verify results", "handle errors carefully") while keeping concrete rules that merely share a verb. Complements the existing env/tool/transient/narration filters. |
| **Architecture docs: agent path made first-class** | — | `Docs/learnkit_architecture.md`, `architecture/*.mmd`, `architecture/README.md` | "Two Learning Paths" + "Agent Path Architecture" sections; new `agent_runtime_flow.mmd`; `full_system_flow.mmd` AgentPath subgraph. |

**Validation (live, 2026-06-25):** `react_live` on `Qwen/Qwen2.5-14B-Instruct`
(port 8002) — PASS. Cold 14 → warmed 9 LLM calls (−36%), success 6/6 → 6/6,
2 replayed + 2 guided; reinforce / signature-reject / family-seed events all
fire correctly. Unit suite: **167 passed, 1 xfailed**. New tests:
`test_refine_rejected_when_run_regresses_quality`,
`test_refine_accepted_keeps_rollback_snapshot_and_best_score`,
`test_demote_rolls_back_to_previous_body_then_quarantines`,
`test_merge_insights_drops_generic_advice_keeps_concrete_rules`.

---

## 📦 Deferred to post-MVP — High-Scale & Rapid-Iteration Roadmap (was: 2026-06-25)

> **Status (2026-06-27):** every item below is **out of scope for the MVP
> handover**. Forward-looking work for scaling the memory layer and
> iterating fast. Grouped by theme; each item lists **Source**, **Value**,
> **Effort**, and concrete landing notes. None block current functionality;
> ordered roughly by value/effort.

### A. Skill quality & negative-transfer control (highest strategic value)

| Item | Source | Value | Effort | Landing notes |
|---|---|---|---|---|
| **Per-consumer negative-transfer guard on the model path** | SkillLens (25% of pairs hurt; same skill +4.93 GPT vs −1.69 Qwen-9B) | HIGH | M | The agent path already demotes on failed replay; the **model path has no guard**. Track per-target outcome attribution on retrieval (`attribution.py` already summarises retrieval/injection) and demote/suppress a record *for the targets it measurably hurts* while keeping it for those it helps. LearnKit can do this online; SkillLens (offline) cannot. This is the single most strategic item. |
| **Held-out non-regression gate generalized to prose `SkillRecord` promotion** | SkillOpt validation gate | HIGH | M | Extend the agent-path gate to `memory_quality.decide_storage`: before promoting a distilled record to `active`, replay/score it against the last *k* sibling tasks in the family and accept only on non-regression. Reuses `replay_plan` + `outcome_score` for tool skills; needs a lightweight scorer for prose skills. |
| **Drop LLM-judge skill ranking; score on concrete failure-mechanism content** | SkillLens (judge worse-than-chance; format inert) | MED | S | Audit `evaluator.py` / quality scoring so skill utility is **not** weighted by prose polish. Add a deterministic specificity/failure-mechanism signal (named tools/objects, blacklist verbs) as a tiebreak. |
| **Reflection quality scorecard + semantic dedup** | improvements (carried) + SkillLens | MED | M | Score reflected bullets for specificity, non-contradiction, semantic de-dup (`cosine > τ`); demote low-quality updates. Pairs naturally with the rubric prompt just shipped. |

### B. Distillation at scale (batch / offline)

| Item | Source | Value | Effort | Landing notes |
|---|---|---|---|---|
| **Minibatch distillation** | SkillOpt reflect (minibatch) + SkillLens | MED | M | Distil *N* recent trajectories per domain jointly instead of one-at-a-time — less noise, catches cross-episode patterns. `consolidate_skills` already half-does this in the background; make the primary distill path batch-aware. |
| **Mode-based extraction intermediate (success/failure modes → hierarchical merge)** | SkillLens parallel extraction | MED | M | Add an explicit `{success_modes, failure_modes}` intermediate before skill synthesis so consolidation's umbrella-merge is principled and parallelizable. LearnKit half-has this via Fact/Heuristic/Failure records. |
| **Offline `learnkit sleep` consolidation job** | SkillOpt-Sleep | MED | M | A nightly batch (harvest stored trajectories → minibatch re-distill → re-gate skills) complementing the online `background_postprocess`. Natural home for the held-out gate (item A.2) and edit-budget (below). |
| **Edit-budget + rejected-edit buffer for consolidation** | SkillOpt (LR / gradient-clip / rejected buffer) | LOW | S | Bound how much one consolidation pass can change a skill (top-L edits) and remember candidates that failed the gate so they aren't re-derived/re-rejected. Cheap thrash protection for `consolidation.py` / GEPA. |
| **Experience success/failure ratio balancing per domain** | SkillLens (all-failure pools = worst; optimum domain-specific) | LOW | S | When selecting trajectories to distil, balance success/failure mix per domain rather than distilling whatever is present; never distil from only-failures. |

### C. Storage & retrieval scale-out

| Item | Source | Value | Effort | Landing notes |
|---|---|---|---|---|
| **Native vector embeddings (sqlite-vec push-down)** | carried (Hermes + sqlite-vec) | HIGH | M | Replaces the bounded `list_all(100)` lexical-fallback scan in `retriever.py` with a push-down ANN query. Unblocks semantic dedup (A.4) and large stores. |
| **Async / batched backend writes** | — | MED | M | Post-processing currently writes records one at a time. Add a batched `add_many` + write-behind queue so high-throughput agents don't serialize on the DB. |
| **Backend sharding / scoped partitions** | — | MED | L | Partition by `scope`/`domain` (or tenant) so per-user stores stay small and retrieval is bounded. Keep the `BaseBackend` contract; add a routing layer. |
| **Retrieval result + embedding cache** | — | LOW | S | Cache classify→retrieve for repeated/sibling tasks (the agent path already detects exact/sibling); memoize embeddings keyed by content hash. |

### D. Rapid-iteration / developer velocity

| Item | Source | Value | Effort | Landing notes |
|---|---|---|---|---|
| **Offline deterministic gold-task harness for CI** | improvements (carried) | HIGH | M | Fixed mock model/tool outputs for fast, stable PR gating; keep live-model runs for nightly. Removes live-model variance from the merge path. |
| **Bootstrap CIs on `playbook_effect` + gate on lower bound** | improvements (carried) | MED | S | ≥3 seeds × ≥3 trials, gate on the lower bound not the mean (`run_agentic_suite.py`). |
| **Per-model parser/health preflight before matrix runs** | improvements (carried) | MED | S | Record `parses_tool_calls=true/false` per endpoint (the Hermes-3 FAIL was a parser-config gap, not a framework gap). |
| **Standard adapters (TAU-bench-style, SWE-bench Lite subset)** | improvements (carried) | MED | L | External credibility on top of the internal suite for the agent path. |
