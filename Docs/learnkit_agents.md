# AGENTS.md — LearnKit SDK
## Complete Build Instructions for Any Coding Agent

> Read this entire file before writing a single line of code.
> These instructions are designed to be followed by Claude Code, Codex, Cursor, or any agentic coding tool.

---

## Behavioral Rules (from Karpathy's CLAUDE.md)

These rules apply to every task in this document. The agent that follows them writes less code, ships faster, and produces fewer bugs.

**Rule 1 — Think before coding.**
State your assumptions before implementing. If multiple approaches exist, name them and pick one explicitly. If something is unclear, stop and ask. Never pick silently.

**Rule 2 — Simplicity first.**
Write the minimum code that solves the problem. No abstractions for single-use code. No configurability that wasn't asked for. If you write 200 lines and it could be 50, rewrite it.

**Rule 3 — Surgical changes.**
Touch only what you must. Match existing style. Don't refactor unrelated code. Every changed line should trace directly to the task requirement.

**Rule 4 — Goal-driven execution.**
Transform every task into a verifiable goal before starting:
- "Build the classifier" → "DSPy Predict returns multi-label dict with domain scores. Test with 5 sample tasks. All pass."
- "Add SQLite store" → "Can write a skill record, read it back by id, list by domain. Unit tests pass."

State a plan for multi-step tasks. Loop until verified. Don't ship until the verify step passes.

---

## What We Are Building

**LearnKit** is an agent-agnostic SDK that gives any AI agent a self-improving memory layer.

The core loop, in plain English:
1. User asks an agent a task
2. LearnKit classifies the task (e.g. "legal", "coding")
3. LearnKit retrieves relevant past experience from memory
4. That experience is injected into the agent's context
5. Agent runs and produces a response
6. LearnKit evaluates quality of the response
7. If quality is good enough, the trace is distilled into typed memory records
8. Those records improve every future run on similar tasks

The agent does not change. The model does not change. The context it receives gets richer every time.

**This is fine-tuning without fine-tuning.** Every "learned" pattern is an auditable, deletable JSON record.

---

## Four Sources — Read Before Building

Every design decision in this SDK traces to one of four sources. Read the relevant section before starting each phase.

### Source 1 — Hermes Agent (NousResearch)
**Repo:** github.com/NousResearch/hermes-agent (MIT, 163K stars)

Files to study before Phase 1:
- `tools/memory_tool.py` — four-op memory interface (add/replace/remove/read)
- `agent/trajectory.py` — JSONL trajectory format
- `agent/prompt_builder.py` — layered prompt construction
- `gateway/session.py` — SQLite FTS5 session search
- `skills/*.md` — skill document format
- `agent/context_compressor.py` — context compression on overflow

Files to study before Phase 3:
- `toolsets.py` + `tools/registry.py` — backend registration pattern
- `hermes-agent-self-evolution/` — GEPA MIT-licensed evolution loop

Key principle borrowed: **bounded memory**. Hermes intentionally limits memory size to avoid "memory soup." We enforce this with a hard token cap (1,200 tokens / 8 records maximum per retrieval). This is non-negotiable.

### Source 2 — ReaComp (Carnegie Mellon, arXiv 2605.05485)
**Repo:** github.com/cmu-llab/ReaComp

Files to study before Phase 2:
- `src/reacomp/pipeline.py` — two-stage inference (solver first, LLM fallback)
- `src/reacomp/induction.py` — trace → reusable artifact
- `src/reacomp/evaluate.py` — reward signal design

Critical findings to implement:
- **CoT traces are mandatory** — removing them collapses accuracy by 50 percentage points
- **Two-stage inference** — high-confidence skill = minimal LLM reasoning, low-confidence = full reasoning
- **Failure traces are first-class** — store and activate immediately, no quarantine
- **Ensemble diversity** — run GEPA evolution 3+ times in parallel, ensemble results

### Source 3 — Karpathy LLM Wiki (gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

The wiki concept maps directly to our memory store. Karpathy's three-layer model:
- **Raw sources** (immutable) → our execution traces
- **The wiki** (LLM-maintained, compounding) → our skill/fact/failure memory store
- **The schema** (CLAUDE.md / AGENTS.md) → our skill document format and retrieval conventions

Key insight to internalize: **"The LLM is the programmer; the wiki is the codebase."**
In our system: **"The agent is the programmer; the memory store is the wiki."**
Every task the agent runs is like a commit. The memory store accumulates knowledge the way a good wiki accumulates understanding. Cross-references are already there. Contradictions already flagged. New tasks build on everything before.

The three operations from the LLM Wiki — **Ingest, Query, Maintain** — map to our three core loops:
- Ingest → Memory Distiller (trace → records)
- Query → Semantic Retriever (task → relevant records)
- Maintain → Memory Scorer + GEPA (confidence decay, evolution)

### Source 4 — Karpathy CLAUDE.md (shown above)
These are the behavioral rules at the top of this file. They apply to the coding agent reading this document and to the agents that will use LearnKit in production. The CLAUDE.md format is also what we ship as our own `SKILL.md` template — structured behavioral instructions that make LLMs perform better on specific tasks.

---

## Repository Structure

```
learnkit/
├── AGENTS.md                    ← this file (ship with the repo)
├── README.md
├── pyproject.toml
├── learnkit/
│   ├── __init__.py              ← public API surface
│   ├── core.py                  ← LearnKit main class + @lk.agent decorator
│   ├── classifier.py            ← Task Classifier (DSPy multi-label)
│   ├── router.py                ← Memory Router (hard cap, retrieval plan)
│   ├── retriever.py             ← Semantic Retriever (BM25 + dense)
│   ├── composer.py              ← Context Composer (typed formatting)
│   ├── evaluator.py             ← Quality Gate (0–5 scoring)
│   ├── distiller.py             ← Memory Distiller (trace → records)
│   ├── compressor.py            ← Context Compressor (overflow handling)
│   ├── trajectory.py            ← Trajectory capture (JSONL)
│   ├── inference_mode.py        ← PRESCRIPTIVE / GUIDED / EXPLORATORY
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base.py              ← MemoryRecord base schema
│   │   ├── skill.py             ← Skill record + SKILL.md template
│   │   ├── fact.py              ← Fact record
│   │   ├── failure.py           ← Failure record (activates immediately)
│   │   ├── strategy.py          ← Strategy record
│   │   ├── preference.py        ← Preference record
│   │   ├── trace.py             ← Execution trace record
│   │   └── heuristic.py         ← Domain heuristic record
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── registry.py          ← Backend registry (Hermes toolset pattern)
│   │   ├── base.py              ← BaseBackend abstract class
│   │   ├── sqlite.py            ← SQLite + FTS5 (default, Hermes-inspired)
│   │   ├── mem0.py              ← Mem0 adapter
│   │   ├── zep.py               ← Zep adapter
│   │   └── qdrant.py            ← Qdrant adapter
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── langchain.py         ← LangChain callback adapter
│   │   ├── langgraph.py         ← LangGraph node wrapper
│   │   ├── autogen.py           ← AutoGen reply_func adapter
│   │   └── openai_raw.py        ← Raw OpenAI/Anthropic API wrapper
│   └── evolution/
│       ├── __init__.py
│       └── gepa.py              ← GEPA evolution (hermes-self-evolution, MIT)
├── tests/
│   ├── test_classifier.py
│   ├── test_retriever.py
│   ├── test_distiller.py
│   ├── test_evaluator.py
│   ├── test_sqlite_backend.py
│   └── fixtures/
│       ├── sample_traces.jsonl
│       └── sample_skills/
└── skills/                      ← bundled starter skills (Hermes format)
    ├── legal/
    │   └── contract_summarization/
    │       ├── SKILL.md
    │       └── metadata.json
    └── coding/
        └── debug_python_error/
            ├── SKILL.md
            └── metadata.json
```

---

## SKILL.md Template

Every skill is two files: a human-readable SKILL.md and a machine-readable metadata.json.
This format is directly borrowed from Hermes Agent's skills/ directory with extensions.

### SKILL.md format

```markdown
# {skill_name}

## When to use this skill
{one sentence: what task type triggers retrieval of this skill}

## Approach
1. {step one}
2. {step two}
3. {step three}

## Tools used
- {tool_name}: {why}

## Known constraints
- {constraint}

## Known failure modes
- {what can go wrong and how to avoid it}

## Examples
### Good output pattern
{brief example of what success looks like}

### Bad output pattern
{brief example of what to avoid}
```

### metadata.json format

```json
{
  "id": "uuid-v4",
  "version": 1,
  "type": "skill",
  "domains": {
    "legal": 0.9,
    "finance": 0.3
  },
  "task_type": "contract_summarization",
  "tools_used": ["pdf_reader", "clause_extractor"],
  "constraints": ["under 500 words", "no legal jargon"],
  "failure_modes": ["hallucinated clause references"],
  "outcome_quality": 4.2,
  "confidence": 0.87,
  "reuse_count": 0,
  "success_rate": null,
  "scope": "team",
  "status": "active",
  "created_at": "2026-05-25T10:00:00Z",
  "expires_at": "2026-11-25T10:00:00Z",
  "last_reinforced": null,
  "transfer_domains": [],
  "transfer_confidence": null,
  "evolution_gen": 0
}
```

---

## Phase 1 — Core Plumbing (Weeks 1–4)

*Hermes-derived. Working code to reference in their repo.*

### Task 1.1 — Project setup

**Goal:** Installable Python package. `pip install -e .` works. `import learnkit` works.

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "learnkit"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "dspy-ai>=2.4.0",
    "sentence-transformers>=3.0.0",
    "rank-bm25>=0.2.2",
    "sqlite-vec>=0.1.0",
    "pydantic>=2.0.0",
    "opentelemetry-sdk>=1.25.0",
    "anthropic>=0.34.0",
]

[project.optional-dependencies]
mem0 = ["mem0ai>=0.0.20"]
zep = ["zep-python>=2.0.0"]
qdrant = ["qdrant-client>=1.10.0"]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]
```

**Verify:** `python -c "import learnkit; print('ok')"` prints ok.

---

### Task 1.2 — Trajectory capture

**Inspiration:** `agent/trajectory.py` from Hermes Agent — JSONL format, `save_trajectories` opt-in.

**Goal:** A decorator that wraps any function call and saves a JSONL trajectory file with every tool call, reasoning step, and final output captured.

```python
# learnkit/trajectory.py

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TrajectoryStep:
    step: int
    role: str                          # "user" | "assistant" | "tool"
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    reasoning: Optional[str] = None    # CoT trace — CRITICAL per ReaComp finding
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


@dataclass  
class Trajectory:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task: str = ""
    domain_hint: Optional[str] = None
    steps: list = field(default_factory=list)
    outcome: Optional[str] = None      # "success" | "failure" | "partial"
    quality_score: Optional[float] = None   # 0–5, set by Evaluator
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def add_step(self, role: str, content: str, **kwargs):
        self.steps.append(TrajectoryStep(
            step=len(self.steps) + 1,
            role=role,
            content=content,
            **kwargs
        ))

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for step in self.steps:
                f.write(json.dumps(asdict(step)) + "\n")
            f.write(json.dumps({
                "id": self.id, "task": self.task,
                "outcome": self.outcome, "quality_score": self.quality_score,
                "created_at": self.created_at
            }) + "\n")

    @classmethod
    def load(cls, path: Path) -> "Trajectory":
        lines = path.read_text().strip().split("\n")
        meta = json.loads(lines[-1])
        steps = [TrajectoryStep(**json.loads(l)) for l in lines[:-1]]
        t = cls(id=meta["id"], task=meta["task"])
        t.steps = steps
        t.outcome = meta.get("outcome")
        t.quality_score = meta.get("quality_score")
        return t
```

**Verify:** Write a trajectory, save to disk, load it back. All fields match.

---

### Task 1.3 — Base schema + 7 memory types

**Goal:** All 7 typed MemoryRecord subclasses. Pydantic models. Round-trip to/from dict.

```python
# learnkit/schemas/base.py

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timedelta
import uuid

MemoryType = Literal["skill", "fact", "failure", "strategy", "preference", "trace", "heuristic"]
MemoryScope = Literal["user", "team", "public"]
MemoryStatus = Literal["active", "stale", "quarantine", "deprecated"]

# Default TTL per type (days) — borrowed from LLM Wiki "keep current" principle
TTL_DEFAULTS = {
    "skill": 180, "fact": 90, "failure": 90,
    "strategy": 180, "preference": 365, "trace": 30, "heuristic": 90
}

class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    domains: dict[str, float] = {}         # multi-label: {"legal": 0.9, "finance": 0.4}
    task_type: Optional[str] = None
    content: dict = {}                     # type-specific payload
    confidence: float = 0.5               # starts at 0.5, grows with reuse
    reuse_count: int = 0
    success_rate: Optional[float] = None
    scope: MemoryScope = "team"
    status: MemoryStatus = "active"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    last_reinforced: Optional[str] = None
    transfer_domains: list[str] = []
    transfer_confidence: Optional[float] = None
    evolution_gen: int = 0

    def model_post_init(self, __context):
        if self.expires_at is None:
            days = TTL_DEFAULTS.get(self.type, 90)
            exp = datetime.utcnow() + timedelta(days=days)
            self.expires_at = exp.isoformat()

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > datetime.fromisoformat(self.expires_at)

    def reinforce(self, quality: float):
        """Call after a successful retrieval that produced a good outcome."""
        self.reuse_count += 1
        self.last_reinforced = datetime.utcnow().isoformat()
        # Update rolling success rate
        if self.success_rate is None:
            self.success_rate = quality / 5.0
        else:
            # Weighted average — recent successes count more
            self.success_rate = 0.8 * self.success_rate + 0.2 * (quality / 5.0)
        # Confidence grows toward 0.95 with use, capped
        self.confidence = min(0.95, self.confidence + 0.02)
```

```python
# learnkit/schemas/skill.py
from .base import MemoryRecord

class SkillRecord(MemoryRecord):
    type: str = "skill"

    # content dict keys for a skill:
    # steps: list[str]      — ordered approach steps
    # tools_used: list[str] — tool names
    # constraints: list[str]
    # failure_modes: list[str]
    # examples: dict        — good/bad output patterns

    def to_skill_md(self) -> str:
        """Generate a human-readable SKILL.md from this record."""
        c = self.content
        steps = "\n".join(f"{i+1}. {s}" for i, s in enumerate(c.get("steps", [])))
        tools = "\n".join(f"- {t}" for t in c.get("tools_used", []))
        constraints = "\n".join(f"- {c_}" for c_ in c.get("constraints", []))
        failures = "\n".join(f"- {f}" for f in c.get("failure_modes", []))
        return f"""# {self.task_type}

## When to use this skill
Use for {self.task_type} tasks in {list(self.domains.keys())} domains.

## Approach
{steps}

## Tools used
{tools}

## Known constraints
{constraints}

## Known failure modes
{failures}
"""
```

**Verify:** `SkillRecord(type="skill", domains={"legal": 0.9}, task_type="contract_summarization", content={"steps": ["step 1"]})` — model validates, `to_skill_md()` returns non-empty string.

---

### Task 1.4 — SQLite backend with FTS5

**Inspiration:** `gateway/session.py` from Hermes Agent.

**Goal:** Write, read, search, list, delete memory records. BM25 full-text search. Works with zero external dependencies.

```python
# learnkit/backends/sqlite.py

import sqlite3
import json
from pathlib import Path
from typing import Optional
from ..schemas.base import MemoryRecord, MemoryType


class SQLiteBackend:
    """
    Default backend. Zero dependencies, offline-capable.
    Uses SQLite FTS5 for BM25 text search (borrowed from Hermes session_search).
    """

    def __init__(self, db_path: str = "~/.learnkit/memory.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = self._conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                domains TEXT,        -- JSON
                task_type TEXT,
                content TEXT,        -- JSON
                confidence REAL DEFAULT 0.5,
                reuse_count INTEGER DEFAULT 0,
                success_rate REAL,
                scope TEXT DEFAULT 'team',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                expires_at TEXT,
                last_reinforced TEXT,
                full_record TEXT     -- full JSON for round-trip
            )
        """)
        # FTS5 virtual table for BM25 search (Hermes session_search pattern)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
                id UNINDEXED,
                task_type,
                content_text,        -- flattened text of content dict
                domains_text,        -- flattened domain names
                content=records,
                content_rowid=rowid
            )
        """)
        conn.commit()
        conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, record: MemoryRecord) -> str:
        conn = self._conn()
        domains_text = " ".join(record.domains.keys())
        content_text = " ".join(str(v) for v in record.content.values() if isinstance(v, (str, list)))
        if isinstance(content_text, list):
            content_text = " ".join(content_text)
        
        conn.execute("""
            INSERT OR REPLACE INTO records 
            (id, type, domains, task_type, content, confidence, reuse_count,
             success_rate, scope, status, created_at, expires_at, full_record)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            record.id, record.type, json.dumps(record.domains),
            record.task_type, json.dumps(record.content),
            record.confidence, record.reuse_count, record.success_rate,
            record.scope, record.status, record.created_at, record.expires_at,
            record.model_dump_json()
        ))
        conn.execute("""
            INSERT OR REPLACE INTO records_fts (id, task_type, content_text, domains_text)
            VALUES (?,?,?,?)
        """, (record.id, record.task_type or "", content_text, domains_text))
        conn.commit()
        conn.close()
        return record.id

    def read(self, id: str) -> Optional[MemoryRecord]:
        conn = self._conn()
        row = conn.execute("SELECT full_record FROM records WHERE id=?", (id,)).fetchone()
        conn.close()
        if row is None:
            return None
        return MemoryRecord.model_validate_json(row["full_record"])

    def remove(self, id: str):
        conn = self._conn()
        conn.execute("DELETE FROM records WHERE id=?", (id,))
        conn.execute("DELETE FROM records_fts WHERE id=?", (id,))
        conn.commit()
        conn.close()

    def search(
        self,
        query: str,
        record_type: Optional[MemoryType] = None,
        domain: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = 8,
        exclude_stale: bool = True
    ) -> list[MemoryRecord]:
        """
        BM25 full-text search via FTS5 (Hermes session_search pattern).
        Returns records ranked by BM25 score × confidence × recency.
        """
        conn = self._conn()
        fts_query = f'"{query}"' if " " in query else query

        sql = """
            SELECT r.full_record, r.confidence, r.created_at,
                   bm25(records_fts) as bm25_score
            FROM records_fts
            JOIN records r ON records_fts.id = r.id
            WHERE records_fts MATCH ?
              AND r.confidence >= ?
              AND r.status != 'quarantine'
        """
        params = [fts_query, min_confidence]

        if record_type:
            sql += " AND r.type = ?"
            params.append(record_type)
        if domain:
            sql += " AND r.domains LIKE ?"
            params.append(f'%"{domain}"%')
        if exclude_stale:
            sql += " AND r.status != 'stale'"

        sql += " ORDER BY (bm25_score * r.confidence) DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        conn.close()

        results = []
        for row in rows:
            try:
                rec = MemoryRecord.model_validate_json(row["full_record"])
                if not rec.is_expired():
                    results.append(rec)
            except Exception:
                pass
        return results

    def list_by_domain(self, domain: str, limit: int = 20) -> list[MemoryRecord]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT full_record FROM records
            WHERE domains LIKE ? AND status = 'active'
            ORDER BY confidence DESC LIMIT ?
        """, (f'%"{domain}"%', limit)).fetchall()
        conn.close()
        return [MemoryRecord.model_validate_json(r["full_record"]) for r in rows]

    def update_confidence(self, id: str, new_confidence: float):
        conn = self._conn()
        conn.execute(
            "UPDATE records SET confidence=? WHERE id=?",
            (new_confidence, id)
        )
        conn.commit()
        conn.close()
```

**Verify:**
```python
backend = SQLiteBackend(":memory:")   # in-memory for tests
record = SkillRecord(task_type="contract_summarization", domains={"legal": 0.9}, content={"steps": ["extract obligations"]})
backend.add(record)
results = backend.search("contract summarization", domain="legal")
assert len(results) > 0
assert results[0].id == record.id
```

---

### Task 1.5 — Context Composer

**Inspiration:** `agent/prompt_builder.py` from Hermes Agent — layered prompt construction.
**Also:** Karpathy LLM Wiki "The wiki is a persistent, compounding artifact" — format it to read as accumulated wisdom, not a data dump.

**Goal:** Takes a list of MemoryRecords and formats them into a context block for injection into an agent's system prompt. Each memory type formats differently.

```python
# learnkit/composer.py

from typing import Optional
from .schemas.base import MemoryRecord
from .inference_mode import InferenceMode


MAX_CONTEXT_TOKENS = 1200   # hard cap — Hermes bounded memory principle
CHARS_PER_TOKEN = 4         # rough estimate


def compose_context(
    records: list[MemoryRecord],
    task: str,
    inference_mode: InferenceMode,
) -> str:
    """
    Formats retrieved memory records into a system prompt context block.
    Borrowed from Hermes prompt_builder.py layered construction pattern.
    """
    if not records:
        return ""

    sections = []

    # Skills — most important, inject first
    skills = [r for r in records if r.type == "skill"]
    for skill in skills:
        steps = skill.content.get("steps", [])
        tools = skill.content.get("tools_used", [])
        failures = skill.content.get("failure_modes", [])
        confidence_pct = int(skill.confidence * 100)
        reuses = skill.reuse_count
        
        block = f"SKILL — {skill.task_type} (confidence {confidence_pct}%, used {reuses} times):"
        if steps:
            block += "\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps))
        if tools:
            block += f"\n  Tools: {', '.join(tools)}"
        if failures:
            block += "\n  Watch out for: " + "; ".join(failures)
        sections.append(block)

    # Failure records — inject as explicit warnings (ReaComp: failures are first-class)
    failures = [r for r in records if r.type == "failure"]
    for f in failures:
        desc = f.content.get("description", "")
        what_to_avoid = f.content.get("what_to_avoid", "")
        sections.append(f"KNOWN FAILURE in this domain:\n  {desc}\n  Avoid: {what_to_avoid}")

    # Facts — grounding information
    facts = [r for r in records if r.type == "fact"]
    for fact in facts:
        statement = fact.content.get("statement", "")
        source = fact.content.get("source", "unknown")
        is_stale = fact.status == "stale"
        staleness = " ⚠️ (may be outdated — verify before relying on)" if is_stale else ""
        sections.append(f"FACT (verified {source}){staleness}:\n  {statement}")

    # Preferences
    prefs = [r for r in records if r.type == "preference"]
    for pref in prefs:
        key = pref.content.get("key", "")
        value = pref.content.get("value", "")
        sections.append(f"PREFERENCE: {key} → {value}")

    # Domain heuristics
    heuristics = [r for r in records if r.type == "heuristic"]
    for h in heuristics:
        rule = h.content.get("rule", "")
        sections.append(f"DOMAIN RULE: {rule}")

    if not sections:
        return ""

    mode_note = {
        InferenceMode.PRESCRIPTIVE: "Follow the skill above closely. High confidence — minimal deviation needed.",
        InferenceMode.GUIDED: "Use the skill as a scaffold. Adapt where the specific task requires it.",
        InferenceMode.EXPLORATORY: "No established skill for this task. Reason carefully and document your approach.",
    }[inference_mode]

    header = f"=== LearnKit Context [{inference_mode.value} mode] ===\n{mode_note}\n"
    body = "\n\n".join(sections)
    footer = "\n=== End Context ==="
    full = header + "\n" + body + footer

    # Enforce hard token cap (Hermes bounded memory principle)
    if len(full) > MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN:
        full = _compress_context(full, MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN)

    return full


def _compress_context(text: str, max_chars: int) -> str:
    """
    Truncate context to hard cap.
    Inspired by Hermes context_compressor.py — prefer truncation of lower-priority sections.
    """
    if len(text) <= max_chars:
        return text
    # Keep header + first skill (most important) + truncation notice
    lines = text.split("\n")
    result = []
    char_count = 0
    for line in lines:
        if char_count + len(line) > max_chars - 60:
            result.append("\n[Context truncated — additional records available in memory store]")
            break
        result.append(line)
        char_count += len(line) + 1
    return "\n".join(result)
```

**Verify:** Pass 3 skill records + 2 failure records. Output string contains "SKILL" and "KNOWN FAILURE". Length stays under 1200*4=4800 chars.

---

## Phase 2 — Intelligence Layer (Weeks 5–8)

*ReaComp-derived. This is where the system becomes self-improving.*

### Task 2.1 — Inference Mode

**Inspiration:** ReaComp two-stage inference. Solver first (zero cost), LLM fallback only on failure.

```python
# learnkit/inference_mode.py

from enum import Enum
from .schemas.base import MemoryRecord


class InferenceMode(Enum):
    PRESCRIPTIVE = "prescriptive"   # skill confidence >= 0.90 — follow closely
    GUIDED = "guided"               # skill confidence >= 0.70 — use as scaffold
    EXPLORATORY = "exploratory"     # no match — full LLM reasoning, capture trace


def determine_inference_mode(records: list[MemoryRecord]) -> InferenceMode:
    """
    ReaComp two-stage pattern:
    - High confidence → prescriptive (minimal LLM reasoning, reduced token cost)
    - Partial match → guided
    - No match → exploratory (capture trace for future distillation)
    """
    skills = [r for r in records if r.type == "skill"]
    if not skills:
        return InferenceMode.EXPLORATORY
    best = max(skills, key=lambda r: r.confidence)
    if best.confidence >= 0.90:
        return InferenceMode.PRESCRIPTIVE
    if best.confidence >= 0.70:
        return InferenceMode.GUIDED
    return InferenceMode.EXPLORATORY
```

---

### Task 2.2 — Task Classifier

**Goal:** Takes a raw task string, returns multi-label domain vector and task type.
Uses DSPy for structured output. Cheap — one Haiku-class model call.

```python
# learnkit/classifier.py

import dspy
from pydantic import BaseModel


class ClassificationOutput(BaseModel):
    task_type: str           # e.g. "contract_summarization"
    domains: dict[str, float]  # e.g. {"legal": 0.9, "finance": 0.3}
    complexity: str          # "low" | "medium" | "high"


class TaskClassifier(dspy.Module):
    """
    Multi-label domain classifier.
    DSPy Predict with typed output — single cheap LLM call per task.
    """

    def __init__(self):
        super().__init__()
        self.classify = dspy.TypedPredictor(
            dspy.Signature(
                "task -> classification",
                task=dspy.InputField(desc="The user's task description"),
                classification=dspy.OutputField(
                    desc="JSON with task_type (snake_case string), "
                         "domains (dict of domain_name to confidence 0-1), "
                         "complexity (low|medium|high)"
                )
            )
        )

    def forward(self, task: str) -> ClassificationOutput:
        result = self.classify(task=task)
        # Parse and validate
        import json
        data = json.loads(result.classification)
        return ClassificationOutput(**data)


def classify_task(task: str, lm=None) -> ClassificationOutput:
    if lm is None:
        lm = dspy.LM("anthropic/claude-haiku-4-5-20251001")
    with dspy.context(lm=lm):
        classifier = TaskClassifier()
        return classifier(task=task)
```

**Verify:** `classify_task("summarize this NDA for a software license")` returns a ClassificationOutput where `"legal"` is the top domain (confidence > 0.7).

---

### Task 2.3 — Evaluator (quality gate)

**Critical:** Never use "agent responded = success" as the quality signal.
This is the most important module. A bad evaluator poisons the entire memory store.

```python
# learnkit/evaluator.py

from enum import Enum
from typing import Optional
import dspy


class EvaluationSignal(Enum):
    USER_FEEDBACK = "user_feedback"
    LLM_JUDGE = "llm_judge"
    NLI_CONSISTENCY = "nli_consistency"


class EvaluationResult:
    def __init__(self, score: float, signal: EvaluationSignal, reasoning: str):
        self.score = score                    # 0.0 – 5.0
        self.signal = signal
        self.reasoning = reasoning
        self.passes_threshold = score >= 3.5  # default threshold


class Evaluator:
    """
    Quality gate before any record enters the memory store.
    
    Priority order (most reliable first):
    1. USER_FEEDBACK — explicit thumbs up/down or rating
    2. LLM_JUDGE — separate model reads task + response, scores 0-5
    3. NLI_CONSISTENCY — factual consistency check (cheapest, least reliable)
    
    Failure records skip this gate entirely (they already failed — store immediately).
    """

    QUALITY_THRESHOLD = 3.5

    def evaluate_with_llm_judge(
        self,
        task: str,
        response: str,
        reasoning_trace: Optional[str] = None,
        lm=None
    ) -> EvaluationResult:
        """
        LLM-as-judge evaluation. Separate model from the one that ran the task.
        ReaComp equivalent: reward signal for whether solver succeeded.
        """
        if lm is None:
            lm = dspy.LM("anthropic/claude-haiku-4-5-20251001")

        judge_prompt = f"""
You are evaluating an AI agent's response quality. Score from 0-5.

TASK: {task}

RESPONSE: {response}

{f"AGENT REASONING: {reasoning_trace}" if reasoning_trace else ""}

Score 0-5 where:
5 = Excellent: accurate, complete, well-structured, no hallucinations
4 = Good: accurate, mostly complete, minor gaps
3 = Acceptable: basically correct, some important omissions
2 = Poor: significant errors or omissions
1 = Bad: mostly wrong or misleading
0 = Harmful: incorrect information presented as fact

Respond with JSON only: {{"score": <number>, "reasoning": "<one sentence>"}}
"""
        with dspy.context(lm=lm):
            response_text = lm(judge_prompt)

        import json
        try:
            data = json.loads(response_text)
            return EvaluationResult(
                score=float(data["score"]),
                signal=EvaluationSignal.LLM_JUDGE,
                reasoning=data.get("reasoning", "")
            )
        except Exception:
            # If judge fails to parse, default conservative score
            return EvaluationResult(
                score=2.0,
                signal=EvaluationSignal.LLM_JUDGE,
                reasoning="Judge response unparseable — conservative score applied"
            )

    def evaluate_from_user_feedback(self, rating: int) -> EvaluationResult:
        """Direct user feedback (1-5 stars or thumbs up = 4.5)."""
        return EvaluationResult(
            score=float(rating),
            signal=EvaluationSignal.USER_FEEDBACK,
            reasoning=f"Direct user rating: {rating}/5"
        )
```

**Verify:** `evaluator.evaluate_with_llm_judge(task="summarize this contract", response="The contract requires Party A to deliver services by Q3...")` returns a score between 0 and 5.

---

### Task 2.4 — Memory Distiller

**Inspiration:** ReaComp trace → reusable artifact. CRITICAL: must capture reasoning trace (CoT), not just output.

```python
# learnkit/distiller.py

import dspy
from typing import Optional
from .trajectory import Trajectory
from .schemas.skill import SkillRecord
from .schemas.failure import FailureRecord
from .schemas.fact import FactRecord


DISTILL_PROMPT = """
You are reading an AI agent's execution trace to extract reusable knowledge.

TASK: {task}
DOMAINS: {domains}
QUALITY SCORE: {quality}/5

REASONING TRACE:
{reasoning}

EXECUTION STEPS:
{steps}

FINAL OUTPUT:
{output}

Extract reusable knowledge. Respond with JSON only:
{{
  "skill": {{
    "steps": ["step 1", "step 2"],         // ordered approach that worked
    "tools_used": ["tool_name"],
    "constraints": ["constraint"],
    "failure_modes": ["what almost went wrong"]
  }},
  "facts": [
    {{"statement": "...", "source": "from trace"}}
  ],
  "failures": []                           // any dead ends encountered
}}

If no reusable skill can be extracted (task was one-off), set skill to null.
Focus on the APPROACH, not the specific content. The skill must generalize.
"""


class MemoryDistiller:
    """
    Converts successful execution traces into typed memory records.
    
    Key insight from ReaComp: the reasoning trace (CoT) is the learning signal.
    Removing it collapses distillation quality dramatically.
    Without the reasoning trace, the distiller can only see inputs and outputs,
    missing the structural insights about how to approach the problem.
    """

    def __init__(self, lm=None):
        self.lm = lm or dspy.LM("anthropic/claude-haiku-4-5-20251001")

    def distill(
        self,
        trajectory: Trajectory,
        domain_vector: dict[str, float],
        quality_score: float
    ) -> tuple[Optional[SkillRecord], list[FactRecord], list[FailureRecord]]:

        if quality_score < 3.5:
            raise ValueError("Distillation called on low-quality trace. Evaluator should have gated this.")

        # Flatten trajectory for the prompt
        reasoning_steps = []
        execution_steps = []
        final_output = ""

        for step in trajectory.steps:
            if step.reasoning:
                reasoning_steps.append(step.reasoning)
            if step.role == "assistant":
                execution_steps.append(f"Agent: {step.content[:300]}")
                final_output = step.content
            elif step.role == "tool":
                execution_steps.append(f"Tool({step.tool_name}): {step.content[:200]}")

        import json
        prompt = DISTILL_PROMPT.format(
            task=trajectory.task,
            domains=list(domain_vector.keys()),
            quality=quality_score,
            reasoning="\n".join(reasoning_steps) or "No reasoning trace captured",
            steps="\n".join(execution_steps),
            output=final_output[:500]
        )

        with dspy.context(lm=self.lm):
            raw = self.lm(prompt)

        data = json.loads(raw)

        # Build records
        skill = None
        if data.get("skill"):
            skill = SkillRecord(
                domains=domain_vector,
                task_type=trajectory.task[:80],
                content=data["skill"],
                status="quarantine"   # 24h quarantine before becoming active
            )

        facts = [
            FactRecord(
                domains=domain_vector,
                content={"statement": f["statement"], "source": f.get("source", "agent trace")},
                status="quarantine"
            )
            for f in data.get("facts", [])
        ]

        # Failure records activate IMMEDIATELY — no quarantine
        # Per ReaComp: agents need to know what not to do as fast as possible
        failures = [
            FailureRecord(
                domains=domain_vector,
                content={"description": f.get("description", ""), "what_to_avoid": f.get("what_to_avoid", "")},
                status="active"   # immediately active
            )
            for f in data.get("failures", [])
        ]

        return skill, facts, failures
```

**Verify:** Feed a sample trajectory with reasoning steps. Verify that `skill.status == "quarantine"` and any failure records have `status == "active"`.

---

## Phase 3 — Evolution + Team (Weeks 9–12)

### Task 3.1 — GEPA Evolution (MIT Licensed)

**Source:** `hermes-agent-self-evolution` by NousResearch. MIT license. Clone and adapt.

```bash
# Reference repo — study before implementing
git clone https://github.com/NousResearch/hermes-agent-self-evolution.git
# Key file: evolution/skills/evolve_skill.py
# Key class: GEPAEvolver
```

```python
# learnkit/evolution/gepa.py

"""
GEPA (Genetic-Pareto Prompt Evolution) for LearnKit skill library.

Adapted from hermes-agent-self-evolution (MIT License, ICLR 2026 Oral).
Original: github.com/NousResearch/hermes-agent-self-evolution

Key changes from original:
- Operates on LearnKit SkillRecord JSON schema instead of Hermes SKILL.md
- Uses LearnKit Evaluator for quality scoring instead of Hermes benchmarks
- Ensemble policy: runs 3 parallel trials, ensembles results (ReaComp finding)
- Outputs to LearnKit memory backend, not ~/.hermes/skills/
"""

import dspy
from concurrent.futures import ThreadPoolExecutor
from ..backends.base import BaseBackend
from ..schemas.skill import SkillRecord
from ..evaluator import Evaluator


GEPA_SYSTEM = """
You are evolving an AI agent skill to improve its success rate.

Current skill:
{skill_json}

Recent execution traces where this skill was used:
{traces_summary}

Success rate: {success_rate:.0%}

Propose 3 mutations to this skill (modify steps, add constraints, clarify failure modes).
Each mutation should target a different failure pattern observed in the traces.

Respond with JSON: {{"mutations": [{{ "steps": [...], "constraints": [...], "failure_modes": [...] }}]}}
"""


class GEPAEvolver:

    def __init__(self, backend: BaseBackend, evaluator: Evaluator, lm=None):
        self.backend = backend
        self.evaluator = evaluator
        self.lm = lm or dspy.LM("anthropic/claude-sonnet-4-20250514")

    def evolve_skill(
        self,
        skill: SkillRecord,
        traces: list,
        n_trials: int = 3  # ReaComp: ensemble diversity — minimum 3 runs
    ) -> list[SkillRecord]:
        """
        Runs n_trials parallel evolution trials and returns all variants.
        Caller ensembles and picks the best per task (ReaComp ensemble pattern).
        Never overwrites existing skill — creates new evolution_gen variants.
        """
        import json

        traces_summary = "\n".join([
            f"- Task: {t.task[:100]}, Quality: {t.quality_score}/5"
            for t in traces[:10]
        ])

        prompt = GEPA_SYSTEM.format(
            skill_json=skill.model_dump_json(indent=2),
            traces_summary=traces_summary,
            success_rate=skill.success_rate or 0.5
        )

        def run_trial(_):
            with dspy.context(lm=self.lm):
                raw = self.lm(prompt)
            data = json.loads(raw)
            variants = []
            for mutation in data.get("mutations", [])[:3]:
                new_skill = skill.model_copy(deep=True)
                new_skill.id = __import__("uuid").uuid4().__str__()
                new_skill.content.update(mutation)
                new_skill.confidence = 0.5  # starts fresh, builds with use
                new_skill.evolution_gen = skill.evolution_gen + 1
                new_skill.status = "quarantine"
                variants.append(new_skill)
            return variants

        # Run trials in parallel — ensemble for diversity (ReaComp finding)
        all_variants = []
        with ThreadPoolExecutor(max_workers=n_trials) as executor:
            for result in executor.map(run_trial, range(n_trials)):
                all_variants.extend(result)

        # Store all variants — retriever will surface the best per task over time
        for variant in all_variants:
            self.backend.add(variant)

        return all_variants
```

---

### Task 3.2 — Main LearnKit class + @lk.agent decorator

**Goal:** The 5-line integration. Everything composes here.

```python
# learnkit/core.py

import functools
from typing import Optional, Callable
from .classifier import classify_task
from .router import MemoryRouter
from .retriever import SemanticRetriever
from .composer import compose_context
from .evaluator import Evaluator
from .distiller import MemoryDistiller
from .trajectory import Trajectory
from .inference_mode import determine_inference_mode
from .backends.sqlite import SQLiteBackend
from .backends.registry import get_backend


class LearnKit:

    def __init__(
        self,
        memory_backend: str = "sqlite",
        evaluation: str = "llm_judge",
        scope: str = "team",
        capture_reasoning: bool = True,    # ReaComp: mandatory CoT capture
        quality_threshold: float = 3.5,
        **backend_kwargs
    ):
        self.backend = get_backend(memory_backend, **backend_kwargs)
        self.router = MemoryRouter(max_records=8, max_tokens=1200)
        self.retriever = SemanticRetriever(backend=self.backend)
        self.evaluator = Evaluator()
        self.distiller = MemoryDistiller()
        self.scope = scope
        self.capture_reasoning = capture_reasoning
        self.quality_threshold = quality_threshold
        self.evaluation_mode = evaluation

    def agent(self, domain: Optional[str] = None, task_type: Optional[str] = None):
        """
        Decorator that wraps any agent function with the full LearnKit loop.
        
        Usage:
            @lk.agent(domain="legal")
            def my_agent(task: str) -> str:
                return langchain_agent.run(task)
        """
        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(task: str, *args, **kwargs) -> str:
                # 1. Classify
                classification = classify_task(task)
                domain_vector = classification.domains

                # 2. Retrieve relevant memory
                records = self.retriever.retrieve(
                    task=task,
                    domain_vector=domain_vector,
                    router=self.router
                )

                # 3. Determine inference mode (ReaComp two-stage pattern)
                mode = determine_inference_mode(records)

                # 4. Compose context
                context_block = compose_context(records, task, mode)

                # 5. Run agent with enriched context
                traj = Trajectory(task=task)
                traj.add_step("user", task)

                # Inject context into kwargs or modify the call
                enriched_kwargs = {**kwargs, "_learnkit_context": context_block}
                result = fn(task, *args, **enriched_kwargs)

                traj.add_step("assistant", result)

                # 6. Evaluate (async — don't block the return)
                self._post_process_async(traj, domain_vector)

                return result
            return wrapper
        return decorator

    def _post_process_async(self, traj: Trajectory, domain_vector: dict):
        """
        Quality gate + distillation. Runs after response returned to user.
        In production: run in a background thread or async task.
        """
        import threading
        def _run():
            eval_result = self.evaluator.evaluate_with_llm_judge(
                task=traj.task,
                response=traj.steps[-1].content if traj.steps else ""
            )
            traj.quality_score = eval_result.score
            traj.outcome = "success" if eval_result.passes_threshold else "failure"

            if eval_result.passes_threshold:
                skill, facts, failures = self.distiller.distill(
                    trajectory=traj,
                    domain_vector=domain_vector,
                    quality_score=eval_result.score
                )
                if skill:
                    self.backend.add(skill)
                for f in facts:
                    self.backend.add(f)
                for f in failures:
                    self.backend.add(f)
            else:
                # Low quality — store as failure record immediately
                from .schemas.failure import FailureRecord
                failure = FailureRecord(
                    domains=domain_vector,
                    content={
                        "description": f"Failed task: {traj.task[:100]}",
                        "what_to_avoid": "Approach used in this trace"
                    },
                    status="active"
                )
                self.backend.add(failure)

        threading.Thread(target=_run, daemon=True).start()
```

---

## The LLM Wiki Pattern — Connecting to LearnKit

Karpathy's LLM Wiki defines three operations: **Ingest, Query, Maintain.**
Our memory store maps to these exactly:

| LLM Wiki Operation | LearnKit Equivalent | Trigger |
|---|---|---|
| **Ingest** — drop a new source, LLM integrates it | Memory Distiller processes trace → skill + facts | After every successful agent run |
| **Query** — ask a question, wiki synthesizes answer | Semantic Retriever + Context Composer | Before every agent run |
| **Maintain** — keep wiki current, flag contradictions | Memory Scorer decay + GEPA evolution | Weekly background job |

The key insight from the wiki: **"The cross-references are already there. The synthesis already reflects everything you've read."**

In our system: by Day 30, when an agent receives a legal task, the context block already contains cross-referenced patterns from 48 past legal interactions, known failure modes that compound across those interactions, and a confidence-weighted selection of the most successful approaches. The agent doesn't discover this from scratch. It inherits it.

This is what Karpathy means by "compounding artifact." Our memory store is not a log. It is a wiki that gets richer with every run.

---

## CLAUDE.md for LearnKit Itself

Ship this file as `CLAUDE.md` in the repo root. Any coding agent working on LearnKit will read it.

```markdown
# CLAUDE.md — LearnKit SDK

Behavioral guidelines for any coding agent working in this codebase.
Based on Karpathy's CLAUDE.md adapted for this project.

## 1. Think Before Coding
- This SDK is middleware — it plugs into other agents. Never break the public API.
- State assumptions before implementing. If uncertain about how a module connects, read core.py first.
- The decorator pattern in core.py is the user-facing contract. Every other module serves it.

## 2. Simplicity First
- Each module does exactly one thing. Classifier classifies. Retriever retrieves.
- Do not add configuration that wasn't asked for.
- The 5-line integration (LearnKit + @lk.agent) must always stay 5 lines.

## 3. Memory is never directly accessible to the user
- Users interact with the @lk.agent decorator and LearnKit class only.
- Do not expose backend internals. Abstract everything behind BaseBackend.
- Failure records always activate immediately. Never quarantine them.

## 4. The hard token cap (1200 tokens) is non-negotiable
- Do not add a parameter to override it.
- Context explosion is a product failure, not a user preference.

## 5. Test every module independently
- Each module has its own test file. Tests use in-memory SQLite.
- Distiller tests use sample_traces.jsonl fixtures, not live LLM calls.
- Evaluator tests mock the LLM judge.

## 6. Goal-driven tasks
Transform every task into a verifiable statement before coding:
- "Add Mem0 backend" → "Mem0Backend passes all tests in test_sqlite_backend.py"
- "Fix retrieval ranking" → "Search for 'contract' returns legal records above finance records in test fixture"
```

---

## Testing Checklist (Ship When All Pass)

```
Phase 1:
[ ] pip install -e . succeeds
[ ] import learnkit succeeds
[ ] SQLiteBackend: write record, read back by id, search by keyword — all match
[ ] MemoryRecord: expires_at populated automatically, is_expired() correct
[ ] SkillRecord.to_skill_md() returns valid markdown
[ ] Context Composer: output under 4800 chars for 8 records

Phase 2:
[ ] TaskClassifier: "summarize this NDA" → legal domain > 0.7
[ ] InferenceMode: confidence 0.92 → PRESCRIPTIVE, 0.75 → GUIDED, 0.4 → EXPLORATORY
[ ] Evaluator: returns score 0–5 for any task+response pair
[ ] Distiller: failure records have status="active", skill records have status="quarantine"
[ ] Full loop: @lk.agent wraps a simple agent, context is injected, trace is captured

Phase 3:
[ ] GEPA: returns 3+ skill variants per run, all stored with evolution_gen=1
[ ] Ensemble: 3 parallel GEPA trials produce 9+ variants
[ ] Team registry: skills with scope="team" visible to all users in team
[ ] Confidence decay: record confidence decreases 2% per week if not reinforced
```

---

## References

- Hermes Agent: github.com/NousResearch/hermes-agent (MIT)
- GEPA: github.com/NousResearch/hermes-agent-self-evolution (MIT, ICLR 2026)
- ReaComp: arxiv.org/abs/2605.05485 (CMU, May 2026)
- LLM Wiki: gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- CLAUDE.md pattern: github.com/multica-ai/andrej-karpathy-skills/blob/main/CLAUDE.md

---

*AGENTS.md v1.0 — May 2026*
*Ship this file in the repo root. Any agent reading it can build LearnKit.*