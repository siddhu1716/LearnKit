# LearnKit Codebase Review & YC Readiness Plan

Date: June 4, 2026

## Executive Summary

LearnKit is a credible MVP for an agent learning layer. The core idea is strong: agents repeatedly make the same mistakes, and LearnKit gives them a lightweight memory layer that distills execution traces into reusable skills, facts, failures, and heuristics without fine-tuning.

The current codebase supports the basic story. The SDK has a clean decorator-based API, a SQLite-first memory backend, typed memory records, retrieval safeguards, prompt-bounded context composition, adapter support, benchmark scaffolding, and a passing test suite.

The biggest issue is not the idea or the first implementation. The biggest issue is proof. The current benchmark evidence shows the mechanism works on clustered tasks, but it is not yet strong enough to convince a skeptical YC interviewer that LearnKit reliably improves real-world agents. The next milestone should be a reproducible external benchmark or production-like agent workflow where LearnKit shows measurable lift, fewer retries, or lower total cost.

## Product Thesis

Agents today are mostly stateless. Even when they use memory, they often store raw chat logs or loosely retrieved vector memories. That creates three problems:

- Agents repeat prior syntax, schema, tool-use, and reasoning mistakes.
- Context windows grow with noisy historical data.
- There is no reliable distinction between memories that helped and memories that hurt.

LearnKit's wedge is:

> A zero-infrastructure learning layer for agents that turns execution traces into compact, reusable skills and failure lessons.

The best YC framing is not "memory for agents" in the generic sense. That market sounds crowded. The sharper framing is:

> LearnKit helps agents compound procedural knowledge from their own successful and failed executions.

## What Is Good

### 1. The Core SDK Loop Is Coherent

The central loop in `learnkit/core.py` is easy to understand:

1. Classify the task.
2. Retrieve relevant memory.
3. Compose bounded context.
4. Run the user agent.
5. Evaluate the result.
6. Distill the trajectory.
7. Persist new memory records.

This is the right architecture for an SDK. It is simple enough for developers to adopt and clear enough to benchmark.

### 2. The Decorator API Is a Strong Developer Experience

The `@memory.agent(...)` wrapper is the right product shape. It lets users keep their existing agent function and inject LearnKit around it. This matters because developer tools win through low-friction adoption.

The README's five-line integration example is directionally strong:

```python
memory = lk.LearnKit(memory_backend="sqlite", scope="user")

@memory.agent(domain="coding")
def my_agent(task: str, _learnkit_context: str = "") -> str:
    return call_your_llm(prompt=task, system=_learnkit_context)
```

This is much better than requiring users to rewrite their agent architecture.

### 3. SQLite-First Is the Right Default

SQLite + FTS5 is a pragmatic default. It gives LearnKit a strong contrast against memory systems that require vector databases, embedding queues, hosted infrastructure, or complex setup.

For early users, "install and run locally" is a major advantage.

### 4. The Memory Schema Is Well Chosen

The schema supports multiple useful record types:

- `SkillRecord`
- `FactRecord`
- `FailureRecord`
- `StrategyRecord`
- `PreferenceRecord`
- `TraceRecord`
- `HeuristicRecord`

This is better than storing generic text blobs. It gives the product room to evolve into routing, filtering, dashboards, review workflows, and analytics.

### 5. Retrieval Has Real Guardrails

The code already includes useful protections:

- Confidence floor before injection.
- Quarantine for newly distilled skills and facts.
- Immediate activation for failure records.
- Active/stale filtering.
- Bounded memory routing.
- k=1 primary context plus secondary compact guidelines.

These are important because bad retrieval can actively degrade agent performance.

### 6. The Tests Are Real

The local test run passed:

```text
74 passed, 11 warnings
```

That is a meaningful positive. The tests cover the core backend contract, retrieval behavior, adapters, CLI behavior, distillation parsing, and production hardening pieces.

### 7. The Benchmark Writeup Is Honest

`benchmarks/RESULTS.md` correctly identifies limitations:

- Small sample size.
- Single seed.
- Custom benchmark bias.
- Judge ceiling.
- SQL regression caused by wrong-pattern retrieval.

This honesty is valuable. It makes the project more credible than a document that only claims wins.

## What Is Not Good

### 1. The External Benchmark Story Is Weak

The biggest gap is benchmark credibility.

The custom clustered benchmark is useful for validating the mechanism, but it is not enough to prove broad agent improvement. A skeptic can reasonably say the tasks were chosen to show memory lift.

The SWE-bench Lite folder is also not ready. Its README says the harness is not implemented, while the directory contains experimental scripts and prediction files. The visible prediction samples contain empty patches, which should not be used as evidence.

### 2. Optional Backends Are Stubs

The package advertises optional extras for Mem0, Zep, and Qdrant, but the backend files currently raise `ImportError`. That is acceptable for a placeholder, but it should not be framed as real backend support.

Options:

- Remove these from the public pitch until implemented.
- Or implement one properly, preferably Qdrant, and document it clearly.

### 3. CI Is Too Soft

The GitHub workflow currently allows lint and type-check failures with `continue-on-error: true`. That is fine during early development, but it sends the wrong signal for a production SDK.

Recommended change:

- Make `ruff check .` a hard gate.
- Keep mypy soft only if type coverage is not ready.
- Add a packaging smoke test.
- Add an import test against the built wheel.

### 4. The Repo Contains Too Much Runtime Noise

The repo has generated and local artifacts such as virtualenv files, caches, logs, benchmark databases, prediction outputs, and distribution artifacts.

This makes the project look less curated. Before sharing with users, YC, or investors, clean the repo so it looks like an SDK, not a local experiment folder.

### 5. The README Overclaims Some Pieces

The README talks about the evolver and GEPA-based mutation, but that flow is not yet a clearly integrated product workflow. The code exists, but the product surface is not mature enough to claim it as a core capability.

The pitch should distinguish:

- Implemented and tested.
- Implemented but experimental.
- Planned.

### 6. Heavy Default Dependencies Hurt the "Thin SDK" Claim

The package depends on large libraries by default, including DSPy, sentence transformers, sqlite-vec, and Anthropic. This weakens the "thin layer" message.

Recommended packaging split:

- Core: SQLite, Pydantic, minimal runtime.
- LLM features: evaluator, classifier, distiller.
- Embeddings: sentence-transformers/sqlite-vec.
- Framework integrations: LangChain, LangGraph, AutoGen.

## What Needs To Be Improved

### 1. Improve Benchmark Rigor

The benchmark system should produce claims that survive skepticism.

Minimum benchmark improvements:

- Run multiple seeds.
- Report mean and standard error.
- Use deterministic programmatic grading wherever possible.
- Track harmful retrieval separately.
- Track first-try success, retry count, latency, token use, and pass rate.
- Keep control and treatment prompts identical except for LearnKit memory.

Ideal benchmark:

- External task source.
- Real pass/fail grading.
- No LLM judge as the only metric.
- Reproducible run script.
- Public summary with raw result files.

### 2. Add Memory Attribution

Every LearnKit run should be inspectable:

- Which records were retrieved?
- Which one became primary?
- What confidence scores did they have?
- How much context was injected?
- Did the task succeed?
- Were the retrieved records reinforced or penalized?

This is important for both debugging and user trust.

### 3. Add Reinforcement And Demotion

The system needs a stronger feedback loop after memory use.

Current direction:

- Distill records after runs.
- Store records.
- Retrieve by confidence.

Needed direction:

- If a retrieved memory contributed to success, reinforce it.
- If a retrieved memory contributed to failure, demote it.
- If a memory repeatedly hurts outcomes, quarantine or deprecate it.

This is one of the most important missing product features.

### 4. Add Bad-Memory Detection

The SQL regression in the benchmark is the exact failure mode LearnKit must handle. A related but wrong memory can hurt agent performance.

Add a harmful-memory audit:

- Compare treatment outcome against control or retry outcome.
- If treatment fails after using a memory, record the memory as suspicious.
- Lower confidence when suspicious memories recur.
- Create a contrastive failure record that says when not to use that skill.

### 5. Improve CLI

The current CLI is too small. A useful SDK CLI should include:

```bash
learnkit inspect "task"
learnkit list --type skill
learnkit show <record-id>
learnkit export memory.json
learnkit import memory.json
learnkit seed
learnkit maintain
learnkit report
```

This would make the product feel much more real.

### 6. Add Privacy Controls

Agents may process secrets, source code, customer data, credentials, and private user information.

Add:

- Secret redaction before trace storage.
- Configurable trace capture.
- Memory deletion by scope, domain, or record type.
- Local-only mode.
- Optional encryption at rest.
- A clear statement on what is stored.

### 7. Improve Packaging

Recommended package layout:

```text
learnkit-ai
├── core dependencies only
├── [llm] classifier/evaluator/distiller
├── [embeddings] dense retrieval
├── [langchain]
├── [langgraph]
├── [autogen]
├── [qdrant]
└── [dev]
```

This would make the SDK easier to install and easier to trust.

## Missing Key Features

### 1. Memory Dashboard

Build a small local dashboard or report page that shows:

- Recent runs.
- Distilled memories.
- Retrieved memories.
- Confidence changes.
- Failures avoided.
- Harmful memories.
- Token and latency impact.

This is highly demoable and helps users understand the product immediately.

### 2. Run Report

Add a report generator:

```bash
learnkit report --db ~/.learnkit/memory.db
```

Output:

- Total runs.
- Success rate.
- Average context tokens.
- Top reused skills.
- Memories created.
- Memories reinforced.
- Memories demoted.
- Harmful retrieval count.
- Estimated token overhead.
- Estimated retry savings.

### 3. Agent Framework Examples

The repo should include polished examples for:

- Raw OpenAI-compatible chat.
- LangChain.
- LangGraph.
- A coding agent.
- A tool-using agent.

The best example would be a coding agent that makes a mistake once, distills the lesson, and avoids the mistake on the next task.

### 4. Memory Review Workflow

Users should be able to approve or reject quarantined memories.

Example:

```bash
learnkit review
learnkit approve <record-id>
learnkit reject <record-id>
```

This turns LearnKit from an invisible background system into a controlled learning layer.

### 5. Team Memory

The strongest commercial direction is team-level procedural memory.

Example:

> LearnKit learns your repo conventions, internal APIs, coding style, debugging patterns, and repeated failure modes so every agent starts with team-specific experience.

This is more valuable than generic memory.

### 6. Memory Transfer

Add a way to export learned skills from one agent or project and seed another:

```bash
learnkit export --domain python_debugging team_python_skills.json
learnkit import team_python_skills.json
```

This supports the "compounding knowledge" story.

### 7. Deterministic Task Evaluators

For coding and tool tasks, LearnKit should support deterministic evaluators:

- Unit test pass/fail.
- JSON schema validation.
- SQL result comparison.
- Program output comparison.
- Static checks.

LLM judges are useful, but deterministic grading is much more credible.

## Benchmark Readiness Assessment

### Current Evidence

The current benchmark evidence supports this claim:

> LearnKit's experience-distillation loop can produce measurable lift on clustered task sequences where prior tasks contain reusable procedural patterns.

It does not yet support this stronger claim:

> LearnKit reliably improves arbitrary real-world agents across standard benchmarks.

### Strong Results

The custom simple replace benchmark is the cleanest signal:

- Control: 95%
- Cold Start: 100%
- Warmed Start: 100%
- Latency reduced by roughly 30%

This shows first-try success improvement when repeated procedural patterns exist.

### Weak Or Neutral Results

PBEBench-Lite pilot:

- Control: 10%
- Cold Start: 10%
- Warmed Start: 5%

This shows that irrelevant or poorly matched memory can hurt.

SLR-Bench:

- All arms: 100%

This shows LearnKit does not degrade performance, but it does not prove improvement because the base model already solved everything.

### YC Benchmark Recommendation

Before YC submission or interview, produce one stronger benchmark:

1. Use a real external task source.
2. Run control vs LearnKit.
3. Use deterministic grading where possible.
4. Report first-try success and retry reduction.
5. Include harmful retrieval count.
6. Publish the exact reproduction command.

Good candidates:

- SWE-bench Lite subset with real patch validation.
- A smaller coding-repair benchmark with unit tests.
- A browser/tool-use benchmark with repeated workflows.
- A repo-specific internal benchmark where agents repeatedly handle similar bugs.

For YC, even a narrow result is enough if it is honest and reproducible.

## YC Positioning

### Strong One-Liner

LearnKit is a learning layer for AI agents that turns successful and failed executions into reusable skills, so agents stop repeating the same mistakes.

### Problem

AI agents are expensive because they are stateless. They repeatedly rediscover the same tool-use patterns, retry the same failed approaches, and forget what worked in prior runs.

### Solution

LearnKit wraps any Python agent and automatically distills execution traces into a compact memory library of skills, facts, and failure lessons. On future tasks, it retrieves only high-confidence relevant memories and injects them into the agent context.

### Why Now

Agents are moving from demos to repeated production workflows. As soon as an agent performs recurring work, procedural memory becomes valuable. Companies do not want agents that start from zero on every run.

### Initial Wedge

Developer agents and coding workflows:

- Debugging repeated error patterns.
- Remembering repo-specific conventions.
- Avoiding failed patch strategies.
- Learning internal APIs.
- Reducing retry loops.

### Differentiation

Compared with generic vector memory:

- LearnKit stores typed procedural records, not raw chat logs.
- It tracks confidence and lifecycle state.
- It records failures as first-class memory.
- It is zero-infrastructure by default.
- It is designed for agent execution traces, not human note storage.

## Recommended Roadmap

### Phase 1: Repo And SDK Cleanup

Priority: immediate.

- Clean runtime artifacts from repo.
- Make CI stricter.
- Split heavy optional dependencies.
- Remove or clearly label backend stubs.
- Tighten README claims.
- Add package smoke tests.

### Phase 2: Observability And Control

Priority: high.

- Add `learnkit inspect`.
- Add `learnkit list/show/export/import`.
- Add memory attribution per run.
- Add memory review workflow.
- Add run report.

### Phase 3: Memory Quality Loop

Priority: high.

- Reinforce helpful memories.
- Demote harmful memories.
- Track memory contribution.
- Add suspicious-memory detection.
- Add deterministic evaluators.

### Phase 4: Credible Benchmark

Priority: highest for YC.

- Pick one external or production-like benchmark.
- Run control vs LearnKit.
- Use deterministic grading.
- Report pass rate, retry count, latency, token use, and harmful retrieval.
- Publish methodology and caveats.

### Phase 5: Team Memory Product

Priority: commercial direction.

- Project/team scoped memory.
- Repo-specific seed memory.
- Memory export/import.
- Dashboard.
- Privacy controls.

## Key Risks

### Risk 1: Bad Memories Hurt Agents

If LearnKit retrieves the wrong memory, it can reduce performance. This already appeared in the SQL benchmark.

Mitigation:

- Harmful retrieval tracking.
- Memory demotion.
- Better task-pattern matching.
- Programmatic post-run validation.

### Risk 2: Benchmark Lift Is Too Narrow

If lift only appears on hand-clustered tasks, the product may look like a demo.

Mitigation:

- External benchmark.
- Real user workflow.
- Focus on repeated production tasks where memory is naturally valuable.

### Risk 3: LLM Judge Credibility

LLM judges are useful but not enough.

Mitigation:

- Use deterministic graders.
- Use tests, execution checks, and exact output comparison.
- Keep LLM judge as supplemental analysis.

### Risk 4: Install Weight

If the SDK feels heavy, developers may not adopt it.

Mitigation:

- Slim core package.
- Optional extras.
- Lazy imports.

## Final Recommendation

LearnKit is worth continuing. The codebase is past the idea stage and has a reasonable MVP architecture. The strongest next move is not adding more memory types or more theoretical features. The strongest next move is proving the loop in a credible setting.

For YC, the application should say:

> We built a working learning layer for agents. It wraps existing Python agents, distills successful and failed executions into reusable typed memories, and retrieves high-confidence lessons on future runs. Our early benchmarks show measurable lift on repeated task families, and we are now validating on external coding-agent benchmarks.

The most important milestone before submission:

> Show one reproducible result where LearnKit improves a real agent workflow by reducing retries, improving first-try success, or lowering total cost.

