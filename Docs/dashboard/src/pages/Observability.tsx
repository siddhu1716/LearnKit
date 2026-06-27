import React, { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import styles from './Observability.module.css';
import { client } from '../api/client';
import type { ObservabilitySummary } from '../types';
import { MetricCard } from '../components/ui/MetricCard';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import {
  Coins,
  DollarSign,
  Timer,
  Activity,
  Cpu,
  TrendingUp,
} from '../components/icons';

const fmtInt = (n: number) => n.toLocaleString('en-US');
const fmtTokens = (n: number) =>
  n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;
const fmtCost = (n: number) => `$${n.toFixed(n < 1 ? 4 : 2)}`;
const fmtMs = (n: number | null) => (n == null ? '—' : `${Math.round(n)} ms`);

const MODEL_COLORS = [
  'var(--accent)',
  'var(--secondary)',
  'var(--warn)',
  'var(--success)',
  'var(--error)',
];

export const Observability: React.FC = () => {
  const [data, setData] = useState<ObservabilitySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    client
      .getObservability()
      .then((d) => active && setData(d))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  if (loading || !data) {
    return (
      <div className={styles.page}>
        <SkeletonLoader />
      </div>
    );
  }

  const { totals, latency, models, timeseries } = data;
  const maxModelTokens = Math.max(1, ...models.map((m) => m.tokens));

  const TooltipBox = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    return (
      <div className={styles.tooltip}>
        <p className={styles.tooltipTitle}>{label}</p>
        {payload.map((p: any) => (
          <div key={p.dataKey} className={styles.tooltipRow}>
            <span style={{ color: p.color }}>●</span>
            <span>{p.name}</span>
            <b>
              {p.dataKey === 'costUsd'
                ? fmtCost(p.value)
                : p.dataKey === 'avgLatencyMs'
                ? fmtMs(p.value)
                : fmtInt(p.value)}
            </b>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.titleRow}>
            <Activity size={22} className={styles.titleIcon} />
            <h1 className={styles.title}>Observability</h1>
            {data.estimated && (
              <span className={styles.estBadge} title="Token and cost figures are estimated from text volume; latency and model are measured.">
                est.
              </span>
            )}
          </div>
          <p className={styles.subtitle}>
            LLM token usage, latency, and cost across every learning run.
          </p>
        </div>
        <span className={styles.updated}>
          Updated {new Date(data.lastUpdated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </header>

      {/* KPI band */}
      <div className={styles.kpiGrid}>
        <MetricCard
          label="Total tokens"
          value={fmtTokens(totals.totalTokens)}
          icon={<Coins size={16} />}
          color="accent"
        />
        <MetricCard
          label="Total cost"
          value={fmtCost(totals.costUsd)}
          icon={<DollarSign size={16} />}
          color="secondary"
        />
        <MetricCard
          label="Avg latency"
          value={fmtMs(latency.avgMs)}
          icon={<Timer size={16} />}
          color="warn"
        />
        <MetricCard
          label="Runs traced"
          value={fmtInt(totals.runs)}
          icon={<Activity size={16} />}
          color="neutral"
        />
        <MetricCard
          label="Avg tokens / run"
          value={fmtInt(totals.avgTokensPerRun)}
          icon={<TrendingUp size={16} />}
          color="accent"
        />
        <MetricCard
          label="Avg cost / run"
          value={fmtCost(totals.avgCostPerRun)}
          icon={<DollarSign size={16} />}
          color="secondary"
        />
      </div>

      <div className={styles.columns}>
        {/* Token split + latency percentiles */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Token breakdown</h2>
          <div className={styles.splitBar}>
            <div
              className={styles.splitPrompt}
              style={{
                width: `${(totals.promptTokens / Math.max(1, totals.totalTokens)) * 100}%`,
              }}
            />
            <div
              className={styles.splitCompletion}
              style={{
                width: `${(totals.completionTokens / Math.max(1, totals.totalTokens)) * 100}%`,
              }}
            />
          </div>
          <div className={styles.splitLegend}>
            <span>
              <i className={styles.dotPrompt} /> Prompt {fmtInt(totals.promptTokens)}
            </span>
            <span>
              <i className={styles.dotCompletion} /> Completion {fmtInt(totals.completionTokens)}
            </span>
          </div>

          <h2 className={styles.cardTitle} style={{ marginTop: 'var(--space-lg)' }}>
            Latency percentiles
          </h2>
          <div className={styles.percentiles}>
            {[
              { label: 'p50', value: latency.p50Ms },
              { label: 'p95', value: latency.p95Ms },
              { label: 'p99', value: latency.p99Ms },
            ].map((p) => (
              <div key={p.label} className={styles.percentile}>
                <span className={styles.percentileLabel}>{p.label}</span>
                <span className={styles.percentileValue}>{fmtMs(p.value)}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Model usage breakdown */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>
            <Cpu size={15} className={styles.inlineIcon} /> Model usage
          </h2>
          <div className={styles.modelList}>
            {models.length === 0 && (
              <p className={styles.empty}>No model usage recorded yet.</p>
            )}
            {models.map((m, i) => (
              <div key={m.model} className={styles.modelRow}>
                <div className={styles.modelHead}>
                  <span className={styles.modelName} title={m.model}>
                    {m.model.split('/').pop()}
                  </span>
                  <span className={styles.modelMeta}>
                    {fmtTokens(m.tokens)} tok · {fmtCost(m.costUsd)} · {m.runs} runs
                  </span>
                </div>
                <div className={styles.modelTrack}>
                  <div
                    className={styles.modelFill}
                    style={{
                      width: `${(m.tokens / maxModelTokens) * 100}%`,
                      background: MODEL_COLORS[i % MODEL_COLORS.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Time series */}
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>Tokens & cost over time</h2>
        <div className={styles.chart}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeseries} margin={{ top: 10, right: 12, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="tokGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis
                dataKey="date"
                stroke="var(--text-muted)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                dy={8}
                fontFamily="var(--font-mono)"
              />
              <YAxis
                stroke="var(--text-muted)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                fontFamily="var(--font-mono)"
                tickFormatter={(v) => fmtTokens(Number(v))}
              />
              <Tooltip content={<TooltipBox />} />
              <Area
                type="monotone"
                dataKey="tokens"
                name="Tokens"
                stroke="var(--accent)"
                strokeWidth={2}
                fill="url(#tokGrad)"
              />
              <Line
                type="monotone"
                dataKey="avgLatencyMs"
                name="Avg latency"
                stroke="var(--warn)"
                strokeWidth={2}
                dot={false}
                yAxisId={0}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>

      <p className={styles.footnote}>
        Latency and model names are measured directly. Token counts and cost are
        estimated from text volume across the classify, judge, and distill stages
        (LearnKit calls models through DSPy, which does not expose per-call usage).
      </p>
    </div>
  );
};

export default Observability;
