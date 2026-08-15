import json

from learnkit.mcp_server import build_server, list_procedures
from learnkit.plugin_runtime import (
    append_event,
    doctor,
    finalize_session,
    normalize_event_name,
)


def test_hook_event_aliases_cover_claude_and_copilot():
    assert normalize_event_name("UserPromptSubmit") == "user_prompt"
    assert normalize_event_name("userPromptSubmitted") == "user_prompt"
    assert normalize_event_name("PostToolUseFailure") == "tool_failure"
    assert normalize_event_name("agentStop") == "stop"


def test_payload_is_redacted_before_event_is_written(tmp_path):
    payload = {
        "session_id": "session-1",
        "tool_input": {
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz1234567890",
            "header": "Bearer abcdefghijklmnopqrstuvwxyz",
        },
    }

    path = append_event("PostToolUse", payload, state_dir=str(tmp_path))
    stored = json.loads(path.read_text(encoding="utf-8"))

    assert stored["payload"]["tool_input"]["api_key"] == "[REDACTED]"
    assert stored["payload"]["tool_input"]["header"] == "[REDACTED]"
    assert "abcdefghijklmnopqrstuvwxyz" not in path.read_text(encoding="utf-8")


def test_stop_finalizes_captured_tools_into_a_procedure(tmp_path):
    state_dir = tmp_path / "state"
    db_path = tmp_path / "memory.db"
    identity = {"session_id": "session-1", "cwd": str(tmp_path)}
    append_event(
        "UserPromptSubmit",
        {**identity, "prompt": "build active user report"},
        state_dir=str(state_dir),
    )
    append_event(
        "PostToolUse",
        {
            **identity,
            "tool_name": "query",
            "tool_input": {"table": "users"},
            "tool_output": "rows",
        },
        state_dir=str(state_dir),
    )
    append_event(
        "PostToolUse",
        {
            **identity,
            "tool_name": "format",
            "tool_input": {"fmt": "csv"},
            "tool_output": "report.csv",
        },
        state_dir=str(state_dir),
    )

    result = finalize_session(
        identity,
        db_path=str(db_path),
        state_dir=str(state_dir),
    )

    assert result == {"learned": True, "tool_calls": 2, "success": True}
    procedures = list_procedures(db_path=str(db_path))
    assert len(procedures) == 1
    assert procedures[0]["tool_sequence"] == ["query", "format"]


def test_stop_ignores_learnkit_mcp_tools(tmp_path):
    state_dir = tmp_path / "state"
    db_path = tmp_path / "memory.db"
    identity = {"session_id": "session-1", "cwd": str(tmp_path)}
    append_event(
        "UserPromptSubmit",
        {**identity, "prompt": "check whether LearnKit is healthy"},
        state_dir=str(state_dir),
    )
    append_event(
        "PostToolUse",
        {
            **identity,
            "tool_name": "mcp__learnkit__learnkit_status",
            "tool_input": {},
            "tool_output": {"ok": True},
        },
        state_dir=str(state_dir),
    )

    result = finalize_session(identity, db_path=str(db_path), state_dir=str(state_dir))

    assert result == {"learned": False, "reason": "no task or tool calls"}
    assert list_procedures(db_path=str(db_path)) == []


def test_doctor_and_mcp_server_are_available(tmp_path):
    result = doctor(db_path=str(tmp_path / "memory.db"), state_dir=str(tmp_path / "state"))
    assert result["ok"] is True

    server = build_server(db_path=str(tmp_path / "memory.db"))
    assert server.name == "learnkit"
