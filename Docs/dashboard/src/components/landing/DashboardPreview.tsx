import { useState } from 'react'
import {
  Activity,
  Database,
  GitBranch,
  Home,
  Layers,
  LineChart,
  Search,
  Settings,
  Sparkles,
  Gauge,
  Bot,
  Wrench,
} from 'lucide-react'

type TabKey =
  | 'overview'
  | 'memory'
  | 'traces'
  | 'benchmarks'
  | 'agents'
  | 'playground'

export function DashboardPreview() {
  const [tab, setTab] = useState<TabKey>('overview')

  const monitorItems = [
    { icon: Home, label: 'Overview', key: 'overview' as TabKey },
    { icon: Database, label: 'Memory', key: 'memory' as TabKey },
    { icon: Activity, label: 'Traces', key: 'traces' as TabKey },
    { icon: Bot, label: 'Agents', key: 'agents' as TabKey },
    { icon: Gauge, label: 'Benchmarks', key: 'benchmarks' as TabKey },
    { icon: Sparkles, label: 'Playground', key: 'playground' as TabKey },
  ]

  const insightItems = [
    { icon: LineChart, label: 'Retrieval quality' },
    { icon: GitBranch, label: 'Evolution' },
    { icon: Layers, label: 'Skills' },
    { icon: Wrench, label: 'Failure analysis' },
    { icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0a0a0a] shadow-[0_40px_120px_-30px_rgba(0,0,0,0.9)]">
      {/* macOS titlebar */}
      <div className="flex items-center gap-2 border-b border-white/5 bg-[#0d0d0d] px-4 py-3">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
          <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
        </div>
        <div className="ml-4 hidden flex-1 items-center justify-center sm:flex">
          <div className="flex items-center gap-2 rounded-md border border-white/5 bg-white/[0.02] px-3 py-1 text-xs text-white/40">
            <Search className="h-3 w-3" />
            <span>app.lialabs.ai/dashboard</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-[220px_1fr]">
        {/* Sidebar */}
        <aside className="hidden border-r border-white/5 bg-[#080808] p-4 sm:block">
          <div className="mb-6 flex items-center gap-2 px-2">
            <div className="flex h-5 w-5 items-center justify-center rounded bg-white text-black">
              <span className="text-[9px] font-bold">L</span>
            </div>
            <span className="text-xs font-medium text-white">LIA Labs</span>
            <span className="ml-auto rounded-md border border-white/10 px-1.5 py-0.5 font-mono text-[9px] text-white/40">
              dashboard
            </span>
          </div>

          <div className="mb-2 px-2 text-[10px] font-medium uppercase tracking-widest text-white/30">
            Monitor
          </div>
          <nav className="space-y-0.5">
            {monitorItems.map((item) => {
              const Icon = item.icon
              const active = tab === item.key
              return (
                <button
                  key={item.label}
                  onClick={() => setTab(item.key)}
                  className={`relative flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-xs transition ${
                    active
                      ? 'bg-white/[0.06] text-white'
                      : 'text-white/50 hover:bg-white/[0.03] hover:text-white/80'
                  }`}
                >
                  {active && (
                    <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-white" />
                  )}
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              )
            })}
          </nav>

          <div className="mb-2 mt-6 px-2 text-[10px] font-medium uppercase tracking-widest text-white/30">
            Insights
          </div>
          <nav className="space-y-0.5">
            {insightItems.map((item) => {
              const Icon = item.icon
              return (
                <button
                  key={item.label}
                  className="flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left text-xs text-white/50 transition hover:bg-white/[0.03] hover:text-white/80"
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </button>
              )
            })}
          </nav>
        </aside>

        {/* Main content */}
        <div className="min-h-[560px] bg-[#0a0a0a]">
          {tab === 'overview' && <OverviewTab />}
          {tab === 'memory' && <MemoryTab />}
          {tab === 'traces' && <TracesTab />}
          {tab === 'benchmarks' && <BenchmarksTab />}
          {tab === 'agents' && <AgentsTab />}
          {tab === 'playground' && <PlaygroundTab />}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════ OVERVIEW ══════════════════════════════════ */
function OverviewTab() {
  const metrics = [
    { label: 'Success rate', value: '98.7%', delta: '+1.2%', good: true },
    { label: 'p95 latency', value: '245ms', delta: '−12ms', good: true },
    { label: 'Memories', value: '2,453', delta: '+184', good: true },
    { label: 'Cost / task', value: '$0.021', delta: '−34%', good: true },
  ]

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            Production · last 7 days
          </div>
          <h3 className="mt-1 text-xl font-medium text-white">Agent overview</h3>
        </div>
        <div className="hidden items-center gap-2 rounded-md border border-white/10 bg-white/[0.02] px-2.5 py-1 text-[11px] text-white/60 sm:flex">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Live
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {metrics.map((m) => (
          <div key={m.label} className="rounded-lg border border-white/5 bg-white/[0.02] p-4">
            <div className="text-[11px] uppercase tracking-wider text-white/40">{m.label}</div>
            <div className="mt-2 flex items-baseline gap-2">
              <div className="text-xl font-medium text-white">{m.value}</div>
              <div className={`text-[11px] ${m.good ? 'text-emerald-400' : 'text-orange-400'}`}>
                {m.delta}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg border border-white/5 bg-white/[0.02] p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-white">Task success rate</div>
            <div className="text-[11px] text-white/40">Rolling 24h · with vs without LearnKit</div>
          </div>
          <div className="flex gap-1 rounded-md border border-white/10 bg-white/[0.02] p-0.5 text-[10px]">
            {['24h', '7d', '30d'].map((t, i) => (
              <button
                key={t}
                className={`rounded px-2 py-1 transition ${
                  i === 1 ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <LineSparkline />
      </div>
    </div>
  )
}

function LineSparkline() {
  const withLK = [62, 68, 71, 74, 78, 81, 83, 86, 88, 90, 92, 93, 95, 96, 97, 98, 98, 99]
  const without = [62, 63, 62, 64, 63, 65, 64, 66, 65, 67, 66, 68, 67, 69, 68, 70, 69, 71]

  const width = 640
  const height = 160
  const pad = 12

  const toPath = (data: number[]) => {
    const step = (width - pad * 2) / (data.length - 1)
    return data
      .map((v, i) => {
        const x = pad + i * step
        const y = pad + (height - pad * 2) * (1 - (v - 55) / (100 - 55))
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
      })
      .join(' ')
  }

  const areaWith = `${toPath(withLK)} L ${width - pad} ${height - pad} L ${pad} ${height - pad} Z`

  return (
    <div className="w-full">
      <div className="mb-3 flex items-center gap-5 text-[11px]">
        <span className="flex items-center gap-2 text-white/70">
          <span className="h-1.5 w-3 rounded-full bg-emerald-400" />
          With LearnKit
        </span>
        <span className="flex items-center gap-2 text-white/40">
          <span className="h-1.5 w-3 rounded-full bg-white/25" />
          Baseline
        </span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="h-40 w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={pad}
            x2={width - pad}
            y1={pad + (height - pad * 2) * f}
            y2={pad + (height - pad * 2) * f}
            stroke="rgba(255,255,255,0.04)"
          />
        ))}
        <path d={areaWith} fill="url(#areaGrad)" />
        <path d={toPath(without)} stroke="rgba(255,255,255,0.25)" strokeWidth="1.5" fill="none" strokeDasharray="4 3" />
        <path d={toPath(withLK)} stroke="#10b981" strokeWidth="2" fill="none" />
      </svg>
    </div>
  )
}

/* ═══════════════════════════════════════════ MEMORY ═══════════════════════════════════ */
function MemoryTab() {
  const rows = [
    { kind: 'skill', title: 'Retry with exponential backoff on 429', conf: 0.94, uses: 42 },
    { kind: 'skill', title: 'Cache tool responses within a task', conf: 0.91, uses: 38 },
    { kind: 'failure', title: 'Do not call `write_file` before validation', conf: 0.88, uses: 14 },
    { kind: 'skill', title: 'Chunk large payloads at natural boundaries', conf: 0.86, uses: 27 },
    { kind: 'failure', title: 'Timeout scales with input size, not fixed', conf: 0.82, uses: 9 },
    { kind: 'skill', title: 'Prefer structured output when schema is known', conf: 0.79, uses: 22 },
    { kind: 'fact', title: 'API v2 rate limit is 60 req/min per key', conf: 0.97, uses: 51 },
  ]

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            Distilled records
          </div>
          <h3 className="mt-1 text-xl font-medium text-white">Memory explorer</h3>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px]">
          <span className="rounded-md border border-white/10 bg-white/[0.02] px-2 py-1 text-white/60">All · 2,453</span>
          <span className="rounded-md border border-emerald-400/20 bg-emerald-400/[0.06] px-2 py-1 text-emerald-300">Skills · 1,842</span>
          <span className="rounded-md border border-orange-400/20 bg-orange-400/[0.06] px-2 py-1 text-orange-300">Failures · 611</span>
          <span className="rounded-md border border-violet-400/20 bg-violet-400/[0.06] px-2 py-1 text-violet-300">Facts · 294</span>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-white/5">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02] text-left text-[10px] uppercase tracking-widest text-white/40">
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Record</th>
              <th className="hidden px-4 py-2 font-medium sm:table-cell">Confidence</th>
              <th className="px-4 py-2 text-right font-medium">Uses</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-white/5 last:border-0 transition hover:bg-white/[0.02]">
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      r.kind === 'skill'
                        ? 'bg-emerald-400/10 text-emerald-300'
                        : r.kind === 'failure'
                        ? 'bg-orange-400/10 text-orange-300'
                        : 'bg-violet-400/10 text-violet-300'
                    }`}
                  >
                    {r.kind}
                  </span>
                </td>
                <td className="px-4 py-3 text-[13px] text-white/85">{r.title}</td>
                <td className="hidden px-4 py-3 sm:table-cell">
                  <div className="flex items-center gap-2">
                    <div className="h-1 w-20 overflow-hidden rounded-full bg-white/5">
                      <div className="h-full rounded-full bg-emerald-400" style={{ width: `${r.conf * 100}%` }} />
                    </div>
                    <span className="font-mono text-[11px] text-white/50">{r.conf.toFixed(2)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-[12px] text-white/60">{r.uses}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════ TRACES ═══════════════════════════════════ */
function TracesTab() {
  const steps = [
    { name: 'classify', dur: 84, kind: 'model' },
    { name: 'retrieve', dur: 42, kind: 'memory' },
    { name: 'compose', dur: 12, kind: 'internal' },
    { name: 'agent.plan', dur: 320, kind: 'model' },
    { name: 'tool.web_search', dur: 480, kind: 'tool' },
    { name: 'agent.synthesize', dur: 240, kind: 'model' },
    { name: 'distill', dur: 62, kind: 'memory' },
  ]
  const max = Math.max(...steps.map((s) => s.dur))
  const kindColor: Record<string, string> = {
    model: 'bg-violet-400/70',
    tool: 'bg-orange-400/70',
    memory: 'bg-emerald-400/70',
    internal: 'bg-white/40',
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            Task #4521 · 1.24s · success
          </div>
          <h3 className="mt-1 text-xl font-medium text-white">
            Trace: &ldquo;Draft a launch email for Q3&rdquo;
          </h3>
        </div>
        <div className="hidden md:flex items-center gap-4 text-[11px] text-white/50">
          {Object.entries(kindColor).map(([k, c]) => (
            <span key={k} className="flex items-center gap-1.5">
              <span className={`h-2 w-2 rounded-sm ${c}`} />
              {k}
            </span>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-white/5 bg-white/[0.01] p-6">
        <div className="space-y-2.5">
          {steps.map((s, i) => (
            <div key={i} className="grid grid-cols-[140px_1fr_60px] items-center gap-3 text-[12px]">
              <div className="truncate font-mono text-white/70">{s.name}</div>
              <div className="relative h-5 rounded-sm bg-white/5">
                <div
                  className={`h-full rounded-sm ${kindColor[s.kind]} transition-all`}
                  style={{ width: `${(s.dur / max) * 100}%` }}
                />
              </div>
              <div className="text-right font-mono text-white/50">{s.dur}ms</div>
            </div>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-4 border-t border-white/5 pt-4 text-[11px] text-white/50">
          <span>2 retrieved memories applied</span>
          <span className="h-1 w-1 rounded-full bg-white/20" />
          <span>1 skill reinforced</span>
          <span className="h-1 w-1 rounded-full bg-white/20" />
          <span>0 failures</span>
          <span className="ml-auto rounded-md border border-emerald-400/20 bg-emerald-400/[0.06] px-2 py-0.5 font-mono text-[10px] text-emerald-300">
            −38% vs cold
          </span>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════ BENCHMARKS ═══════════════════════════════ */
function BenchmarksTab() {
  const suites = [
    { name: 'react_live', cold: 14, warm: 9, delta: '−36%' },
    { name: 'evolution_live', cold: 39, warm: 21, delta: '−46%' },
    { name: 'synthesis (PBE)', cold: 18, warm: 12, delta: '−33%' },
    { name: 'synthesis (SLR)', cold: 12, warm: 8, delta: '−33%' },
  ]

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            Reproducible · Qwen2.5-14B · trials=3
          </div>
          <h3 className="mt-1 text-xl font-medium text-white">Benchmarks</h3>
        </div>
        <div className="rounded-md border border-emerald-400/20 bg-emerald-400/[0.06] px-2.5 py-1 text-[11px] font-medium text-emerald-300">
          Gate PASS · +1.88
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: 'Playbook effect', value: '+1.88', hint: 'novel siblings' },
          { label: 'Success held', value: '100%', hint: 'no regression' },
          { label: 'Avg cost cut', value: '−37%', hint: 'across suites' },
        ].map((k) => (
          <div key={k.label} className="rounded-lg border border-white/5 bg-white/[0.02] p-4">
            <div className="text-[10px] uppercase tracking-widest text-white/40">{k.label}</div>
            <div className="mt-2 text-2xl font-medium text-white">{k.value}</div>
            <div className="mt-1 text-[10px] text-white/40">{k.hint}</div>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-6">
        <div className="mb-4 text-[11px] font-medium uppercase tracking-widest text-white/40">
          LLM calls · cold → warm
        </div>
        <div className="space-y-3">
          {suites.map((s) => {
            const warmPct = (s.warm / s.cold) * 100
            return (
              <div key={s.name} className="grid grid-cols-[160px_1fr_50px] items-center gap-4">
                <div className="font-mono text-[12px] text-white/80">{s.name}</div>
                <div className="flex items-center gap-3">
                  <span className="w-6 text-right font-mono text-[11px] text-white/40">{s.cold}</span>
                  <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-white/5">
                    <div className="absolute inset-y-0 left-0 rounded-full bg-emerald-400/70" style={{ width: `${warmPct}%` }} />
                  </div>
                  <span className="w-6 font-mono text-[11px] text-emerald-400">{s.warm}</span>
                </div>
                <div className="text-right font-mono text-[12px] font-medium text-emerald-400">{s.delta}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════ AGENTS ═══════════════════════════════════ */
function AgentsTab() {
  const agents = [
    { name: 'coder-agent', status: 'active', tasks: 1247, success: 98.4, memories: 842 },
    { name: 'legal-analyst', status: 'active', tasks: 634, success: 96.1, memories: 512 },
    { name: 'research-assistant', status: 'idle', tasks: 289, success: 94.7, memories: 271 },
    { name: 'support-triage', status: 'active', tasks: 3120, success: 99.2, memories: 828 },
  ]

  return (
    <div className="p-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            4 active · 2 idle
          </div>
          <h3 className="mt-1 text-xl font-medium text-white">Registered agents</h3>
        </div>
        <button className="rounded-md border border-white/15 bg-white/[0.02] px-3 py-1.5 text-[11px] font-medium text-white/80 transition hover:border-white/25 hover:text-white">
          + New agent
        </button>
      </div>

      <div className="space-y-3">
        {agents.map((a) => (
          <div
            key={a.name}
            className="grid grid-cols-[1.6fr_0.8fr_1fr_1fr_1fr] items-center gap-4 rounded-lg border border-white/5 bg-white/[0.02] px-5 py-4 transition hover:border-white/12"
          >
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-md border border-white/10 bg-white/[0.03] flex items-center justify-center">
                <Bot className="h-4 w-4 text-white/50" />
              </div>
              <div>
                <div className="font-mono text-[13px] text-white/90">{a.name}</div>
                <div className="text-[10px] text-white/40">@lk.agent_learn</div>
              </div>
            </div>

            <div>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  a.status === 'active'
                    ? 'bg-emerald-400/10 text-emerald-300'
                    : 'bg-white/[0.05] text-white/50'
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    a.status === 'active' ? 'bg-emerald-400 animate-pulse' : 'bg-white/40'
                  }`}
                />
                {a.status}
              </span>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-white/40">tasks</div>
              <div className="mt-0.5 font-mono text-[13px] text-white/90">{a.tasks.toLocaleString()}</div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-white/40">success</div>
              <div className="mt-0.5 font-mono text-[13px] text-emerald-400">{a.success}%</div>
            </div>

            <div>
              <div className="text-[10px] uppercase tracking-widest text-white/40">memories</div>
              <div className="mt-0.5 font-mono text-[13px] text-white/90">{a.memories}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════ PLAYGROUND ═══════════════════════════════ */
function PlaygroundTab() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
          Live inspection · coding · warmed
        </div>
        <h3 className="mt-1 text-xl font-medium text-white">Playground</h3>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left — input */}
        <div className="rounded-lg border border-white/5 bg-white/[0.02] p-5">
          <div className="mb-3 text-[10px] font-medium uppercase tracking-widest text-white/40">
            Task input
          </div>
          <div className="rounded-md border border-white/8 bg-black/40 p-3 font-mono text-[12px] leading-relaxed text-white/80">
            Write a Python function that reads a large CSV file
            in chunks and returns rows matching a regex predicate.
          </div>
          <div className="mt-4 flex items-center gap-3">
            <button className="rounded-md bg-white px-3 py-1.5 text-[11px] font-medium text-black transition hover:bg-white/90">
              Inspect
            </button>
            <span className="text-[11px] text-white/40">domain: coding</span>
          </div>
        </div>

        {/* Right — output */}
        <div className="rounded-lg border border-white/5 bg-white/[0.02] p-5">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-[10px] font-medium uppercase tracking-widest text-white/40">
              Retrieved memories
            </div>
            <span className="font-mono text-[10px] text-emerald-400">3 hits · 42ms</span>
          </div>

          <div className="space-y-2">
            {[
              { kind: 'skill', title: 'Read CSV in chunks with pandas', score: 0.92 },
              { kind: 'skill', title: 'Compile regex once, reuse per row', score: 0.88 },
              { kind: 'failure', title: 'Avoid `csv.reader` on files > 500MB', score: 0.81 },
            ].map((r, i) => (
              <div
                key={i}
                className="flex items-center gap-3 rounded-md border border-white/5 bg-white/[0.02] px-3 py-2"
              >
                <span
                  className={`rounded-full px-1.5 py-0.5 text-[9px] font-medium ${
                    r.kind === 'skill'
                      ? 'bg-emerald-400/10 text-emerald-300'
                      : 'bg-orange-400/10 text-orange-300'
                  }`}
                >
                  {r.kind}
                </span>
                <span className="flex-1 text-[12px] text-white/80">{r.title}</span>
                <span className="font-mono text-[10px] text-white/50">{r.score.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
