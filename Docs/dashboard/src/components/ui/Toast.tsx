import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import styles from './Toast.module.css';

export type ToastVariant = 'success' | 'error' | 'warn' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  variant?: ToastVariant;
}

interface ToastContainerProps {
  toasts: ToastMessage[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onDismiss }) => {
  return createPortal(
    <div className={styles.container} role="region" aria-label="Notifications" aria-live="polite">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={onDismiss} />
      ))}
    </div>,
    document.body
  );
};

const Toast: React.FC<{ toast: ToastMessage; onDismiss: (id: string) => void }> = ({
  toast,
  onDismiss,
}) => {
  const dismiss = useCallback(() => onDismiss(toast.id), [toast.id, onDismiss]);

  useEffect(() => {
    const timer = setTimeout(dismiss, 5000);
    return () => clearTimeout(timer);
  }, [dismiss]);

  const icons: Record<ToastVariant, string> = {
    success: '✓',
    error: '✕',
    warn: '⚠',
    info: 'ℹ',
  };

  const variant = toast.variant ?? 'info';

  return (
    <div className={`${styles.toast} ${styles[variant]} animate-fade-in`} role="alert">
      <span className={styles.icon}>{icons[variant]}</span>
      <span className={styles.msg}>{toast.message}</span>
      <button className={styles.close} onClick={dismiss} aria-label="Dismiss notification">
        ✕
      </button>
    </div>
  );
};

// Toast hook
let _addToast: ((msg: Omit<ToastMessage, 'id'>) => void) | null = null;

export function registerToastFn(fn: (msg: Omit<ToastMessage, 'id'>) => void) {
  _addToast = fn;
}

export function toast(message: string, variant: ToastVariant = 'info') {
  _addToast?.({ message, variant });
}
