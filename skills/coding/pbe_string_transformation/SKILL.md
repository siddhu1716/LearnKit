# Programming-by-Example String Transformation

## When to use this skill
Solve Programming-by-Example (PBE) tasks by finding an ordered sequence of Python `replace(A, B)` calls to transform input strings to output strings.

## Approach
1. **Analyze Patterns**: Identify character transformations by comparing the exact inputs and outputs.
2. **Order by Specificity**: Place replacements for longer strings first. If you replace a single character first, it may destroy the context needed for replacing longer strings containing that character later (known as bleeding).
3. **Trace Sequential Execution**: Evaluate how the output of the first replace call affects subsequent replace calls (known as feeding).
4. **Enclose output**: Format the final program sequence strictly as a Python list of strings inside a ```python ``` markdown block, e.g. `["replace('a', 'b')"]`.

## Known constraints
- Arguments A and B in `replace(A, B)` must have length <= 3.
- Predicate A must have length >= 1.
- Maximum of 5 programs per sequence.

## Examples
### Good output pattern
```python
["replace('bc', 'dc')", "replace('ad', 'ed')"]
```
