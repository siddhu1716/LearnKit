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
