# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_022003`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | python_debugging | 18 | 3 | 3.56 | 0.00 | 268 | 0.52 | 0 |
| treatment | python_debugging | 18 | 3 | 3.49 | 0.06 | 348 | 0.52 | 325 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| python_debugging | 3.56 ± 0.00 | 3.49 ± 0.06 | -0.06 | -1.8% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python_debugging | 5.0 | 5.0 | 5.0 | 3.5 | 3.5 | 2.5 | 3.5 | 3.5 | 0.0 | 2.0 | 5.0 | 3.5 | 5.0 | 1.5 | 3.5 | 1.0 | 3.5 | 5.0 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python_debugging | 0 | 922 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1104 | 1303 | 0 | 0 | 1202 | 906 | 0 |
