import React from 'react';
import styles from './Settings.module.css';

export const DocsHub: React.FC = () => {
  return (
    <div className={styles.settings}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Docs & API</h1>
          <p className={styles.subtitle}>
            Local-first dashboard docs, API contract, and branch guidance for production and frontend work.
          </p>
        </div>
      </header>

      <section className={styles.card}>
        <h2 className={styles.cardTitle}>What exists today</h2>
        <p className={styles.cardDesc}>
          The dashboard talks to the FastAPI server in Docs/server.py and falls back to localStorage/mock
          data when the backend is unavailable.
        </p>
        <ul>
          <li>GET /healthz</li>
          <li>GET /api/domains</li>
          <li>POST /api/inspect</li>
          <li>GET /api/v1/records and related memory lifecycle routes</li>
        </ul>
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardTitle}>Branch plan</h2>
        <p className={styles.cardDesc}>
          production owns backend endpoints and persistence; frontend owns the React dashboard and shared UI.
        </p>
      </section>
    </div>
  );
};

export default DocsHub;
