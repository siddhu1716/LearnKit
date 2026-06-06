# Write Unit Test

## When to use this skill
Write focused, deterministic unit tests for a function or method that verify
behaviour — not implementation — and will catch real regressions.

## Approach
1. Identify the function's contract: inputs, outputs, and observable side effects
2. List cases: happy path, boundary values, invalid inputs, known failure modes
3. Write one test per behaviour with a name that reads as a sentence:
   `test_<function>_<condition>_<expected_result>`
4. Assert only on outputs and observable side effects — never on internal state
5. Mock only at external boundaries (I/O, network, clock); never mock the unit itself
6. Run the test to confirm it **fails** before the implementation is correct, then passes after

## Tools used
- **pytest**: test runner and assertion library
- **unittest.mock**: patching external dependencies at the boundary
- **hypothesis**: property-based testing for boundary and fuzz cases

## Known constraints
- One assertion focus per test — split multi-concern tests
- Tests must be fully independent: no shared mutable state, no ordering assumptions
- Tests must be deterministic: freeze time, seed random, mock network

## Known failure modes
- Testing implementation details (private methods, internal state) — breaks on refactor
- Over-mocking causes tests that always pass but never catch real bugs
- Shared mutable fixtures causing order-dependent test failures
- Asserting on log output or print statements instead of return values

## Examples
### Good output pattern
```python
def test_parse_date_iso_format_returns_date_object():
    result = parse_date("2026-01-15")
    assert result == date(2026, 1, 15)

def test_parse_date_invalid_string_raises_value_error():
    with pytest.raises(ValueError, match="Invalid date"):
        parse_date("not-a-date")
```

### Bad output pattern
```python
def test_parse_date():
    # Tests three different things, unclear what fails
    assert parse_date("2026-01-15") == date(2026, 1, 15)
    assert parse_date("") is None
    assert parse_date("bad") is None
```
