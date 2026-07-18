import { Check, X, Minus } from 'lucide-react'

type Cell = boolean | 'partial' | string

interface Competitor {
  name: string
  tagline: string
  isUs?: boolean
}

const competitors: Competitor[] = [
  { name: 'LIA Labs', tagline: 'LearnKit', isUs: true },
  { name: 'Deep Agents', tagline: 'LangChain Skills' },
  { name: 'Letta', tagline: 'MemGPT' },
  { name: 'Mem0', tagline: 'Semantic memory' },
  { name: 'Zep', tagline: 'Temporal graph' },
]

interface Row {
  label: string
  hint?: string
  cells: Cell[]
}

const rows: Row[] = [
  {
    label: 'Procedural memory',
    hint: 'Reuses how a task was done — not just facts or conversations',
    cells: [true, true, 'partial', false, false],
  },
  {
    label: 'Auto-induced from real runs',
    hint: 'Procedures are captured automatically, not hand-authored',
    cells: [true, false, 'partial', false, false],
  },
  {
    label: 'Replays tool procedures',
    hint: 'Zero-LLM execution on an exact repeat',
    cells: [true, false, false, false, false],
  },
  {
    label: 'Cuts planning / LLM calls',
    hint: 'Published, reproducible call reduction on repeat tasks',
    cells: ['−38%', false, false, false, false],
  },
  {
    label: 'Quality-gated + help/harm attribution',
    hint: 'Tracks whether each memory actually helped, and decays the rest',
    cells: [true, false, 'partial', false, false],
  },
  {
    label: 'Semantic recall (LoCoMo)',
    hint: 'Vendor-published long-conversation recall — a different axis; each number is the vendor’s own',
    cells: [false, false, 'partial', '92.5', '94.7'],
  },
  {
    label: 'Framework-agnostic',
    hint: 'Works outside a single agent framework',
    cells: [true, false, false, true, true],
  },
  {
    label: 'Open source',
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
  // string value like "−38%"
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
