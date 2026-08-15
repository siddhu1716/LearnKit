import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "learnkit"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_claude_marketplace_and_plugin_contract():
    marketplace = _json(ROOT / ".claude-plugin" / "marketplace.json")
    assert marketplace["plugins"][0]["source"] == "./plugins/learnkit"

    manifest = _json(PLUGIN / ".claude-plugin" / "plugin.json")
    assert manifest["mcpServers"]["learnkit"] == {
        "command": "learnkit",
        "args": ["mcp"],
    }

    hooks = _json(PLUGIN / "hooks" / "hooks.json")["hooks"]
    assert {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"} <= set(hooks)
    assert all("${CLAUDE_PLUGIN_ROOT}" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)
    assert all("claude-code" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)


def test_copilot_plugin_contract():
    manifest = _json(PLUGIN / "plugin.json")
    assert manifest["mcpServers"] == ".mcp.copilot.json"
    assert manifest["hooks"] == "hooks/hooks.copilot.json"

    hooks = _json(PLUGIN / "hooks" / "hooks.copilot.json")
    assert hooks["version"] == 1
    assert {"sessionStart", "userPromptSubmitted", "postToolUse", "agentStop"} <= set(hooks["hooks"])
    assert all("${COPILOT_PLUGIN_ROOT}" in entry["command"] for values in hooks["hooks"].values() for entry in values)
    assert all("copilot-cli" in entry["command"] for values in hooks["hooks"].values() for entry in values)


def test_codex_plugin_and_marketplace_contract():
    marketplace = _json(ROOT / ".codex-plugin" / "marketplace.json")
    source = marketplace["plugins"][0]["source"]
    assert source["path"] == "./plugins/learnkit"

    manifest = _json(PLUGIN / ".codex-plugin" / "plugin.json")
    assert manifest["mcpServers"] == "./.codex-plugin/mcp.json"
    assert manifest["hooks"] == "./.codex-plugin/hooks.json"

    mcp = _json(PLUGIN / ".codex-plugin" / "mcp.json")
    assert mcp["mcpServers"]["learnkit"]["args"] == ["mcp"]
    hooks = _json(PLUGIN / ".codex-plugin" / "hooks.json")["hooks"]
    assert {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"} <= set(hooks)
    assert all("${PLUGIN_ROOT}" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)
    assert all("codex" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)


def test_gemini_extension_contract():
    manifest = _json(ROOT / "gemini-extension.json")
    assert manifest["name"] == "learnkit"
    assert manifest["mcpServers"]["learnkit"]["args"] == ["mcp"]

    hooks = _json(ROOT / "hooks" / "hooks.json")["hooks"]
    assert {"SessionStart", "BeforeAgent", "AfterTool", "AfterModel", "AfterAgent", "PreCompress"} <= set(hooks)
    assert all("--host gemini-cli" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)


def test_antigravity_cli_and_ide_contracts():
    cli = ROOT / "plugins" / "learnkit-antigravity"
    assert _json(cli / "plugin.json")["name"] == "learnkit"
    assert _json(cli / "mcp_config.json")["mcpServers"]["learnkit"]["args"] == ["mcp"]
    hooks = _json(cli / "hooks.json")["hooks"]
    assert {"PreInvocation", "PostToolUse", "Stop"} <= set(hooks)
    assert all("--host antigravity-cli" in entry["hooks"][0]["command"] for values in hooks.values() for entry in values)

    ide = ROOT / "plugins" / "learnkit-antigravity-ide"
    assert _json(ide / "mcp_config.json")["mcpServers"]["learnkit"]["args"] == ["mcp"]


def test_vscode_copilot_config_contract():
    vscode = ROOT / "plugins" / "learnkit-vscode-copilot"
    assert "learnkit" in _json(vscode / "mcp.json")["servers"]
    hooks = _json(vscode / "hooks.json")["hooks"]
    assert {"SessionStart", "PostToolUse", "PreCompact"} <= set(hooks)
    assert all("--host vscode-copilot" in entry["command"] for values in hooks.values() for entry in values)


def test_plugin_bundle_contains_launcher_and_skill():
    assert (PLUGIN / "scripts" / "hook.mjs").is_file()
    assert (PLUGIN / "skills" / "learnkit" / "SKILL.md").is_file()


def test_release_version_matches_all_plugin_manifests():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    manifests = [
        PLUGIN / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
        PLUGIN / ".codex-plugin" / "plugin.json",
        ROOT / "gemini-extension.json",
        ROOT / "plugins" / "learnkit-antigravity" / "plugin.json",
    ]
    assert {str(path): _json(path)["version"] for path in manifests} == {
        str(path): version for path in manifests
    }
