import React from 'react';
import styles from './SkeletonLoader.module.css';

interface SkeletonLoaderProps {
  variant?: 'text' | 'rect' | 'circle';
  width?: string;
  height?: string;
  className?: string;
}

export const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant = 'rect',
  width,
  height,
  className = '',
}) => {
  const style: React.CSSProperties = {
    width,
    height,
  };

  return (
    <div
      className={`${styles.skeleton} ${styles[variant]} ${className}`}
      style={style}
      role="progressbar"
      aria-busy="true"
    />
  );
};
