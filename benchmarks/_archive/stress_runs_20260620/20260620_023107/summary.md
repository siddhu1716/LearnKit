# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_023107`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | contract_summarization | 6 | 3 | 3.77 | 0.00 | 274 | 0.36 | 0 |
| control | python_debugging | 6 | 3 | 3.33 | 0.00 | 244 | 0.51 | 0 |
| control | sql_authoring | 8 | 3 | 5.00 | 0.00 | 206 | 0.32 | 0 |
| treatment | contract_summarization | 6 | 3 | 3.61 | 0.20 | 547 | 0.39 | 1183 |
| treatment | python_debugging | 6 | 3 | 3.33 | 0.00 | 318 | 0.41 | 325 |
| treatment | sql_authoring | 8 | 3 | 5.00 | 0.00 | 238 | 0.32 | 148 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 3.77 ± 0.00 | 3.61 ± 0.20 | -0.17 | -4.5% |
| python_debugging | 3.33 ± 0.00 | 3.33 ± 0.00 | +0.00 | +0.0% |
| sql_authoring | 5.00 ± 0.00 | 5.00 ± 0.00 | +0.00 | +0.0% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 5.0 | 4.3 | 1.2 | 2.0 | 5.0 | 4.2 | 0.0 | 0.0 |
| python_debugging | 0.0 | 0.0 | 5.0 | 5.0 | 5.0 | 5.0 | 0.0 | 0.0 |
| sql_authoring | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 |
|---|---|---|---|---|---|---|---|---|
| contract_summarization | 1248 | 1243 | 1283 | 1254 | 696 | 921 | 0 | 0 |
| python_debugging | 1228 | 0 | 0 | 0 | 0 | 589 | 0 | 0 |
| sql_authoring | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1271 |
