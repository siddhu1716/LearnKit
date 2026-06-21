# LearnKit SLR-Bench Benchmark Results

Run: `20260605_011101`
Agent Model: `openai/Qwen/Qwen2.5-72B-Instruct`
Tasks Run: 20

## Summary Table

| Arm | Pass Rate (%) | Mean Latency (s) | Mean Total Tokens |
|---|---|---|---|
| control | 100.0% | 1.22s | 582.0 |
| cold_start | 70.0% | 2.11s | 823.6 |
| warmed_start | 70.0% | 1.16s | 822.3 |

## Compounding Curve (Score per task index)

| Arm | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 | t19 | t20 |
|---| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| cold_start | 5 | 0 | 5 | 0 | 0 | 5 | 0 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 | 5 | 5 | 5 |
| warmed_start | 5 | 0 | 5 | 0 | 0 | 5 | 0 | 0 | 5 | 5 | 5 | 5 | 5 | 5 | 0 | 5 | 5 | 5 | 5 | 5 |