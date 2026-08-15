# LearnKit coding-agent plugin

## Prerequisite

```bash
pip install "learnkit-ai[coding-agents]"
learnkit plugin doctor
```

The `learnkit` command must be available in the environment that launches the coding agent.

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

## Scope

The plugin captures prompts and tool outcomes, learns successful procedures at the end of a turn, and exposes read-only MCP tools for search and guidance. It does not directly execute native host tools.