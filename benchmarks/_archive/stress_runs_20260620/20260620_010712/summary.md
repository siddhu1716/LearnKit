# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_010712`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | contract_summarization | 6 | 3 | 3.77 | 0.00 | 276 | 0.36 | 0 |
| control | python_debugging | 6 | 3 | 3.33 | 0.00 | 252 | 0.48 | 0 |
| control | sql_authoring | 8 | 3 | 5.00 | 0.00 | 207 | 0.31 | 0 |
| treatment | contract_summarization | 6 | 3 | 3.65 | 0.23 | 557 | 0.37 | 1237 |
| treatment | python_debugging | 6 | 3 | 3.61 | 0.28 | 437 | 0.46 | 789 |
| treatment | sql_authoring | 8 | 3 | 5.00 | 0.00 | 404 | 0.30 | 905 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 3.77 ± 0.00 | 3.65 ± 0.23 | -0.13 | -3.4% |
| python_debugging | 3.33 ± 0.00 | 3.61 ± 0.28 | +0.28 | +8.3% |
| sql_authoring | 5.00 ± 0.00 | 5.00 ± 0.00 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 4.3 | 1.2 | 4.0 | 5.0 | 4.2 | 0.0 | 0.0 |
| python_debugging | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 0.0 | 0.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 1204 | 1125 | 1219 | 1308 | 1097 | 1163 | 0 | 0 |
| python_debugging | 1094 | 956 | 708 | 1015 | 0 | 711 | 0 | 0 |
| sql_authoring | 726 | 1263 | 1167 | 0 | 895 | 895 | 1173 | 895 |
