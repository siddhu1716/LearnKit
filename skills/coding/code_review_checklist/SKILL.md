# Code Review Checklist

## When to use this skill
Conduct a structured, thorough review of a pull request that catches real bugs,
security issues, and scope creep — without nitpicking style that tooling should enforce.

## Approach
1. Read the PR description first to understand the intent before reading a single line of code
2. Check **correctness**: does the code actually do what the description claims?
3. Check **security**: injection vectors, hardcoded secrets, unvalidated external input
4. Check **error handling**: are failure paths explicit, recoverable, and logged?
5. Check **test coverage**: do new tests exercise the new code paths?
6. Check **readability**: are names self-documenting? Is complexity justified by the problem?
7. Check **scope**: is anything included that is outside the stated goal of the PR?
8. Leave comments that are actionable and specific — cite line numbers, propose alternatives

## Tools used
- **git diff**: review the exact changeset, not the full file
- **static analysis / linter**: run before reviewing to filter out mechanical issues
- **test runner**: verify the test suite passes locally on the branch

## Known constraints
- Mark comments as **Blocking** or **Suggestion** — never leave ambiguity about what must change
- Approve only when all blocking issues are resolved
- Do not request changes that belong in a separate PR

## Known failure modes
- Spending 80% of review time on style issues a formatter should catch
- Approving without reading the tests — most bugs hide in untested paths
- Conflating "I would have done it differently" with "this is wrong"
- Blocking PRs on out-of-scope issues instead of opening a follow-up ticket

## Examples
### Good comment
> **Blocking** — `user_id` comes from the query string but is interpolated directly
> into the SQL string at line 42. Use a parameterised query instead:
> `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`

### Bad comment
> "This could probably be written more cleanly."
