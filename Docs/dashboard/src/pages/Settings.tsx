import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { toast } from '../components/ui/Toast';
import styles from './Settings.module.css';

export const Settings: React.FC = () => {
  // Policy State
  const [quarantineHours, setQuarantineHours] = useState<number>(24);
  const [minQualityScore, setMinQualityScore] = useState<number>(0.75);
  const [autoDecay, setAutoDecay] = useState<boolean>(true);
  
  // Privacy State
  const [piiScrubbing, setPiiScrubbing] = useState<boolean>(true);
  const [localOnly, setLocalOnly] = useState<boolean>(true);
  const [redactedTags, setRedactedTags] = useState<string>('emails, phone_numbers, api_keys, passwords');

  const [saving, setSaving] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      toast('Settings saved successfully', 'success');
    }, 600);
  };

  return (
    <div className={styles.settings}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Settings</h1>
          <p className={styles.subtitle}>
            Configure memory policies, retention schedules, and local-first privacy parameters
          </p>
        </div>
      </header>

      <form onSubmit={handleSave} className={styles.formLayout}>
        {/* Card 1: Memory Curation Policies */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Memory Curation Policies</h2>
          <p className={styles.cardDesc}>
            Control quality gates for newly distilled skills and decay intervals for aging guidelines.
          </p>

          <div className={styles.formGroup}>
            <label className={styles.label}>Quarantine Hold Period (Hours)</label>
            <input
              type="number"
              value={quarantineHours}
              onChange={(e) => setQuarantineHours(parseInt(e.target.value) || 24)}
              className={styles.input}
              min={1}
            />
            <span className={styles.helpText}>Time new memory items wait in quarantine for verification.</span>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>
              Minimum Quality Threshold: <span className={styles.valNum}>{minQualityScore}</span>
            </label>
            <input
              type="range"
              min="0.5"
              max="0.95"
              step="0.05"
              value={minQualityScore}
              onChange={(e) => setMinQualityScore(parseFloat(e.target.value))}
              className={styles.slider}
            />
            <span className={styles.helpText}>Minimum attribution quality required to bypass quarantine hold.</span>
          </div>

          <div className={styles.checkboxGroup}>
            <input
              type="checkbox"
              id="autoDecay"
              checked={autoDecay}
              onChange={(e) => setAutoDecay(e.target.checked)}
              className={styles.checkbox}
            />
            <label htmlFor="autoDecay" className={styles.checkboxLabel}>
              Enable automatic retention decay (-0.05 confidence per week without hits)
            </label>
          </div>
        </section>

        {/* Card 2: Privacy & Redaction */}
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Privacy & PII Redaction</h2>
          <p className={styles.cardDesc}>
            Configure PII scrubbing variables and restrict telemetry behavior to ensure local compliance.
          </p>

          <div className={styles.checkboxGroup}>
            <input
              type="checkbox"
              id="localOnly"
              checked={localOnly}
              onChange={(e) => setLocalOnly(e.target.checked)}
              className={styles.checkbox}
            />
            <label htmlFor="localOnly" className={styles.checkboxLabel}>
              Strict Local-First Mode (Never transmit traces outside localhost sqlite store)
            </label>
          </div>

          <div className={styles.checkboxGroup}>
            <input
              type="checkbox"
              id="piiScrubbing"
              checked={piiScrubbing}
              onChange={(e) => setPiiScrubbing(e.target.checked)}
              className={styles.checkbox}
            />
            <label htmlFor="piiScrubbing" className={styles.checkboxLabel}>
              Enable automatic PII scrubbing on distilled trace content
            </label>
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>PII Entities to Scrub (Comma separated)</label>
            <input
              type="text"
              value={redactedTags}
              onChange={(e) => setRedactedTags(e.target.value)}
              className={styles.input}
              disabled={!piiScrubbing}
            />
            <span className={styles.helpText}>Regular expression matches for these tags will be replaced with [REDACTED].</span>
          </div>
        </section>

        {/* Card 3: Action Actions */}
        <div className={styles.actionsBar}>
          <Button variant="primary" type="submit" loading={saving}>
            Save Configuration
          </Button>
        </div>
      </form>
    </div>
  );
};
export default Settings;
