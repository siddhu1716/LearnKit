# GDPR Clause Check

## When to use this skill
Review a contract or data processing agreement for GDPR compliance gaps,
flagging missing or inadequate clauses with specific article references.

## Approach
1. Identify all parties and their roles: data controller, processor, or sub-processor
2. Locate the lawful basis clause and verify it names a valid basis under Art. 6
   (consent, contract, legal obligation, vital interests, public task, legitimate interests)
3. Check that data subject rights are addressed: access (Art. 15), erasure (Art. 17),
   portability (Art. 20), objection (Art. 21)
4. Verify data retention limits and deletion or return obligations are explicit (Art. 5(1)(e))
5. Identify international transfer mechanisms: SCCs, adequacy decision, or BCRs (Chapter V)
6. Flag clauses that transfer GDPR liability without corresponding operational controls
7. Confirm a Data Processing Agreement (DPA) is present where one party processes on behalf of another (Art. 28)
8. Output a numbered gap list with: Clause | Issue | Relevant Article | Severity (Critical / Advisory)

## Tools used
- **pdf_reader**: extract full contract text
- **clause_extractor**: locate sections by keyword
- **regex**: identify article references and defined terms

## Known constraints
- Cite GDPR article numbers for every finding — never assert non-compliance without a reference
- Distinguish Critical gaps (enforceable requirement missing) from Advisory findings (best practice)
- Flag findings for qualified legal review — this skill does not constitute legal advice

## Known failure modes
- Missing sub-processor clauses that create downstream Art. 28 liability
- Confusing controller and processor obligations — they are asymmetric under GDPR
- Overlooking implicit international transfers via the processor's cloud provider data centres
- Treating boilerplate "we comply with GDPR" language as substantive compliance

## Examples
### Good output pattern
| # | Clause | Issue | Article | Severity |
|---|--------|-------|---------|----------|
| 1 | §4 Data Processing | No lawful basis stated for processing employee data | Art. 6 | Critical |
| 2 | §7 Retention | Retention period not defined; says "as long as necessary" | Art. 5(1)(e) | Critical |
| 3 | §9 Sub-processors | No requirement to notify controller of sub-processor changes | Art. 28(2) | Critical |

### Bad output pattern
"The contract seems mostly GDPR compliant but could be improved in some areas."
