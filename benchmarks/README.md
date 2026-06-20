# LearnKit Benchmarks

Empirical validation that LearnKit's experience-distillation loop produces measurable improvement over a baseline agent.

## Design

Two arms, same model:

- **Control**: `agent(task)` — Gemini Flash, no memory, no LearnKit. Each task runs against a cold state.
- **Treatment**: `@lk.agent` wrapped `agent(task)` — Gemini Flash with LearnKit on top. Tasks run in order, so task N has access to the distilled skills/facts/failures from tasks 1..N-1.

Judge: Anthropic Claude Haiku (different vendor from the agent — independence is the point).

## Suites

| Suite | Tasks | Domains | Why |
|---|---|---|---|
| `custom_clustered` | 30 | python_debugging, contract_summarization, sql_authoring | Tasks within each domain share recurring patterns. This is the setup where LearnKit's compounding effect should appear. Built specifically for v0.1.0 internal validation. |
| `swe_bench_lite` | TBD | Real-world Python fixes | External-credibility benchmark. Scaffolded for v0.2.0 follow-up — needs Docker + a stronger agent model than Flash to produce meaningful absolute scores. |

## Agent-path benchmark matrix (`@lk.agent_learn`)

These measure the procedural path where value is step/cost reduction and
learning-by-injection on sibling tasks.

| Benchmark | Purpose | Core metric | Status |
|---|---|---|---|
| `run_agent_learn.py` | Deterministic replay/reuse smoke | tool-calls/task, success | Active |
| `agentic_bench.py` | Deterministic exact + sibling + unrelated mix | tool-calls/task, success, arg correctness | Active |
| `react_live.py` | Live hosted model, cold vs warmed with exact replay | LLM calls, tool calls, success | Active |
| `evolution_live.py` | Multi-round durability and reuse growth | reuse/confidence/evolution + cost | Active |
| `injection_ablation.py` | Isolated quality effect of playbook injection | compliance score on novel siblings | Active |

### Injection ablation (new)

`injection_ablation.py` is the direct answer to "does it truly learn?".

- 3 arms: `cold` vs `procedure` (tool scaffold only) vs `playbook` (scaffold + natural-language know-how).
- Novel sibling tasks only (no exact replay) to avoid conflating with memoization.
- Verifier checks real tool arguments for required conventions.

Example observed run (Qwen2.5-7B):

- `cold`: avg 0.50/3, full compliance 0/8
- `procedure`: avg 0.75/3, full compliance 0/8
- `playbook`: avg 3.00/3, full compliance 8/8

Interpretation: scaffold alone gave weak lift; injected playbook carried the quality jump.

## What the runner reports

For each (suite, arm, task):

- Response text
- Judge score 0–5
- Tokens in / out (when the SDK exposes them)
- Wall-clock latency
- For treatment: chars of `_learnkit_context` injected, inference mode, count of memory records retrieved

Aggregate output:

- `results/<suite>_<timestamp>.json` — full raw per-task records
- `results/<suite>_<timestamp>.md` — human-readable summary table + compounding curve (quality vs task index within a domain)

## Run it

```bash
pip install python-dotenv litellm
# Put GEMINI_API_KEY in benchmarks/.env (gitignored)
# Have ANTHROPIC_API_KEY set globally for the judge

python benchmarks/run_custom.py
```

Agent-path runs:

```bash
python -m benchmarks.run_agent_learn
python -m benchmarks.agentic_bench
python -m benchmarks.react_live
python -m benchmarks.evolution_live
python -m benchmarks.injection_ablation
```

For live-hosted runs (`react_live`, `evolution_live`, `injection_ablation`), set:

```bash
export LK_BASE_URL=http://206.1.58.252:8000/v1
export LK_MODEL=Qwen/Qwen2.5-7B-Instruct
export LK_API_KEY=none
```

Run cost is dominated by 30 × 2 = 60 agent calls + 60 judge calls + LearnKit's internal classifier/distiller calls during the treatment arm (~30 extra). Gemini Flash + Haiku is cheap — well under $2 for a full run.
