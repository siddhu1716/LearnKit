import React from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { AgentCurvePoint } from '../../types';

interface LearningCurveProps {
  data: AgentCurvePoint[];
}

// Visualizes how an agent learns over successive runs: tool calls per run
// (going down as memory kicks in), calls reduced vs. its own baseline, and the
// cumulative count of skills learned.
export const LearningCurve: React.FC<LearningCurveProps> = ({ data }) => {
  const formatted = data.map((d) => ({
    index: d.index,
    task: d.task,
    toolCalls: d.toolCalls,
    callsReduced: Math.round(d.callsReduced),
    cumulativeSkills: d.cumulativeSkills,
    replayed: d.replayed,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload as (typeof formatted)[number];
      return (
        <div
          style={{
            background: 'var(--surface-accent)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px',
            fontFamily: 'var(--font-main)',
            boxShadow: 'var(--shadow-md)',
            maxWidth: 260,
          }}
        >
          <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Run #{p.index} {p.replayed ? '· replayed' : '· cold'}
          </p>
          <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-secondary)' }}>{p.task}</p>
          <div style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'grid', gap: 4 }}>
            <span>Tool calls: <b style={{ fontFamily: 'var(--font-mono)' }}>{p.toolCalls}</b></span>
            <span>Calls reduced: <b style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>{p.callsReduced}</b></span>
            <span>Skills learned: <b style={{ fontFamily: 'var(--font-mono)', color: 'var(--secondary)' }}>{p.cumulativeSkills}</b></span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={formatted} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid stroke="rgba(255, 255, 255, 0.03)" vertical={false} />
          <XAxis
            dataKey="index"
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            dy={10}
            fontFamily="var(--font-mono)"
          />
          <YAxis
            stroke="var(--text-muted)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            fontFamily="var(--font-mono)"
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            iconSize={8}
            formatter={(value) => (
              <span style={{ color: 'var(--text-secondary)', fontSize: '12px', fontFamily: 'var(--font-main)', fontWeight: 500, marginRight: '16px' }}>
                {value}
              </span>
            )}
          />
          <Bar name="Calls reduced" dataKey="callsReduced" fill="rgba(0, 255, 136, 0.25)" radius={[3, 3, 0, 0]} barSize={22} />
          <Line name="Tool calls / run" type="monotone" dataKey="toolCalls" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
          <Line name="Skills learned" type="monotone" dataKey="cumulativeSkills" stroke="#00ff88" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
