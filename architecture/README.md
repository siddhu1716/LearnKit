# Architecture Diagrams

This folder contains Mermaid diagrams that explain LearnKit from multiple angles.

LearnKit has **two learning paths** that share one substrate (classify → retrieve →
route → compose → evaluate → store):

- **Model path (`@lk.learn`)** — treats the agent as a black box, learns from the
  final answer. See `runtime_flow.mmd`.
- **Agent path (`@lk.agent_learn`)** — observes the agent's tool calls, captures the
  cleaned tool *procedure*, and replays it on repeats (exact) or guides siblings.
  See `agent_runtime_flow.mmd`.

## Files and what they show

- `runtime_flow.mmd`
  - Scope: single task execution through the **model path** (`@lk.learn`).
  - Shows: classify -> retrieve -> route -> compose -> agent call -> evaluate -> distill -> persist.
  - Use when: you want to understand request-time behavior and where context is injected.

- `agent_runtime_flow.mmd`
  - Scope: single task execution through the **agent path** (`@lk.agent_learn`).
  - Shows: classify/retrieve/compose (shared) -> ToolTracker inject -> procedure match
    (exact/sibling/none) -> replay or guided/cold run -> tool-success gate ->
    procedure capture -> reinforce/demote -> persist.
  - Use when: you want to understand procedure capture, exact replay (zero-LLM),
    and sibling guidance for tool-using agents.

- `benchmark_flow.mmd`
  - Scope: benchmark orchestration pipeline.
  - Shows: task loading, control vs treatment arms, scoring, summarization, and output artifacts.
  - Use when: you want to understand how benchmark results are produced and where attribution metrics come from.

- `storage_lifecycle.mmd`
  - Scope: lifecycle of a memory record over time (both paths share it).
  - Shows: validation, initial status, promotion, reinforcement, demotion, stale/deprecated transitions.
  - Use when: you want to understand durability, memory quality controls, and maintenance effects.

- `full_system_flow.mmd`
  - Scope: full system view across runtime, the agent-path capture/replay branch, post-processing, storage, adapters, and benchmarks.
  - Shows: module boundaries and how all major parts (both decorators) connect end-to-end.
  - Use when: you want a big-picture architecture map for onboarding or design review.

## Suggested reading order

1. `runtime_flow.mmd` for the core request loop (model path).
2. `agent_runtime_flow.mmd` for procedure capture and replay (agent path).
3. `storage_lifecycle.mmd` for memory semantics and status transitions.
4. `benchmark_flow.mmd` for evaluation and experiment flow.
5. `full_system_flow.mmd` for a complete architecture overview.

## How to view

- Open any `.mmd` file in VS Code with Mermaid preview enabled.
- Or copy the content into mermaid.live for interactive viewing.
