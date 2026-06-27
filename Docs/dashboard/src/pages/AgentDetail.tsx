import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { client } from '../api/client';
import { LearningCurve } from '../components/charts/LearningCurve';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import type { AgentStats } from '../types';
import styles from './AgentDetail.module.css';

export const AgentDetail: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const navigate = useNavigate();
  const [stats, setStats] = useState<AgentStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!agentId) return;
    (async () => {
      try {
        setLoading(true);
        setStats(await client.getAgentStats(agentId));
      } catch (error) {
        console.error('Error fetching agent stats:', error);
      } finally {
        setLoading(false);
      }
    })();
  }, [agentId]);

  if (loading || !stats) {
    return (
      <div className={styles.page}>
        <SkeletonLoader width="280px" height="36px" />
        <SkeletonLoader height="120px" />
        <SkeletonLoader height="360px" />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <button className={styles.back} onClick={() => navigate('/agents')}>
        ← All agents
      </button>

      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>{stats.agentName}</h1>
          <p className={styles.subtitle}>{stats.agentId}</p>
        </div>
      </header>

      <section className={styles.kpiRow}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Tasks</span>
          <span className={styles.kpiValue}>{stats.taskCount}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Success Rate</span>
          <span className={styles.kpiValue}>{Math.round(stats.successRate * 100)}%</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Calls Reduced</span>
          <span className={`${styles.kpiValue} ${styles.accent}`}>{Math.round(stats.callsReduced)}</span>
        </div>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Skills Learned</span>
          <span className={`${styles.kpiValue} ${styles.green}`}>{stats.skillsLearned}</span>
        </div>
      </section>

      <section className={styles.chartSection}>
        <div className={styles.chartHeader}>
          <h2 className={styles.sectionTitle}>Learning Curve</h2>
          <div className={styles.hint}>Tool calls drop and skills accumulate as memory is reused</div>
        </div>
        <div className={styles.chartWrapper}>
          <LearningCurve data={stats.curve} />
        </div>
      </section>

      <section className={styles.tableSection}>
        <h2 className={styles.sectionTitle}>Run History</h2>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>#</th>
                <th>Task</th>
                <th>Mode</th>
                <th>Tool Calls</th>
                <th>Baseline</th>
                <th>Reduced</th>
                <th>Outcome</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {[...stats.curve].reverse().map((p) => (
                <tr key={p.index}>
                  <td className={styles.mono}>{p.index}</td>
                  <td>
                    <Link to={`/tasks`} className={styles.taskLink} title={p.task}>
                      {p.task || '—'}
                    </Link>
                  </td>
                  <td>
                    <span className={p.replayed ? styles.tagWarm : styles.tagCold}>
                      {p.replayed ? 'replayed' : 'cold'}
                    </span>
                  </td>
                  <td className={styles.mono}>{p.toolCalls}</td>
                  <td className={styles.mono}>{p.baselineCalls ?? '—'}</td>
                  <td className={`${styles.mono} ${styles.accent}`}>{Math.round(p.callsReduced)}</td>
                  <td>
                    <span className={p.outcome === 'success' ? styles.ok : styles.bad}>
                      {p.outcome ?? '—'}
                    </span>
                  </td>
                  <td className={styles.mono}>{p.score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
