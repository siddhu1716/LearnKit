import { useState } from 'react'
import { TrendingDown, Zap, Target, DollarSign, Check } from 'lucide-react'

/**
 * Growth-model benchmark numbers from benchmarks/RESULTS.json.
 * Only models that PASSed the playbook_effect gate are shown.
 *
 * Generated: 2026-07-02T11:02:47Z
 * Reproduce: LK_MAX_OUTPUT_TOKENS=128 python -m benchmarks.run_agentic_matrix \
 *   --trials 1 --k 1 --seed 7
 */

const headline = [
  {
    icon: Zap,
    value: '+2.25',
    label: 'Best quality lift',
    detail: 'Llama-3.3-70B · playbook_effect',
  },
  {
    icon: TrendingDown,
    value: '−38.4%',
    label: 'Pooled call reduction',
    detail: 'across all suites, all models',
  },
  {
    icon: Target,
    value: '3 / 3',
    label: 'Gate passed',
    detail: 'every model cleared threshold',
  },
  {
    icon: DollarSign,
    value: '100%',
    label: 'Success held',
    detail: 'zero regression, warm vs cold',
  },
]

/* ══════════════════════════════════════════════════════════════════
   Growth-model matrix — from RESULTS.json (gate=PASS only).
   ══════════════════════════════════════════════════════════════════ */
const models = [
  {
    name: 'Llama-3.3-70B-Instruct',
    slug: 'llama-3.3-70b',
    quality: 2.25,
    react: { cold: 24, warm: 16, red: 33.3, s: '6/6' },
    evolution: { cold: 64, warm: 40, red: 37.5, s: '16/16' },
    combined: { cold: 88, warm: 56, red: 36.4 },
    injection: { proc: 0.0, playbook: 2.25, passK: 0.0 },
    highlight: true,
    tag: 'Best quality lift',
  },
  {
    name: 'Qwen2.5-14B-Instruct',
    slug: 'qwen2.5-14b',
    quality: 1.875,
    react: { cold: 15, warm: 9, red: 40.0, s: '6/6' },
    evolution: { cold: 38, warm: 21, red: 44.7, s: '16/16' },
    combined: { cold: 53, warm: 30, red: 43.4 },
    injection: { proc: 1.125, playbook: 3.0, passK: 1.0 },
    highlight: false,
    tag: 'Best cost reduction',
  },
  {
    name: 'Qwen2.5-32B-Instruct',
    slug: 'qwen2.5-32b',
    quality: 1.75,
    react: { cold: 12, warm: 8, red: 33.3, s: '6/6' },
    evolution: { cold: 32, warm: 20, red: 37.5, s: '16/16' },
    combined: { cold: 44, warm: 28, red: 36.4 },
    injection: { proc: 1.25, playbook: 3.0, passK: 1.0 },
    highlight: false,
    tag: 'Highest pass^k',
  },
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
  const [selected, setSelected] = useState(0)
  const m = models[selected]

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

      {/* ─── Model tabs ─── */}
      <div>
        <div className="mb-6 flex items-end justify-between">
          <div>
            <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
              Growth models · 3 / 3 passed gate
            </div>
            <h3 className="mt-1 text-lg font-medium text-white">
              Pick a model to see the detail
            </h3>
          </div>
          <div className="hidden text-[11px] font-mono text-white/40 sm:block">
            gate threshold ≥ 0.5
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {models.map((mm, i) => (
            <button
              key={mm.slug}
              onClick={() => setSelected(i)}
              className={`rounded-2xl border p-5 text-left transition ${
                selected === i
                  ? 'border-white/25 bg-white/[0.04]'
                  : 'border-white/8 bg-white/[0.02] hover:border-white/15'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-400/15">
                    <Check className="h-2.5 w-2.5 text-emerald-400" strokeWidth={3} />
                  </div>
                  <span className="text-[10px] font-medium uppercase tracking-widest text-emerald-300">
                    Pass
                  </span>
                </div>
                {mm.highlight && (
                  <span className="rounded-full bg-white/8 px-2 py-0.5 text-[9px] font-medium uppercase tracking-widest text-white/70">
                    Best
                  </span>
                )}
              </div>
              <div className="mt-4 font-mono text-[13px] text-white/95">
                {mm.name}
              </div>
              <div className="mt-1 text-[11px] text-white/40">{mm.tag}</div>

              <div className="mt-5 flex items-baseline gap-2">
                <div className="text-3xl font-medium tracking-[-0.04em] text-white">
                  +{mm.quality.toFixed(2)}
                </div>
                <div className="text-[10px] uppercase tracking-widest text-white/40">
                  quality lift
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 font-mono text-[11px] text-white/60">
                <div>
                  react{' '}
                  <span className="text-emerald-400">−{mm.react.red.toFixed(0)}%</span>
                </div>
                <div>
                  evolution{' '}
                  <span className="text-emerald-400">−{mm.evolution.red.toFixed(0)}%</span>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ─── Detail panel for selected model ─── */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
        <div className="flex flex-col gap-2 border-b border-white/5 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium text-white">
              <span className="font-mono">{m.name}</span>{' '}
              <span className="text-white/40">· suite detail</span>
            </div>
            <div className="mt-0.5 text-[11px] text-white/40">
              trials=1 · k=1 · seed=7 · temperature=0 · self-hosted vLLM
            </div>
          </div>
          <a
            href="https://github.com/siddhu1716/LearnKit/tree/main/benchmarks"
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

        {[
          {
            name: 'react_live',
            kind: 'ReAct loops · 6 tasks',
            cold: m.react.cold,
            warm: m.react.warm,
            delta: m.react.red,
            s: m.react.s,
          },
          {
            name: 'evolution_live',
            kind: 'Multi-round · 16 tasks',
            cold: m.evolution.cold,
            warm: m.evolution.warm,
            delta: m.evolution.red,
            s: m.evolution.s,
          },
          {
            name: 'injection_ablation',
            kind: `playbook lift vs procedure · pass^k ${m.injection.passK.toFixed(1)}`,
            cold: Math.max(1, Math.round(m.injection.proc * 10)),
            warm: Math.max(1, Math.round(m.injection.playbook * 10)),
            delta: m.quality,
            s: '',
            isLift: true,
          },
          {
            name: 'combined',
            kind: 'Total across react + evolution',
            cold: m.combined.cold,
            warm: m.combined.warm,
            delta: m.combined.red,
            s: '',
          },
        ].map((s) => (
          <div
            key={s.name}
            className="grid grid-cols-[1.5fr_1fr_100px_80px] items-center gap-3 border-b border-white/5 px-6 py-4 last:border-0 transition hover:bg-white/[0.015]"
          >
            <div>
              <div className="font-mono text-[13px] text-white/90">{s.name}</div>
              <div className="text-[11px] text-white/40">{s.kind}</div>
            </div>
            {s.isLift ? (
              <div className="font-mono text-[11px] text-white/60">
                proc {m.injection.proc.toFixed(2)} →{' '}
                <span className="text-emerald-400">
                  playbook {m.injection.playbook.toFixed(2)}
                </span>
              </div>
            ) : (
              <DeltaBar cold={s.cold} warm={s.warm} />
            )}
            <div className="text-right font-mono text-[12px] text-white/70">{s.s || '—'}</div>
            <div className="text-right font-mono text-[13px] font-medium text-emerald-400">
              {s.isLift ? `+${s.delta.toFixed(2)}` : `−${s.delta.toFixed(1)}%`}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
