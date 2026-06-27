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
    GET  /                  -> Docs/dashboard/index.html (landing page)
    GET  /healthz           -> {"ok": true}
    GET  /api/domains       -> available playground domain stores
    POST /api/inspect       -> {classification, records, context, inference_mode}
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

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

# Live store: the user's real learning DB that the dashboard's /api/v1 endpoints
# read from. Defaults to the standard LearnKit home DB; override with
# LEARNKIT_DB_PATH. This is the store agents write to via @lk.agent_learn, so the
# dashboard reflects real agent runs (traces, calls reduced, skills learned).
LIVE_DB_PATH = os.environ.get(
    "LEARNKIT_DB_PATH", str(Path("~/.learnkit/memory.db").expanduser())
)
LIVE: dict[str, lk.LearnKit] = {}


def _live() -> lk.LearnKit:
    """Return the live LearnKit store, creating it on first use."""
    if "mem" not in LIVE:
        LIVE["mem"] = lk.LearnKit(
            memory_backend="sqlite",
            db_path=LIVE_DB_PATH,
            scope="user",
            background_postprocess=False,
        )
    return LIVE["mem"]



def _has_api_key() -> bool:
    return (
        bool(os.environ.get("ANTHROPIC_API_KEY")) or
        bool(os.environ.get("GEMINI_API_KEY")) or
        bool(os.environ.get("OPENAI_API_BASE"))
    )


def _stub_classifier(task: str) -> ClassificationOutput:
    """Offline fallback when no API keys are set.

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
    for mem in LIVE.values():
        mem.shutdown(wait=True)


app = FastAPI(title="LearnKit", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # site is single-origin, but keep permissive for local dev
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



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

    if _has_api_key():
        try:
            classification = classify_task(req.task)
        except Exception:
            classification = _stub_classifier(req.task)
            notes = {"classifier": "stub_fallback", "reason": "DSPy classifier raised"}
        else:
            if os.environ.get("ANTHROPIC_API_KEY"):
                clf_type = "dspy_haiku"
            elif os.environ.get("GEMINI_API_KEY"):
                clf_type = "dspy_gemini"
            else:
                clf_type = "dspy_qwen"
            notes = {"classifier": clf_type}
    else:
        classification = _stub_classifier(req.task)
        notes = {"classifier": "stub_offline", "reason": "No API keys or local base url configured"}

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


# ============================================================
# Dashboard API (/api/v1) — live agent-learning data
# Backed by the real LearnKit store (LIVE). The React dashboard
# (Docs/dashboard) consumes these; it falls back to mock data when
# an endpoint is unavailable.
# ============================================================


def _record_to_api(r) -> dict:
    """Map a backend MemoryRecord to the dashboard's record shape (snake_case;
    the client normalizes it)."""
    content = r.content or {}
    return {
        "id": r.id,
        "type": r.type,
        "task_type": r.task_type or "generic",
        "domains": list(r.domains.keys()),
        "confidence": round(float(r.confidence), 3),
        "content": content,
        "scope": r.scope,
        "status": r.status,
        "retrieval_count": r.reuse_count,
        "reuse_count": r.reuse_count,
        "help_count": int(content.get("success_count", r.reuse_count) or 0),
        "harm_count": int(content.get("_harmful_hits", 0) or 0),
        "neutral_count": 0,
        "generality": float(content.get("generality", 0.5) or 0.5),
        "task_overlap": float(content.get("_task_overlap", 0.0) or 0.0),
        "quality_score": float(content.get("_quality_score", r.success_rate or 0.0) or 0.0),
        "tags": list(r.domains.keys()),
        "created_at": r.created_at,
        "expires_at": r.expires_at,
    }


def _run_to_task(run: dict) -> dict:
    return {
        "id": run["run_id"],
        "input": run.get("task") or "",
        "status": "success" if run.get("outcome") == "success" else "failure",
        "score": round(float(run.get("quality_score") or 0.0), 2),
        "armName": "warmed" if run.get("replayed") else "coldStart",
        "timestamp": run.get("created_at"),
        "agentId": run.get("agent_id"),
        "toolCalls": run.get("tool_calls", 0),
        "callsReduced": run.get("calls_reduced", 0),
    }


@app.get("/api/v1/metrics")
def api_metrics() -> dict:
    mem = _live()
    records = mem.backend.list_all(limit=5000)
    runs = mem.backend.list_runs(limit=2000)

    counts = {t: 0 for t in ("skill", "failure", "fact", "strategy", "preference", "heuristic", "trace")}
    for r in records:
        if r.type in counts:
            counts[r.type] += 1
    total_records = sum(counts.values()) or 1

    success = [1.0 if r.get("outcome") == "success" else 0.0 for r in runs]
    success_rate = (sum(success) / len(success)) if success else 0.0

    # retry/calls reduction: average fractional reduction over replayed runs
    ratios = []
    inj_records, inj_replayed = [], 0
    for r in runs:
        base = r.get("baseline_calls")
        calls = r.get("tool_calls") or 0
        if base and base > 0 and calls is not None:
            ratios.append(max(0.0, (base - calls) / base))
        inj_records.append(len(r.get("record_ids") or []))
        if r.get("replayed"):
            inj_replayed += 1
    retry_reduction = (sum(ratios) / len(ratios)) if ratios else 0.0

    avg_records_injected = (sum(inj_records) / len(inj_records)) if inj_records else 0.0
    replayed_frac = (inj_replayed / len(runs)) if runs else 0.0

    router = mem.router
    max_tokens = getattr(router, "max_tokens", 1200)
    return {
        "recordCounts": counts,
        "lastUpdated": _now_iso(),
        "successRate": round(success_rate, 3),
        "avgTokens": int(avg_records_injected * 160),
        "retryReduction": round(retry_reduction, 3),
        "primaryDistribution": {
            "skill": round(counts["skill"] / total_records, 3),
            "failure": round(counts["failure"] / total_records, 3),
            "fact": round(counts["fact"] / total_records, 3),
        },
        "inferenceModeMix": {
            "prescriptive": round(replayed_frac, 3),
            "guided": 0.0,
            "exploratory": round(1.0 - replayed_frac, 3),
        },
        "retrieval": {
            "avgRecordsInjected": round(avg_records_injected, 2),
            "maxRecords": getattr(router, "max_records", 8),
            "avgTokensInjected": int(avg_records_injected * 160),
            "maxTokens": max_tokens,
            "avgRedundancy": 0.0,
            "diversityLambda": getattr(router, "diversity_lambda", 0.7),
        },
    }


@app.get("/api/v1/records")
def api_records(type: Optional[str] = None, status: Optional[str] = None) -> dict:
    mem = _live()
    records = mem.backend.list_all(limit=5000)
    out = [_record_to_api(r) for r in records]
    if type and type != "all":
        out = [r for r in out if r["type"] == type]
    if status:
        out = [r for r in out if r["status"] == status]
    return {"records": out}


@app.get("/api/v1/records/{record_id}")
def api_record(record_id: str) -> dict:
    mem = _live()
    r = mem.backend.read(record_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"record {record_id} not found")
    return _record_to_api(r)


@app.delete("/api/v1/records/{record_id}")
def api_delete_record(record_id: str) -> dict:
    mem = _live()
    mem.backend.remove(record_id)
    return {"deleted": True}


@app.post("/api/v1/records/{record_id}/reinforce")
def api_reinforce(record_id: str) -> dict:
    mem = _live()
    r = mem.backend.read(record_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"record {record_id} not found")
    new_conf = min(0.95, r.confidence + 0.05)
    mem.backend.update_confidence(record_id, new_conf)
    return {"id": record_id, "confidence": round(new_conf, 3)}


@app.post("/api/v1/records/{record_id}/demote")
def api_demote(record_id: str) -> dict:
    mem = _live()
    r = mem.backend.read(record_id)
    if r is None:
        raise HTTPException(status_code=404, detail=f"record {record_id} not found")
    new_conf = max(0.0, r.confidence - 0.10)
    mem.backend.update_confidence(record_id, new_conf)
    return {"id": record_id, "confidence": round(new_conf, 3)}


@app.get("/api/v1/tasks")
def api_tasks(status: Optional[str] = None, agentId: Optional[str] = None) -> dict:
    mem = _live()
    runs = mem.backend.list_runs(agent_id=agentId, limit=1000)
    tasks = [_run_to_task(r) for r in runs]
    if status and status != "all":
        tasks = [t for t in tasks if t["status"] == status]
    return {"tasks": tasks}


@app.get("/api/v1/tasks/{task_id}/trace")
def api_trace(task_id: str) -> dict:
    mem = _live()
    run = mem.backend.get_run(task_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run {task_id} not found")

    matches = []
    for i, rid in enumerate(run.get("record_ids") or []):
        rec = mem.backend.read(rid)
        if rec is None:
            continue
        matches.append({
            "recordId": rec.id,
            "type": rec.type,
            "confidence": round(float(rec.confidence), 3),
            "score": round(float(rec.confidence), 3),
            "reason": "retrieved",
            "droppedByMmr": False,
            "primary": i == 0,
        })

    steps = run.get("steps") or []
    attempts = [
        {
            "prompt": s.get("content", ""),
            "response": "",
            "feedback": f"{s.get('role')} {s.get('tool_name') or ''}".strip(),
        }
        for s in steps
    ]
    return {
        "taskId": run["run_id"],
        "input": run.get("task") or "",
        "inferenceMode": "prescriptive" if run.get("replayed") else "exploratory",
        "memoryRetrieval": {
            "budget": {
                "recordsUsed": len(matches),
                "maxRecords": getattr(mem.router, "max_records", 8),
                "tokensUsed": len(matches) * 160,
                "maxTokens": getattr(mem.router, "max_tokens", 1200),
                "diversityLambda": getattr(mem.router, "diversity_lambda", 0.7),
                "redundancy": 0.0,
            },
            "matches": matches,
        },
        "reasoning": {"attempts": attempts},
        "output": (steps[-1].get("content") if steps else "") or "",
        "expected": "",
        "score": round(float(run.get("quality_score") or 0.0), 2),
        "toolCalls": run.get("tool_calls", 0),
        "callsReduced": run.get("calls_reduced", 0),
        "baselineCalls": run.get("baseline_calls"),
        "attribution": [
            {
                "recordId": m["recordId"],
                "rank": i + 1,
                "primary": m["primary"],
                "reuseCount": 0,
                "helped": run.get("outcome") == "success",
            }
            for i, m in enumerate(matches)
        ],
    }


@app.get("/api/v1/agents")
def api_agents() -> dict:
    mem = _live()
    summaries = mem.backend.agent_summaries()
    agents = [
        {
            "id": s["agent_id"],
            "name": s.get("agent_name") or s["agent_id"],
            "taskCount": s["task_count"],
            "successRate": round(float(s["success_rate"] or 0.0), 3),
            "callsReduced": round(float(s["calls_reduced"] or 0.0), 1),
            "skillsLearned": int(s.get("skills_learned") or 0),
            "avgScore": round(float(s["avg_score"]), 2) if s.get("avg_score") is not None else None,
            "createdAt": s.get("created_at"),
            "lastActive": s.get("last_active"),
        }
        for s in summaries
    ]
    return {"agents": agents}


@app.get("/api/v1/agents/{agent_id}/stats")
def api_agent_stats(agent_id: str) -> dict:
    mem = _live()
    runs = list(reversed(mem.backend.list_runs(agent_id=agent_id, limit=1000)))
    if not runs:
        raise HTTPException(status_code=404, detail=f"agent {agent_id} has no runs")

    curve = []
    cumulative_skills = 0
    success_window: list[float] = []
    for i, r in enumerate(runs):
        is_cold_success = (not r.get("replayed")) and r.get("outcome") == "success"
        if is_cold_success:
            cumulative_skills += 1
        success_window.append(1.0 if r.get("outcome") == "success" else 0.0)
        recent = success_window[-10:]
        curve.append({
            "index": i + 1,
            "task": (r.get("task") or "")[:80],
            "toolCalls": r.get("tool_calls", 0),
            "baselineCalls": r.get("baseline_calls"),
            "callsReduced": round(float(r.get("calls_reduced") or 0.0), 1),
            "replayed": bool(r.get("replayed")),
            "outcome": r.get("outcome"),
            "score": round(float(r.get("quality_score") or 0.0), 2),
            "cumulativeSkills": cumulative_skills,
            "successRate": round(sum(recent) / len(recent), 3),
            "timestamp": r.get("created_at"),
        })

    total_reduced = sum(max(0.0, float(r.get("calls_reduced") or 0.0)) for r in runs)
    total_calls = sum(int(r.get("tool_calls") or 0) for r in runs)
    success = [1.0 if r.get("outcome") == "success" else 0.0 for r in runs]
    return {
        "agentId": agent_id,
        "agentName": runs[-1].get("agent_name") or agent_id,
        "taskCount": len(runs),
        "successRate": round(sum(success) / len(success), 3) if success else 0.0,
        "callsReduced": round(total_reduced, 1),
        "totalToolCalls": total_calls,
        "skillsLearned": cumulative_skills,
        "curve": curve,
    }


@app.get("/api/v1/lifecycle/quarantine")
def api_quarantine() -> dict:
    mem = _live()
    records = [r for r in mem.backend.list_all(limit=5000) if r.status == "quarantine"]
    out = []
    for r in records:
        out.append({
            "id": r.id,
            "type": r.type,
            "content": _snippet(r),
            "confidence": round(float(r.confidence), 3),
            "createdAt": r.created_at,
            "promotableAfter": r.created_at,
        })
    return {"records": out}


@app.post("/api/v1/maintain")
def api_maintain(body: Optional[dict] = None) -> dict:
    mem = _live()
    body = body or {}
    stats = mem.maintain_memory(
        quarantine_hours=float(body.get("quarantineHours", 0)),
        decay_rate=float(body.get("decay", 0.02)),
    )
    return {
        "promoted": stats.get("promoted", 0),
        "decayed": stats.get("decayed", 0),
        "staled": stats.get("stale", 0),
        "purged": stats.get("consolidated_archived", 0),
    }


@app.get("/api/v1/activity")
def api_activity() -> dict:
    mem = _live()
    runs = mem.backend.list_runs(limit=20)
    events = []
    for r in runs:
        ok = r.get("outcome") == "success"
        icon = "📚" if (ok and not r.get("replayed")) else ("♻️" if r.get("replayed") else "⚠️")
        verb = "learned from" if (ok and not r.get("replayed")) else ("replayed a skill on" if r.get("replayed") else "struggled with")
        events.append({
            "time": (r.get("created_at") or "")[11:16],
            "icon": icon,
            "message": f"{r.get('agent_name') or r.get('agent_id')} {verb}: {(r.get('task') or '')[:48]}",
        })
    return {"events": events}


@app.get("/api/v1/config/diversity")
def api_get_diversity() -> dict:
    return {"diversityLambda": getattr(_live().router, "diversity_lambda", 0.7)}


@app.put("/api/v1/config/diversity")
def api_set_diversity(body: dict) -> dict:
    mem = _live()
    val = float(body.get("diversityLambda", 0.7))
    mem.router.diversity_lambda = val
    return {"diversityLambda": val}


@app.get("/api/v1/metrics/crowded-out")
def api_crowded_out() -> dict:
    return {"records": []}


# --- Static assets ---
# Prefer the built dashboard (Docs/dashboard/dist) when present so the live
# React app + landing page are served from one origin; fall back to the source
# directory for dev. The app uses HashRouter, so no server-side SPA rewrite is
# needed.
_DIST = HERE / "dashboard" / "dist"
SITE_DIR = _DIST if _DIST.exists() else HERE / "dashboard"


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(SITE_DIR / "index.html")


@app.get("/app.html", include_in_schema=False)
def dashboard_app() -> FileResponse:
    return FileResponse(SITE_DIR / "app.html")


# Serve the dashboard's static frontend (landing page, app, docs, assets).
app.mount("/static", StaticFiles(directory=HERE / "dashboard"), name="static")
app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")


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
