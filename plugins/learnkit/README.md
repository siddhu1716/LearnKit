# LearnKit coding-agent plugin

## Prerequisite

```bash
pip install "learnkit-ai[coding-agents]"
learnkit plugin doctor
```

The `learnkit` command must be available in the environment that launches the coding agent.

The Python engine and host integration are separate layers. A Git clone is not
required for the engine, but the `learnkit` executable must be available on the
PATH inherited by the host.

## Claude Code

```text
/plugin marketplace add siddhu1716/LearnKit
/plugin install learnkit@learnkit
```

For a local checkout, launch Claude Code with `plugins/learnkit` as a local plugin directory.

## GitHub Copilot CLI

```bash
copilot plugin install siddhu1716/LearnKit:plugins/learnkit
```

For a local checkout:

```bash
copilot --plugin-dir ./plugins/learnkit
```

## Codex CLI

```bash
codex plugin marketplace add siddhu1716/LearnKit
codex plugin add learnkit@learnkit
```

## Other hosts

- Gemini CLI: the repository root is a Gemini extension.
- Antigravity CLI: use `plugins/learnkit-antigravity/`.
- Antigravity IDE: use the MCP-only config in `plugins/learnkit-antigravity-ide/`.
- VS Code Copilot: use the project files in `plugins/learnkit-vscode-copilot/`.

See [`DEVELOPERS.md`](../../DEVELOPERS.md) for complete install and verification steps.

## Scope

The plugin captures prompts and tool outcomes, learns successful procedures at the end of a turn, and exposes read-only MCP tools for search and guidance. It does not directly execute native host tools.