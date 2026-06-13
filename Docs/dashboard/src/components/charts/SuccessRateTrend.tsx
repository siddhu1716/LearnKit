import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import type { SuccessRatePoint } from '../../types';

interface SuccessRateTrendProps {
  data: SuccessRatePoint[];
}

export const SuccessRateTrend: React.FC<SuccessRateTrendProps> = ({ data }) => {
  // Map data to percentages
  const formattedData = data.map((d) => ({
    ...d,
    control: Math.round(d.control),
    coldStart: Math.round(d.coldStart),
    warmedStart: Math.round(d.warmedStart),
  }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div
          style={{
            background: 'var(--surface-accent)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '12px',
            fontFamily: 'var(--font-main)',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <p style={{ margin: '0 0 8px 0', fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Day {label}
          </p>
          {payload.map((entry: any) => (
            <div
              key={entry.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '13px',
                color: 'var(--text-primary)',
                margin: '4px 0',
              }}
            >
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: entry.color,
                  display: 'inline-block',
                }}
              />
              <span style={{ fontWeight: 500 }}>{entry.name}:</span>
              <span style={{ fontFamily: 'var(--font-mono)', color: entry.color, fontWeight: 600 }}>
                {entry.value}%
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={formattedData}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <CartesianGrid stroke="rgba(255, 255, 255, 0.03)" vertical={false} />
          <XAxis
            dataKey="day"
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
            tickFormatter={(value) => `${value}%`}
            domain={[0, 100]}
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
          <Line
            name="Control (Baseline)"
            type="monotone"
            dataKey="control"
            stroke="#52525b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
          <Line
            name="Cold Start"
            type="monotone"
            dataKey="coldStart"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
          <Line
            name="Warmed Start"
            type="monotone"
            dataKey="warmedStart"
            stroke="#00ff88"
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 5, strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
