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
import { DocsHub } from './pages/DocsHub';
import { ToastContainer } from './components/ui/Toast';

export const App: React.FC = () => {
  return (
    <HashRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/memory" element={<MemoryExplorer />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agents/:agentId" element={<AgentDetail />} />
          
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
      <ToastContainer />
    </HashRouter>
  );
};
export default App;
