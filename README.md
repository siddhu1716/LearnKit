# LearnKit

> **Work In Progress: Pre-Release Concept**  
> LearnKit is currently in active development. This repository serves as the architectural blueprint and conceptual overview of what we are building. The code is not yet released for production use.

---

# Fine-Tuning Without Fine-Tuning

LearnKit is an **agent-agnostic SDK** that gives any AI agent a **self-improving memory layer**.

Most agents today suffer from **amnesia** or rely on **naive memory** (storing endless raw chat logs). This creates:

- “Memory soup”
- Exploding context windows
- No signal on whether a past action was actually successful

LearnKit replaces raw chat logs with **Experience Distillation**.

Every time your agent runs, LearnKit:

1. Evaluates the execution trace
2. Extracts what worked (and what failed)
3. Compiles reusable structured memory artifacts

Over time, the agent builds a compounding **“wiki” of expertise** — without retraining the underlying model.

---

# Core Philosophy :

LearnKit treats agent memory like a curated wiki operating across three continuous loops:

## 1. Ingest (The Distiller)

After a task completes, LearnKit analyzes the agent’s Chain-of-Thought (CoT).

- Successful traces → distilled into reusable `SkillRecord`
- Failed traces → converted into `FailureRecord`
- Prevents agents from repeating known mistakes

---

## 2. Query (The Retriever)

Before a task begins:

- LearnKit classifies the domain and task type
- Retrieves high-confidence relevant memories
- Injects only the most useful context

---

## 3. Maintain (The Evolver)

Memory is continuously optimized:

- Unused records decay over time
- High-value skills evolve automatically
- GEPA-based prompt mutation discovers better strategies

---

# ⚙️ How It Works — Execution Loop

The underlying agent remains unchanged.

You simply wrap your existing agent with the LearnKit decorator.

```python
import learnkit as lk

# Initialize LearnKit
memory = lk.LearnKit(
    memory_backend="sqlite",
    scope="team"
)

# Wrap your existing agent
@memory.agent(domain="software_engineering")
def my_coding_agent(task: str) -> str:
    return run_llm(task)

# Agent now has a compounding memory layer
result = my_coding_agent(
    "Debug this Python multiprocessing error"
)


