# Contributing to LearnKit

Thanks for your interest in contributing! LearnKit is **procedural memory for
tool-using AI agents** — it captures the tool procedure that solved a task and
replays it on repeats. This guide gets you from clone to merged PR.

## Ways to contribute

- **Bug fixes** — find a repro, add a failing test, fix it.
- **Adapters** — add support for a new agent framework under `learnkit/adapters/`.
- **Backends** — add a storage backend under `learnkit/backends/` (implement the
  registry contract).
- **Benchmarks** — extend the agentic suite in `benchmarks/` with new task families.
- **Docs** — improve the README, the `architecture/` diagrams, or docstrings.

If you're planning a larger change, **open an issue first** to discuss the design.

## Development setup

```bash
git clone https://github.com/siddhu1716/LearnKit
cd LearnKit

python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -e ".[dev]"      # core SDK + pytest / ruff / mypy
pre-commit install           # enable commit hooks (ruff, formatting, hygiene)
```

No API key is required for development: the agent path and the deterministic
benchmarks run **keyless** (task classification falls back to a heuristic).
An `ANTHROPIC_API_KEY` only enables the optional LLM classifier/distiller.

## Run the checks (do this before every PR)

```bash
pytest -q                    # full test suite (fast, offline)
ruff check learnkit tests    # lint
ruff format --check learnkit # formatting
mypy learnkit                # type check (best-effort)
```

The frontend (observability dashboard) lives in `Docs/dashboard`:

```bash
cd Docs/dashboard
npm install
npm run build                # tsc + vite build must pass
```

## Where things live

| Path | What it is |
|---|---|
| `learnkit/core.py` | Orchestrator: `@memory.agent_learn`, `prepare_run` → `finalize_run` → post-process |
| `learnkit/tool_tracker.py` | `ToolTracker` — captures tool calls, the tool-success gate, plan attach |
| `learnkit/procedural.py` | `extract_procedure`, task-signature / coverage matching |
| `learnkit/replay.py` | `replay_plan` — execute a captured procedure with 0 LLM calls |
| `learnkit/adapters/react.py` | `run_react_agent` — auto-replay ReAct runner |
| `learnkit/drift.py` | `check_drift` + golden-suite export (procedure regression) |
| `learnkit/retriever.py`, `router.py`, `composer.py` | retrieve → route → compose |
| `learnkit/schemas/` | the 7 typed record kinds |
| `learnkit/backends/` | SQLite (default) + Qdrant / Mem0 / Zep + registry |
| `benchmarks/` | agentic suite + reproducible `RESULTS.json` / `MATRIX.md` |
| `Docs/` | FastAPI server (`server.py`) + React dashboard (`dashboard/`) |
| `architecture/` | Mermaid diagrams of the system |
| `examples/agent_learn_demo.py` | runnable offline cold→warm demo |

## Pull-request guidelines

1. **Branch** off `lia/agent_mvp` (or `main` once released): `feature/<short-name>`.
2. **Keep it focused** — one logical change per PR. Don't mix refactors with features.
3. **Add tests** for any behavior change; keep the suite green.
4. **Match the style** — the project uses `ruff` (line length 100). Run the checks above.
5. **Update docs** — if you change public behavior, update the README and/or `architecture/`.
6. **Write a clear PR description** — what, why, and how you verified it.

### PR checklist

- [ ] `pytest -q` passes
- [ ] `ruff check` clean
- [ ] New/changed behavior covered by tests
- [ ] Docs updated if the public API or behavior changed
- [ ] No secrets, keys, or large binaries committed

## Design principles (please preserve these)

- **Exact-match replay only.** A procedure is hard-replayed (0 LLM) *only* on an
  exact task-signature match. Siblings are **guided** (the model still plans) —
  never a fuzzy replay that could silently produce the wrong result.
- **Gate on the real outcome.** Storage/reinforcement is gated on the tool-success
  signal, not an LLM judge, on the agent path.
- **Bounded memory.** Retrieval is capped (≤ 8 records / ~1,200 tokens); don't
  remove the router caps.
- **Framework-agnostic + local-first.** Default backend is local SQLite; nothing
  phones home.

## Code of conduct

Be respectful and constructive. We follow the spirit of the
[Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions are licensed under the
project's [Apache License 2.0](LICENSE).
