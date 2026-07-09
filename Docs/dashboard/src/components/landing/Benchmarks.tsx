import { useState } from 'react'
import { TrendingDown, Zap, Target, DollarSign, Check, X } from 'lucide-react'

/**
 * Real benchmark numbers from:
 *   Docs/FINAL_BENCHMARK_NUMBERS_2026-06-21.txt
 *   benchmarks/BENCHMARK_SUMMARY.md
 *   FINAL_MODEL_MATRIX_2026-06-21.txt
 */

const headline = [
  {
    icon: TrendingDown,
    value: '−46%',
    label: 'LLM calls reduced',
    detail: 'evolution_live · Qwen2.5-14B',
  },
  {
    icon: Target,
    value: '100%',
    label: 'Success held',
    detail: 'no regression when warm',
  },
  {
    icon: Zap,
    value: '+1.88',
    label: 'Playbook lift',
    detail: 'novel siblings · Qwen2.5-14B',
  },
  {
    icon: DollarSign,
    value: '−33%',
    label: 'Cost per task',
    detail: 'agentic PBE + SLR · 32B models',
  },
]

/* ═══════════════════════════════════════════════════════════
   Model matrix — every model we've published against.
   ═══════════════════════════════════════════════════════════ */
const models = [
  {
    name: 'Qwen2.5-14B-Instruct',
    endpoint: ':8002',
    gate: true,
    playbookEffect: 1.875,
    passK: 1.0,
    reactCold: 14,
    reactWarm: 9,
    evolCold: 39,
    evolWarm: 21,
    reactSuccess: '6/6',
    evolSuccess: '16/16',
    highlight: true,
  },
  {
    name: 'Qwen2.5-32B-Instruct',
    endpoint: ':8001',
    gate: true,
    playbookEffect: 1.75,
    passK: 1.0,
    reactCold: 12,
    reactWarm: 8,
    evolCold: 32,
    evolWarm: 20,
    reactSuccess: '6/6',
    evolSuccess: '16/16',
    highlight: false,
  },
  {
    name: 'Qwen2.5-Coder-32B',
    endpoint: 'PBE / SLR',
    gate: true,
    playbookEffect: 1.75,
    passK: 1.0,
    reactCold: 18,
    reactWarm: 12,
    evolCold: 12,
    evolWarm: 8,
    reactSuccess: '9/9',
    evolSuccess: '6/6',
    highlight: false,
  },
  {
    name: 'Qwen2.5-7B-Instruct',
    endpoint: ':8000',
    gate: true,
    playbookEffect: 2.625,
    passK: 1.0,
    reactCold: 21,
    reactWarm: 8,
    evolCold: 58,
    evolWarm: 20,
    reactSuccess: '6/6',
    evolSuccess: '16/16',
    highlight: false,
  },
  {
    name: 'Hermes-3-Llama-3.1-8B',
    endpoint: ':8000',
    gate: false,
    playbookEffect: 0.0,
    passK: 0.0,
    reactCold: 6,
    reactWarm: 6,
    evolCold: 16,
    evolWarm: 16,
    reactSuccess: '0/6',
    evolSuccess: '0/16',
    highlight: false,
  },
]

/* ═══════════════════════════════════════════════════════════
   Suite data (Qwen2.5-14B, our best performer)
   ═══════════════════════════════════════════════════════════ */
const suite = [
  { name: 'react_live', kind: 'ReAct loops · 6 tasks', cold: 14, warm: 9, delta: -36, s: '6/6' },
  { name: 'evolution_live', kind: 'Multi-round · 16 tasks', cold: 39, warm: 21, delta: -46, s: '16/16' },
  { name: 'synthesis_agentic (PBE)', kind: 'Program-by-example', cold: 18, warm: 12, delta: -33, s: '9/9' },
  { name: 'synthesis_agentic (SLR)', kind: 'Symbolic learning', cold: 12, warm: 8, delta: -33, s: '6/6' },
  { name: 'injection_ablation', kind: 'Novel sibling tasks', cold: 24, warm: 8, delta: -67, s: '8/8' },
]

function DeltaBar({ cold, warm }: { cold: number; warm: number }) {
  const warmPct = (warm / cold) * 100
  return (
    <div className="flex items-center gap-2 font-mono text-[11px]">
      <span className="w-8 text-right text-white/40">{cold}</span>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-emerald-400/70"
          style={{ width: `${warmPct}%` }}
        />
      </div>
      <span className="w-8 text-emerald-400">{warm}</span>
    </div>
  )
}

export function Benchmarks() {
  const [selectedModel, setSelectedModel] = useState(0)

  return (
    <div className="space-y-14">
      {/* ─── Headline stat cards ─── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {headline.map((h) => {
          const Icon = h.icon
          return (
            <div
              key={h.label}
              className="group rounded-2xl border border-white/10 bg-white/[0.02] p-6 transition hover:border-white/20 hover:bg-white/[0.03]"
            >
              <Icon
                className="h-4 w-4 text-white/40 transition group-hover:text-emerald-400"
                strokeWidth={1.5}
              />
              <div className="mt-6 text-4xl font-medium tracking-[-0.04em] text-white sm:text-5xl">
                {h.value}
              </div>
              <div className="mt-2 text-sm font-medium text-white/80">{h.label}</div>
              <div className="mt-1 text-[11px] text-white/40">{h.detail}</div>
            </div>
          )
        })}
      </div>

      {/* ─── Model matrix ─── */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
        <div className="flex flex-col gap-2 border-b border-white/5 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium text-white">Model matrix</div>
            <div className="mt-0.5 text-[11px] text-white/40">
              Every model we've benchmarked · self-hosted vLLM · trials=3 · seed=7
            </div>
          </div>
          <div className="text-[11px] font-mono text-white/40">commit 150889f</div>
        </div>

        <div className="hidden md:grid grid-cols-[2fr_0.9fr_0.9fr_0.9fr_1fr_1fr] items-center gap-3 border-b border-white/5 bg-white/[0.02] px-6 py-2 text-[10px] font-medium uppercase tracking-widest text-white/40">
          <div>Model</div>
          <div className="text-center">Gate</div>
          <div className="text-right">Playbook</div>
          <div className="text-right">pass^k</div>
          <div className="text-right">react (cold→warm)</div>
          <div className="text-right">evolution (cold→warm)</div>
        </div>

        {models.map((m, i) => (
          <button
            key={m.name}
            onClick={() => setSelectedModel(i)}
            className={`w-full grid grid-cols-1 md:grid-cols-[2fr_0.9fr_0.9fr_0.9fr_1fr_1fr] items-center gap-3 border-b border-white/5 px-6 py-4 text-left last:border-0 transition ${
              selectedModel === i
                ? 'bg-white/[0.025]'
                : 'hover:bg-white/[0.015]'
            }`}
          >
            <div className="flex items-center gap-3">
              {m.highlight && (
                <span className="hidden sm:inline-block rounded-full bg-emerald-400/10 border border-emerald-400/25 px-2 py-0.5 text-[9px] font-medium uppercase tracking-widest text-emerald-300">
                  Best
                </span>
              )}
              <div>
                <div className="font-mono text-[13px] text-white/90">{m.name}</div>
                <div className="text-[10px] text-white/40">{m.endpoint}</div>
              </div>
            </div>

            <div className="flex items-center justify-center">
              {m.gate ? (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-400/15">
                  <Check className="h-3 w-3 text-emerald-400" strokeWidth={3} />
                </div>
              ) : (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-red-400/10">
                  <X className="h-3 w-3 text-red-400" strokeWidth={2.5} />
                </div>
              )}
            </div>

            <div
              className={`text-right font-mono text-[12px] font-medium ${
                m.playbookEffect >= 0.5 ? 'text-emerald-400' : 'text-white/30'
              }`}
            >
              {m.playbookEffect > 0 ? `+${m.playbookEffect.toFixed(2)}` : '0.00'}
            </div>

            <div className="text-right font-mono text-[12px] text-white/70">
              {m.passK.toFixed(1)}
            </div>

            <div className="text-right font-mono text-[12px] text-white/70">
              {m.reactCold} → <span className="text-emerald-400">{m.reactWarm}</span>
            </div>

            <div className="text-right font-mono text-[12px] text-white/70">
              {m.evolCold} → <span className="text-emerald-400">{m.evolWarm}</span>
            </div>
          </button>
        ))}
      </div>

      {/* ─── Suite detail (for best model) ─── */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
        <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
          <div>
            <div className="text-sm font-medium text-white">Suite detail</div>
            <div className="mt-0.5 text-[11px] text-white/40">
              <span className="font-mono">{models[selectedModel].name}</span>{' '}
              · click a model above to switch
            </div>
          </div>
          <a
            href="https://github.com/learnkit-ai/learnkit/tree/main/benchmarks"
            target="_blank"
            rel="noreferrer"
            className="text-[11px] font-medium text-white/50 transition hover:text-white"
          >
            Reproduce →
          </a>
        </div>

        <div className="grid grid-cols-[1.5fr_1fr_100px_80px] items-center gap-3 border-b border-white/5 bg-white/[0.02] px-6 py-2 text-[10px] font-medium uppercase tracking-widest text-white/40">
          <div>Suite</div>
          <div>LLM calls (cold → warm)</div>
          <div className="text-right">Success</div>
          <div className="text-right">Δ</div>
        </div>

        {suite.map((s) => (
          <div
            key={s.name}
            className="grid grid-cols-[1.5fr_1fr_100px_80px] items-center gap-3 border-b border-white/5 px-6 py-4 last:border-0 transition hover:bg-white/[0.015]"
          >
            <div>
              <div className="font-mono text-[13px] text-white/90">{s.name}</div>
              <div className="text-[11px] text-white/40">{s.kind}</div>
            </div>
            <DeltaBar cold={s.cold} warm={s.warm} />
            <div className="text-right font-mono text-[12px] text-white/70">
              {s.s} → {s.s}
            </div>
            <div className="text-right font-mono text-[13px] font-medium text-emerald-400">
              {s.delta}%
            </div>
          </div>
        ))}
      </div>

      {/* ─── Historical / additional suites ─── */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            PBEBench-Lite
          </div>
          <div className="mt-2 text-sm font-medium text-white">
            Programming by Example
          </div>
          <div className="mt-4 space-y-2 font-mono text-[11px] text-white/60">
            <div className="flex justify-between">
              <span>control</span>
              <span>95.0%</span>
            </div>
            <div className="flex justify-between">
              <span>cold_start</span>
              <span className="text-emerald-400">100.0%</span>
            </div>
            <div className="flex justify-between">
              <span>warmed_start</span>
              <span className="text-emerald-400">100.0%</span>
            </div>
          </div>
          <div className="mt-4 text-[10px] text-white/30">
            Qwen2.5-Coder-32B · H100 · 20 tasks/arm
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
          <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
            SLR-Bench
          </div>
          <div className="mt-2 text-sm font-medium text-white">Symbolic learning</div>
          <div className="mt-4 space-y-2 font-mono text-[11px] text-white/60">
            <div className="flex justify-between">
              <span>control</span>
              <span>100.0%</span>
            </div>
            <div className="flex justify-between">
              <span>cold_start</span>
              <span>100.0%</span>
            </div>
            <div className="flex justify-between">
              <span>warmed_start</span>
              <span className="text-emerald-400">100.0%</span>
            </div>
          </div>
          <div className="mt-4 text-[10px] text-white/30">
            At model ceiling · reproducible baseline
          </div>
        </div>
      </div>
    </div>
  )
}
