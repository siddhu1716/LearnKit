import React from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { Overview } from './pages/Overview';
import { MemoryExplorer } from './pages/MemoryExplorer';
import { RetrievalQuality } from './pages/RetrievalQuality';
import { TaskHistory } from './pages/TaskHistory';
import { TracePlayback } from './pages/TracePlayback';
import { MemoryLifecycle } from './pages/MemoryLifecycle';
import { Settings } from './pages/Settings';
import { Playground } from './pages/Playground';
import { Agents } from './pages/Agents';
import { AgentDetail } from './pages/AgentDetail';
import { Observability } from './pages/Observability';
import { Blog } from './pages/Blog';
import { BlogPost } from './pages/BlogPost';
import { DocsHub } from './pages/DocsHub';
import { ToastContainer } from './components/ui/Toast';
import { DashboardModeProvider, useDashboardMode } from './context/DashboardModeContext';

const AppRoutes: React.FC = () => {
  const { mode } = useDashboardMode();
  return (
    <AppShell>
      {/* Keying on mode remounts every page when the learn / agent_learn
          toggle flips, so each view re-fetches its mode-scoped telemetry. */}
      <Routes key={mode}>
        <Route path="/" element={<Overview />} />
        <Route path="/memory" element={<MemoryExplorer />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/observability" element={<Observability />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/agents/:agentId" element={<AgentDetail />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:slug" element={<BlogPost />} />

        {/* Legacy redirects */}
        <Route path="/skills" element={<Navigate to="/memory?type=skill" replace />} />
        <Route path="/failures" element={<Navigate to="/memory?type=failure" replace />} />

        <Route path="/retrieval-quality" element={<RetrievalQuality />} />
        <Route path="/tasks" element={<TaskHistory />} />
        <Route path="/tasks/:taskId" element={<TracePlayback />} />
        <Route path="/lifecycle" element={<MemoryLifecycle />} />
        <Route path="/docs" element={<DocsHub />} />
        <Route path="/settings" element={<Settings />} />

        {/* Fallback to Overview */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <HashRouter>
      <DashboardModeProvider>
        <AppRoutes />
        <ToastContainer />
      </DashboardModeProvider>
    </HashRouter>
  );
};
export default App;
