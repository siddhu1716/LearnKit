# improvements.md — Pending Enhancements

This file lists the remaining improvements that are not yet completed, after removing tasks already addressed in the current implementation.

## Original POC Improvements (still pending)

| Improvement | Status | Reason |
|---|---|---|
| Native Vector Embeddings (`sqlite-vec` or `Qdrant`) | **Pending** | Vector store integration and push‑down query not fully verified. |
| Dynamic Domain Adaptation | **Pending** | Requires extensive tracing; scheduled for v2. |
| Time‑Aware Exponential Confidence Decay | **Pending** | Linear decay sufficient for v1.0. |
| Auto‑Instrumenting AST Parser | **Pending** | Invasive; will rely on explicit wrappers for v1.0. |
| Local Dashboard / Wiki Viewer | **Pending** | Developer tooling after core stability. |

## New Discoveries (still pending)

| Improvement | Status | Reason |
|---|---|---|
| Push‑down Vector Retrieval (eliminate `list_all()`) | **In Progress** | Refactoring `retriever.py` to use DB‑side distance computation. |
| Memory Pollution Controls (quarantine promotion, confidence floor) | **Pending** | Quarantine-exclusion-from-retrieval is now in place (see Fixed). Still pending: explicit promotion API + confidence-floor filter. |
| GEPA Evolution Hardening (lineage, dedupe, trial failure handling) | **Pending** | Planned after core modules stabilize. |
| Optional Backends (`mem0`, `zep`, `qdrant`) | **Pending** | Implement adapters and contract tests. |
| Native Adapter Integrations (LangChain, LangGraph, AutoGen, OpenAI/Anthropic) | **Pending** | Build real framework adapters. (LangChain end-to-end already demonstrated via `examples/langchain_demo.py`; native callback / node / reply integrations still to do.) |
| Post‑processing interpreter-shutdown race (judge call after Py_Finalize) | **Partial** | The atexit drain (A3 below) eliminates the LearnKit-pool case ("after shutdown"). A narrower race remains when the in-flight evaluator's LLM call internally schedules sub-tasks after `sys.is_finalizing()` returns True — warning becomes `cannot schedule new futures after interpreter shutdown` and the evaluator's fallback-score path still works. Full fix requires either ensuring background work completes before atexit or directing users to `background_postprocess=False` (which is what `examples/langchain_demo.py` does). Document this in the README quickstart. |

## Fixed in this pass (May 2026)

| Item | Where | Notes |
|---|---|---|
| `LearnKit(scope=...)` not threaded onto distilled records | `core.py:_post_process_now` | Distiller-produced skills/facts/failures/traces, plus the low-quality `FailureRecord` fallback, now inherit `self.scope`. Regression test: `tests/test_phase3.py::test_distilled_records_inherit_instance_scope`. |
| `[langchain]` install extra | `pyproject.toml` | `pip install learnkit[langchain]` pulls `langchain`, `langchain-anthropic`, `langchain-core`. |
| `self.scope` typing as `MemoryScope` | `core.py` | Cleared the 5 new mypy errors my scope-plumbing fix introduced; total project mypy errors 25 → 19 (remaining are pre-existing). |
| **A1 — Quarantine excluded from active retrieval** | `backends/sqlite.py:374,385` (pre-existing, verified) | Verified by `tests/test_backend_contract.py:194` ("quarantined is not returned in search") which already pins this AGENTS_V2 production rule. |
| **A2 — Write-time scope validation** | `backends/sqlite.py:add()` | `SQLiteBackend.add` now raises `BackendError` if `record.scope` is not in `{"user","team","public"}`. Pydantic validates on construction but `validate_assignment=False` by default, so post-construction mutation could previously slip an invalid scope into the DB and break the next read. Regression test: `tests/test_production_hardening.py::test_add_rejects_invalid_scope_with_backenderror`. |
| **A3 — atexit drain of worker pool** | `core.py` | `LearnKit.__init__` registers an `atexit` handler that calls `self.shutdown(wait=True)` via a `weakref` (so it doesn't keep dead instances alive). New `shutdown(wait=True)` method drains the pool; idempotent. `_post_process_async` falls back to sync if already shut down. Eliminates the "after shutdown" warning class; the narrower interpreter-shutdown race is now the only remaining variant (see Pending). Regression tests: `tests/test_production_hardening.py::test_shutdown_is_idempotent_and_pool_drains`, `test_post_process_falls_back_to_sync_after_shutdown`. |
| **A4 — Router token budget enforcement** | `router.py` | `MemoryRouter.route` now caps results at both `max_records=8` AND `max_tokens≈1200` (per-record char estimate × 4-chars-per-token), preserving failure > skill > fact > others priority and always admitting at least one record even if it exceeds the budget on its own. Closes AGENTS_V2 Task H8. LangChain demo run 2 went from 610 → 924 chars of injected context (more efficient packing within budget). Regression tests: 4 tests in `tests/test_production_hardening.py`. |

## Fixed in this pass (May 2026)

| Item | Where | Notes |
|---|---|---|
| `LearnKit(scope=...)` not threaded onto distilled records | `core.py:_post_process_now` | Distiller-produced skills/facts/failures/traces, plus the low-quality `FailureRecord` fallback, now inherit `self.scope`. Without this, any non-default scope wrote records as `team` but retrieved with the custom scope → zero hits. Regression test: `tests/test_phase3.py::test_distilled_records_inherit_instance_scope`. |
| `[langchain]` install extra | `pyproject.toml` | `pip install learnkit[langchain]` now pulls `langchain`, `langchain-anthropic`, `langchain-core` for the `examples/langchain_demo.py` integration path. |
