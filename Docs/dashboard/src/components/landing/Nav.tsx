import { useEffect, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'

export function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'border-b border-white/5 bg-[#050505]/70 backdrop-blur-xl'
          : 'border-b border-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <a href="#" className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-white text-black">
            <span className="text-[11px] font-bold tracking-tight">L</span>
          </div>
          <span className="text-sm font-medium tracking-tight text-white">LIA Labs</span>
        </a>

        <nav className="hidden items-center gap-8 md:flex">
          {[
            { label: 'Product', href: '#dashboard' },
            { label: 'Use cases', href: '#usecases' },
            { label: 'Benchmarks', href: '#benchmarks' },
            { label: 'Compare', href: '#compare' },
            { label: 'FAQ', href: '#faq' },
            { label: 'Docs', href: '/docs.html' },
          ].map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-sm font-medium text-white/60 transition hover:text-white"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <a
            href="/app.html"
            className="hidden text-sm font-medium text-white/60 transition hover:text-white sm:inline"
          >
            Sign in
          </a>
          <a
            href="#contact"
            className="group inline-flex items-center gap-1.5 rounded-full bg-white px-4 py-1.5 text-sm font-medium text-black transition hover:bg-white/90"
          >
            Book a demo
            <ArrowUpRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </a>
        </div>
      </div>
    </header>
  )
}
