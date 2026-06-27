import React from 'react';
import styles from './ConfidenceBadge.module.css';

interface ConfidenceBadgeProps {
  value: number; // 0.0–1.0
  label?: string;
  size?: 'small' | 'medium' | 'large';
  showBar?: boolean;
}

function getColor(value: number): string {
  if (value >= 0.8) return 'var(--success)';
  if (value >= 0.5) return 'var(--warn)';
  return 'var(--error)';
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  value,
  label,
  size = 'medium',
  showBar = true,
}) => {
  const color = getColor(value);
  const pct = Math.round(value * 100);

  return (
    <div className={`${styles.wrap} ${styles[size]}`}>
      <span className={styles.label} style={{ color }}>
        {label ?? value.toFixed(2)}
      </span>
      {showBar && (
        <div className={styles.barTrack}>
          <div
            className={styles.barFill}
            style={{ width: `${pct}%`, background: color }}
          />
        </div>
      )}
    </div>
  );
};
