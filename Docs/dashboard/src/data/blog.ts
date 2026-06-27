// ============================================================
// LearnKit Dashboard — Blog content
// Posts on AI agents and self-improving memory. Bodies are
// Markdown rendered in-app via react-markdown.
// ============================================================

import type { BlogPost } from '../types';

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'self-improving-memory-for-agents',
    title: 'Self-Improving Memory: How Agents Learn From Their Own Runs',
    description:
      'Why static prompts plateau, and how a procedural memory loop lets an agent get measurably faster and more reliable on tasks it has seen before.',
    author: 'LearnKit Team',
    date: '2026-06-18',
    readingMinutes: 7,
    tags: ['memory', 'agents', 'architecture'],
    body: `## The plateau problem

Most production agents are *stateless between tasks*. Every run starts from the
same system prompt, the same tools, and zero recollection of what worked an hour
ago. That design is easy to reason about — but it means the agent never gets
better. It re-derives the same plan, makes the same detours, and pays the same
token and latency cost on the hundredth refund request as it did on the first.

Self-improving memory breaks that plateau. Instead of throwing away each
trajectory, the agent **distills** successful runs into reusable procedures and
**retrieves** them the next time a similar task arrives.

## The loop

LearnKit wraps an agent in a four-stage loop:

1. **Classify** — label the incoming task (domain, task type) so memory can be
   scoped and retrieved precisely.
2. **Retrieve** — pull the most relevant skills, facts, and failure patterns
   under a token budget, with diversity-aware ranking so the context is not
   redundant.
3. **Act** — the agent runs with that injected context.
4. **Distill & evaluate** — an LLM judge scores the outcome; on a fresh success,
   the trajectory is compressed into a procedure and stored.

> The key insight: a *procedure* is fingerprinted by its tool-call sequence. Two
> trajectories that call the same tools in the same order are the same skill, so
> the store dedups naturally instead of ballooning.

## What gets better

- **Tool calls drop.** Once a procedure is learned, replays reuse it instead of
  re-planning. We track \`callsReduced\` against a per-family baseline.
- **Latency drops** with fewer round-trips.
- **Success rate climbs** as failure patterns steer the agent away from known
  dead ends.

The dashboard's **Agents** and **Observability** pages chart exactly these
curves, so you can see learning happen rather than take it on faith.

## Where to go next

Pair this with quarantine + decay so low-quality memories age out, and you get a
store that is not just growing but *curating itself*.`,
  },
  {
    slug: 'observability-for-learning-agents',
    title: 'Observability for Learning Agents: Tokens, Latency, and Cost',
    description:
      'You cannot improve what you cannot see. A practical look at the telemetry every agent platform should surface — and how LearnKit estimates it honestly.',
    author: 'LearnKit Team',
    date: '2026-06-22',
    readingMinutes: 6,
    tags: ['observability', 'cost', 'telemetry'],
    body: `## Four numbers that matter

Agent observability tools (LangSmith, Langfuse, Helicone, and friends) converge
on the same core metrics:

- **Tokens** — prompt vs. completion, per run and in aggregate.
- **Latency** — average plus tail percentiles (p95, p99), because the tail is
  what users feel.
- **Cost** — priced per model, rolled up by agent and over time.
- **Model & labels** — which model served the call, and semantic tags for
  filtering.

## Honest estimates beat missing data

LearnKit calls models through DSPy, which does not expose per-call token usage in
a stable way. Rather than show nothing, the platform measures what it can
directly — **real wall-clock latency**, **real model names**, **real context
size** — and *estimates* prompt/completion tokens from the text volume across the
classify, judge, and distill stages. Cost is computed from a per-model price
table.

Estimated values are flagged \`est.\` everywhere they appear, so you always know
which numbers are measured and which are modelled.

\`\`\`text
run telemetry
├─ latencyMs      1840     (measured)
├─ totalTokens    1920     (estimated)
├─ costUsd        0.0021   (estimated)
└─ model          claude-haiku-4-5
\`\`\`

## Reading the Observability page

- The **totals band** answers "what is this costing me?"
- The **latency percentiles** answer "how bad is the worst case?"
- The **model breakdown** answers "where is the spend going?"
- The **time series** answers "is it trending up or down?"

When an expensive model quietly starts handling more traffic, the breakdown
makes it obvious before the bill does.`,
  },
  {
    slug: 'procedural-vs-declarative-memory',
    title: 'Procedural vs. Declarative Memory in Agent Systems',
    description:
      'Skills, facts, failures, strategies — not all memories are the same. How LearnKit types memory and why that typing drives better retrieval.',
    author: 'LearnKit Team',
    date: '2026-06-25',
    readingMinutes: 5,
    tags: ['memory', 'retrieval', 'design'],
    body: `## Two kinds of knowing

Cognitive science splits long-term memory into **declarative** ("knowing that")
and **procedural** ("knowing how"). Agent memory benefits from the same split:

- **Declarative** — facts, preferences, and strategies. *What is the refund
  window? What tone does this customer prefer?*
- **Procedural** — skills captured as tool-call sequences. *How do I actually
  process a refund end to end?*

## Why typing matters for retrieval

When every memory is an undifferentiated text blob, retrieval is a similarity
contest and skills compete with trivia. Typing lets the retriever:

- **Boost skills** when the task is procedural.
- **Inject failure patterns** as guardrails regardless of similarity.
- **Pin preferences** that should always apply (formal tone, no emoji).

## The LearnKit record types

| Type | Knowing | Example |
| --- | --- | --- |
| Skill | how | Refund processing procedure |
| Strategy | how-ish | De-escalation playbook |
| Fact | that | 30-day refund window |
| Preference | that | Formal English, no emoji |
| Heuristic | that-ish | Aim for 80–200 word replies |
| Failure | not-that | Don't retry immediately on 429 |
| Trace | episodic | One concrete past run |

## Putting it together

Strong agents combine both: procedural memory makes them *fast*, declarative
memory makes them *correct*, and failure memory makes them *safe*. The Memory
Explorer lets you browse each type and watch how confidence and reuse evolve.`,
  },
];

export function getBlogPost(slug: string): BlogPost | undefined {
  return BLOG_POSTS.find((p) => p.slug === slug);
}
