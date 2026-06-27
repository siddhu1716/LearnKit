import React, { useEffect, useState } from 'react';
import { client } from '../api/client';
import { MetricCard } from '../components/ui/MetricCard';
import { SuccessRateTrend } from '../components/charts/SuccessRateTrend';
import { InjectionPie } from '../components/charts/InjectionPie';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import type { DashboardMetrics, SuccessRatePoint, TopSkill, ProblematicFailure, ActivityEvent } from '../types';
import styles from './Overview.module.css';

export const Overview: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trendData, setTrendData] = useState<SuccessRatePoint[]>([]);
  const [topSkills, setTopSkills] = useState<TopSkill[]>([]);
  const [problemFailures, setProblemFailures] = useState<ProblematicFailure[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [m, t, s, f, a] = await Promise.all([
        client.getMetrics(),
        client.getSuccessRateTrend(),
        client.getTopSkills(),
        client.getProblematicFailures(),
        client.getActivityFeed(),
      ]);
      setMetrics(m);
      setTrendData(t);
      setTopSkills(s);
      setProblemFailures(f);
      setActivity(a);
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
                  {Math.round(s.helpRate * 100)}% ✅
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
                  {Math.round(f.hurtRate * 100)}% ❌
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
                <span className={styles.activityIcon}>{act.icon}</span>
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
