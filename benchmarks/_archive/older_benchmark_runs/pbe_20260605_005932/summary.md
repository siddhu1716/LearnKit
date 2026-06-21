# LearnKit PBEBench-Lite Benchmark Results

Run: `20260605_005932`
Agent Model: `openai/Qwen/Qwen2.5-72B-Instruct`
Tasks Run: 20

## Summary Table

| Arm | Pass Rate (%) | Mean Latency (s) | Mean Total Tokens |
|---|---|---|---|
| control | 10.0% | 15.16s | 1778.5 |
| cold_start | 30.0% | 5.27s | 3296.5 |
| warmed_start | 30.0% | 4.57s | 3239.7 |

## Compounding Curve (Score per task index)

| Arm | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 | t11 | t12 | t13 | t14 | t15 | t16 | t17 | t18 | t19 | t20 |
|---| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| control | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 | 0 | 5 |
| cold_start | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 |
| warmed_start | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 0 | 5 |