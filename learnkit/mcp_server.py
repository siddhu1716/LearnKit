"""Read-only MCP surface for LearnKit coding-agent plugins."""

from __future__ import annotations

import os
from importlib import import_module
from pathlib import Path
from typing import Optional

from .core import LearnKit
from .plugin_runtime import context_for_task, doctor


def _database_path(db_path: Optional[str] = None) -> str:
    return str(Path(db_path or os.environ.get("LEARNKIT_DB_PATH", "~/.learnkit/memory.db")).expanduser())


def search_memory(query: str, limit: int = 5, *, db_path: Optional[str] = None) -> list[dict]:
    memory = LearnKit(memory_backend="sqlite", db_path=_database_path(db_path))
    try:
        records = memory.backend.search(query, scope=memory.scope, limit=max(1, min(limit, 20)))
        return [
            {
                "id": record.id,
                "type": record.type,
                "task_type": record.task_type,
                "confidence": record.confidence,
                "status": record.status,
                "content": record.content,
            }
            for record in records
        ]
    finally:
        memory.shutdown()


def list_procedures(query: str = "", limit: int = 10, *, db_path: Optional[str] = None) -> list[dict]:
    memory = LearnKit(memory_backend="sqlite", db_path=_database_path(db_path))
    try:
        bounded = max(1, min(limit, 50))
        records = (
            memory.backend.search(query, record_type="skill", scope=memory.scope, limit=bounded * 3)
            if query.strip()
            else memory.backend.list_by_scope(memory.scope, limit=bounded * 3)
        )
        procedures = []
        for record in records:
            if record.type != "skill" or not record.content.get("procedure"):
                continue
            procedures.append(
                {
                    "id": record.id,
                    "task_type": record.task_type,
                    "trigger": record.content.get("trigger"),
                    "tool_sequence": record.content.get("tool_sequence", []),
                    "confidence": record.confidence,
                    "reuse_count": record.reuse_count,
                    "status": record.status,
                }
            )
            if len(procedures) >= bounded:
                break
        return procedures
    finally:
        memory.shutdown()


def build_server(*, db_path: Optional[str] = None):
    try:
        FastMCP = import_module("mcp.server.fastmcp").FastMCP
    except ImportError as exc:
        raise RuntimeError(
            'The coding-agent plugin requires `pip install "learnkit-ai[coding-agents]"`.'
        ) from exc

    server = FastMCP(
        "learnkit",
        instructions=(
            "LearnKit exposes read-only procedural memory. Use learnkit_context before "
            "repeating a tool workflow; inspect procedures before suggesting reuse."
        ),
        log_level="ERROR",
    )

    @server.tool(description="Check LearnKit plugin, database, and MCP health.")
    def learnkit_status() -> dict:
        return doctor(db_path=db_path)

    @server.tool(description="Search typed LearnKit memories relevant to a coding task.")
    def learnkit_search(query: str, limit: int = 5) -> list[dict]:
        return search_memory(query, limit, db_path=db_path)

    @server.tool(description="List learned successful tool procedures. This never executes tools.")
    def learnkit_procedures(query: str = "", limit: int = 10) -> list[dict]:
        return list_procedures(query, limit, db_path=db_path)

    @server.tool(description="Retrieve bounded procedural guidance for a task. This never executes tools.")
    def learnkit_context(task: str) -> str:
        return context_for_task(task, db_path=db_path)

    return server


def run_server(*, db_path: Optional[str] = None) -> None:
    build_server(db_path=db_path).run(transport="stdio")
