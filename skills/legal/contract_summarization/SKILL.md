# Contract Summarization

## When to use this skill
Summarize the key terms, obligations, and risk areas of a legal contract
into a structured, plain-English bullet summary.

## Approach
1. Extract all obligations per party
2. Extract termination clauses and notice periods
3. Flag indemnity and liability cap clauses separately
4. Identify governing law and dispute resolution mechanisms
5. Simplify legal language to plain English
6. Structure output as a bullet summary grouped by party

## Tools used
- pdf_reader: extract text from contract PDF
- clause_extractor: identify clause boundaries and types

## Known constraints
- Output must be under 500 words
- No legal jargon in the summary — plain English only
- Preserve all monetary figures and dates exactly

## Known failure modes
- Hallucinating clause references that don't exist in the document
- Missing amendment or addendum clauses attached at the end
- Confusing indemnification limits across different liability sections
- Merging obligations from different parties into a single list

## Examples
### Good output pattern
**Party A (Service Provider):**
- Must deliver software by Q3 2026
- 30-day cure period for material breach
- Liability capped at $500,000

**Party B (Client):**
- Payment due within 45 days of invoice
- Must provide access to staging environment

### Bad output pattern
"The contract says things about obligations and there are some clauses about termination."
