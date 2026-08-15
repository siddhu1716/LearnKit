import json

from learnkit.mcp_server import build_server, list_procedures
from learnkit.plugin_runtime import (
    append_event,
    doctor,
    finalize_session,
    format_hook_output,
    normalize_event_name,
)
from learnkit.backends.sqlite import SQLiteBackend


def test_hook_event_aliases_cover_supported_hosts():
    assert normalize_event_name("UserPromptSubmit") == "user_prompt"
    assert normalize_event_name("userPromptSubmitted") == "user_prompt"
    assert normalize_event_name("PostToolUseFailure") == "tool_failure"
    assert normalize_event_name("agentStop") == "stop"
    assert normalize_event_name("BeforeAgent") == "user_prompt"
    assert normalize_event_name("AfterTool") == "tool_success"
    assert normalize_event_name("AfterModel") == "model_usage"
    assert normalize_event_name("AfterAgent") == "stop"
    assert normalize_event_name("PreCompress") == "pre_compact"
    assert normalize_event_name("PreInvocation") == "user_prompt"


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
    run = SQLiteBackend(str(db_path)).list_runs(limit=1)[0]
    assert run["total_tokens"] == 0
    assert run["cost_usd"] == 0.0
    assert run["models"] == {}
    assert run["estimated"] is True


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


def test_gemini_after_tool_error_is_not_learned_as_success(tmp_path):
    state_dir = tmp_path / "state"
    db_path = tmp_path / "memory.db"
    identity = {"session_id": "gemini-1", "cwd": str(tmp_path)}
    append_event(
        "BeforeAgent",
        {**identity, "prompt": "run the failing build"},
        state_dir=str(state_dir),
    )
    append_event(
        "AfterTool",
        {
            **identity,
            "tool_name": "run_shell_command",
            "tool_input": {"command": "npm test"},
            "tool_output": "failed",
            "is_error": True,
        },
        state_dir=str(state_dir),
    )

    result = finalize_session(
        identity,
        db_path=str(db_path),
        state_dir=str(state_dir),
        host="gemini-cli",
    )

    assert result == {"learned": True, "tool_calls": 1, "success": False}
    assert list_procedures(db_path=str(db_path)) == []
    run = SQLiteBackend(str(db_path)).list_runs(limit=1)[0]
    assert run["agent_id"] == "plugin-gemini-cli"
    assert run["agent_name"] == "Gemini CLI"


def test_gemini_hook_output_is_strict_json():
    output = json.loads(format_hook_output("gemini-cli", "BeforeAgent", "Use procedure A"))
    assert output == {
        "hookSpecificOutput": {
            "hookEventName": "BeforeAgent",
            "additionalContext": "Use procedure A",
        }
    }
    assert format_hook_output("antigravity-cli", "PreInvocation", "ignored") == "{}"


def test_gemini_after_model_usage_is_persisted(tmp_path):
    state_dir = tmp_path / "state"
    db_path = tmp_path / "memory.db"
    identity = {"session_id": "gemini-usage", "cwd": str(tmp_path)}
    append_event(
        "BeforeAgent",
        {**identity, "prompt": "build a report"},
        state_dir=str(state_dir),
    )
    append_event(
        "AfterModel",
        {
            **identity,
            "llm_request": {"model": "gemini-3-pro"},
            "llm_response": {
                "modelVersion": "gemini-3-pro-001",
                "usageMetadata": {
                    "promptTokenCount": 120,
                    "candidatesTokenCount": 30,
                    "thoughtsTokenCount": 10,
                },
            },
        },
        state_dir=str(state_dir),
    )
    append_event(
        "AfterTool",
        {
            **identity,
            "tool_name": "query",
            "tool_input": {},
            "tool_output": "rows",
        },
        state_dir=str(state_dir),
    )

    finalize_session(
        identity,
        db_path=str(db_path),
        state_dir=str(state_dir),
        host="gemini-cli",
    )

    run = SQLiteBackend(str(db_path)).list_runs(limit=1)[0]
    assert run["llm_calls"] == 1
    assert run["prompt_tokens"] == 120
    assert run["completion_tokens"] == 40
    assert run["total_tokens"] == 160
    assert run["models"] == {"agent": "gemini-3-pro-001"}


def test_doctor_and_mcp_server_are_available(tmp_path):
    result = doctor(db_path=str(tmp_path / "memory.db"), state_dir=str(tmp_path / "state"))
    assert result["ok"] is True

    server = build_server(db_path=str(tmp_path / "memory.db"))
    assert server.name == "learnkit"
