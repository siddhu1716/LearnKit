# Architecture Diagrams

This folder contains Mermaid diagrams that explain LearnKit from multiple angles.

## Files and what they show

- `runtime_flow.mmd`
  - Scope: single task execution path through LearnKit.
  - Shows: classify -> retrieve -> route -> compose -> agent call -> evaluate -> distill -> persist.
  - Use when: you want to understand request-time behavior and where context is injected.

- `benchmark_flow.mmd`
  - Scope: benchmark orchestration pipeline.
  - Shows: task loading, control vs treatment arms, scoring, summarization, and output artifacts.
  - Use when: you want to understand how benchmark results are produced and where attribution metrics come from.

- `storage_lifecycle.mmd`
  - Scope: lifecycle of a memory record over time.
  - Shows: validation, initial status, promotion, reinforcement, demotion, stale/deprecated transitions.
  - Use when: you want to understand durability, memory quality controls, and maintenance effects.

- `full_system_flow.mmd`
  - Scope: full system view across runtime, post-processing, storage, adapters, and benchmarks.
  - Shows: module boundaries and how all major parts connect end-to-end.
  - Use when: you want a big-picture architecture map for onboarding or design review.

## Suggested reading order

1. `runtime_flow.mmd` for the core request loop.
2. `storage_lifecycle.mmd` for memory semantics and status transitions.
3. `benchmark_flow.mmd` for evaluation and experiment flow.
4. `full_system_flow.mmd` for a complete architecture overview.

## How to view

- Open any `.mmd` file in VS Code with Mermaid preview enabled.
- Or copy the content into mermaid.live for interactive viewing.
