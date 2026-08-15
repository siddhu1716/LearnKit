import json
from pathlib import Path


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


def test_copilot_plugin_contract():
    manifest = _json(PLUGIN / "plugin.json")
    assert manifest["mcpServers"] == ".mcp.copilot.json"
    assert manifest["hooks"] == "hooks/hooks.copilot.json"

    hooks = _json(PLUGIN / "hooks" / "hooks.copilot.json")
    assert hooks["version"] == 1
    assert {"sessionStart", "userPromptSubmitted", "postToolUse", "agentStop"} <= set(hooks["hooks"])
    assert all("${COPILOT_PLUGIN_ROOT}" in entry["command"] for values in hooks["hooks"].values() for entry in values)


def test_plugin_bundle_contains_launcher_and_skill():
    assert (PLUGIN / "scripts" / "hook.mjs").is_file()
    assert (PLUGIN / "skills" / "learnkit" / "SKILL.md").is_file()
