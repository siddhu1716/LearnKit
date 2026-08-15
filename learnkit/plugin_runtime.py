"""Shared lifecycle-hook runtime for coding-agent plugins."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from .core import LearnKit
from .tool_tracker import ToolTracker

MAX_EVENT_BYTES = 32 * 1024
MAX_VALUE_CHARS = 8_000

_SECRET_KEYS = re.compile(
    r"(^|[_-])(authorization|token|secret|password|passwd|pwd|api[_-]?key|cookie|private[_-]?key)($|[_-])",
    re.IGNORECASE,
)
_SECRET_VALUES = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})",
    re.IGNORECASE,
)

_EVENT_ALIASES = {
    "sessionstart": "session_start",
    "userpromptsubmit": "user_prompt",
    "userpromptsubmitted": "user_prompt",
    "posttooluse": "tool_success",
    "posttoolusefailure": "tool_failure",
    "precompact": "pre_compact",
    "agentstop": "stop",
    "sessionend": "stop",
    "taskcompleted": "stop",
}


class _PluginDistiller:
    def distill(self, trajectory, domain_vector, quality_score):
        return None, [], [], None

    def distill_failure(self, *args, **kwargs):
        return None


def normalize_event_name(event: str) -> str:
    compact = re.sub(r"[^a-z]", "", (event or "").lower())
    return _EVENT_ALIASES.get(compact, (event or "unknown").strip().lower())


def redact_payload(value: Any, *, key: str = "") -> Any:
    if key and _SECRET_KEYS.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact_payload(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value[:100]]
    if isinstance(value, str):
        return _SECRET_VALUES.sub("[REDACTED]", value[:MAX_VALUE_CHARS])
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:MAX_VALUE_CHARS]


def _state_root(state_dir: Optional[str] = None) -> Path:
    configured = state_dir or os.environ.get("LEARNKIT_PLUGIN_DIR")
    return Path(configured or "~/.learnkit/plugin").expanduser()


def _db_path(db_path: Optional[str] = None) -> str:
    return str(Path(db_path or os.environ.get("LEARNKIT_DB_PATH", "~/.learnkit/memory.db")).expanduser())


def _session_key(payload: dict) -> str:
    session_id = payload.get("session_id") or payload.get("sessionId")
    if not session_id:
        session_id = f"{payload.get('cwd') or os.getcwd()}:{payload.get('source') or 'agent'}"
    return hashlib.sha256(str(session_id).encode("utf-8")).hexdigest()[:24]


def _event_dir(payload: dict, state_dir: Optional[str] = None) -> Path:
    return _state_root(state_dir) / "sessions" / _session_key(payload)


def append_event(event: str, payload: dict, *, state_dir: Optional[str] = None) -> Path:
    directory = _event_dir(payload, state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    body = {
        "event": normalize_event_name(event),
        "captured_at_ns": time.time_ns(),
        "payload": redact_payload(payload),
    }
    encoded = json.dumps(body, ensure_ascii=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_EVENT_BYTES:
        body["payload"] = {
            "session_id": payload.get("session_id") or payload.get("sessionId"),
            "cwd": payload.get("cwd"),
            "truncated": True,
        }
        encoded = json.dumps(body, ensure_ascii=True, separators=(",", ":"))
    name = f"{body['captured_at_ns']:020d}-{os.getpid()}-{uuid.uuid4().hex}.json"
    target = directory / name
    temporary = directory / f".{name}.tmp"
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, target)
    return target


def _load_events(payload: dict, state_dir: Optional[str] = None) -> list[tuple[Path, dict]]:
    directory = _event_dir(payload, state_dir)
    loaded: list[tuple[Path, dict]] = []
    if not directory.exists():
        return loaded
    for path in sorted(directory.glob("*.json")):
        try:
            loaded.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError):
            continue
    return loaded


def _text(payload: dict, *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _tool_event(event: dict) -> Optional[dict]:
    payload = event.get("payload") or {}
    name = payload.get("tool_name") or payload.get("toolName") or payload.get("tool")
    if not name:
        return None
    normalized_name = str(name).lower().replace(":", "_")
    if normalized_name.split("__")[-1].startswith("learnkit_"):
        return None
    args = payload.get("tool_input", payload.get("toolInput", payload.get("toolArgs", {})))
    output = payload.get(
        "tool_response",
        payload.get("tool_output", payload.get("tool_result", payload.get("toolResult"))),
    )
    return {
        "name": str(name),
        "args": args if isinstance(args, dict) else {"value": args},
        "output": output,
        "success": event.get("event") == "tool_success",
    }


def context_for_task(task: str, *, db_path: Optional[str] = None) -> str:
    if not task.strip():
        return ""
    memory = LearnKit(
        memory_backend="sqlite",
        db_path=_db_path(db_path),
        background_postprocess=False,
        auto_promote=True,
    )
    try:
        run = memory.prepare_run(task)
        context = run.get("context") or ""
        memory.discard_run(run)
        return context
    finally:
        memory.shutdown()


def finalize_session(
    payload: dict,
    *,
    db_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> dict:
    events = _load_events(payload, state_dir)
    prompt_index = -1
    task = ""
    for index, (_, event) in enumerate(events):
        if event.get("event") != "user_prompt":
            continue
        candidate = _text(event.get("payload") or {}, "prompt", "user_prompt", "userPrompt")
        if candidate:
            prompt_index = index
            task = candidate

    selected = events[prompt_index + 1 :] if prompt_index >= 0 else []
    tools = [tool for _, event in selected if (tool := _tool_event(event)) is not None]
    if not task or not tools:
        return {"learned": False, "reason": "no task or tool calls"}

    memory = LearnKit(
        memory_backend="sqlite",
        db_path=_db_path(db_path),
        background_postprocess=False,
        auto_promote=True,
        distiller=_PluginDistiller(),
    )
    try:
        run = memory.prepare_run(task)
        run["learning_mode"] = "agent_learn"
        tracker = ToolTracker(run["trajectory"])
        for tool in tools:
            tracker.record(
                tool["name"],
                tool["args"],
                tool["output"],
                success=tool["success"],
                productive=tool["success"],
            )
        run["tool_calls"] = tracker.call_count
        run["outcome_score"] = tracker.outcome_score()
        response = _text(payload, "last_assistant_message", "response", "result")
        memory.finalize_run(run, response or "coding-agent task completed")
    finally:
        memory.shutdown()

    for path, _ in events[:]:
        try:
            path.unlink()
        except OSError:
            pass
    return {
        "learned": True,
        "tool_calls": len(tools),
        "success": all(tool["success"] for tool in tools),
    }


def handle_hook(
    event: str,
    payload: dict,
    *,
    db_path: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> str:
    normalized = normalize_event_name(event)
    append_event(normalized, payload, state_dir=state_dir)
    if normalized == "user_prompt":
        task = _text(payload, "prompt", "user_prompt", "userPrompt")
        return context_for_task(task, db_path=db_path)
    if normalized == "pre_compact":
        events = _load_events(payload, state_dir)
        for _, item in reversed(events):
            if item.get("event") == "user_prompt":
                task = _text(item.get("payload") or {}, "prompt", "user_prompt", "userPrompt")
                return context_for_task(task, db_path=db_path)
    if normalized == "stop":
        finalize_session(payload, db_path=db_path, state_dir=state_dir)
    return ""


def doctor(*, db_path: Optional[str] = None, state_dir: Optional[str] = None) -> dict:
    result = {
        "database": _db_path(db_path),
        "state_dir": str(_state_root(state_dir)),
        "database_ok": False,
        "state_dir_ok": False,
        "mcp_available": False,
    }
    try:
        root = _state_root(state_dir)
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".write-test"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        result["state_dir_ok"] = True
    except OSError:
        pass
    try:
        memory = LearnKit(memory_backend="sqlite", db_path=_db_path(db_path))
        memory.backend.list_runs(limit=1)
        memory.shutdown()
        result["database_ok"] = True
    except Exception:
        pass
    try:
        import mcp  # noqa: F401

        result["mcp_available"] = True
    except ImportError:
        pass
    result["ok"] = all(
        result[key] for key in ("database_ok", "state_dir_ok", "mcp_available")
    )
    return result
