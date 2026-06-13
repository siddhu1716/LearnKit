import React from 'react';
import styles from './MetricCard.module.css';

type ColorVariant = 'success' | 'warn' | 'error' | 'neutral' | 'accent' | 'secondary';

interface TrendProps {
  direction: 'up' | 'down' | 'neutral';
  percent: number;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: TrendProps;
  icon?: React.ReactNode;
  color?: ColorVariant;
  onClick?: () => void;
  className?: string;
}

const trendIcon = (dir: TrendProps['direction']) => {
  if (dir === 'up') return '↑';
  if (dir === 'down') return '↓';
  return '→';
};

const colorMap: Record<ColorVariant, string> = {
  success: 'var(--success)',
  warn: 'var(--warn)',
  error: 'var(--error)',
  neutral: 'var(--text-secondary)',
  accent: 'var(--accent)',
  secondary: 'var(--secondary)',
};

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  trend,
  icon,
  color = 'neutral',
  onClick,
  className = '',
}) => {
  const accentColor = colorMap[color];

  return (
    <div
      className={`${styles.card} ${onClick ? styles.clickable : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className={styles.header}>
        {icon && (
          <span className={styles.icon} style={{ color: accentColor }}>
            {icon}
          </span>
        )}
        <span className={styles.label}>{label}</span>
      </div>
      <div className={styles.valueRow}>
        <span className={styles.value} style={{ color: accentColor }}>
          {value}
        </span>
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>
      {trend && (
        <div
          className={styles.trend}
          style={{
            color: trend.direction === 'up'
              ? 'var(--success)'
              : trend.direction === 'down'
              ? 'var(--error)'
              : 'var(--text-muted)',
          }}
        >
          <span>{trendIcon(trend.direction)}</span>
          <span>{trend.percent}%</span>
        </div>
      )}
    </div>
  );
};
