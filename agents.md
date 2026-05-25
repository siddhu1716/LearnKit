## 1. Think Before Coding
- This SDK is middleware — it plugs into other agents. Never break the public API.
- State assumptions before implementing. If uncertain about how a module connects, read core.py first.
- The decorator pattern in core.py is the user-facing contract. Every other module serves it.

## 2. Simplicity First
- Each module does exactly one thing. Classifier classifies. Retriever retrieves.
- Do not add configuration that wasn't asked for.
- The 5-line integration (LearnKit + @lk.agent) must always stay 5 lines.

## 3. Memory is never directly accessible to the user
- Users interact with the @lk.agent decorator and LearnKit class only.
- Do not expose backend internals. Abstract everything behind BaseBackend.
- Failure records always activate immediately. Never quarantine them.

## 4. The hard token cap (1200 tokens) is non-negotiable
- Do not add a parameter to override it.
- Context explosion is a product failure, not a user preference.

## 5. Test every module independently
- Each module has its own test file. Tests use in-memory SQLite.
- Distiller tests use sample_traces.jsonl fixtures, not live LLM calls.
- Evaluator tests mock the LLM judge.

## 6. Goal-driven tasks
Transform every task into a verifiable statement before coding:
- "Add Mem0 backend" → "Mem0Backend passes all tests in test_sqlite_backend.py"
- "Fix retrieval ranking" → "Search for 'contract' returns legal records above finance records in test fixture"