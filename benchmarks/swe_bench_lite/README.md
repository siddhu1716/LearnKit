# SWE-bench Lite — LearnKit harness (scaffolded for v0.2.0)

**Status: NOT IMPLEMENTED.** This directory exists to lock in the design so a future session can run real SWE-bench Lite without re-litigating the choices.

## What this is

[SWE-bench](https://www.swebench.com/) is a benchmark of real-world Python bug-fix PRs. **SWE-bench Lite** is a 300-task subset chosen for tractability. Each task gives the agent a repo state + a failing test, and grades whether the agent's patch makes the test pass without breaking others.

It's the strongest external-credibility benchmark for "coding agent quality" — but it's also expensive and unforgiving:

- Each task runs in **a Docker container per repo** with the exact dependency snapshot.
- Each task needs the agent to produce a unified diff patch, not free-form text.
- Grading runs the project's actual test suite — minutes per task.
- Models below GPT-4/Sonnet level score in the single digits, which means the noise floor is high.

## Why this is deferred to v0.2.0

The custom-clustered suite (`benchmarks/run_custom.py`) was the right v0.1.0 choice because:

1. It probes LearnKit's compounding mechanism directly (tasks within a domain share patterns).
2. It runs in minutes, not hours.
3. It uses Gemini Flash Lite, which is cheap and available.

SWE-bench Lite would need:

1. A **stronger agent model** (Gemini Pro / Claude Sonnet) — Flash-class models score near zero on real SWE-bench tasks, so neither control nor treatment will show informative numbers.
2. **Docker + the `swebench` package** with disk for ~100GB of cached repos and images.
3. **A patch-generating agent loop** (read file → propose patch → apply → run tests → revise). This is a much bigger agent than the single-shot we use for custom tasks.
4. **A different LearnKit usage pattern** — SWE-bench tasks are mostly independent (different repo per task), so compounding within the benchmark is limited. The interesting comparison is between a *warm* LearnKit store (seeded with a separate training set of debugging patterns) and a *cold* one — both running SWE-bench Lite. That's a v0.2.0-shape experiment.

## When to implement

After v0.2.0 lands the production hardening list in `AGENTS_V2.md` AND we have a stronger agent model in the integration. Then:

```
benchmarks/swe_bench_lite/
├── README.md                  ← this file
├── setup.sh                   ← installs swebench, pulls Docker images
├── runner.py                  ← per-task harness, dual arm (control vs LearnKit warm-state)
├── seed_corpus/               ← Python-debugging tasks used to pre-warm LearnKit
└── results/<run_id>/          ← parallel structure to ../results/
```

## What we know from the v0.1.0 custom run

See `../results/<latest>/summary.md` for the actual numbers and the methodology notes that should carry into the SWE-bench design.
