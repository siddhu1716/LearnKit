import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import styles from './Sidebar.module.css';

interface SidebarProps {
  open: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({ open }) => {
  const location = useLocation();
  const [explorerOpen, setExplorerOpen] = useState(true);

  const isActive = (path: string, queryParam?: string) => {
    if (queryParam) {
      const searchParams = new URLSearchParams(location.search);
      return location.pathname === path && searchParams.get('type') === queryParam;
    }
    return location.pathname === path && !location.search;
  };

  const isExplorerActive = location.pathname === '/memory';

  const memoryTypes = [
    { type: 'skill', label: 'Skills', icon: '⚡' },
    { type: 'failure', label: 'Failures', icon: '❌' },
    { type: 'fact', label: 'Facts', icon: '📚' },
    { type: 'strategy', label: 'Strategies', icon: '🧩' },
    { type: 'preference', label: 'Preferences', icon: '⚙️' },
    { type: 'heuristic', label: 'Heuristics', icon: '💡' },
    { type: 'trace', label: 'Traces', icon: '⏱️' },
  ];

  return (
    <aside className={`${styles.sidebar} ${open ? styles.open : styles.collapsed}`} aria-label="Sidebar navigation">
      <nav className={styles.nav}>
        <ul className={styles.navList}>
          {/* Dashboard Home */}
          <li>
            <NavLink
              to="/"
              className={({ isActive: linkActive }) => 
                `${styles.navItem} ${linkActive && !location.pathname.startsWith('/memory') && !location.pathname.startsWith('/retrieval-quality') && !location.pathname.startsWith('/tasks') && !location.pathname.startsWith('/lifecycle') && !location.pathname.startsWith('/settings') && !location.pathname.startsWith('/playground') ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>📊</span>
              <span className={styles.label}>Dashboard</span>
            </NavLink>
          </li>

          {/* Playground */}
          <li>
            <NavLink
              to="/playground"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>🎛️</span>
              <span className={styles.label}>Playground</span>
            </NavLink>
          </li>

          {/* Agents */}
          <li>
            <NavLink
              to="/agents"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>🤖</span>
              <span className={styles.label}>Agents</span>
            </NavLink>
          </li>

          {/* Memory Explorer Dropdown */}
          <li>
            <button
              onClick={() => setExplorerOpen(!explorerOpen)}
              className={`${styles.navItem} ${styles.dropdownToggle} ${isExplorerActive ? styles.activeParent : ''}`}
              aria-expanded={explorerOpen}
            >
              <div className={styles.toggleLeft}>
                <span className={styles.icon}>🧠</span>
                <span className={styles.label}>Memory Explorer</span>
              </div>
              <span className={`${styles.arrow} ${explorerOpen ? styles.arrowOpen : ''}`}>▼</span>
            </button>
            
            {explorerOpen && (
              <ul className={styles.subMenu}>
                {memoryTypes.map((t) => (
                  <li key={t.type}>
                    <NavLink
                      to={`/memory?type=${t.type}`}
                      className={`${styles.navItem} ${styles.subNavItem} ${
                        isActive('/memory', t.type) ? styles.active : ''
                      }`}
                    >
                      <span className={styles.subIcon}>{t.icon}</span>
                      <span className={styles.label}>{t.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </li>

          {/* Retrieval Quality */}
          <li>
            <NavLink
              to="/retrieval-quality"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>🎯</span>
              <span className={styles.label}>Retrieval Quality</span>
            </NavLink>
          </li>

          {/* Task History */}
          <li>
            <NavLink
              to="/tasks"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>📜</span>
              <span className={styles.label}>Task History</span>
            </NavLink>
          </li>

          {/* Memory Lifecycle */}
          <li>
            <NavLink
              to="/lifecycle"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>🔄</span>
              <span className={styles.label}>Memory Lifecycle</span>
            </NavLink>
          </li>

          {/* Settings */}
          <li>
            <NavLink
              to="/settings"
              className={({ isActive: linkActive }) =>
                `${styles.navItem} ${linkActive ? styles.active : ''}`
              }
            >
              <span className={styles.icon}>⚙️</span>
              <span className={styles.label}>Settings</span>
            </NavLink>
          </li>
        </ul>
      </nav>
    </aside>
  );
};
