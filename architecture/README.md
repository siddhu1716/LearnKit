# Architecture Diagrams

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/siddhu1716/LearnKit)

This folder contains Mermaid diagrams that explain LearnKit from multiple angles.

LearnKit centers on **one learning path** — the agent (tool) path — over a shared
substrate (classify → retrieve → route → compose → evaluate → store) and one
persistence layer with **two tables**: `records` (typed memory) and `runs`
(per-run telemetry: mode, calls-reduced, tokens, cost, latency — what the
dashboard renders).

- **Agent path (`@lk.agent_learn`)** — the path. Observes the agent's tool
  calls, captures the cleaned tool *procedure*, and replays it on repeats (exact,
  zero-LLM) or guides siblings. Tagged `learning_mode = agent_learn`.
  See `agent_runtime_flow.mmd`.

Scoring degrades gracefully: when no judge key is set the evaluator uses a
transparent **deterministic heuristic** (signal `HEURISTIC`) instead of silently
failing the quality gate; `/healthz` surfaces which mode is active.

## Files and what they show

- `high_level_architecture.mmd`
  - Scope: **the whole system in one colored, at-a-glance picture** — your agent,
    the LearnKit learning layer (retrieve → match → replay/guide/capture), the
    local memory store, and the observability dashboard.
  - Use when: you want the fastest possible mental model, or a screenshot-ready
    diagram for a README / slide (render at [mermaid.live](https://mermaid.live),
    export PNG).

- `agent_runtime_flow.mmd`
  - Scope: single task execution through the **agent path** (`@lk.agent_learn`).
  - Shows: classify/retrieve/compose (shared) → ToolTracker inject → procedure
    match (exact/sibling/none) → replay or guided/cold run → tool-success gate →
    procedure capture → reinforce/demote → persist, plus agent-path telemetry
    (`mode`, `calls_reduced`, `replayed`) to the `runs` table.
  - Use when: you want procedure capture, exact replay (zero-LLM), and sibling
    guidance for tool-using agents.

- `benchmark_flow.mmd`
  - Scope: the **agentic benchmark + reproducible artifact** pipeline.
  - Shows: `run_agentic_matrix` → `run_agentic_suite` per model → three
    deterministic sub-benchmarks (`react_live`, `evolution_live`,
    `injection_ablation`, with per-task / per-round capture) → pinned summary
    JSON → `make_results` → committed `RESULTS.json` + `MATRIX.md` (with `--check`
    drift guard in CI) → `seed_dashboard` → `runs`/`records` → FastAPI
    `/api/v1/benchmarks` → dashboard Benchmarks page.
  - Use when: you want to understand how the published numbers are produced,
    pinned, and reproduced ("clone → one command → see the table").

- `storage_lifecycle.mmd`
  - Scope: lifecycle of a memory record over time (both paths share it).
  - Shows: validation, TTL policy (default per-type expiry **or** persist-forever
    when `record_ttl` is off / `LEARNKIT_PERSIST_FOREVER`), quarantine → promote,
    reinforce/demote, stale/deprecated transitions, and the **non-destructive
    default** of `maintain_memory` (only promotes; decay/stale/consolidate are
    opt-in).
  - Use when: you want durability, quality controls, and maintenance semantics.

- `product_architecture.mmd`
  - Scope: **product-level** architecture map derived from the graphify
    knowledge graph (`graphify-out/graph.json` — 2265 nodes · 4347 edges ·
    168 communities). Groups the codebase into its ten major subsystems —
    Client, Framework Adapters, Core Orchestrator, Read Path, Agent Path,
    Post-Process Learning, Evolution, Memory Schemas, Storage Backends,
    Observability/CLI, Dashboard (React), API Server, and Benchmarks —
    and shows how they wire together.
  - Use when: onboarding at the product level, discussing scope with
    stakeholders, or planning cross-subsystem changes.

## Suggested reading order

1. `product_architecture.mmd` for the product-level subsystem map.
2. `agent_runtime_flow.mmd` for procedure capture and replay (the path).
3. `storage_lifecycle.mmd` for memory semantics and status transitions.
4. `benchmark_flow.mmd` for the reproducible benchmark artifact + dashboard.

## How to view

- Open any `.mmd` file in VS Code with Mermaid preview enabled.
- Or copy the content into mermaid.live for interactive viewing.
