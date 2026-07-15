import { useState } from 'react'
import { Plus } from 'lucide-react'

const faqs = [
  {
    q: 'What exactly does LearnKit store?',
    a: 'LearnKit stores three types of records: **skills** (things that worked — reusable procedures and playbooks), **failures** (things that didn\u2019t work, with the context for why), and **facts** (task-scoped knowledge like schemas, conventions, or user preferences). Each record ships with provenance (which task produced it), confidence, and use counts.',
  },
  {
    q: 'How is this different from a vector database?',
    a: 'Vector databases store what your agent said. LearnKit distills what your agent did — the full trajectory of tool calls, reasoning steps, and outcomes — into structured, reusable knowledge. Retrieval is hybrid (semantic + task classification + procedural playbooks) rather than pure similarity search.',
  },
  {
    q: 'Does it work with my existing agent framework?',
    a: 'Yes. LearnKit is framework-agnostic. Officially tested with DSPy, LangChain, LlamaIndex, OpenAI Assistants, and plain Python. The `@lk.agent_learn` decorator integrates with any tool-using function that takes a task and returns a result.',
  },
  {
    q: 'What LLMs are supported?',
    a: 'Any chat-completions-compatible model — OpenAI, Anthropic, Google, Mistral, and any self-hosted model via vLLM or sglang. Our published benchmarks use Qwen2.5-14B and 32B running on local GPUs, but the SDK is model-agnostic.',
  },
  {
    q: 'How much does it cost to run?',
    a: 'The SDK is MIT-licensed and free. Storage runs on SQLite locally or Postgres in production — no proprietary infrastructure. Distillation uses ~1 additional LLM call per completed task, offset many times over by the −33% to −46% reduction in future call counts.',
  },
  {
    q: 'Is my data ever sent to LIA Labs?',
    a: 'Never. LearnKit runs entirely inside your infrastructure. There is no phone-home, no telemetry, no data upload. The observability dashboard is self-hosted and reads directly from your local store.',
  },
  {
    q: 'How do I know memories are actually helping?',
    a: 'Every dashboard view answers this. The Overview shows cold-vs-warm success rates side by side. The Benchmarks page reproduces our published numbers against your own agent. The Trace view shows exactly which memories were retrieved and applied for any given task.',
  },
  {
    q: 'What happens to bad or outdated memories?',
    a: 'LearnKit tracks confidence and decay on every record. Memories that consistently fail get automatically down-weighted; memories that repeatedly succeed get reinforced. You can also quarantine or delete records manually from the Memory Lifecycle page.',
  },
  {
    q: 'How is this different from LangChain\u2019s memory?',
    a: 'LangChain memory is a chat-buffer abstraction — it stores conversation turns, not learned behavior. LearnKit sits at a different layer: it captures agent decisions, distills them into playbooks, and injects them back as procedural guidance. The two are complementary, not competing.',
  },
  {
    q: 'Can I contribute or self-host the dashboard?',
    a: 'Yes to both. The dashboard, SDK, and benchmark harness are all in the same open-source repository. Docker images and a one-command deploy script are shipped in `/deploy`. Community contributions welcome — see CONTRIBUTING.md.',
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
