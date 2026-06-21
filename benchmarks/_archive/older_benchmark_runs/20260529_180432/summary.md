# LearnKit Custom-Clustered Benchmark — Results

Run: `20260529_180432`
Agent model: `gemini/gemini-flash-lite-latest`
Judge: Anthropic Claude Haiku (via `learnkit.Evaluator`)

## Aggregate per domain × arm

| Arm | Domain | n | Mean score | Stdev | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|
| control | contract_summarization | 10 | 4.70 | 0.48 | 302 | 3.88 | 0 |
| control | python_debugging | 10 | 4.10 | 1.20 | 220 | 4.82 | 0 |
| control | sql_authoring | 10 | 4.50 | 0.97 | 231 | 6.49 | 0 |
| treatment | contract_summarization | 10 | 4.90 | 0.32 | 605 | 4.74 | 1324 |
| treatment | python_debugging | 10 | 4.40 | 0.97 | 351 | 5.96 | 574 |
| treatment | sql_authoring | 10 | 4.50 | 1.08 | 358 | 8.83 | 590 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 4.70 | 4.90 | +0.20 | +4.3% |
| python_debugging | 4.10 | 4.40 | +0.30 | +7.3% |
| sql_authoring | 4.50 | 4.50 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |
|---|---|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 4.0 | 5.0 |
| python_debugging | 5.0 | 5.0 | 4.0 | 5.0 | 5.0 | 4.0 | 4.0 | 5.0 | 5.0 | 2.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 2.0 | 3.0 | 5.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |
|---|---|---|---|---|---|---|---|---|---|---|
| contract_summarization | 0 | 839 | 1228 | 1492 | 1580 | 1633 | 1663 | 1616 | 1622 | 1567 |
| python_debugging | 0 | 842 | 0 | 676 | 680 | 0 | 0 | 796 | 1304 | 1445 |
| sql_authoring | 0 | 616 | 887 | 0 | 0 | 1064 | 694 | 747 | 944 | 944 |
