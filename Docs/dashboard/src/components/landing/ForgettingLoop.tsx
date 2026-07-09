import { useEffect, useState, useRef } from 'react'

/**
 * ForgettingLoop — animated SVG showing an agent that forgets
 * between sessions. Perfect for the "problem" section.
 *
 * Sessions appear one-by-one, run through the agent, then vanish —
 * emphasizing that no knowledge carries over.
 */
export function ForgettingLoop() {
  const [step, setStep] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setStep((s) => (s + 1) % 4)
    }, 1400)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const sessions = [
    { id: 'S1', label: 'session 1' },
    { id: 'S2', label: 'session 2' },
    { id: 'S3', label: 'session 3' },
    { id: 'S4', label: 'session 4' },
  ]

  return (
    <div className="relative w-full aspect-square max-w-[520px] mx-auto">
      <div className="absolute inset-0 rounded-2xl border border-white/8 bg-gradient-to-br from-white/[0.02] to-transparent overflow-hidden">
        {/* grid backdrop */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />

        {/* central agent */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="relative flex h-24 w-24 items-center justify-center rounded-2xl border border-white/15 bg-[#0d0d0d]">
            <span className="text-[10px] font-mono uppercase tracking-widest text-white/50">
              agent
            </span>
            {/* Pulse ring */}
            <span className="absolute inset-0 rounded-2xl border border-emerald-400/30 animate-ping opacity-40" />
          </div>
        </div>

        {/* Sessions arriving and being forgotten */}
        {sessions.map((s, i) => {
          const active = i === step
          const past = i < step
          return (
            <div
              key={s.id}
              className="absolute left-6 flex items-center gap-2 transition-all duration-700 ease-out"
              style={{
                top: `${20 + i * 22}%`,
                opacity: active ? 1 : past ? 0 : 0.35,
                transform: active
                  ? 'translateX(0)'
                  : past
                  ? 'translateX(90px) scale(0.9)'
                  : 'translateX(-8px)',
              }}
            >
              <div
                className={`h-6 w-6 rounded-md border flex items-center justify-center font-mono text-[9px] font-medium transition-colors ${
                  active
                    ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-300'
                    : 'border-white/10 bg-white/[0.02] text-white/40'
                }`}
              >
                {s.id}
              </div>
              <span
                className={`text-[11px] transition-colors ${
                  active ? 'text-white/80' : 'text-white/30'
                }`}
              >
                {s.label}
              </span>
            </div>
          )
        })}

        {/* Forgotten label (right side) */}
        <div className="absolute right-6 top-1/2 -translate-y-1/2 flex flex-col items-end gap-2">
          <div className="text-[10px] font-mono uppercase tracking-widest text-white/40">
            memory
          </div>
          <div className="rounded-md border border-red-400/25 bg-red-400/[0.06] px-2.5 py-1 text-[10px] font-medium text-red-300">
            ⌀ lost
          </div>
          <div className="mt-2 text-[10px] text-white/30 max-w-[110px] text-right leading-relaxed">
            Every session starts from zero.
          </div>
        </div>

        {/* Bottom stat bar */}
        <div className="absolute inset-x-6 bottom-6 flex items-center justify-between rounded-lg border border-white/8 bg-black/40 px-4 py-2 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-red-400 animate-pulse" />
            <span className="text-[11px] font-mono text-white/60">
              retention: 0%
            </span>
          </div>
          <span className="text-[10px] font-mono text-white/40">
            {step + 1}/{sessions.length} sessions
          </span>
        </div>
      </div>
    </div>
  )
}
