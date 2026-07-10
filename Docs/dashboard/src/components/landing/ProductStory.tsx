'use client'
import { useRef } from 'react'
import { useScroll, useTransform } from 'framer-motion'
import { GoogleGeminiEffect } from '../ui/google-gemini-effect'

/**
 * ProductStory — scroll-driven section explaining the LIA Labs value.
 *
 * Five converging paths, each representing a type of learning that flows
 * into a single self-improving agent. Uses the GoogleGeminiEffect.
 */
export function ProductStory() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start start', 'end start'],
  })

  const pathLengthFirst = useTransform(scrollYProgress, [0, 0.8], [0.2, 1.2])
  const pathLengthSecond = useTransform(scrollYProgress, [0, 0.8], [0.15, 1.2])
  const pathLengthThird = useTransform(scrollYProgress, [0, 0.8], [0.1, 1.2])
  const pathLengthFourth = useTransform(scrollYProgress, [0, 0.8], [0.05, 1.2])
  const pathLengthFifth = useTransform(scrollYProgress, [0, 0.8], [0, 1.2])

  const memoryTypes = [
    { name: 'skills', color: 'bg-emerald-400' },
    { name: 'facts', color: 'bg-emerald-300' },
    { name: 'procedures', color: 'bg-white' },
    { name: 'preferences', color: 'bg-violet-400' },
    { name: 'failures', color: 'bg-orange-400' },
  ]

  return (
    <div
      ref={ref}
      className="relative h-[220vh] w-full overflow-clip rounded-none bg-transparent pt-24"
    >
      {/* Left-edge memory-type labels — visible while sticky content is in view */}
      <div className="pointer-events-none sticky top-[42%] hidden -translate-y-1/2 lg:block">
        <div className="mx-auto max-w-[1440px] px-8">
          <div className="flex flex-col gap-6 font-mono text-[11px] uppercase tracking-widest text-white/40">
            {memoryTypes.map((m) => (
              <div key={m.name} className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 rounded-full ${m.color}`} />
                <span>{m.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <GoogleGeminiEffect
        title="One powerful agent."
        description="Every skill, failure, and fact — distilled from every task, compounded into a single self-improving agent."
        pathLengths={[
          pathLengthFirst,
          pathLengthSecond,
          pathLengthThird,
          pathLengthFourth,
          pathLengthFifth,
        ]}
      />
    </div>
  )
}
