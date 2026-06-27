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
- Supports multi-trial runs (`--trials`), pass^k reporting (`--k`), seeded task-order shuffles (`--seed`), and persisted detailed/summary JSON artifacts.

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
python -m benchmarks.injection_ablation --trials 3 --k 3 --seed 7
python -m benchmarks.run_agentic_suite --trials 3 --k 3 --seed 7
python -m benchmarks.run_agentic_matrix --trials 1 --k 1 --seed 7
```

One-command suite runner (new):

- `benchmarks/run_agentic_suite.py` orchestrates `react_live`, `evolution_live`,
	and `injection_ablation` in one run.
- Produces merged artifacts:
	- `benchmarks/results/agentic_suite_<timestamp>_detailed.json`
	- `benchmarks/results/agentic_suite_<timestamp>_summary.json`
- Enforces the first regression gate by default:
	- `playbook_effect = avg_score(playbook) - avg_score(procedure)`
	- fail if `playbook_effect < --min-playbook-effect` (default `0.5`)

Useful flags:

```bash
# fast validation (injection-only)
python -m benchmarks.run_agentic_suite --skip-react --skip-evolution --trials 1 --k 1

# full suite with reflection enabled for evolution benchmark
python -m benchmarks.run_agentic_suite --trials 3 --k 3 --reflect

# run across hosted model matrix (current self-hosted lineup)
#   :8000 Qwen/Qwen2.5-Coder-32B-Instruct
#   :8001 Qwen/Qwen2.5-32B-Instruct
#   :8002 Qwen/Qwen2.5-14B-Instruct
python -m benchmarks.run_agentic_matrix --trials 1 --k 1 --seed 7 --per-model-timeout 1800 --react-timeout 1500 --evolution-timeout 1500 --injection-timeout 1500 --continue-on-fail
```

Injection ablation artifacts are written to `benchmarks/results/`:

- `<prefix>_<timestamp>_detailed.json`
- `<prefix>_<timestamp>_summary.json`

For live-hosted runs (`react_live`, `evolution_live`, `injection_ablation`), set:

```bash
export LK_BASE_URL=http://127.0.0.1:8002/v1
export LK_MODEL=Qwen/Qwen2.5-14B-Instruct
export LK_API_KEY=none
```

Run cost is dominated by 30 × 2 = 60 agent calls + 60 judge calls + LearnKit's internal classifier/distiller calls during the treatment arm (~30 extra). Gemini Flash + Haiku is cheap — well under $2 for a full run.

## Trace capture for the observability dashboard

The suite scripts above (`react_live.py`, `evolution_live.py`,
`injection_ablation.py`) instantiate `LearnKit(db_path=":memory:")` and
`db_path=tempfile.gettempdir()/learnkit_evolution.db` by design — each run is
self-contained so the regression gate is reproducible. **Their traces do not
flow to the React dashboard** at `Docs/dashboard`.

To populate the dashboard with real agent runs (instead of mock data), use a
short driver that writes to the dashboard's live store:

```bash
# point any agent run at the dashboard's live DB
export LEARNKIT_DB_PATH="$HOME/.learnkit/memory.db"   # Windows: %USERPROFILE%\.learnkit\memory.db

# any script that instantiates LearnKit(db_path=os.environ["LEARNKIT_DB_PATH"])
# will land its runs/records in the same store the FastAPI backend reads from.
python examples/minimal_agent.py
```

Then start the dashboard server and open the UI:

```bash
python Docs/server.py                            # serves /api/v1/* against $LEARNKIT_DB_PATH
cd Docs/dashboard && npm run dev                 # opens http://localhost:5173/dashboard/
```

The dashboard's `client.ts` falls back to mock data when the FastAPI backend
is unreachable; with `server.py` live, it surfaces the real `runs`,
`records`, and per-run telemetry written by
`learnkit/core.py:insert_run`.
