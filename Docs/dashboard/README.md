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
