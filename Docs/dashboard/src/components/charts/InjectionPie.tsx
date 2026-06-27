import React from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';

interface DataItem {
  name: string;
  value: number;
  color: string;
}

interface InjectionPieProps {
  data: {
    skill: number;
    failure: number;
    fact: number;
  };
}

export const InjectionPie: React.FC<InjectionPieProps> = ({ data }) => {
  const chartData: DataItem[] = [
    { name: 'Skill', value: Math.round(data.skill * 100), color: '#00ff88' },
    { name: 'Failure', value: Math.round(data.failure * 100), color: '#ef4444' },
    { name: 'Fact', value: Math.round(data.fact * 100), color: '#a78bfa' },
  ];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as DataItem;
      return (
        <div
          style={{
            background: 'var(--surface-accent)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 12px',
            fontFamily: 'var(--font-main)',
            fontSize: '13px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: data.color,
              display: 'inline-block',
              marginRight: '8px',
            }}
          />
          <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{data.name}: </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: data.color }}>
            {data.value}%
          </span>
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ width: '100%', height: 160, display: 'flex', alignItems: 'center' }}>
      <div style={{ width: '55%', height: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={45}
              outerRadius={60}
              paddingAngle={4}
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} stroke="var(--surface)" strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div style={{ width: '45%', display: 'flex', flexDirection: 'column', gap: '8px', justifyContent: 'center' }}>
        {chartData.map((item) => (
          <div key={item.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '13px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: item.color }} />
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-main)' }}>{item.name}</span>
            </div>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: item.color }}>
              {item.value}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
