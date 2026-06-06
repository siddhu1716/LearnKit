# Data Cleaning Pipeline

## When to use this skill
Design and execute a repeatable, auditable pipeline that transforms a raw dataset
into a validated, schema-conformant output without silently losing records.

## Approach
1. **Profile** the raw dataset: row count, null rates, type distributions, value ranges, duplicate rate
2. **Define the target schema**: expected types, nullability rules, and value constraints per column
3. **Handle missing values** per column — document the decision for each:
   - Drop the row (flag the reason)
   - Impute (median, mode, forward-fill — document the assumption)
   - Retain as null if null is meaningful
4. **Standardise formats**: dates → ISO 8601, strings → strip whitespace, normalise case where appropriate
5. **Deduplicate**: define the primary key, resolve conflicts by recency or highest confidence score
6. **Validate** against the schema — quarantine non-conforming rows to a separate output file
7. **Write a cleaning report**: rows in, rows out, rows quarantined, transformation applied per column
8. Verify the pipeline is **idempotent**: running it twice produces identical output

## Tools used
- **pandas / polars**: data manipulation
- **pydantic / pandera**: schema validation
- **great_expectations**: data quality assertions and profiling
- **duckdb**: SQL-based transformations on large files without loading into memory

## Known constraints
- Never modify the raw input in place — always write to a new output path
- Quarantine invalid rows — never silently drop them; make data loss visible
- Pipeline must be idempotent: same input always produces same output

## Known failure modes
- Silently dropping validation-failing rows, hiding upstream data quality problems
- Imputing missing values without documenting the assumption — taints downstream analysis
- Non-idempotent deduplication (e.g., using `row_number()` without a stable sort) produces different counts on re-runs
- Treating encoding errors (replacement character `�`) as empty strings instead of flagging them

## Examples
### Good cleaning report
```
Input rows:   48,320
Output rows:  47,891  (429 quarantined)
Quarantine reasons:
  - missing 'customer_id': 312 rows  → quarantine/missing_id.parquet
  - 'amount' out of range [0, 1e6]: 117 rows → quarantine/invalid_amount.parquet
Transformations:
  - 'order_date': parsed ISO 8601, 0 failures
  - 'email': lowercased and stripped, 2,341 values normalised
```

### Bad output pattern
"I dropped some rows with nulls and the dataset looks cleaner now."
