# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_022324`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | contract_summarization | 6 | 3 | 3.77 | 0.00 | 274 | 0.36 | 0 |
| control | python_debugging | 6 | 3 | 3.33 | 0.00 | 244 | 0.51 | 0 |
| control | sql_authoring | 8 | 3 | 5.00 | 0.00 | 206 | 0.31 | 0 |
| treatment | contract_summarization | 6 | 3 | 3.48 | 0.23 | 548 | 0.37 | 1214 |
| treatment | python_debugging | 6 | 3 | 4.17 | 0.00 | 421 | 0.43 | 761 |
| treatment | sql_authoring | 8 | 3 | 5.00 | 0.00 | 410 | 0.30 | 925 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 3.77 ± 0.00 | 3.48 ± 0.23 | -0.30 | -7.8% |
| python_debugging | 3.33 ± 0.00 | 4.17 ± 0.00 | +0.83 | +25.0% |
| sql_authoring | 5.00 ± 0.00 | 5.00 ± 0.00 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 4.3 | 1.2 | 3.0 | 5.0 | 4.2 | 0.0 | 0.0 |
| python_debugging | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 0.0 | 0.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 1267 | 1298 | 1282 | 1387 | 696 | 1346 | 0 | 0 |
| python_debugging | 1077 | 1037 | 711 | 1033 | 0 | 711 | 0 | 0 |
| sql_authoring | 726 | 1323 | 1240 | 0 | 895 | 895 | 1136 | 998 |
