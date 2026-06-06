# Refactor for Readability

## When to use this skill
Improve the clarity of existing code without changing its behaviour — targeting
naming, function length, nesting depth, or mixed abstraction levels.

## Approach
1. Confirm full test coverage **before touching any code** — refactoring without tests is rewriting
2. Identify the primary readability problem: naming, length, nesting, or abstraction mismatch
3. Rename variables and functions to reflect their purpose, not their type or shape
4. Extract long functions at natural seams — each function should do one thing at one level
5. Flatten deep nesting with early returns and guard clauses
6. Remove dead code: commented-out blocks, unused imports, unreachable branches
7. Run all tests after **each atomic change** to catch accidental behaviour drift
8. If a bug is found during refactoring, stop — open a separate fix PR first

## Tools used
- **pytest**: run after every atomic change
- **rope**: safe automated rename and extract-function refactoring
- **ast**: inspect the parse tree for structural issues before editing

## Known constraints
- Zero behaviour change — this is the hard rule
- Commit each atomic step separately so `git bisect` can isolate regressions
- Never mix refactoring and feature changes in the same PR

## Known failure modes
- Breaking behaviour while renaming because tests weren't run in between
- Over-abstracting simple, linear code into layers of indirection
- Renaming to shorter identifiers that lose domain meaning (`process` instead of `validate_invoice_totals`)
- Bundling unrelated cleanup into one massive commit that is impossible to review

## Examples
### Good output pattern
**Before:**
```python
def f(d):
    if d is not None:
        if d.get('type') == 'invoice':
            if d.get('total') > 0:
                return True
    return False
```
**After:**
```python
def is_valid_invoice(document: dict) -> bool:
    if document is None:
        return False
    return document.get("type") == "invoice" and document.get("total", 0) > 0
```

### Bad output pattern
Renaming `process_data()` to `p()` to save keystrokes, or extracting a two-line
function into a class with three layers of inheritance.
