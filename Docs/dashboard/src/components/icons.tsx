// ============================================================
// LearnKit Dashboard — Icon system
// Central re-export of lucide-react icons so the app uses a
// single, consistent iconography (no emoji). Import icons from
// here rather than reaching into lucide-react directly.
// ============================================================

import React from 'react';
import {
  LayoutDashboard,
  Activity,
  Bot,
  Brain,
  Target,
  History,
  RefreshCw,
  Settings,
  FileText,
  BookOpen,
  Gauge,
  Zap,
  XCircle,
  Library,
  Puzzle,
  Lightbulb,
  Clock,
  Search,
  Coins,
  Timer,
  DollarSign,
  Cpu,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronRight,
  Menu,
  Circle,
  CheckCircle2,
  Trash2,
  Sparkles,
  Wrench,
  ArrowUpRight,
  ArrowDownRight,
  Hash,
  Home,
  Layers,
  Tag,
  Calendar,
  User,
  AlertTriangle,
  Inbox,
  type LucideIcon,
} from 'lucide-react';

export type { LucideIcon };

export {
  LayoutDashboard,
  Activity,
  Bot,
  Brain,
  Target,
  History,
  RefreshCw,
  Settings,
  FileText,
  BookOpen,
  Gauge,
  Zap,
  XCircle,
  Library,
  Puzzle,
  Lightbulb,
  Clock,
  Search,
  Coins,
  Timer,
  DollarSign,
  Cpu,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronRight,
  Menu,
  Circle,
  CheckCircle2,
  Trash2,
  Sparkles,
  Wrench,
  ArrowUpRight,
  ArrowDownRight,
  Hash,
  Home,
  Layers,
  Tag,
  Calendar,
  User,
  AlertTriangle,
  Inbox,
};

// Memory record types -> icon (used in sidebar + explorer).
export const MEMORY_TYPE_ICONS: Record<string, LucideIcon> = {
  skill: Zap,
  failure: XCircle,
  fact: Library,
  strategy: Puzzle,
  preference: Settings,
  heuristic: Lightbulb,
  trace: Clock,
};

// Activity-feed semantic keys -> icon + accent color var.
export const ACTIVITY_ICONS: Record<string, { icon: LucideIcon; color: string }> = {
  distill: { icon: Sparkles, color: 'var(--accent)' },
  failure: { icon: XCircle, color: 'var(--error)' },
  success: { icon: CheckCircle2, color: 'var(--success)' },
  purge: { icon: Trash2, color: 'var(--text-muted)' },
  reinforce: { icon: RefreshCw, color: 'var(--secondary)' },
  maintain: { icon: Wrench, color: 'var(--warn)' },
};

interface ActivityIconProps {
  type: string;
  size?: number;
}

/** Render an activity icon from a semantic key, with a sensible fallback. */
export const ActivityIcon: React.FC<ActivityIconProps> = ({ type, size = 16 }) => {
  const entry = ACTIVITY_ICONS[type] ?? { icon: Activity, color: 'var(--text-secondary)' };
  const Icon = entry.icon;
  return <Icon size={size} style={{ color: entry.color }} aria-hidden />;
};
