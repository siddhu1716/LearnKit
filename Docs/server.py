"""
LearnKit marketing site + live Playground backend.
=====================================================

Serves the static landing page at /, and a /api/inspect endpoint that runs
the Classify -> Retrieve -> Compose stages of the LearnKit loop against
pre-seeded SQLite stores (one per benchmark domain). The Playground panel
on the page hits this endpoint so visitors can see the mechanism work on
their own task, against real distilled records from the v0.1.0 benchmark.

Run:
    pip install fastapi uvicorn[standard] python-dotenv
    # ANTHROPIC_API_KEY required (classifier uses Haiku)
    python Docs/server.py
    # then open http://localhost:8000/

Endpoints:
    GET  /                  -> Docs/index.html
    GET  /healthz           -> {"ok": true}
    GET  /api/domains       -> available playground domain stores
    POST /api/inspect       -> {classification, records, context, inference_mode}
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HERE = Path(__file__).parent
ROOT = HERE.parent
load_dotenv(ROOT / "benchmarks" / ".env")
load_dotenv(HERE / ".env")
sys.path.insert(0, str(ROOT))

import learnkit as lk  # noqa: E402
from learnkit.classifier import ClassificationOutput, classify_task  # noqa: E402
from learnkit.composer import compose_context  # noqa: E402
from learnkit.inference_mode import determine_inference_mode  # noqa: E402

PLAYGROUND_STORES: dict[str, dict] = {
    "python_debugging": {
        "label": "Python debugging",
        "db_path": HERE / "data" / "playground_python.db",
        "example": "Why does my multiprocessing.Pool().map() hang on macOS Python 3.12?",
    },
    "contract_summarization": {
        "label": "Contract summarization",
        "db_path": HERE / "data" / "playground_contract.db",
        "example": (
            "Summarize obligations, term, termination, and liability cap for "
            "a SaaS agreement with 99.9% uptime and a 12-month auto-renew."
        ),
    },
    "sql_authoring": {
        "label": "SQL authoring",
        "db_path": HERE / "data" / "playground_sql.db",
        "example": "Write Postgres SQL for the top 3 orders per customer using a window function.",
    },
}

MEMORIES: dict[str, lk.LearnKit] = {}


def _has_anthropic_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _stub_classifier(task: str) -> ClassificationOutput:
    """Offline fallback when ANTHROPIC_API_KEY is not set.

    Picks a domain label by keyword heuristic so the Playground stays usable
    without API keys. Retrieval uses FTS5 text matching, so the displayed
    classification need only inform the user, not the retriever.
    """
    t = task.lower()
    domains: dict[str, float] = {}
    if any(
        k in t
        for k in ["python", "asyncio", "multiprocess", "lambda", "def ", "import "]
    ):
        domains["Python"] = 0.9
    if any(
        k in t
        for k in [
            "contract",
            "obligation",
            "termination",
            "liability",
            "nda",
            "license",
        ]
    ):
        domains["Legal"] = 0.9
    if any(k in t for k in ["sql", "postgres", "select", "join", "window", "table"]):
        domains["SQL"] = 0.9
    if not domains:
        domains["General"] = 0.6
    complexity = "high" if len(task) > 300 else ("medium" if len(task) > 120 else "low")
    return ClassificationOutput(
        task_type="auto", domains=domains, complexity=complexity
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Pre-load the LearnKit instances and promote quarantined records once."""
    for key, cfg in PLAYGROUND_STORES.items():
        db = cfg["db_path"]
        if not db.exists():
            print(f"[warn] missing playground store: {db}")
            continue
        mem = lk.LearnKit(
            memory_backend="sqlite",
            db_path=str(db),
            scope="user",
            background_postprocess=False,
        )
        # Records from the benchmark are still in `quarantine` (24h probation).
        # Promote them now so the demo surfaces real distilled records.
        stats = mem.maintain_memory(quarantine_hours=0)
        print(f"[init] {key}: promoted={stats['promoted']} stale={stats['stale']}")
        MEMORIES[key] = mem
    yield
    for mem in MEMORIES.values():
        mem.shutdown(wait=True)


app = FastAPI(title="LearnKit", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # site is single-origin, but keep permissive for local dev
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class InspectRequest(BaseModel):
    task: str = Field(..., min_length=8, max_length=1000)
    domain: str = Field("python_debugging")


class InspectResponse(BaseModel):
    task: str
    classification: dict
    inference_mode: str
    records: list[dict]
    context: str
    context_chars: int
    notes: dict


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "stores": list(MEMORIES.keys())}


@app.get("/api/domains")
def list_domains() -> dict:
    out = []
    for key, cfg in PLAYGROUND_STORES.items():
        info = {"key": key, "label": cfg["label"], "example": cfg["example"]}
        mem = MEMORIES.get(key)
        if mem is not None:
            try:
                info["record_count"] = len(mem.backend.list_all(limit=500))
            except Exception:
                info["record_count"] = None
        out.append(info)
    return {"domains": out}


@app.post("/api/inspect", response_model=InspectResponse)
def inspect(req: InspectRequest) -> InspectResponse:
    mem = MEMORIES.get(req.domain)
    if mem is None:
        raise HTTPException(status_code=404, detail=f"unknown domain {req.domain!r}")

    if _has_anthropic_key():
        try:
            classification = classify_task(req.task)
        except Exception:
            classification = _stub_classifier(req.task)
            notes = {"classifier": "stub_fallback", "reason": "DSPy classifier raised"}
        else:
            notes = {"classifier": "dspy_haiku"}
    else:
        classification = _stub_classifier(req.task)
        notes = {"classifier": "stub_offline", "reason": "ANTHROPIC_API_KEY not set"}

    # Domain labels produced by the live classifier are freeform (e.g. "Python
    # Programming") and rarely match the stored records' domain strings byte-
    # for-byte. For Playground retrieval we deliberately bypass strict domain
    # filtering and let FTS5 text matching surface relevant records — same
    # algorithm, looser join condition.
    try:
        records = mem.retriever.retrieve(
            task=req.task, domain_vector={}, scope=mem.scope, router=mem.router
        )
    except Exception as e:
        records = []
        notes["retrieval_error"] = type(e).__name__

    mode = determine_inference_mode(records)
    context_block = compose_context(records, req.task, mode)

    return InspectResponse(
        task=req.task,
        classification={
            "task_type": classification.task_type,
            "domains": dict(classification.domains),
            "complexity": classification.complexity,
        },
        inference_mode=mode.value,
        records=[
            {
                "id": r.id[:8],
                "type": r.type,
                "task_type": r.task_type or "—",
                "domains": list(r.domains.keys())[:3],
                "confidence": round(r.confidence, 2),
                "reuse_count": r.reuse_count,
                "status": r.status,
                "snippet": _snippet(r),
            }
            for r in records
        ],
        context=context_block,
        context_chars=len(context_block),
        notes=notes,
    )


def _snippet(record) -> str:
    """Short readable summary of a record's content for the UI."""
    c = record.content or {}
    if record.type == "skill":
        steps = c.get("steps", [])
        if steps:
            return f"{len(steps)} steps: {steps[0][:80]}…"
        return "skill"
    if record.type == "failure":
        return (c.get("description") or c.get("what_to_avoid") or "failure")[:140]
    if record.type == "fact":
        return (c.get("statement") or "fact")[:140]
    if record.type == "trace":
        return f"trace (task={(c.get('task') or '')[:80]})"
    return str(c)[:140]


# --- Static assets ---
@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(ROOT / "docs" / "index.html")


# Serve sibling files like favicon if present
app.mount("/static", StaticFiles(directory=ROOT / "docs"), name="static")


@app.exception_handler(Exception)
async def unhandled(_, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": type(exc).__name__, "detail": str(exc)[:200]},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("Docs.server:app", host="127.0.0.1", port=port, reload=False)
