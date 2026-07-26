import { useEffect, useState } from 'react'
import VaporizeTextCycle, { Tag } from '../../components/ui/vapour-text-effect'
import { DashboardPreview } from '../../components/landing/DashboardPreview'
import { Benchmarks } from '../../components/landing/Benchmarks'
import { CompetitorTable } from '../../components/landing/CompetitorTable'
import { FAQ } from '../../components/landing/FAQ'
import { ForgettingLoop } from '../../components/landing/ForgettingLoop'
import { ProductShowcase } from '../../components/landing/ProductShowcase'
import { ProductStory } from '../../components/landing/ProductStory'
import { UseCases } from '../../components/landing/UseCases'
import { Contact } from '../../components/landing/Contact'
import { Nav } from '../../components/landing/Nav'
import { Footer } from '../../components/landing/Footer'
import { ArrowRight, ArrowUpRight, Calendar } from 'lucide-react'

export function LandingPage() {
  const [heroReady, setHeroReady] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setHeroReady(true), 200)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="min-h-screen bg-[#050505] text-white antialiased selection:bg-white/20">
      <Nav />

      {/* ══════════════════════════════════════════════════════════════
          HERO
          ══════════════════════════════════════════════════════════════ */}
      <section className="relative min-h-[100vh] w-full overflow-hidden pt-24 pb-16">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_0%,rgba(16,185,129,0.10),transparent_60%)]" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_100%,rgba(139,92,246,0.06),transparent_60%)]" />
          <div
            className="absolute inset-0 opacity-40"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
              backgroundSize: '48px 48px',
              maskImage:
                'radial-gradient(ellipse 70% 70% at 50% 50%, black 20%, transparent 90%)',
              WebkitMaskImage:
                'radial-gradient(ellipse 70% 70% at 50% 50%, black 20%, transparent 90%)',
            }}
          />
        </div>

        <div className="relative z-10 mx-auto flex min-h-[calc(100vh-96px)] max-w-6xl flex-col items-center justify-center px-6 text-center">
          <div
            className={`transition-all duration-1000 ease-[cubic-bezier(0.16,1,0.3,1)] ${
              heroReady ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
            }`}
          >
            {/* Vapour "Introducing" — big and single word */}
            <div className="mx-auto mb-6 h-[68px] w-[420px] sm:h-[80px] sm:w-[560px] md:h-[92px] md:w-[680px]">
              <VaporizeTextCycle
                texts={['Introducing']}
                font={{
                  fontFamily: "'Geist', 'Inter', sans-serif",
                  fontSize: '64px',
                  fontWeight: 400,
                }}
                color="rgb(200, 200, 200)"
                spread={4}
                density={6}
                animation={{ vaporizeDuration: 1.6, fadeInDuration: 1.0, waitDuration: 3.0 }}
                direction="left-to-right"
                alignment="center"
                tag={Tag.P}
              />
            </div>

            {/* Static LIA Labs */}
            <h1 className="text-6xl font-semibold tracking-[-0.055em] text-white sm:text-7xl md:text-8xl lg:text-[128px] lg:leading-[0.9]">
              LIA Labs
            </h1>

            <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-white/70 sm:text-xl">
              The learning layer for
              <span className="text-white"> tool-using AI agents.</span>
              <br className="hidden sm:block" />
              Capture the winning tool procedure once — replay it on repeats with zero planning calls.
            </p>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/45">
              Procedural memory for agents — workflow induction, not a vector store. −38% planning calls at equal task success.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <a
                href="#contact"
                className="group inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-medium text-black transition hover:bg-white/90"
              >
                <Calendar className="h-4 w-4" />
                Book a demo
              </a>
              <a
                href="/app.html"
                className="group inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.02] px-5 py-2.5 text-sm font-medium text-white/90 transition hover:border-white/25 hover:bg-white/[0.05]"
              >
                Open the dashboard
                <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </a>
            </div>

            <div className="mt-14 inline-flex items-center gap-2 rounded-full border border-white/8 bg-white/[0.02] px-3 py-1 text-xs font-medium text-white/50">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              LearnKit v1.0 · Apache-2.0 · +2.25 quality lift on Llama-3.3-70B
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          PRODUCT STORY — scroll-driven Gemini effect
          Explains the whole product: multiple learning streams converge
          into a single self-improving agent.
          ══════════════════════════════════════════════════════════════ */}
      <ProductStory />

      {/* ══════════════════════════════════════════════════════════════
          TRUST STRIP
          ══════════════════════════════════════════════════════════════ */}
      <section className="border-y border-white/5 bg-black/40 py-10">
        <div className="mx-auto max-w-6xl px-6">
          <p className="mb-6 text-center text-xs font-medium uppercase tracking-[0.2em] text-white/40">
            Works with any agent stack
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-4 text-white/30">
            {['OPENAI', 'ANTHROPIC', 'DSPY', 'LANGCHAIN', 'LLAMAINDEX', 'MISTRAL', 'MODAL', 'VLLM'].map((n) => (
              <span key={n} className="text-sm font-medium tracking-widest transition hover:text-white/60">
                {n}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          01 — PROBLEM
          ══════════════════════════════════════════════════════════════ */}
      <section id="problem" className="relative py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="01" label="The problem" />

          <div className="mt-10 grid gap-12 lg:grid-cols-[1.1fr_1fr] lg:items-center">
            <div>
              <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.1]">
                Every release starts
                <br />
                <span className="text-white/40">from zero.</span>
              </h2>

              <p className="mt-6 max-w-md text-base leading-relaxed text-white/60 sm:text-lg">
                Your agent solved this problem last week. It won&apos;t remember
                today. Learnings don&apos;t compound — and neither does your AI
                investment.
              </p>

              <ul className="mt-8 space-y-3 max-w-md">
                {[
                  'Repeated tool calls waste tokens',
                  'The same failures recur weekly',
                  'Reliability plateaus after week two',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm text-white/55">
                    <span className="mt-2 h-px w-4 flex-shrink-0 bg-white/25" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <ForgettingLoop />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          02 — SOLUTION — Distill / Retrieve / Improve
          ══════════════════════════════════════════════════════════════ */}
      <section id="platform" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="02" label="The solution" />

          <div className="mt-10 mb-10 max-w-2xl">
            <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.1]">
              A closed-loop memory layer.
              <br />
              <span className="text-white/40">Learn once. Reuse forever.</span>
            </h2>
          </div>

          <div className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/5 sm:grid-cols-3">
            {[
              {
                num: '01',
                title: 'Distill',
                body: 'Convert raw agent trajectories into structured, retrievable knowledge with confidence scoring and provenance.',
              },
              {
                num: '02',
                title: 'Retrieve',
                body: 'Bounded hybrid retrieval combines task classification, search, and procedural playbooks without flooding the prompt.',
              },
              {
                num: '03',
                title: 'Improve',
                body: 'Outcome attribution shows which procedures help, which hurt, and which should be reinforced or retired.',
              },
            ].map((p) => (
              <div key={p.num} className="group relative bg-[#0a0a0a] p-10 transition hover:bg-[#0f0f0f]">
                <div className="mb-6 font-mono text-xs text-white/30">{p.num}</div>
                <h3 className="mb-3 text-xl font-medium tracking-tight text-white">{p.title}</h3>
                <p className="text-sm leading-relaxed text-white/50">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          03 — PRODUCT SHOWCASE (BENTO-STYLE with screenshots)
          ══════════════════════════════════════════════════════════════ */}
      <section id="dashboard" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="03" label="The product" />

          <div className="mt-10 mb-14 max-w-3xl">
            <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
              Improve your agents with
              <br />
              <span className="text-white/40">every production run.</span>
            </h2>
            <p className="mt-6 text-base leading-relaxed text-white/60 sm:text-lg">
              One dashboard for the entire feedback loop — from raw trace to
              distilled skill to deployed improvement. Click each feature to
              explore.
            </p>
          </div>

          <ProductShowcase />

          {/* Live interactive preview underneath */}
          <div className="mt-24">
            <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-widest text-white/40">
                  Or try it interactively
                </div>
                <h3 className="mt-1 text-2xl font-medium tracking-[-0.02em] text-white">
                  Live dashboard preview
                </h3>
              </div>
              <a
                href="/app.html"
                className="group inline-flex items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white/90 transition hover:border-white/30"
              >
                Open the real thing
                <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </a>
            </div>

            <div className="relative">
              <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-tr from-emerald-500/5 via-transparent to-violet-500/5 blur-2xl" />
              <DashboardPreview />
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          04 — USE CASES
          ══════════════════════════════════════════════════════════════ */}
      <section id="usecases" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="04" label="Where it fits" />

          <div className="mt-10 mb-14 flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div className="max-w-2xl">
              <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
                Built for teams
                <br />
                <span className="text-white/40">running agents in production.</span>
              </h2>
              <p className="mt-6 text-base leading-relaxed text-white/60 sm:text-lg">
                If your agent takes tool actions and the same tasks recur, LearnKit
                compounds. Here are the shapes we&apos;ve seen it win.
              </p>
            </div>
          </div>

          <UseCases />
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          05 — BENCHMARKS
          ══════════════════════════════════════════════════════════════ */}
      <section id="benchmarks" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="05" label="Benchmarks" />

          <div className="mt-10 mb-14 max-w-3xl">
            <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
              Three models. Three passes.
              <br />
              <span className="text-white/40">Equal success. Fewer planning calls.</span>
            </h2>
            <p className="mt-6 text-base leading-relaxed text-white/60 sm:text-lg">
              Every number below is generated by <span className="font-mono text-white/80">python -m benchmarks.make_results</span> from committed suite JSONs.
              Run it against your own agent and compare on identical infrastructure.
            </p>
          </div>

          <Benchmarks />

          <div className="mt-10 rounded-2xl border border-white/5 bg-white/[0.02] p-6 text-sm text-white/60">
            <span className="font-mono text-xs text-white/40">$ </span>
            <span className="font-mono text-xs text-white/70">
              python -m benchmarks.make_results --check
            </span>
            <span className="ml-3 text-xs text-white/40">
              → verifies this matrix from committed raw runs
            </span>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          06 — COMPARE
          ══════════════════════════════════════════════════════════════ */}
      <section id="compare" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="06" label="How we compare" />

          <div className="mt-10 mb-14 max-w-3xl">
            <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
              Not another
              <br />
              <span className="text-white/40">vector store.</span>
            </h2>
            <p className="mt-6 text-base leading-relaxed text-white/60 sm:text-lg">
              Most &ldquo;memory&rdquo; tools store conversation. LearnKit distills
              tool trajectories into reusable procedures.
            </p>
          </div>

          <CompetitorTable />

          <p className="mt-6 text-center text-xs text-white/40">
            Comparison as of 2026-07. Reflects publicly documented capabilities.
          </p>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          07 — LEARNKIT (open source)
          ══════════════════════════════════════════════════════════════ */}
      <section id="learnkit" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="07" label="The open-source engine" />

          <div className="mt-14 grid gap-16 lg:grid-cols-[1.1fr_1fr] lg:items-center">
            <div>
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs font-medium text-white/70">
                <span className="text-emerald-400">●</span> Apache-2.0 · self-hostable
              </div>
              <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl">
                LearnKit
              </h2>
              <p className="mt-6 text-base leading-relaxed text-white/60 sm:text-lg">
                The experience-distillation SDK powering LIA Labs. A thin,
                framework-agnostic layer that gives any agent a memory that
                improves with use.
              </p>

              <ul className="mt-8 space-y-4">
                {[
                  { title: 'Framework agnostic', body: 'Works with DSPy, LangChain, LlamaIndex, or plain Python.' },
                  { title: 'Local by default', body: 'SQLite is included; a pluggable backend contract supports deployment-specific stores.' },
                  { title: 'Auditable memory', body: 'Every retrieved record includes provenance, confidence, and evolution history.' },
                ].map((f) => (
                  <li key={f.title} className="flex gap-4">
                    <div className="mt-2 h-px w-6 flex-shrink-0 bg-white/20" />
                    <div>
                      <div className="text-sm font-medium text-white">{f.title}</div>
                      <div className="mt-1 text-sm text-white/50">{f.body}</div>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="mt-8 flex flex-wrap gap-3">
                <a
                  href="https://github.com/siddhu1716/LearnKit"
                  target="_blank"
                  rel="noreferrer"
                  className="group inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-medium text-black transition hover:bg-white/90"
                >
                  View on GitHub
                  <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </a>
                <a
                  href="/docs.html"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-2.5 text-sm font-medium text-white/80 transition hover:border-white/30 hover:text-white"
                >
                  Read the docs
                </a>
              </div>
            </div>

            <div className="relative">
              <div className="absolute -inset-8 -z-10 rounded-3xl bg-gradient-to-tr from-emerald-500/10 via-transparent to-violet-500/10 blur-2xl" />
              <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#0a0a0a] shadow-2xl">
                <div className="flex items-center gap-2 border-b border-white/5 bg-white/[0.02] px-4 py-3">
                  <div className="flex gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                    <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                    <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                  </div>
                  <span className="ml-2 font-mono text-xs text-white/40">agent.py</span>
                </div>
                <pre className="overflow-x-auto p-6 font-mono text-[13px] leading-[1.7] text-white/80">
{`import learnkit as lk

memory = lk.LearnKit(
  agent_id="support-agent",
  memory_backend="sqlite",
)

`}<span className="text-white/40">{`# Your existing planner and tools stay unchanged.`}</span>{`
result = lk.run_react_agent(
  memory, user_query, tools, planner
)`}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          08 — FAQ
          ══════════════════════════════════════════════════════════════ */}
      <section id="faq" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="08" label="Frequently asked" />

          <div className="mt-10 mb-14 max-w-2xl">
            <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl md:leading-[1.05]">
              Questions,
              <br />
              <span className="text-white/40">answered.</span>
            </h2>
          </div>

          <FAQ />
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          09 — CONTACT / BOOK A DEMO
          ══════════════════════════════════════════════════════════════ */}
      <section id="contact" className="border-t border-white/5 py-28 sm:py-36">
        <div className="mx-auto max-w-6xl px-6">
          <SectionEyebrow number="09" label="Get in touch" />

          <div className="mt-10">
            <Contact />
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          FINAL CTA
          ══════════════════════════════════════════════════════════════ */}
      <section className="relative border-t border-white/5 py-28 sm:py-36">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_100%,rgba(16,185,129,0.12),transparent_70%)]" />
        <div className="relative mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-3xl font-medium tracking-[-0.03em] text-white sm:text-4xl md:text-5xl">
            Ship agents that get
            <br />
            <span className="italic font-light text-white/50">cheaper with proven reuse.</span>
          </h2>
          <p className="mx-auto mt-6 max-w-lg text-base leading-relaxed text-white/60 sm:text-lg">
            Fifteen-minute install. Fully self-hostable. No infrastructure.
            No vendor lock-in.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a
              href="#contact"
              className="group inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-medium text-black transition hover:bg-white/90"
            >
              <Calendar className="h-4 w-4" />
              Book a demo
            </a>
            <a
              href="/app.html"
              className="group inline-flex items-center gap-2 rounded-full border border-white/15 px-6 py-3 text-sm font-medium text-white/90 transition hover:border-white/30"
            >
              Open dashboard
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </a>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function SectionEyebrow({ number, label }: { number: string; label: string }) {
  return (
    <div className="flex items-center gap-3 text-xs font-medium uppercase tracking-[0.2em] text-white/40">
      <span className="h-px w-8 bg-white/20" />
      {number} — {label}
    </div>
  )
}
