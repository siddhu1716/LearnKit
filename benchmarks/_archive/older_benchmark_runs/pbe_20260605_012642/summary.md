# LearnKit PBEBench-Lite Benchmark Results

Run: `20260605_012642`
Agent Model: `openai/Qwen/Qwen2.5-72B-Instruct`
Tasks Run: 20

## Summary Table

| Arm | Pass Rate (%) | Mean Latency (s) | Mean Total Tokens |
|---|---|---|---|
| control | 15.0% | 4.48s | 2724.1 |
| cold_start | 35.0% | 4.71s | 3385.7 |
| warmed_start | 35.0% | 4.38s | 3427.0 |

## Compounding Curve (Score per task index)

| Arm | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 | t19 | t20 |
|---| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 5 |
| cold_start | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 5 | 0 | 5 |
| warmed_start | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 5 | 0 | 5 |