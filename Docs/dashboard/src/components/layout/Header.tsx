import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import styles from './Header.module.css';
import { Home, LayoutDashboard, BookOpen, FileText, Settings, Circle } from '../icons';
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
          <Link to="/" className={styles.logo} aria-label="LearnKit Dashboard home">
            <span className={styles.logoBrace}>{'{ }'}</span>
            <span className={styles.logoName}>LearnKit</span>
            <span className={styles.logoBadge}>Dashboard</span>
          </Link>
        </div>

        {/* Desktop nav */}
        <nav className={styles.nav} aria-label="Main navigation">
          <a href="index.html" className={styles.navLink}>
            <Home size={15} />
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
                <Icon size={15} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right side */}
        <div className={styles.right}>
          {/* Learn / Agent-Learn mode toggle — scopes all run telemetry to one
              learning path. Memory records are shared across both. */}
          <div
            role="group"
            aria-label="Dashboard mode"
            style={{
              display: 'inline-flex',
              borderRadius: 8,
              border: '1px solid var(--border, #30363d)',
              overflow: 'hidden',
            }}
          >
            {([
              { key: 'learn', label: 'Learn', title: 'Model / answer-quality path (@memory.learn). Records & tasks, no tool procedures.' },
              { key: 'agent_learn', label: 'Agent-Learn', title: 'Agent / tool path (@memory.agent_learn). Full view: calls-reduced, procedures, replays.' },
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
                    padding: '5px 12px',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: 'pointer',
                    border: 'none',
                    background: active ? 'var(--accent, #2f81f7)' : 'transparent',
                    color: active ? '#fff' : 'var(--text-muted, #8b949e)',
                    transition: 'background 0.15s, color 0.15s',
                  }}
                >
                  {opt.label}
                </button>
              );
            })}
          </div>
          <div
            className={styles.mockBadge}
            title={
              backendLive
                ? 'Live data — connected to the LearnKit FastAPI backend on /api/v1'
                : 'Mock data mode — backend not reachable; falls back to local cache'
            }
            style={backendLive ? { color: '#3fb950', borderColor: '#3fb950' } : undefined}
          >
            <Circle size={8} className={styles.mockDot} fill="currentColor" />
            <span>{backendLive ? 'Live data' : 'Mock data'}</span>
          </div>
          <div className={styles.avatar} aria-label="User avatar" role="img">
            LK
          </div>
        </div>
      </div>
    </header>
  );
};

