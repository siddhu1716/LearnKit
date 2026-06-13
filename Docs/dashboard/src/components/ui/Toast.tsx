import React, { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import styles from './Toast.module.css';

export type ToastVariant = 'success' | 'error' | 'warn' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  variant?: ToastVariant;
}

import { useState } from 'react';

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const handleDismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleAdd = useCallback((msg: Omit<ToastMessage, 'id'>) => {
    const newToast: ToastMessage = {
      ...msg,
      id: Math.random().toString(36).slice(2, 9),
    };
    setToasts((prev) => [...prev, newToast]);
  }, []);

  useEffect(() => {
    registerToastFn(handleAdd);
  }, [handleAdd]);

  return createPortal(
    <div className={styles.container} role="region" aria-label="Notifications" aria-live="polite">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={handleDismiss} />
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
