# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_002551`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | contract_summarization | 8 | 1 | 4.74 | 0.00 | 252 | 0.31 | 0 |
| control | python_debugging | 8 | 1 | 3.75 | 0.00 | 261 | 0.64 | 0 |
| control | sql_authoring | 8 | 1 | 4.38 | 0.00 | 225 | 0.34 | 0 |
| treatment | contract_summarization | 8 | 1 | 4.56 | 0.00 | 387 | 0.30 | 618 |
| treatment | python_debugging | 8 | 1 | 3.75 | 0.00 | 449 | 0.55 | 764 |
| treatment | sql_authoring | 8 | 1 | 4.38 | 0.00 | 358 | 0.35 | 567 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 4.74 ± 0.00 | 4.56 ± 0.00 | -0.18 | -3.8% |
| python_debugging | 3.75 ± 0.00 | 3.75 ± 0.00 | +0.00 | +0.0% |
| sql_authoring | 4.38 ± 0.00 | 4.38 ± 0.00 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 5.0 | 5.0 | 3.6 | 4.2 | 5.0 | 3.8 | 5.0 |
| python_debugging | 5.0 | 0.0 | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| sql_authoring | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 0 | 0 | 1160 | 1287 | 0 | 1119 | 0 | 1377 |
| python_debugging | 0 | 659 | 0 | 991 | 955 | 991 | 1192 | 1327 |
| sql_authoring | 0 | 0 | 0 | 710 | 949 | 1137 | 804 | 936 |
