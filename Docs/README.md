# LearnKit site

A single-page marketing site for LearnKit + a live **Playground** that runs the SDK's `Classify → Retrieve → Compose` stages against pre-seeded memory stores, **plus** the FastAPI backend that powers the observability dashboard under `Docs/dashboard`.

## What's here

| File | Purpose |
|---|---|
| `index.html` | The marketing page. Cream/serif/mono aesthetic, no build step. |
| `server.py` | FastAPI app — serves the page, the `/api/inspect` Playground endpoint, and the `/api/v1/*` dashboard API (records, runs, metrics, observability) against `LEARNKIT_DB_PATH` (default `~/.learnkit/memory.db`). |
| `data/playground_*.db` | SQLite memory stores pre-seeded with distilled records from the v0.1.0 benchmark run. One per Playground domain. |
| `dashboard/` | React/Vite/TypeScript observability dashboard (see [`dashboard/README.md`](dashboard/README.md)). Hits `/api/v1/*` from `server.py`; falls back to mock data if the backend is offline. |
| `learnkit_architecture.md` | Full architecture document (mechanism, agent path, mermaid diagrams). |
| `LEARNKIT_CONSOLIDATED_FLOW_PLAN.md` | Master execution flow document that consolidates roadmap, backlog, benchmark gates, and cross-repo production additions. |
| `FINAL_BENCHMARK_NUMBERS_2026-06-21.txt` | Single-model (Qwen2.5-7B) reference numbers — cited by the root README's Status section. |
| `FINAL_MODEL_MATRIX_2026-06-21.txt` | Cross-model matrix table. |
| `.env.example` | Copy to `.env` to override defaults. Gitignored. |

## How the Playground works

1. User types a task and picks a domain (python_debugging / contract_summarization / sql_authoring).
2. Browser POSTs to `/api/inspect`.
3. Server:
   - runs the **TaskClassifier** (DSPy + Claude Haiku if `ANTHROPIC_API_KEY` is set, else a keyword-heuristic stub),
   - runs the **SemanticRetriever** against the domain's pre-seeded SQLite store using FTS5 + BM25,
   - picks an **inference mode** based on top-record confidence,
   - composes the bounded prompt block (≤ 8 records, ≤ 1,200 tokens),
4. Browser renders the four artifacts: classification, mode, retrieved records, composed context.

The **agent execution + LLM-judge + distillation** steps from the full loop are *not* run here — this endpoint is read-only. That keeps the demo fast, cheap, and deterministic across visits.

## Run locally

```bash
# from repo root
pip install -e . fastapi 'uvicorn[standard]' python-dotenv
export ANTHROPIC_API_KEY="sk-ant-..."     # optional but recommended for classifier
export LEARNKIT_DB_PATH="$HOME/.learnkit/memory.db"  # default; override per-store
# Windows PowerShell: $env:LEARNKIT_DB_PATH = "$HOME\.learnkit\memory.db"
python Docs/server.py
# open http://127.0.0.1:8000/                  for the Playground page
# dashboard dev server: cd Docs/dashboard && npm run dev
#   -> http://localhost:5173/dashboard/        (proxies /api/* to :8000)
```

The page works without the server too — the Playground will just show "backend offline" and tell the visitor how to start it. Everything else (benchmarks, mechanism diagram, code snippet, comparison table) is static and renders normally. The dashboard equivalently falls back to mock data when `server.py` is offline.

## Why this exists

Marketing pages that *claim* "we have memory" don't convince engineers. Pages that *show* the actual classification output, the actual retrieved records (with IDs and confidence scores), and the actual prompt block that would be injected — those do. The Playground is the credibility move: same code path as production, real records, no marketing illusion.

## Deploy notes (production)

This is a single-process FastAPI app. For real deploy:

- Put it behind a reverse proxy (Caddy / Nginx) with HTTPS.
- Set a small rate limit on `/api/inspect` (e.g. 10 req / minute / IP via `slowapi`) — currently unlimited.
- Pin the `ANTHROPIC_API_KEY` budget alert; the classifier costs ~$0.0005 per visitor click.
- The playground DBs are read-only in spirit but writable on disk — mount them read-only or copy to a tmpfs at start if you're paranoid about state leaking.
- Static-only fallback: if you don't want to host the API, drop the `<section id="playground">` block from `index.html` and serve the file from any CDN.
