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

Run cost is dominated by 30 × 2 = 60 agent calls + 60 judge calls + LearnKit's internal classifier/distiller calls during the treatment arm (~30 extra). Gemini Flash + Haiku is cheap — well under $2 for a full run.
