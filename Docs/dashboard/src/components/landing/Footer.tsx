export function Footer() {
  const cols = [
    {
      title: 'Product',
      links: [
        { label: 'LearnKit SDK', href: '#learnkit' },
        { label: 'Dashboard', href: '/app.html' },
        { label: 'Benchmarks', href: '#benchmarks' },
        { label: 'Compare', href: '#compare' },
      ],
    },
    {
      title: 'Company',
      links: [
        { label: 'About', href: '#problem' },
        { label: 'Blog', href: '/app.html#/blog' },
        { label: 'Careers', href: '#' },
        { label: 'Contact', href: 'mailto:hello@lialabs.ai' },
      ],
    },
    {
      title: 'Developers',
      links: [
        { label: 'GitHub', href: 'https://github.com/learnkit-ai/learnkit' },
        { label: 'Docs', href: '/docs.html' },
        { label: 'Examples', href: '/docs.html' },
        { label: 'Changelog', href: '#' },
      ],
    },
    {
      title: 'Resources',
      links: [
        { label: 'FAQ', href: '#faq' },
        { label: 'Privacy', href: '#' },
        { label: 'Terms', href: '#' },
        { label: 'Security', href: '#' },
      ],
    },
  ]

  return (
    <footer className="relative border-t border-white/5 bg-[#030303] overflow-hidden">
      {/* Link columns */}
      <div className="mx-auto max-w-6xl px-6 pt-20 pb-8">
        <div className="grid gap-12 md:grid-cols-[2fr_1fr_1fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-md bg-white text-black">
                <span className="text-[11px] font-bold tracking-tight">L</span>
              </div>
              <span className="text-sm font-medium tracking-tight text-white">LIA Labs</span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-white/50">
              Infrastructure for AI agents that compound knowledge over time.
            </p>
            <div className="mt-6 flex items-center gap-2 text-[11px] text-white/40">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              All systems operational
            </div>
          </div>

          {cols.map((col) => (
            <div key={col.title}>
              <h4 className="mb-4 text-xs font-medium uppercase tracking-[0.15em] text-white/40">
                {col.title}
              </h4>
              <ul className="space-y-3">
                {col.links.map((l) => (
                  <li key={l.label}>
                    <a
                      href={l.href}
                      className="text-sm text-white/60 transition hover:text-white"
                    >
                      {l.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex flex-col items-start justify-between gap-4 border-t border-white/5 pt-8 sm:flex-row sm:items-center">
          <p className="text-xs text-white/40">
            © {new Date().getFullYear()} LIA Labs. All rights reserved.
          </p>
          <div className="flex gap-6 text-xs text-white/40">
            <a href="#" className="transition hover:text-white/60">Twitter</a>
            <a href="#" className="transition hover:text-white/60">LinkedIn</a>
            <a href="https://github.com/learnkit-ai/learnkit" className="transition hover:text-white/60">GitHub</a>
          </div>
        </div>
      </div>

      {/* Gradient-fade wordmark — static, transparent bottom fade */}
      <div
        className="pointer-events-none select-none w-full text-center leading-none px-2"
        aria-hidden="true"
      >
        <div
          className="mx-auto font-semibold tracking-[-0.055em]"
          style={{
            fontFamily: "'Geist', 'Inter', sans-serif",
            fontSize: 'clamp(72px, 18vw, 260px)',
            lineHeight: 0.9,
            paddingBottom: '0.05em',
            backgroundImage:
              'linear-gradient(180deg, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0.08) 55%, rgba(255,255,255,0.00) 100%)',
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
            WebkitTextFillColor: 'transparent',
          }}
        >
          LIA&nbsp;LABS
        </div>
      </div>
    </footer>
  )
}
