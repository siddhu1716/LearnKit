# LearnKit Custom-Clustered Benchmark — Results

Run: `20260529_155542`
Agent model: `gemini/gemini-flash-lite-latest`
Judge: Anthropic Claude Haiku (via `learnkit.Evaluator`)

## Aggregate per domain × arm

| Arm | Domain | n | Mean score | Stdev | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|
| control | contract_summarization | 10 | 4.90 | 0.32 | 300 | 2.85 | 0 |
| control | python_debugging | 10 | 4.40 | 0.97 | 214 | 1.84 | 0 |
| control | sql_authoring | 10 | 4.50 | 0.97 | 227 | 2.06 | 0 |
| treatment | contract_summarization | 10 | 4.90 | 0.32 | 355 | 2.41 | 162 |
| treatment | python_debugging | 10 | 4.10 | 0.99 | 330 | 1.77 | 481 |
| treatment | sql_authoring | 10 | 4.20 | 1.48 | 371 | 1.19 | 629 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 4.90 | 4.90 | +0.00 | +0.0% |
| python_debugging | 4.40 | 4.10 | -0.30 | -6.8% |
| sql_authoring | 4.50 | 4.20 | -0.30 | -6.7% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |
|---|---|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 5.0 | 5.0 | 4.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| python_debugging | 4.0 | 4.0 | 3.0 | 5.0 | 5.0 | 4.0 | 4.0 | 5.0 | 5.0 | 2.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 1.0 | 4.0 | 2.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |
|---|---|---|---|---|---|---|---|---|---|---|
| contract_summarization | 0 | 0 | 0 | 0 | 0 | 1617 | 0 | 0 | 0 | 0 |
| python_debugging | 0 | 888 | 0 | 1152 | 603 | 0 | 0 | 828 | 1339 | 0 |
| sql_authoring | 0 | 711 | 662 | 0 | 0 | 796 | 631 | 1045 | 1087 | 1354 |
