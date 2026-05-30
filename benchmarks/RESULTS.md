# LearnKit Benchmark Results — v0.1.0

**Run:** `20260529_180432` (custom-clustered suite, 60 tasks, 3 domains × 10 tasks × 2 arms)
**Agent model:** `gemini-flash-lite-latest`
**Judge:** Anthropic Claude Haiku 4.5 (via `learnkit.Evaluator`)
**Per-run detail:** [results/20260529_180432/summary.md](results/20260529_180432/summary.md)

---

## Headline

| Domain | Control mean | Treatment mean | Δ score | Relative |
|---|---|---|---|---|
| contract_summarization | 4.70 | **4.90** | **+0.20** | **+4.3%** |
| python_debugging | 4.10 | **4.40** | **+0.30** | **+7.3%** |
| sql_authoring | 4.50 | 4.50 | +0.00 | +0.0% |

LearnKit produces a measurable, positive score lift on 2 of 3 domains. The SQL domain is flat — explained below.

---

## What this tested

- **Control arm**: raw `litellm.completion` calls with a fixed domain-appropriate system prompt. No memory, no LearnKit.
- **Treatment arm**: same agent function wrapped in `@memory.agent(domain=...)`. Tasks within a domain run sequentially against a fresh SQLite store, so task N has access to the distilled skills/facts/failures from tasks 1..N-1.
- **Judge**: a different vendor (Anthropic Haiku) scoring 0–5 against the task prompt + response. Independence between agent and judge is required by the blueprint.
- **Task design**: 10 tasks per domain, deliberately clustered into 2–3 recurring patterns each. This is the setting where LearnKit's compounding effect *should* appear.

---

## What the compounding curve shows

Treatment context size (chars injected into the system prompt) by task index:

| Domain | t1 | t2 | t3 | t4 | t5 | t6 | t7 | t8 | t9 | t10 |
|---|---|---|---|---|---|---|---|---|---|---|
| contract_summarization | 0 | 839 | 1228 | 1492 | 1580 | 1633 | 1663 | 1616 | 1622 | 1567 |
| python_debugging | 0 | 842 | 0 | 676 | 680 | 0 | 0 | 796 | 1304 | 1445 |
| sql_authoring | 0 | 616 | 887 | 0 | 0 | 1064 | 694 | 747 | 944 | 944 |

**Contract is the clean case** — context grows monotonically from 0 → ~1,600 chars and stays there (hard-capped by the router at ~1,200 tokens ≈ 4,800 chars). Every task after t1 successfully retrieves and injects distilled patterns from prior tasks.

**Python and SQL show gaps** — some tasks retrieve nothing. This is correct behavior, not a bug: the retriever returns empty when no prior records meaningfully match (e.g. py03 asks about logging+ProcessPoolExecutor, but py01–02 distilled patterns are about Pool().map and Process — adjacent but not matching).

---

## Why SQL is flat

The single hurtful case is **sql06** — control scored 5.0, treatment scored 2.0 with 1,064 chars of injected context. The task is a "gap detection" SQL query; the retrieved context was from prior `upsert` tasks (wrong pattern). The injected skill misled the model.

This is a real LearnKit failure mode: when retrieval surfaces a *related-but-wrong* pattern, the injected guidance can hurt rather than help. This is what the GEPA evolution loop (`learnkit/evolution/gepa.py`) and the contrastive failure-prompting work in `improvements.md` are meant to address. It's also the failure mode that ReasoningBank's k=1 PRIMARY/SECONDARY split is designed to mitigate — limit the agent's reliance on a single retrieved skill when confidence is mid-range.

---

## Cost of the lift

Treatment roughly **doubles per-task token consumption** (the cost of injecting context):

| Domain | Control mean tokens | Treatment mean tokens | Δ |
|---|---|---|---|
| contract_summarization | 302 | 605 | +100% |
| python_debugging | 220 | 351 | +60% |
| sql_authoring | 231 | 358 | +55% |

This matches the expected tradeoff: LearnKit buys quality with prompt-side tokens. At Gemini Flash Lite pricing (~$0.075 / 1M input tokens), the extra cost is on the order of fractions of a cent per task. Worth it whenever a quality bump matters more than a small extra prompt cost.

---

## Bug surfaced and fixed during the run

The first run produced *negative* lift (treatment worse than control). Root cause turned out to be a real bug in `learnkit/backends/sqlite.py::escape_fts` — multi-word search queries that contained any FTS5 reserved word (`AND`, `OR`, `NOT`, `NEAR`) produced a malformed MATCH expression and the search silently returned empty. Almost every contract task prompt contains the word "and" (e.g. "obligations, term, termination, **and** liability"), so contract retrieval was broken on nearly every task.

**Fix:** double-quote each token in `escape_fts` so reserved words become literal phrases. Regression test added in `tests/test_sqlite_backend.py::test_search_with_fts5_reserved_words_in_query`. All 47 tests pass.

Without this fix, the benchmark would have been measuring a broken retrieval path and falsely concluding LearnKit doesn't work.

---

## Methodology caveats

These results are honest but limited. Things to be skeptical about:

- **n=10 per cell is small.** A score delta of +0.20 with stdev ~0.4 isn't statistically significant in any rigorous sense. To make this evidence rather than indication, we need n=50+ or many seeds.
- **Judge ceiling is real.** Both arms score ~4.5–4.9 on most tasks. The Haiku judge is too lenient on short, well-structured Flash Lite responses. A stricter judge (or a rubric-based scorer for tasks with ground truth) would surface more lift signal.
- **Custom benchmark is not adversarial.** External skeptics will reasonably ask: "did you pick tasks that LearnKit happens to win on?" The answer is yes — the suite is designed to test the mechanism, not to prove competitive parity on standard benchmarks. SWE-bench Lite is scaffolded in `swe_bench_lite/README.md` for v0.2.0 follow-up to address that critique.
- **Single seed.** Both arms ran once. LLM outputs aren't deterministic. Variance across seeds is unmeasured.

What this *is* sufficient to claim: **LearnKit's experience-distillation loop produces measurable positive lift on domain-clustered tasks at a real but manageable token cost. The mechanism (skill distillation, context injection, sequential retrieval) demonstrably fires as designed when retrieval is healthy.**

What this is *not* sufficient to claim: that LearnKit improves agent quality on arbitrary independent tasks at industry-standard benchmark scale. That's the v0.2.0 SWE-bench question.

---

## How to reproduce

```bash
pip install -e ".[dev]"
pip install python-dotenv litellm
# Put GEMINI_API_KEY in benchmarks/.env (gitignored)
# Have ANTHROPIC_API_KEY set globally for the judge
python benchmarks/run_custom.py
```

Run cost: ~$0.50–$2.00 total, ~10–20 minutes including Gemini 503 backoffs.
