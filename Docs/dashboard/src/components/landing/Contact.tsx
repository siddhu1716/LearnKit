import { useState } from 'react'
import { Calendar, Mail, Code2, ArrowUpRight, MessageSquare } from 'lucide-react'

const CALENDLY_URL = 'https://calendly.com/shivanampalli/30min'
const CONTACT_EMAIL = 'shivanampalli@gmail.com'
const GITHUB_URL = 'https://github.com/siddhu1716/LearnKit/tree/lia/mvp'

export function Contact() {
  const [copied, setCopied] = useState(false)

  const copyEmail = async () => {
    try {
      await navigator.clipboard.writeText(CONTACT_EMAIL)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* no-op */
    }
  }

  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.03] to-transparent p-8 sm:p-12 lg:p-16">
      {/* Ambient */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_20%_20%,rgba(16,185,129,0.08),transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_100%_100%,rgba(139,92,246,0.06),transparent_60%)]" />

      <div className="relative grid gap-12 lg:grid-cols-[1fr_1fr] lg:items-start">
        {/* Left — pitch */}
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-medium text-white/70">
            <MessageSquare className="h-3 w-3" />
            Talk to us
          </div>

          <h2 className="mt-6 text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
            Let&apos;s see if
            <br />
            <span className="text-white/40">we&apos;re a fit.</span>
          </h2>

          <p className="mt-6 max-w-md text-base leading-relaxed text-white/60">
            30-minute call, no slides. We&apos;ll walk through your agent stack,
            show LearnKit against a task you care about, and share benchmark
            numbers on your model.
          </p>

          <ul className="mt-8 space-y-3">
            {[
              'Live dashboard walkthrough',
              'Bench on your own model',
              'Deploy plan on your infra',
            ].map((item) => (
              <li
                key={item}
                className="flex items-start gap-3 text-sm text-white/60"
              >
                <span className="mt-2 h-px w-4 flex-shrink-0 bg-emerald-400/60" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        {/* Right — action cards */}
        <div className="space-y-3">
          {/* Book demo — primary */}
          <a
            href={CALENDLY_URL}
            target="_blank"
            rel="noreferrer"
            className="group flex items-center justify-between rounded-2xl border border-white/15 bg-white/[0.05] p-5 transition hover:border-white/30 hover:bg-white/[0.08]"
          >
            <div className="flex items-center gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-black">
                <Calendar className="h-5 w-5" strokeWidth={2} />
              </div>
              <div>
                <div className="text-sm font-medium text-white">Book a demo</div>
                <div className="mt-0.5 text-xs text-white/50">
                  30 min · pick any slot on our calendar
                </div>
              </div>
            </div>
            <ArrowUpRight className="h-4 w-4 text-white/50 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" />
          </a>

          {/* Email */}
          <button
            type="button"
            onClick={copyEmail}
            className="group flex w-full items-center justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-5 text-left transition hover:border-white/20 hover:bg-white/[0.04]"
          >
            <div className="flex items-center gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-white/70">
                <Mail className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div>
                <div className="text-sm font-medium text-white">Email us</div>
                <div className="mt-0.5 font-mono text-xs text-white/50">
                  {CONTACT_EMAIL}
                </div>
              </div>
            </div>
            <span
              className={`text-[11px] font-medium transition ${
                copied ? 'text-emerald-400' : 'text-white/40 group-hover:text-white/70'
              }`}
            >
              {copied ? 'copied' : 'copy'}
            </span>
          </button>

          {/* GitHub */}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="group flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.02] p-5 transition hover:border-white/20 hover:bg-white/[0.04]"
          >
            <div className="flex items-center gap-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] text-white/70">
                <Code2 className="h-5 w-5" strokeWidth={1.5} />
              </div>
              <div>
                <div className="text-sm font-medium text-white">
                  Try it yourself
                </div>
                <div className="mt-0.5 font-mono text-xs text-white/50">
                  github.com/siddhu1716/LearnKit
                </div>
              </div>
            </div>
            <ArrowUpRight className="h-4 w-4 text-white/50 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" />
          </a>
        </div>
      </div>
    </div>
  )
}
