import { Check, X, Minus } from 'lucide-react'

type Cell = boolean | 'partial' | string

interface Competitor {
  name: string
  tagline: string
  isUs?: boolean
}

const competitors: Competitor[] = [
  { name: 'LIA Labs', tagline: 'LearnKit', isUs: true },
  { name: 'Mem0', tagline: 'Personal memory' },
  { name: 'MemGPT', tagline: 'Letta / long context' },
  { name: 'LangChain Memory', tagline: 'Chat buffers' },
  { name: 'Vector RAG', tagline: 'Pinecone / Weaviate' },
]

interface Row {
  label: string
  hint?: string
  cells: Cell[]
}

const rows: Row[] = [
  {
    label: 'Distills tool trajectories',
    hint: 'Not just messages — full agent execution traces',
    cells: [true, false, false, false, false],
  },
  {
    label: 'Procedural playbooks',
    hint: 'Reusable step-by-step procedures, not just facts',
    cells: [true, false, false, false, false],
  },
  {
    label: 'Reduces LLM calls',
    hint: 'Measured cost reduction on repeat tasks',
    cells: ['−46%', 'partial', 'partial', false, false],
  },
  {
    label: 'Failure records',
    hint: 'Learns from mistakes, not only successes',
    cells: [true, false, false, false, false],
  },
  {
    label: 'Memory evolution tracking',
    hint: 'Watch confidence, decay, and reinforcement over time',
    cells: [true, false, false, false, false],
  },
  {
    label: 'Framework agnostic',
    cells: [true, true, false, false, true],
  },
  {
    label: 'Semantic retrieval',
    cells: [true, true, true, 'partial', true],
  },
  {
    label: 'Auditable provenance',
    hint: 'Every memory shows where it came from',
    cells: [true, false, false, false, 'partial'],
  },
  {
    label: 'Reproducible benchmarks',
    hint: 'Published numbers you can reproduce',
    cells: [true, false, 'partial', false, false],
  },
  {
    label: 'Open source',
    cells: [true, true, true, true, 'partial'],
  },
  {
    label: 'Self-hostable',
    cells: [true, true, true, true, 'partial'],
  },
]

function CellIcon({ value, isUs }: { value: Cell; isUs?: boolean }) {
  if (value === true) {
    return (
      <div className="flex items-center justify-center">
        <div className={`flex h-5 w-5 items-center justify-center rounded-full ${isUs ? 'bg-emerald-400/15' : 'bg-white/5'}`}>
          <Check className={`h-3 w-3 ${isUs ? 'text-emerald-400' : 'text-white/70'}`} strokeWidth={3} />
        </div>
      </div>
    )
  }
  if (value === false) {
    return (
      <div className="flex items-center justify-center">
        <X className="h-3.5 w-3.5 text-white/20" strokeWidth={2} />
      </div>
    )
  }
  if (value === 'partial') {
    return (
      <div className="flex items-center justify-center">
        <Minus className="h-3.5 w-3.5 text-white/30" strokeWidth={2.5} />
      </div>
    )
  }
  // string value like "−46%"
  return (
    <div className="flex items-center justify-center">
      <span className={`font-mono text-[11px] font-medium ${isUs ? 'text-emerald-400' : 'text-white/60'}`}>
        {value}
      </span>
    </div>
  )
}

export function CompetitorTable() {
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[720px] rounded-2xl border border-white/10 bg-white/[0.02]">
        {/* Header row */}
        <div className="grid grid-cols-[1.6fr_1.05fr_1fr_1fr_1fr_1fr] items-end gap-2 border-b border-white/5 px-6 py-6">
          <div />
          {competitors.map((c) => (
            <div key={c.name} className="text-center">
              <div className={`text-sm font-medium ${c.isUs ? 'text-white' : 'text-white/70'}`}>
                {c.name}
              </div>
              <div className={`mt-1 text-[10px] uppercase tracking-widest ${c.isUs ? 'text-emerald-400/80' : 'text-white/30'}`}>
                {c.tagline}
              </div>
            </div>
          ))}
        </div>

        {/* Rows */}
        {rows.map((row) => (
          <div
            key={row.label}
            className="grid grid-cols-[1.6fr_1.05fr_1fr_1fr_1fr_1fr] items-center gap-2 border-b border-white/5 px-6 py-4 last:border-0 transition hover:bg-white/[0.015]"
          >
            <div>
              <div className="text-[13px] text-white/85">{row.label}</div>
              {row.hint && (
                <div className="mt-0.5 text-[11px] leading-relaxed text-white/40">{row.hint}</div>
              )}
            </div>
            {row.cells.map((cell, i) => (
              <CellIcon key={i} value={cell} isUs={competitors[i]?.isUs} />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
