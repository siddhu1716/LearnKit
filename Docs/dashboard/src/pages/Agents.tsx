import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import type { Agent } from '../types';
import styles from './Agents.module.css';

export const Agents: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      setLoading(true);
      setAgents(await client.getAgents());
    } catch (error) {
      console.error('Error fetching agents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const totals = agents.reduce(
    (acc, a) => {
      acc.tasks += a.taskCount;
      acc.callsReduced += a.callsReduced;
      acc.skills += a.skillsLearned;
      return acc;
    },
    { tasks: 0, callsReduced: 0, skills: 0 }
  );

  if (loading) {
    return (
      <div className={styles.page}>
        <SkeletonLoader width="280px" height="36px" />
        <SkeletonLoader height="120px" />
        <SkeletonLoader height="320px" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Agents</h1>
          <p className={styles.subtitle}>
            Track how each agent is learning — calls saved and skills acquired over time
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchData} aria-label="Refresh agents">
          Refresh ↻
        </button>
      </header>

      <section className={styles.kpiRow}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Active Agents</span>
          <span className={styles.kpiValue}>{agents.length}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Total Tasks</span>
          <span className={styles.kpiValue}>{totals.tasks}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Calls Reduced</span>
          <span className={`${styles.kpiValue} ${styles.accent}`}>{Math.round(totals.callsReduced)}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Skills Learned</span>
          <span className={`${styles.kpiValue} ${styles.green}`}>{totals.skills}</span>
        </div>
      </section>

      {agents.length === 0 ? (
        <div className={styles.empty}>
          No agents yet. Run a task with <code>@lk.agent_learn(agent_id="my-agent")</code> to start tracking.
        </div>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Tasks</th>
                <th>Success</th>
                <th>Calls Reduced</th>
                <th>Skills</th>
                <th>Avg Score</th>
                <th>Last Active</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr key={a.id} className={styles.row} onClick={() => navigate(`/agents/${a.id}`)}>
                  <td>
                    <div className={styles.agentName}>{a.name}</div>
                    <div className={styles.agentId}>{a.id}</div>
                  </td>
                  <td className={styles.mono}>{a.taskCount}</td>
                  <td className={styles.mono}>{Math.round(a.successRate * 100)}%</td>
                  <td className={`${styles.mono} ${styles.accent}`}>{Math.round(a.callsReduced)}</td>
                  <td className={`${styles.mono} ${styles.green}`}>{a.skillsLearned}</td>
                  <td className={styles.mono}>{a.avgScore != null ? a.avgScore.toFixed(1) : '—'}</td>
                  <td className={styles.muted}>
                    {a.lastActive ? new Date(a.lastActive).toLocaleString() : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
