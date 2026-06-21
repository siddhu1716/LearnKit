# LearnKit SLR-Bench Benchmark Results

Run: `20260605_013311`
Agent Model: `openai/Qwen/Qwen2.5-72B-Instruct`
Tasks Run: 20

## Summary Table

| Arm | Pass Rate (%) | Mean Latency (s) | Mean Total Tokens |
|---|---|---|---|
| control | 100.0% | 1.22s | 582.0 |
| cold_start | 75.0% | 1.14s | 881.9 |
| warmed_start | 75.0% | 1.03s | 881.9 |

## Compounding Curve (Score per task index)

| Arm | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 | t19 | t20 |
|---| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| cold_start | 5 | 0 | 5 | 0 | 0 | 5 | 0 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| warmed_start | 5 | 0 | 5 | 0 | 0 | 5 | 0 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |