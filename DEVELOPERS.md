# LearnKit Developer Guide

This guide covers installation, coding-agent integrations, the local dashboard, and verification.

## Choose an installation mode

LearnKit has two layers:

1. The Python engine (`learnkit-ai`) stores, retrieves, evaluates, and serves procedural memory.
2. A host integration provides lifecycle hooks and MCP registration for a coding agent.

A Git clone is not required for the engine. Install it from PyPI:

```bash
pipx install "learnkit-ai[coding-agents]==2.0.0"
# Alternative: uv tool install "learnkit-ai[coding-agents]"
# Project environment: python -m pip install "learnkit-ai[coding-agents]"

learnkit plugin doctor
```

The `learnkit` executable must be on the PATH inherited by the coding agent.

> GitHub tag `v2.0` corresponds to canonical PyPI version `2.0.0`. To test
> changes that have not been published yet, install the current branch directly:
>
> ```bash
> pipx install "learnkit-ai[coding-agents] @ git+https://github.com/siddhu1716/LearnKit.git@lia/agent_mvp"
> ```

### SDK only

Use this when you own the Python agent loop:

```bash
python -m pip install learnkit-ai
```

This provides `LearnKit`, `@memory.agent_learn`, framework adapters, and `run_react_agent`. Exact repeat replay with zero planner calls is available when LearnKit owns the tool registry.

### MCP only

Register this stdio server in any MCP client:

```json
{
  "mcpServers": {
    "learnkit": {
      "command": "learnkit",
      "args": ["mcp"]
    }
  }
}
```

MCP-only mode provides `learnkit_status`, `learnkit_search`, `learnkit_procedures`, and `learnkit_context`. It does not automatically observe the host's native tools, so it cannot learn complete procedures by itself.

### Full coding-agent integration

Install the Python engine first, then install the host plugin or hook configuration below. The host layer captures prompts and tool results; the MCP layer provides retrieval and inspection.

## Host integrations

### Claude Code

```text
/plugin marketplace add siddhu1716/LearnKit
/plugin install learnkit@learnkit
```

The bundle is in `plugins/learnkit/` and registers MCP, hooks, and the LearnKit skill.

### GitHub Copilot CLI

```bash
copilot plugin install siddhu1716/LearnKit:plugins/learnkit
```

For local development:

```bash
copilot --plugin-dir ./plugins/learnkit
```

### Codex CLI

```bash
codex plugin marketplace add siddhu1716/LearnKit
codex plugin add learnkit@learnkit
```

The Codex bundle uses `SessionStart`, `UserPromptSubmit`, `PostToolUse`, `PreCompact`, and `Stop`. If a Codex build asks for plugin-hook approval, keep normal approvals enabled and trust only the checked-out LearnKit bundle.

### Gemini CLI

The repository root is a Gemini extension (`gemini-extension.json`, `hooks/hooks.json`, and `GEMINI.md`). After the first GitHub release:

```bash
gemini extensions install https://github.com/siddhu1716/LearnKit --ref v2.0
```

For local development from a clone:

```bash
gemini extensions link .
```

Gemini uses `BeforeAgent` for prompt capture, `AfterTool` for tool outcomes, `AfterAgent` for finalization, and `PreCompress` for continuity.

### Antigravity CLI

```bash
agy plugin install https://github.com/siddhu1716/LearnKit/tree/v2.0/plugins/learnkit-antigravity
```

Antigravity CLI provides prompt, tool, and stop hooks through this bundle. For local development, pass the local `plugins/learnkit-antigravity` directory to `agy plugin install`.

### Antigravity IDE

The IDE integration is MCP-only because the current IDE surface does not expose the lifecycle hooks needed for automatic native-tool capture. Merge `plugins/learnkit-antigravity-ide/mcp_config.json` into:

```text
~/.gemini/antigravity/mcp_config.json
```

Add the contents of `plugins/learnkit-antigravity-ide/GEMINI.md` to the IDE's project instructions.

### VS Code Copilot

Copy or merge:

```text
plugins/learnkit-vscode-copilot/mcp.json   -> .vscode/mcp.json
plugins/learnkit-vscode-copilot/hooks.json -> .github/hooks/learnkit.json
```

Append `plugins/learnkit-vscode-copilot/copilot-instructions.md` to `.github/copilot-instructions.md`.

VS Code Copilot capture is currently partial because this integration has no user-prompt hook. MCP retrieval works; automatic task-to-procedure learning is strongest in Claude Code, Copilot CLI, Codex CLI, Gemini CLI, and Antigravity CLI.

## Storage

Default database:

```text
~/.learnkit/memory.db
```

Override it before launching the coding agent:

```bash
export LEARNKIT_DB_PATH=/path/to/memory.db
export LEARNKIT_PLUGIN_DIR=/path/to/hook-state
```

PowerShell:

```powershell
$env:LEARNKIT_DB_PATH = "$HOME\.learnkit\memory.db"
$env:LEARNKIT_PLUGIN_DIR = "$HOME\.learnkit\plugin"
```

The plugin and dashboard must use the same `LEARNKIT_DB_PATH`.

## Dashboard

The dashboard currently runs from the repository source tree; its React assets are not yet shipped inside the PyPI wheel.

```bash
git clone https://github.com/siddhu1716/LearnKit.git
cd LearnKit
python -m pip install -e ".[dashboard,coding-agents]"
python Docs/run_server.py
```

In another terminal:

```bash
cd Docs/dashboard
npm install
npm run dev
```

Open the Vite URL printed by the command. Plugin-originated records and runs appear automatically when both processes share `LEARNKIT_DB_PATH`.

## Verify an installation

```bash
learnkit --version
learnkit plugin doctor
```

Then ask the host to call `learnkit_status`. Expected fields include:

```json
{
  "database_ok": true,
  "state_dir_ok": true,
  "mcp_available": true,
  "ok": true
}
```

Run a repeated workflow, then inspect:

- `learnkit_procedures` for the captured tool sequence;
- Task History for the finalized run;
- Memory Explorer for the procedural skill; and
- Agents for the stable host identity, such as `plugin-copilot-cli`.

## Security and behavior boundaries

- Hook payloads are bounded and secret-shaped values are redacted before persistence.
- Hook failures fail open and are logged under `~/.learnkit/plugin/hook-errors.log`.
- Plugin MCP tools are read-only.
- Host-native tool execution and approvals remain under the host's control.
- A successful tool call is not automatically proof that the overall code change is correct; production validation should use tests or another trusted outcome signal.

## Development checks

```bash
python -m pip install -e ".[dev,coding-agents]"
pytest -q
ruff check learnkit tests/test_plugin_runtime.py tests/test_plugin_bundle.py
python -m benchmarks.make_results --check
```

See `RELEASING.md` for PyPI and GitHub release steps.
