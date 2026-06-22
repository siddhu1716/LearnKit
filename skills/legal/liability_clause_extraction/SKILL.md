# Liability Clause Extraction

## When to use this skill
Extract, classify, and summarise all liability and indemnity clauses from a
contract, including caps, carve-outs, and asymmetric risk allocations.

## Approach
1. Search for keywords: "liability", "indemnif", "limitation", "cap", "consequential",
   "exclude", "indirect", "loss", "damages"
2. Extract each matching clause with its section number and verbatim text
3. Classify each clause:
   - **Mutual cap**: both parties subject to the same limit
   - **One-sided cap**: limit applies to only one party
   - **Exclusion**: certain loss types excluded from liability entirely
   - **Indemnity**: one party agrees to compensate the other for specific events
   - **Carve-out**: exceptions to a cap or exclusion
4. Identify the cap amount and its basis: fees paid in preceding 12 months, fixed sum, insurance limit
5. List all carve-outs from the cap: fraud, gross negligence, IP infringement, data breach, death/personal injury
6. Flag asymmetric structures that disproportionately burden one party
7. Output as a structured table: Section | Type | Cap Amount | Carve-outs | Notes

## Tools used
- **pdf_reader**: extract full contract text
- **clause_extractor**: locate liability sections
- **regex**: find defined terms and cross-references

## Known constraints
- Preserve exact monetary figures, multipliers, and time periods — never paraphrase
- Quote carve-out language verbatim — paraphrase loses legal precision
- Trace cross-references to definitions sections before interpreting a clause

## Known failure modes
- Missing indirect / consequential loss exclusions buried in the definitions section
- Overlooking carve-outs defined by reference to another section (e.g., "except as set out in Schedule 2")
- Confusing aggregate annual cap with per-incident cap — materially different risk exposure
- Ignoring insurance-backed liability clauses that effectively transfer risk off the balance sheet

## Examples
### Good output pattern
| Section | Type | Cap Amount | Carve-outs |
|---------|------|-----------|-----------|
| §12.1 | Mutual cap | 12 months' fees paid | Fraud, wilful misconduct, data breach |
| §12.3 | Exclusion | N/A — consequential loss excluded | Death or personal injury |
| §12.4 | Indemnity (one-sided) | Uncapped | IP infringement by Supplier |

### Bad output pattern
"The contract limits liability to a reasonable amount with some exceptions for serious issues."
