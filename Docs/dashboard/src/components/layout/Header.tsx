import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import styles from './Header.module.css';

interface HeaderProps {
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onToggleSidebar, sidebarOpen }) => {
  const location = useLocation();

  const navLinks = [
    { to: '/', label: 'Dashboard' },
    { to: '/settings', label: 'Settings' },
  ];

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
            Home
          </a>
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`${styles.navLink} ${
                location.pathname === link.to ? styles.active : ''
              }`}
            >
              {link.label}
            </Link>
          ))}
          <a
            href="docs.html"
            target="_blank"
            rel="noopener"
            className={styles.navLink}
          >
            Docs
          </a>
        </nav>

        {/* Right side */}
        <div className={styles.right}>
          <div className={styles.mockBadge} title="Mock data mode — production API endpoints pending">
            <span className={styles.mockDot} />
            <span>Mock data</span>
          </div>
          <div className={styles.avatar} aria-label="User avatar" role="img">
            LK
          </div>
        </div>
      </div>
    </header>
  );
};
