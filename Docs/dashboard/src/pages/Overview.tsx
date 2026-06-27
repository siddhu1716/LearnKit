import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { MetricCard } from '../components/ui/MetricCard';
import { SuccessRateTrend } from '../components/charts/SuccessRateTrend';
import { InjectionPie } from '../components/charts/InjectionPie';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { ActivityIcon, ArrowUpRight } from '../components/icons';
import type { DashboardMetrics, SuccessRatePoint, TopSkill, ProblematicFailure, ActivityEvent, Agent } from '../types';
import styles from './Overview.module.css';

export const Overview: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trendData, setTrendData] = useState<SuccessRatePoint[]>([]);
  const [topSkills, setTopSkills] = useState<TopSkill[]>([]);
  const [problemFailures, setProblemFailures] = useState<ProblematicFailure[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchData = async () => {
    try {
      setLoading(true);
      const [m, t, s, f, a, ag] = await Promise.all([
        client.getMetrics(),
        client.getSuccessRateTrend(),
        client.getTopSkills(),
        client.getProblematicFailures(),
        client.getActivityFeed(),
        client.getAgents(),
      ]);
      setMetrics(m);
      setTrendData(t);
      setTopSkills(s);
      setProblemFailures(f);
      setActivity(a);
      setAgents(ag);
    } catch (error) {
      console.error('Error fetching overview data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading || !metrics) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.header}>
          <SkeletonLoader width="250px" height="36px" />
          <SkeletonLoader width="100px" height="36px" />
        </div>
        <div className={styles.topCardsGrid}>
          <SkeletonLoader height="160px" />
          <SkeletonLoader height="160px" />
          <SkeletonLoader height="160px" />
        </div>
        <div className={styles.chartWrapper}>
          <SkeletonLoader height="360px" />
        </div>
        <div className={styles.bottomGrid}>
          <SkeletonLoader height="280px" />
          <SkeletonLoader height="280px" />
          <SkeletonLoader height="280px" />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.overview}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Memory Overview</h1>
          <p className={styles.subtitle}>Observability & retrieval metrics for local SDK stores</p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchData} aria-label="Refresh metrics">
          Refresh ↻
        </button>
      </header>

      {/* Top row: 3 Cards */}
      <section className={styles.topCardsGrid}>
        {/* Memory Stats Card */}
        <div className={styles.statCard}>
          <h2 className={styles.cardTitle}>Memory Stats</h2>
          <div className={styles.countsList}>
            <div className={styles.countRow}>
              <span>Skills (distilled procedures)</span>
              <Badge variant="accent">{metrics.recordCounts.skill}</Badge>
            </div>
            <div className={styles.countRow}>
              <span>Failures (dead ends)</span>
              <Badge variant="error">{metrics.recordCounts.failure}</Badge>
            </div>
            <div className={styles.countRow}>
              <span>Facts (domain facts)</span>
              <Badge variant="info">{metrics.recordCounts.fact}</Badge>
            </div>
            <div className={styles.countRow}>
              <span>Other record types</span>
              <Badge variant="neutral">
                {metrics.recordCounts.strategy +
                  metrics.recordCounts.preference +
                  metrics.recordCounts.heuristic +
                  metrics.recordCounts.trace}
              </Badge>
            </div>
          </div>
          <div className={styles.cardFooter}>
            Last updated: {new Date(metrics.lastUpdated).toLocaleTimeString()}
          </div>
        </div>

        {/* Task Metrics Card */}
        <div className={styles.statCard}>
          <h2 className={styles.cardTitle}>Task Metrics</h2>
          <div className={styles.metricsContainer}>
            <div className={styles.metricValGroup}>
              <span className={styles.metricValLabel}>Success Rate</span>
              <div className={styles.metricVal}>
                {Math.round(metrics.successRate * 100)}%
                <span className={styles.trendUp}>+5pp</span>
              </div>
            </div>
            <div className={styles.metricsDetailsRow}>
              <div className={styles.metricSub}>
                <span className={styles.metricSubLabel}>Avg Cost</span>
                <span className={styles.metricSubVal}>{metrics.avgTokens} tk</span>
              </div>
              <div className={styles.metricSub}>
                <span className={styles.metricSubLabel}>Retries Saved</span>
                <span className={styles.metricSubVal}>-{Math.round(metrics.retryReduction * 100)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Injection Trends Card */}
        <div className={styles.statCard}>
          <h2 className={styles.cardTitle}>Injection Trends</h2>
          <InjectionPie data={metrics.primaryDistribution} />
        </div>
      </section>

      {/* Agent learning band */}
      <section className={styles.agentBand} onClick={() => navigate('/agents')} role="button" tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && navigate('/agents')}>
        <div className={styles.agentBandHeader}>
          <h2 className={styles.cardTitle}>How Your Agents Are Learning</h2>
          <span className={styles.agentBandLink}>View all agents <ArrowUpRight size={14} /></span>
        </div>
        <div className={styles.agentBandStats}>
          <div className={styles.agentStat}>
            <span className={styles.agentStatValue}>{agents.length}</span>
            <span className={styles.agentStatLabel}>Active Agents</span>
          </div>
          <div className={styles.agentStat}>
            <span className={`${styles.agentStatValue} ${styles.accentText}`}>
              {Math.round(agents.reduce((acc, a) => acc + a.callsReduced, 0))}
            </span>
            <span className={styles.agentStatLabel}>Calls Reduced</span>
          </div>
          <div className={styles.agentStat}>
            <span className={`${styles.agentStatValue} ${styles.greenText}`}>
              {agents.reduce((acc, a) => acc + a.skillsLearned, 0)}
            </span>
            <span className={styles.agentStatLabel}>Skills Learned</span>
          </div>
          <div className={styles.agentStat}>
            <span className={styles.agentStatValue}>
              {agents.reduce((acc, a) => acc + a.taskCount, 0)}
            </span>
            <span className={styles.agentStatLabel}>Total Tasks</span>
          </div>
        </div>
      </section>

      {/* Mid row: Main Chart */}
      <section className={styles.chartSection}>
        <div className={styles.chartHeader}>
          <h2 className={styles.sectionTitle}>Success Rate Trend (30 Days)</h2>
          <div className={styles.chartLegendHint}>Comparing agent starts: Control vs. Cold vs. Warmed</div>
        </div>
        <div className={styles.chartWrapper}>
          <SuccessRateTrend data={trendData} />
        </div>
      </section>

      {/* Bottom row: Lists */}
      <section className={styles.bottomGrid}>
        {/* Top Performing Skills */}
        <div className={styles.listCard}>
          <h2 className={styles.listCardTitle}>Top Performing Skills</h2>
          <ul className={styles.list}>
            {topSkills.map((s, idx) => (
              <li key={s.id} className={styles.listItem}>
                <span className={styles.listItemIndex}>{idx + 1}.</span>
                <span className={styles.listItemName} title={s.name}>{s.name}</span>
                <span className={styles.listItemValGreen}>
                  {Math.round(s.helpRate * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Problematic Failures */}
        <div className={styles.listCard}>
          <h2 className={styles.listCardTitle}>Problematic Failures</h2>
          <ul className={styles.list}>
            {problemFailures.map((f, idx) => (
              <li key={f.id} className={styles.listItem}>
                <span className={styles.listItemIndex}>{idx + 1}.</span>
                <span className={styles.listItemName} title={f.name}>{f.name}</span>
                <span className={styles.listItemValRed}>
                  {Math.round(f.hurtRate * 100)}%
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recent Activity */}
        <div className={styles.listCard}>
          <h2 className={styles.listCardTitle}>Recent Activity</h2>
          <ul className={styles.activityList}>
            {activity.map((act, idx) => (
              <li key={idx} className={styles.activityItem}>
                <span className={styles.activityIcon}>
                  <ActivityIcon type={act.icon} />
                </span>
                <div className={styles.activityContent}>
                  <div className={styles.activityMsg}>{act.message}</div>
                  <div className={styles.activityTime}>{act.time}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
};
