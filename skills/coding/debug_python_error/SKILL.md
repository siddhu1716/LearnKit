# Debug Python Error

## When to use this skill
Diagnose and resolve a Python runtime error, traceback, or unexpected behavior
by systematically isolating the root cause and applying the minimal fix.

## Approach
1. Read the full traceback from bottom to top — identify the exception type and line
2. Reproduce the error in isolation with a minimal test case
3. Check for common causes: import errors, type mismatches, concurrency issues
4. Inspect the call stack for unexpected state mutations
5. Apply the minimal fix and verify with the original failing case
6. Add a regression test to prevent recurrence

## Tools used
- pdb: interactive debugger for stepping through execution
- pytest: run targeted test to reproduce and verify fix
- traceback: format and analyze exception chains

## Known constraints
- Always reproduce before fixing — never guess-fix
- Prefer minimal changes over refactoring during debugging
- Document the root cause in the commit message

## Known failure modes
- Fixing the symptom instead of the root cause (e.g., catching an exception instead of preventing it)
- Using fork start method on macOS (use spawn instead for multiprocessing)
- Missing transitive dependency errors masked by dev environment
- Circular import issues hidden by lazy imports

## Examples
### Good output pattern
**Root cause:** `Pool.map()` hangs on macOS because the default start method is `fork`, which is unsafe with threads.
**Fix:** Set `mp.set_start_method("spawn")` before creating the pool.
**Regression test:** Added `test_pool_spawn_method()` to verify spawn is used.

### Bad output pattern
"I added a try/except around the error so it doesn't crash anymore."
