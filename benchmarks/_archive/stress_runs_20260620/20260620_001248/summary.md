# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_001248`
Agent model: `openai/Qwen/Qwen2.5-72B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | contract_summarization | 5 | 1 | 5.00 | 0.00 | 276 | 1.98 | 0 |
| control | python_debugging | 5 | 1 | 5.00 | 0.00 | 196 | 2.00 | 0 |
| control | sql_authoring | 5 | 1 | 4.00 | 0.00 | 233 | 2.07 | 0 |
| treatment | contract_summarization | 5 | 1 | 5.00 | 0.00 | 546 | 2.61 | 992 |
| treatment | python_debugging | 5 | 1 | 5.00 | 0.00 | 277 | 1.81 | 361 |
| treatment | sql_authoring | 5 | 1 | 4.00 | 0.00 | 395 | 2.18 | 697 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 5.00 ± 0.00 | 5.00 ± 0.00 | +0.00 | +0.0% |
| python_debugging | 5.00 ± 0.00 | 5.00 ± 0.00 | +0.00 | +0.0% |
| sql_authoring | 4.00 ± 0.00 | 4.00 ± 0.00 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 |
|---|---|---|---|---|---|
| contract_summarization | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| python_debugging | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 0.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 |
|---|---|---|---|---|---|
| contract_summarization | 0 | 1245 | 1304 | 1199 | 1213 |
| python_debugging | 0 | 0 | 0 | 1114 | 693 |
| sql_authoring | 0 | 778 | 1289 | 0 | 1419 |
