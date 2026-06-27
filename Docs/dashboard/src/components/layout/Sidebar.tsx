import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import styles from './Sidebar.module.css';
import {
  LayoutDashboard,
  Activity,
  Bot,
  Brain,
  Target,
  History,
  RefreshCw,
  Settings,
  BookOpen,
  FileText,
  ChevronDown,
  MEMORY_TYPE_ICONS,
  type LucideIcon,
} from '../icons';

interface SidebarProps {
  open: boolean;
}

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const sections: { heading: string; items: NavItem[] }[] = [
  {
    heading: 'Monitor',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/observability', label: 'Observability', icon: Activity },
      { to: '/agents', label: 'Agents', icon: Bot },
    ],
  },
  {
    heading: 'Analyze',
    items: [
      { to: '/retrieval-quality', label: 'Retrieval Quality', icon: Target },
      { to: '/tasks', label: 'Task History', icon: History },
      { to: '/lifecycle', label: 'Memory Lifecycle', icon: RefreshCw },
    ],
  },
  {
    heading: 'Build',
    items: [{ to: '/playground', label: 'Playground', icon: Target }],
  },
  {
    heading: 'Learn',
    items: [
      { to: '/blog', label: 'Blog', icon: BookOpen },
      { to: '/docs', label: 'Docs', icon: FileText },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

const memoryTypes = [
  { type: 'skill', label: 'Skills' },
  { type: 'failure', label: 'Failures' },
  { type: 'fact', label: 'Facts' },
  { type: 'strategy', label: 'Strategies' },
  { type: 'preference', label: 'Preferences' },
  { type: 'heuristic', label: 'Heuristics' },
  { type: 'trace', label: 'Traces' },
];

export const Sidebar: React.FC<SidebarProps> = ({ open }) => {
  const location = useLocation();
  const [explorerOpen, setExplorerOpen] = useState(true);

  const isExplorerActive = location.pathname === '/memory';

  const isTypeActive = (type: string) => {
    const searchParams = new URLSearchParams(location.search);
    return location.pathname === '/memory' && searchParams.get('type') === type;
  };

  return (
    <aside
      className={`${styles.sidebar} ${open ? styles.open : styles.collapsed}`}
      aria-label="Sidebar navigation"
    >
      <nav className={styles.nav}>
        {sections.map((section, idx) => (
          <div className={styles.section} key={section.heading}>
            <span className={styles.sectionHeading}>{section.heading}</span>
            <ul className={styles.navList}>
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.to === '/'}
                      className={({ isActive }) =>
                        `${styles.navItem} ${isActive ? styles.active : ''}`
                      }
                    >
                      <span className={styles.icon}>
                        <Icon size={18} />
                      </span>
                      <span className={styles.label}>{item.label}</span>
                    </NavLink>
                  </li>
                );
              })}

              {/* Memory Explorer dropdown lives in the Analyze section */}
              {idx === 1 && (
                <li>
                  <button
                    onClick={() => setExplorerOpen(!explorerOpen)}
                    className={`${styles.navItem} ${styles.dropdownToggle} ${
                      isExplorerActive ? styles.activeParent : ''
                    }`}
                    aria-expanded={explorerOpen}
                  >
                    <div className={styles.toggleLeft}>
                      <span className={styles.icon}>
                        <Brain size={18} />
                      </span>
                      <span className={styles.label}>Memory Explorer</span>
                    </div>
                    <span
                      className={`${styles.arrow} ${explorerOpen ? styles.arrowOpen : ''}`}
                    >
                      <ChevronDown size={14} />
                    </span>
                  </button>

                  {explorerOpen && (
                    <ul className={styles.subMenu}>
                      {memoryTypes.map((t) => {
                        const TypeIcon = MEMORY_TYPE_ICONS[t.type];
                        return (
                          <li key={t.type}>
                            <NavLink
                              to={`/memory?type=${t.type}`}
                              className={`${styles.navItem} ${styles.subNavItem} ${
                                isTypeActive(t.type) ? styles.active : ''
                              }`}
                            >
                              <span className={styles.subIcon}>
                                <TypeIcon size={15} />
                              </span>
                              <span className={styles.label}>{t.label}</span>
                            </NavLink>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              )}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
};

