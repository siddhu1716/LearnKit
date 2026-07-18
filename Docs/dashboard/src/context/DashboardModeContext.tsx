import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { setDashboardMode, type DashboardMode } from '../api/client';

// The dashboard operates in a single mode: 'agent_learn' — the agent/tool path
// (@memory.agent_learn). It captures tool procedures, replays exact matches, and
// reports calls-reduced. The DashboardMode type is retained so run/telemetry
// queries stay explicitly scoped, but there is no user-facing path toggle.

const STORAGE_KEY = 'learnkit_dashboard_mode';

interface DashboardModeContextValue {
  mode: DashboardMode;
  setMode: (mode: DashboardMode) => void;
}

const DashboardModeContext = createContext<DashboardModeContextValue | undefined>(undefined);

function readInitialMode(): DashboardMode {
  // agent_learn is the only path exposed in the product. The model/answer
  // path was removed from the UI, so we always land on the agent (tool) path
  // — where the published benchmark results live (calls-reduced + replay).
  return 'agent_learn';
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
