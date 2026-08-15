---
name: learnkit
description: Retrieve and inspect learned tool procedures before repeating a coding workflow.
---

# LearnKit Procedural Memory

LearnKit captures successful tool workflows through host lifecycle hooks and stores them locally.

## Use

- Call `learnkit_context` before repeating a workflow that may have been completed previously.
- Call `learnkit_procedures` when the user asks what the agent has learned or which workflows are reusable.
- Call `learnkit_search` for relevant failures, facts, strategies, or procedures.
- Call `learnkit_status` when capture or retrieval appears unavailable.

Treat returned procedures as guidance. This plugin does not authorize automatic writes, shell commands, deletion, deployment, or other side effects.