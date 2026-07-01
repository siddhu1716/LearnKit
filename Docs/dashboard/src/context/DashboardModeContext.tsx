import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { setDashboardMode, type DashboardMode } from '../api/client';

// LearnKit exposes two learning paths that produce very different telemetry:
//   • learn       — model/answer-quality path (@memory.learn / @memory.agent).
//                   No tools, no procedures; value = answer quality.
//   • agent_learn — agent/tool path (@memory.agent_learn). Captures procedures,
//                   replays exact matches; value = tool calls reduced.
// The dashboard lets the user toggle between these so each view is scoped to
// one path. 'agent_learn' shows the full rich view (calls-reduced, procedures);
// 'learn' shows a lighter records + tasks + quality view.

const STORAGE_KEY = 'learnkit_dashboard_mode';

interface DashboardModeContextValue {
  mode: DashboardMode;
  setMode: (mode: DashboardMode) => void;
}

const DashboardModeContext = createContext<DashboardModeContextValue | undefined>(undefined);

function readInitialMode(): DashboardMode {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'learn' || raw === 'agent_learn') return raw;
  } catch {
    /* ignore */
  }
  // Default to the model/answer path since that's the primary "learn" surface.
  return 'learn';
}

export const DashboardModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<DashboardMode>(readInitialMode);

  // Keep the API client in sync so every run-backed getter scopes its query.
  // Run synchronously on first render (not just in an effect) so the very first
  // fetch already carries the correct mode.
  if (typeof window !== 'undefined') {
    setDashboardMode(mode);
  }

  useEffect(() => {
    setDashboardMode(mode);
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  const setMode = useCallback((next: DashboardMode) => {
    setDashboardMode(next);
    setModeState(next);
  }, []);

  const value = useMemo(() => ({ mode, setMode }), [mode, setMode]);

  return <DashboardModeContext.Provider value={value}>{children}</DashboardModeContext.Provider>;
};

export function useDashboardMode(): DashboardModeContextValue {
  const ctx = useContext(DashboardModeContext);
  if (!ctx) {
    throw new Error('useDashboardMode must be used within a DashboardModeProvider');
  }
  return ctx;
}
