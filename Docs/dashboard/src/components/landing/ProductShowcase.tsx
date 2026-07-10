import { useEffect, useRef, useState } from 'react'

/**
 * BentoLabs-style feature showcase.
 * LEFT: numbered feature list that highlights the active item.
 * RIGHT: sticky image panel that changes as you scroll through the list.
 *
 * Falls back to a stacked layout on mobile.
 */

interface Feature {
  num: string
  title: string
  body: string
  image: string
  alt: string
}

const features: Feature[] = [
  {
    num: '01',
    title: 'Memory Explorer',
    body:
      'Every skill, failure, and fact your agents have distilled — with confidence, task overlap, and generality scores. Promote what works, quarantine what breaks.',
    image: '/screenshots/Lia-Memory-Explorer.png',
    alt: 'LIA Memory Explorer showing distilled skills with confidence scores',
  },
  {
    num: '02',
    title: 'Task History',
    body:
      'Every production run — the input, the tools called, the score, the latency, and which memories were applied. Searchable, filterable, replayable.',
    image: '/screenshots/Lia-Task-History.png',
    alt: 'LIA Task History showing production runs with outcomes and scores',
  },
  {
    num: '03',
    title: 'Learning Curve',
    body:
      'Watch tool calls drop and skills accumulate as memory reuse compounds. Prove to your team that every deploy is measurably smarter than the last.',
    image: '/screenshots/Lia-Agents-2.png',
    alt: 'LIA Agents learning curve showing calls reduced and skills learned per run',
  },
  {
    num: '04',
    title: 'Observability',
    body:
      'LLM tokens, latency, and cost — for every run, every agent, every path. OpenTelemetry-native spans that plug into your existing infra.',
    image: '/screenshots/Lia-Observability.png',
    alt: 'LIA Observability with token usage, latency percentiles, and per-model breakdown',
  },
  {
    num: '05',
    title: 'Agent overview',
    body:
      'Real-time dashboard for the agent path: procedures, replays, injection trends, and calls reduced — the closed loop, at a glance.',
    image: '/screenshots/Lia-Dashboard.png',
    alt: 'LIA Agent-Learn overview with memory stats, task metrics, and injection trends',
  },
]

export function ProductShowcase() {
  const [active, setActive] = useState(0)
  const itemRefs = useRef<Array<HTMLDivElement | null>>([])

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        // Find the entry closest to the top of the viewport that is intersecting
        let bestIdx = -1
        let bestTop = Infinity
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const idx = itemRefs.current.findIndex((r) => r === entry.target)
            const top = entry.boundingClientRect.top
            if (idx >= 0 && top >= -200 && top < bestTop) {
              bestTop = top
              bestIdx = idx
            }
          }
        })
        if (bestIdx >= 0) setActive(bestIdx)
      },
      { rootMargin: '-30% 0px -50% 0px', threshold: 0 }
    )

    itemRefs.current.forEach((r) => r && observer.observe(r))
    return () => observer.disconnect()
  }, [])

  return (
    <div className="grid gap-12 lg:grid-cols-[1fr_1.15fr] lg:gap-16">
      {/* LEFT — feature list */}
      <div className="space-y-4 lg:space-y-2">
        {features.map((f, i) => {
          const isActive = i === active
          return (
            <div
              key={f.num}
              ref={(el) => {
                itemRefs.current[i] = el
              }}
              onClick={() => setActive(i)}
              className={`group cursor-pointer rounded-2xl border p-6 transition-all duration-500 ${
                isActive
                  ? 'border-white/15 bg-white/[0.03]'
                  : 'border-white/5 bg-transparent hover:border-white/10 hover:bg-white/[0.01]'
              }`}
            >
              <div className="flex items-start gap-5">
                <div
                  className={`font-mono text-xs transition-colors ${
                    isActive ? 'text-emerald-400' : 'text-white/30'
                  }`}
                >
                  {f.num}
                </div>
                <div className="flex-1">
                  <h3
                    className={`text-xl font-medium tracking-tight transition-colors sm:text-2xl ${
                      isActive ? 'text-white' : 'text-white/70'
                    }`}
                  >
                    {f.title}
                  </h3>
                  <p
                    className={`mt-2 text-sm leading-relaxed transition-all duration-500 ${
                      isActive
                        ? 'text-white/60 max-h-40 opacity-100'
                        : 'text-white/40 max-h-0 opacity-0 lg:opacity-100 lg:max-h-none overflow-hidden'
                    }`}
                  >
                    {f.body}
                  </p>

                  {/* Mobile image inline */}
                  <div className="mt-4 overflow-hidden rounded-lg border border-white/10 lg:hidden">
                    <img
                      src={f.image}
                      alt={f.alt}
                      className="w-full"
                      loading="lazy"
                    />
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* RIGHT — sticky image panel (desktop only) */}
      <div className="relative hidden lg:block">
        <div className="sticky top-24">
          <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#0a0a0a] shadow-[0_40px_120px_-30px_rgba(0,0,0,0.9)]">
            {/* Ambient glow */}
            <div className="pointer-events-none absolute -inset-8 -z-10 rounded-3xl bg-gradient-to-tr from-emerald-500/10 via-transparent to-violet-500/10 blur-2xl" />

            {features.map((f, i) => (
              <img
                key={f.num}
                src={f.image}
                alt={f.alt}
                loading={i === 0 ? 'eager' : 'lazy'}
                className={`w-full transition-all duration-500 ${
                  i === active
                    ? 'opacity-100 relative'
                    : 'opacity-0 absolute inset-0 pointer-events-none'
                }`}
              />
            ))}
          </div>

          {/* Small caption */}
          <div className="mt-4 flex items-center justify-between px-1">
            <div className="font-mono text-[11px] text-white/40">
              {features[active].num} / {String(features.length).padStart(2, '0')}
            </div>
            <div className="text-[11px] font-medium text-white/60">
              {features[active].title}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
