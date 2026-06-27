# LearnKit Observability Dashboard — Frontend Client

This is the Vite + React + TypeScript observability dashboard for LearnKit, built to match the **v1.1 Frontend Design Document**.

## Features

- **Dashboard Home**: Live stats cards, task metric aggregations, primary record injection distributions, and success rate trends comparing evaluation arms.
- **Playground**: Submit tasks to see real-time task type classification, confidence-weighted memory retrieval, and system context prompt composition.
- **Memory Explorer**: Search, sort, filter, view details, edit, add, and delete records across all 7 types of memories (`Skill`, `Fact`, `Failure`, `Strategy`, `Preference`, `Heuristic`, and `Trace`).
- **Retrieval Quality**: Track average context utilization, pairwise Jaccard redundancy indicators, inference mode splits, MMR diversity parameters, and consolidate duplicated crowded-out records.
- **Task History**: Timeline list of past evaluation tasks with navigation to vertical trace timelines.
- **Trace Playback**: Detailed playback timelines showing prompt queries, retrieved matches, MMR-dropped records, injected context formatting, CoT reasoning steps, and human-in-the-loop attribution feedback buttons (Reinforce/Demote).
- **Memory Lifecycle**: Manage quarantined records and trigger automated maintenance curation routines (decaying confidence score rates, staling low-performance items).
- **Settings**: Adjust threshold configurations, quarantine limits, automatic decay policies, PII scrubbing expressions, and local-first compliance constraints.

## Tech Stack

- **Framework**: React 18+ & TypeScript (strict compiler settings)
- **Tooling**: Vite (hot reloading, development proxy configuration)
- **Routing**: React Router v6
- **Styling**: Pure CSS Modules (no third-party styling frameworks, styled according to theme design tokens)
- **Charts**: Recharts
- **Aesthetics**: Sleek dark mode utilizing deep glassmorphic layers, harmonize accents (`#00ff88` and `#a78bfa`), smooth page transitions (200ms), and hover micro-animations.

## Installation & Running

1. Make sure you have **Node.js** (v18+) and **npm** installed on your system.
2. Navigate to this directory in your terminal:
   ```bash
   cd LearnKit/Docs/dashboard
   ```
3. Install the dependencies:
   ```bash
   npm install
   ```
4. Run the local development server:
   ```bash
   npm run dev
   ```
5. Open your browser to the local server address shown in the terminal (typically `http://localhost:5173/dashboard/`).

## API Proxy

The Vite dev server is configured with a proxy to forward API requests starting with `/api` to the local FastAPI backend running at `http://127.0.0.1:8000`. If the FastAPI backend is offline or pending the implementation of the v1.1 endpoints, the dashboard automatically falls back to a mock simulation layer powered by `localStorage` so all screens remain fully functional and interactive.

## See real data instead of mock

The mock fallback is what you see on a fresh checkout. To wire the dashboard
to **real agent runs** (real `records`, real `runs` with per-run telemetry):

1. Start the FastAPI backend that serves `/api/v1/*` against the live store:

   ```bash
   # from repo root
   export LEARNKIT_DB_PATH="$HOME/.learnkit/memory.db"      # default; override per-store
   # Windows PowerShell: $env:LEARNKIT_DB_PATH = "$HOME\.learnkit\memory.db"
   python Docs/server.py                                     # FastAPI on :8000
   ```

2. Generate some runs into the same DB (any `@lk.agent` or `@lk.agent_learn`
   script that uses `LearnKit(db_path=os.environ["LEARNKIT_DB_PATH"])`):

   ```bash
   python examples/minimal_agent.py                          # writes runs + records
   ```

3. Run this dashboard against that backend:

   ```bash
   cd Docs/dashboard && npm run dev                          # http://localhost:5173/dashboard/
   ```

The API contract the client expects is implemented in
[`Docs/server.py`](../server.py) (`/api/v1/metrics`, `/records`,
`/records/{id}`, `/records/{id}/reinforce|demote`, `/tasks`,
`/observability`). Anything the backend does not yet implement gracefully
falls back to mock per-screen so the UI never breaks.

> **Note (MVP):** the `agentic_*` benchmarks under `benchmarks/` use
> `db_path=":memory:"` so their gate runs stay self-contained. They do **not**
> populate the dashboard. Use the path above (or any agent script with
> `db_path` pointed at `$LEARNKIT_DB_PATH`) to see real traces in the UI.
