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
| Router Token Budget Enforcement (8 records + ~1200 tokens) | **Pending** | Needed to prevent memory soup. |
| Memory Pollution Controls (quarantine promotion, confidence floor) | **Pending** | To be added in upcoming sprint. |
| GEPA Evolution Hardening (lineage, dedupe, trial failure handling) | **Pending** | Planned after core modules stabilize. |
| Optional Backends (`mem0`, `zep`, `qdrant`) | **Pending** | Implement adapters and contract tests. |
| Native Adapter Integrations (LangChain, LangGraph, AutoGen, OpenAI/Anthropic) | **Pending** | Build real framework adapters. |
| Post‑processing background race (judge call after worker pool shutdown) | **Pending** | `core.py` worker pool is closed at interpreter exit while in‑flight evaluator/distiller futures still schedule sub‑tasks. Quick‑start emits `eval_model_call_fail: cannot schedule new futures after shutdown`; evaluator falls back to heuristic score. Fix needs explicit pool drain or `atexit` join before shutdown. |
| Quarantine excluded from active retrieval | **Pending** | AGENTS_V2 production rules require quarantined records to be invisible until promoted, but `SQLiteBackend.search` only excludes `stale`. Today quarantined skills DO appear in retrieval (lucky for the langchain demo; wrong for production). Pair with the "Memory Pollution Controls" item above. |
| Scope validation deferred to read time | **Pending** | `MemoryRecord.scope` is `Literal['user','team','public']`, but `SQLiteBackend.add` writes whatever string it gets and `parse_record` is the one that rejects it. Result: an invalid `scope` value silently writes a poison row that explodes on subsequent reads. Validate (or coerce) at write time, or raise a typed `BackendError` early. |

## Fixed in this pass (May 2026)

| Item | Where | Notes |
|---|---|---|
| `LearnKit(scope=...)` not threaded onto distilled records | `core.py:_post_process_now` | Distiller-produced skills/facts/failures/traces, plus the low-quality `FailureRecord` fallback, now inherit `self.scope`. Without this, any non-default scope wrote records as `team` but retrieved with the custom scope → zero hits. Regression test: `tests/test_phase3.py::test_distilled_records_inherit_instance_scope`. |
| `[langchain]` install extra | `pyproject.toml` | `pip install learnkit[langchain]` now pulls `langchain`, `langchain-anthropic`, `langchain-core` for the `examples/langchain_demo.py` integration path. |
