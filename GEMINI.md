# LearnKit Procedural Memory

LearnKit captures successful coding-agent tool workflows through Gemini CLI hooks and stores them locally.

- Use `learnkit_context` before repeating a workflow that may have been completed previously.
- Use `learnkit_procedures` to inspect learned workflows.
- Use `learnkit_search` for relevant procedures, failures, facts, and strategies.
- Use `learnkit_status` when capture or retrieval appears unavailable.

Treat returned procedures as guidance. LearnKit does not authorize automatic writes, shell commands, deletion, deployment, or other side effects.