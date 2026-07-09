import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styles from './Header.module.css';
import { Home, LayoutDashboard, BookOpen, FileText, Settings } from '../icons';
import { useDashboardMode } from '../../context/DashboardModeContext';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, sidebarOpen }) => {
  const location = useLocation();
  const [backendLive, setBackendLive] = useState<boolean | null>(null);
  const { mode, setMode } = useDashboardMode();

  useEffect(() => {
    let cancelled = false;
    const probe = async () => {
      try {
        const res = await fetch('/healthz', { cache: 'no-store' });
        if (!cancelled) setBackendLive(res.ok);
      } catch {
        if (!cancelled) setBackendLive(false);
      }
    };
    probe();
    const id = setInterval(probe, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const navLinks = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/blog', label: 'Blog', icon: BookOpen, end: false },
    { to: '/docs', label: 'Docs', icon: FileText, end: false },
    { to: '/settings', label: 'Settings', icon: Settings, end: false },
  ];

  const isActive = (to: string, end: boolean) =>
    end ? location.pathname === to : location.pathname.startsWith(to);

  return (
    <header className={styles.header} role="banner">
      <div className={styles.inner}>
        {/* Logo + sidebar toggle */}
        <div className={styles.left}>
          <button
            className={styles.hamburger}
            onClick={onToggleSidebar}
            aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            aria-expanded={sidebarOpen}
          >
            <span className={styles.hamburgerLine} />
            <span className={styles.hamburgerLine} />
            <span className={styles.hamburgerLine} />
          </button>
          <Link to="/" className={styles.logo} aria-label="LIA Labs Dashboard home">
            <span className={styles.logoMark}>L</span>
            <span className={styles.logoName}>LIA Labs</span>
            <span className={styles.logoBadge}>dashboard</span>
          </Link>
        </div>

        {/* Desktop nav */}
        <nav className={styles.nav} aria-label="Main navigation">
          <a href="index.html" className={styles.navLink}>
            <Home size={14} />
            <span>Home</span>
          </a>
          {navLinks.map((link) => {
            const Icon = link.icon;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`${styles.navLink} ${
                  isActive(link.to, link.end) ? styles.active : ''
                }`}
              >
                <Icon size={14} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className={styles.right}>
          {/* Learn / Agent-Learn mode toggle */}
          <div
            role="group"
            aria-label="Dashboard mode"
            style={{
              display: 'inline-flex',
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--surface-accent)',
              overflow: 'hidden',
              padding: 2,
              gap: 2,
            }}
          >
            {([
              { key: 'agent_learn', label: 'Agent-Learn', title: 'Agent / tool path (@memory.agent_learn). Full view: calls-reduced, procedures, replays. This is the primary path.' },
              { key: 'learn', label: 'Learn · beta', title: 'Model / answer-quality path (@memory.learn) — under development. Records & tasks, no tool procedures.' },
            ] as const).map((opt) => {
              const active = mode === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => setMode(opt.key)}
                  title={opt.title}
                  aria-pressed={active}
                  style={{
                    padding: '3px 10px',
                    fontSize: 11,
                    fontWeight: 500,
                    letterSpacing: '0.01em',
                    cursor: 'pointer',
                    border: 'none',
                    borderRadius: 4,
                    background: active ? 'rgba(255,255,255,0.08)' : 'transparent',
                    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                    transition: 'background 0.15s, color 0.15s',
                  }}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>

          <div
            className={styles.statusPill}
            title={
              backendLive
                ? 'Live data — connected to the LearnKit FastAPI backend on /api/v1'
                : 'Mock data mode — backend not reachable; falls back to local cache'
            }
          >
            <span
              className={`${styles.statusDot} ${
                backendLive === null
                  ? ''
                  : backendLive
                  ? styles.statusDotLive
                  : styles.statusDotDown
              }`}
            />
            <span>{backendLive ? 'Live' : 'Mock'}</span>
          </div>

          <div className={styles.avatar} aria-label="User avatar" role="img">
            LK
          </div>
        </div>
      </div>
    </header>
  );
};

