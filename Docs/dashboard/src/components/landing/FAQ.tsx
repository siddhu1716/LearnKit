import { useState } from 'react'
import { Plus } from 'lucide-react'

const faqs = [
  {
    q: 'What exactly does LearnKit store?',
    a: 'LearnKit stores three kinds of records: **skills** (reusable tool procedures and playbooks that worked), **failures** (dead ends, with the context for why), and **facts** (task-scoped knowledge like schemas or conventions). Each record carries provenance (which run produced it), a confidence score, and reuse counts.',
  },
  {
    q: 'Isn\u2019t this just a vector database?',
    a: 'A vector database stores and retrieves text your agent saw. LearnKit distills what your agent **did** — the productive tool-call sequence — and can replay it. Retrieval is hybrid (semantic + task classification), but the reusable unit is a procedure, not a text chunk.',
  },
  {
    q: 'Isn\u2019t this just Mem0 or Zep?',
    a: 'Those are **semantic/episodic** memory — they help an agent remember facts and conversations, and they benchmark long-conversation recall (Mem0 and Zep publish LoCoMo / LongMemEval accuracy). LearnKit is **procedural** memory: it cuts the planning/LLM calls a tool-using agent spends re-deriving the same workflow. Different axis — often complementary.',
  },
  {
    q: 'How is this different from LangChain Deep Agents Skills?',
    a: 'Deep Agents Skills is the closest — also procedural memory. The difference is authoring and scope: Skills are **hand-written and maintained by you** and live inside LangGraph / Deep Agents. LearnKit **auto-induces** procedures from real successful runs, quality-gates them on the tool outcome, tracks help/harm, and decays stale ones — and it\u2019s framework-agnostic. It can even export a Deep Agents-compatible SKILL.md library, so the two compose.',
  },
  {
    q: 'Is this the same as plan caching?',
    a: 'No. Plan caching keys a whole plan and trades a few points of accuracy for cost. LearnKit does **workflow induction**: it hard-replays only on an exact match (zero LLM) and *guides* similar tasks — the model still plans — so success holds rather than degrades.',
  },
  {
    q: 'Does it work with my existing agent framework?',
    a: 'Yes — LearnKit is framework-agnostic. It ships adapters for **LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, the OpenAI Agents SDK, and raw OpenAI/Anthropic**. The `@lk.agent_learn` decorator wraps any tool-using function that takes a task and returns a result.',
  },
  {
    q: 'What LLMs are supported?',
    a: 'Any chat-completions-compatible model — OpenAI, Anthropic, Google, Mistral, or self-hosted via vLLM / sglang. The published benchmarks run on self-hosted **Qwen2.5-14B, Qwen2.5-32B, and Llama-3.3-70B**, but the SDK is model-agnostic.',
  },
  {
    q: 'How much does it cost, and how much does it save?',
    a: 'The SDK is MIT-licensed; storage is local SQLite (or Postgres) — no proprietary infrastructure. Capturing a procedure adds ~1 LLM call per task, repaid many times over: the published benchmarks show **~38% fewer planning calls** on repeat tasks (up to ~45% on some suites) at equal success.',
  },
  {
    q: 'What happens to bad or outdated memories?',
    a: 'Every record has a confidence score that decays over time. Memories that consistently fail get down-weighted; ones that repeatedly succeed get reinforced. You can also quarantine or delete records manually from the Memory Lifecycle page.',
  },
  {
    q: 'Is my data ever sent to LIA Labs?',
    a: 'Never. LearnKit runs entirely inside your infrastructure — no phone-home, no telemetry, no data upload. The observability dashboard is self-hosted and reads directly from your local store.',
  },
]

function FaqItem({ q, a, defaultOpen = false }: { q: string; a: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)

  const formatted = a.split('**').map((part, i) =>
    i % 2 === 1 ? <strong key={i} className="font-medium text-white/90">{part}</strong> : part
  )

  return (
    <div className="border-b border-white/5 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="group flex w-full items-center justify-between gap-6 py-6 text-left"
      >
        <span className="text-base font-medium text-white/90 transition group-hover:text-white">
          {q}
        </span>
        <span
          className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border border-white/10 text-white/50 transition ${
            open ? 'rotate-45 border-white/25 text-white' : 'group-hover:border-white/20 group-hover:text-white/80'
          }`}
        >
          <Plus className="h-3.5 w-3.5" strokeWidth={2.5} />
        </span>
      </button>
      <div
        className={`grid transition-all duration-300 ease-out ${
          open ? 'grid-rows-[1fr] pb-6' : 'grid-rows-[0fr]'
        }`}
      >
        <div className="overflow-hidden">
          <p className="max-w-2xl text-[15px] leading-relaxed text-white/55">{formatted}</p>
        </div>
      </div>
    </div>
  )
}

export function FAQ() {
  return (
    <div className="mx-auto max-w-3xl">
      {faqs.map((f, i) => (
        <FaqItem key={f.q} q={f.q} a={f.a} defaultOpen={i === 0} />
      ))}
    </div>
  )
}
