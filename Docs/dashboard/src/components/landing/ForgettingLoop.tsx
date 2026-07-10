import { useEffect, useRef, useState } from 'react'

/**
 * ForgettingLoop — a visceral animation of an agent that forgets.
 *
 * Sessions arrive on the left, get processed by a central "agent",
 * emit colored memory tokens (skills/failures/facts), which then
 * drift toward a "retain?" gate — but the gate always drops them
 * into a "void" that empties every cycle. The counter tries to
 * accumulate but keeps resetting to 0.
 */

type TokenKind = 'skill' | 'failure' | 'fact'

interface Token {
  id: number
  kind: TokenKind
  /** progress 0 → 1 along its flight path */
  t: number
  /** vertical offset applied to the flight arc */
  offset: number
  /** unique random speed multiplier */
  speed: number
}

const KIND_COLOR: Record<TokenKind, string> = {
  skill: 'bg-emerald-400',
  failure: 'bg-orange-400',
  fact: 'bg-violet-400',
}
const KIND_TEXT: Record<TokenKind, string> = {
  skill: 'text-emerald-300',
  failure: 'text-orange-300',
  fact: 'text-violet-300',
}

export function ForgettingLoop() {
  const [tokens, setTokens] = useState<Token[]>([])
  const [session, setSession] = useState(1)
  const [pulseKey, setPulseKey] = useState(0)
  const [retention, setRetention] = useState(0)
  const nextIdRef = useRef(1)
  const rafRef = useRef<number | null>(null)
  const lastEmitRef = useRef(performance.now())
  const lastFlushRef = useRef(performance.now())
  const lastFrameRef = useRef(performance.now())
  const retentionRef = useRef(0)

  useEffect(() => {
    const step = (now: number) => {
      const dt = (now - lastFrameRef.current) / 1000
      lastFrameRef.current = now

      // Emit a new token every ~380ms
      if (now - lastEmitRef.current > 380) {
        lastEmitRef.current = now
        const kinds: TokenKind[] = ['skill', 'failure', 'fact', 'skill']
        const kind = kinds[Math.floor(Math.random() * kinds.length)]
        nextIdRef.current += 1
        setTokens((prev) => {
          // Cap active tokens to keep DOM light
          const next = prev.length > 30 ? prev.slice(-30) : prev
          return [
            ...next,
            {
              id: nextIdRef.current,
              kind,
              t: 0,
              offset: (Math.random() - 0.5) * 30,
              speed: 0.55 + Math.random() * 0.35,
            },
          ]
        })
        // Retention creeps up as tokens are "generated"
        retentionRef.current = Math.min(1, retentionRef.current + 0.08)
        setRetention(retentionRef.current)
      }

      // Every 3.2s, "flush" — reset retention, advance session, pulse
      if (now - lastFlushRef.current > 3200) {
        lastFlushRef.current = now
        retentionRef.current = 0
        setRetention(0)
        setSession((s) => s + 1)
        setPulseKey((k) => k + 1)
      }

      // Advance token progress
      setTokens((prev) =>
        prev
          .map((tok) => ({ ...tok, t: tok.t + dt * tok.speed }))
          .filter((tok) => tok.t < 1.15)
      )

      rafRef.current = requestAnimationFrame(step)
    }

    rafRef.current = requestAnimationFrame(step)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [])

  return (
    <div className="relative w-full aspect-[4/5] max-w-[520px] mx-auto">
      <div className="absolute inset-0 overflow-hidden rounded-2xl border border-white/8 bg-gradient-to-br from-white/[0.02] to-transparent">
        {/* Grid backdrop */}
        <div
          className="absolute inset-0 opacity-25"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />

        {/* Legend row */}
        <div className="absolute inset-x-0 top-0 flex items-center justify-between border-b border-white/5 bg-black/30 px-4 py-2.5 backdrop-blur-sm">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-white/50">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            live · no memory
          </div>
          <div className="flex items-center gap-3 text-[10px] text-white/40">
            <Legend color="bg-emerald-400" label="skill" />
            <Legend color="bg-orange-400" label="failure" />
            <Legend color="bg-violet-400" label="fact" />
          </div>
        </div>

        {/* ─── Main stage ─── */}
        <div className="absolute inset-x-0 top-11 bottom-16 flex items-center">
          <div className="relative w-full h-full">
            {/* Incoming session queue (left) */}
            <div className="absolute left-4 top-1/2 -translate-y-1/2 flex flex-col gap-1.5">
              <div className="mb-1 text-[10px] font-mono uppercase tracking-widest text-white/30">
                incoming
              </div>
              {[0, 1, 2].map((i) => {
                const sid = session + i
                return (
                  <div
                    key={i}
                    className="flex items-center gap-2 transition-all duration-300"
                    style={{ opacity: 1 - i * 0.35 }}
                  >
                    <div className="flex h-5 w-5 items-center justify-center rounded border border-white/10 bg-white/[0.02] font-mono text-[9px] text-white/60">
                      s
                    </div>
                    <span className="font-mono text-[10px] text-white/40">
                      #{String(sid).padStart(3, '0')}
                    </span>
                  </div>
                )
              })}
            </div>

            {/* Agent core (center) */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="relative">
                <div
                  key={pulseKey}
                  className="absolute inset-0 rounded-2xl border border-emerald-400/40 animate-[ping_1.4s_ease-out_forwards]"
                />
                <div className="relative flex h-24 w-24 flex-col items-center justify-center rounded-2xl border border-white/15 bg-[#0c0c0c]">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-white/40">
                    agent
                  </span>
                  <span className="mt-1 font-mono text-[11px] font-medium text-white/85">
                    #{String(session).padStart(3, '0')}
                  </span>
                </div>
              </div>
            </div>

            {/* Void / drain (right) */}
            <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col items-end gap-2">
              <div className="text-[10px] font-mono uppercase tracking-widest text-white/30">
                retain?
              </div>
              <div className="relative flex h-16 w-14 flex-col items-center justify-center rounded-lg border border-dashed border-red-400/40 bg-red-400/[0.05]">
                <span className="text-[10px] font-medium text-red-300/80">⌀</span>
                <span className="mt-0.5 font-mono text-[9px] text-red-300/60">
                  void
                </span>
                {/* animated drain lines */}
                <div className="pointer-events-none absolute inset-x-2 bottom-0 flex flex-col gap-0.5 overflow-hidden">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="h-px bg-red-400/25"
                      style={{ animation: `flDrain 1.2s ${i * 0.2}s linear infinite` }}
                    />
                  ))}
                </div>
              </div>
              <div className="text-[10px] text-white/30 max-w-[100px] text-right leading-snug">
                Discarded every session.
              </div>
            </div>

            {/* Flying tokens — from agent center toward the void */}
            {tokens.map((tok) => (
              <FlyingToken key={tok.id} token={tok} />
            ))}
          </div>
        </div>

        {/* Bottom retention bar */}
        <div className="absolute inset-x-4 bottom-4 rounded-lg border border-white/8 bg-black/40 px-4 py-2.5 backdrop-blur-sm">
          <div className="flex items-center justify-between text-[10px] font-mono">
            <span className="uppercase tracking-widest text-white/40">
              retention
            </span>
            <span className={retention > 0 ? KIND_TEXT.failure : 'text-white/40'}>
              accumulating…
            </span>
          </div>
          <div className="relative mt-2 h-1.5 overflow-hidden rounded-full bg-white/5">
            <div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-emerald-400/70 via-orange-400/70 to-red-400/70 transition-[width] duration-300 ease-out"
              style={{ width: `${retention * 100}%` }}
            />
            {/* Reset flash */}
            <div
              key={pulseKey}
              className="absolute inset-0 bg-red-400/40 animate-[flFlash_0.7s_ease-out_forwards]"
            />
          </div>
          <div className="mt-2 flex items-center justify-between text-[10px] text-white/40">
            <span className="font-mono">session #{String(session).padStart(3, '0')}</span>
            <span className="font-mono text-red-300/70">→ 0% after flush</span>
          </div>
        </div>

        {/* Keyframes */}
        <style>{`
          @keyframes flDrain {
            0%   { transform: translateY(-6px); opacity: 0; }
            30%  { opacity: 1; }
            100% { transform: translateY(6px); opacity: 0; }
          }
          @keyframes flFlash {
            0%   { opacity: 1; }
            100% { opacity: 0; }
          }
        `}</style>
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      <span className="text-white/45">{label}</span>
    </span>
  )
}

/* ═════════════════════════════════════════════════════════════
   Token that flies from the agent center to the "void" (right).
   Uses percentages so it scales with the container.
   ═════════════════════════════════════════════════════════════ */
function FlyingToken({ token }: { token: Token }) {
  const t = token.t
  const clamped = Math.max(0, Math.min(1, t))
  // x: 50% → 90%
  const x = 50 + 40 * clamped
  // y: 50% + arc offset
  const arc = Math.sin(clamped * Math.PI) * 12 // gentle arc
  const y = 50 + token.offset * 0.02 + arc * (token.offset > 0 ? -1 : 1)

  // Fade out toward the end
  let opacity: number
  if (t < 0.7) opacity = 1
  else opacity = Math.max(0, 1 - (t - 0.7) / 0.4)

  // Scale down slightly as it approaches void
  const scale = 1 - clamped * 0.4

  return (
    <div
      className="pointer-events-none absolute"
      style={{
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%, -50%) scale(${scale.toFixed(3)})`,
        opacity,
        transition: 'none',
      }}
    >
      <div className="flex items-center gap-1 rounded-full border border-white/10 bg-black/60 px-1.5 py-0.5 backdrop-blur-sm">
        <span className={`h-1.5 w-1.5 rounded-full ${KIND_COLOR[token.kind]}`} />
        <span className="font-mono text-[9px] text-white/70">{token.kind}</span>
      </div>
    </div>
  )
}
