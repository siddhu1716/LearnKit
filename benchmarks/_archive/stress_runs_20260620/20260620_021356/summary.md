# LearnKit Custom-Clustered Benchmark — Results

Run: `20260620_021356`
Agent model: `openai/Qwen/Qwen2.5-Coder-7B-Instruct`
Deterministic Custom Rubric Graders (No LLM Judge)

## Aggregate per domain × arm

| Arm | Domain | n_tasks | n_seeds | Mean score | SE | Mean tokens | Mean latency (s) | Mean ctx chars |
|---|---|---|---|---|---|---|---|---|
| control | python_debugging | 18 | 3 | 3.56 | 0.00 | 268 | 0.52 | 0 |
| treatment | python_debugging | 18 | 3 | 3.43 | 0.25 | 407 | 0.54 | 545 |

## Lift: treatment − control (per domain)

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| python_debugging | 3.56 ± 0.00 | 3.43 ± 0.25 | -0.13 | -3.6% |

## Compounding curve (treatment score by task index)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python_debugging | 5.0 | 5.0 | 5.0 | 3.5 | 3.5 | 2.5 | 3.5 | 3.5 | 0.0 | 2.0 | 5.0 | 3.5 | 5.0 | 1.5 | 3.5 | 3.5 | 5.0 | 3.5 |

## LearnKit context size by task index (treatment)

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| python_debugging | 0 | 922 | 0 | 0 | 0 | 0 | 1078 | 843 | 872 | 0 | 1035 | 1201 | 1243 | 0 | 0 | 1274 | 624 | 1250 |
