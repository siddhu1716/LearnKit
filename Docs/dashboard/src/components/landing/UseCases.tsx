import {
  MessageSquare,
  Code2,
  Database,
  Search,
  ShoppingBag,
  FileText,
  type LucideIcon,
} from 'lucide-react'

interface UseCase {
  icon: LucideIcon
  title: string
  domain: string
  body: string
  metric: string
  metricLabel: string
}

const cases: UseCase[] = [
  {
    icon: MessageSquare,
    title: 'Support agents',
    domain: 'Customer service',
    body: 'Learn resolutions across tickets. Distil common triage patterns, refund flows, and escalation rules — apply them before the agent even reaches for a tool.',
    metric: '−43%',
    metricLabel: 'LLM calls per ticket',
  },
  {
    icon: Code2,
    title: 'Coding agents',
    domain: 'Developer tools',
    body: 'Retain successful API patterns, error-recovery playbooks, and testing conventions. Every failed attempt becomes a guardrail for the next run.',
    metric: '−46%',
    metricLabel: 'planning calls',
  },
  {
    icon: Database,
    title: 'Data extraction',
    domain: 'ETL & pipelines',
    body: 'Capture schema quirks, column mappings, and format handlers per source. Warm-start every new pipeline against your entire extraction history.',
    metric: '+2.25',
    metricLabel: 'quality lift',
  },
  {
    icon: Search,
    title: 'Research agents',
    domain: 'Analyst workflows',
    body: 'Reuse domain conventions, source-vetting rules, and citation patterns. Your research agent gets sharper with every report it writes.',
    metric: '100%',
    metricLabel: 'success held',
  },
  {
    icon: ShoppingBag,
    title: 'Sales / CRM',
    domain: 'Revenue operations',
    body: 'Learn objection handling, discount rules, and account-specific preferences. Every closed deal reinforces the playbook.',
    metric: '−37%',
    metricLabel: 'avg cost per lead',
  },
  {
    icon: FileText,
    title: 'Doc Q&A',
    domain: 'Knowledge assistants',
    body: 'Learn document structure, jargon mappings, and reformulation patterns. Answer the same question the same right way every time.',
    metric: '3× faster',
    metricLabel: 'to correct answer',
  },
]

export function UseCases() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {cases.map((c) => {
        const Icon = c.icon
        return (
          <div
            key={c.title}
            className="group relative flex flex-col rounded-2xl border border-white/8 bg-white/[0.02] p-6 transition hover:border-white/18 hover:bg-white/[0.035]"
          >
            <div className="flex items-center justify-between">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/10 bg-white/[0.03] text-white/70 transition group-hover:border-emerald-400/25 group-hover:text-emerald-300">
                <Icon className="h-4 w-4" strokeWidth={1.5} />
              </div>
              <span className="text-[10px] font-medium uppercase tracking-widest text-white/30">
                {c.domain}
              </span>
            </div>

            <h3 className="mt-6 text-xl font-medium tracking-tight text-white">
              {c.title}
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-white/55">{c.body}</p>

            <div className="mt-6 flex items-baseline justify-between border-t border-white/5 pt-4">
              <div className="font-mono text-xl font-medium text-emerald-400">
                {c.metric}
              </div>
              <div className="text-[10px] uppercase tracking-widest text-white/40">
                {c.metricLabel}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
