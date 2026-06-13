import React, { useEffect, useState } from 'react';
import { client } from '../api/client';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import type { QuarantineRecord } from '../types';
import styles from './MemoryLifecycle.module.css';

export const MemoryLifecycle: React.FC = () => {
  const [quarantineRecords, setQuarantineRecords] = useState<QuarantineRecord[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Maintenance variables
  const [quarantineHours, setQuarantineHours] = useState<number>(24);
  const [decayActive, setDecayActive] = useState<boolean>(true);
  const [runningMaintenance, setRunningMaintenance] = useState<boolean>(false);
  const [maintenanceResult, setMaintenanceResult] = useState<{
    promoted: number;
    decayed: number;
    staled: number;
    purged: number;
  } | null>(null);

  const fetchQuarantine = async () => {
    try {
      setLoading(true);
      const data = await client.getQuarantineRecords();
      setQuarantineRecords(data);
    } catch (e) {
      console.error('Error fetching quarantine records:', e);
      toast('Failed to load quarantine queue', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuarantine();
  }, []);

  const handleRunMaintenance = async () => {
    try {
      setRunningMaintenance(true);
      setMaintenanceResult(null);
      
      const result = await client.runMaintenance({
        quarantineHours,
        decay: decayActive,
      });

      setMaintenanceResult(result);
      toast('Memory maintenance complete!', 'success');
      
      // Refresh quarantine records
      await fetchQuarantine();
    } catch (e) {
      toast('Failed to run memory maintenance', 'error');
    } finally {
      setRunningMaintenance(false);
    }
  };

  const handleManualPromote = async (id: string) => {
    try {
      toast(`Promoting record ${id} immediately...`, 'info');
      // Promote record by updating status to active
      await client.updateRecord(id, { status: 'active' });
      // Remove from local quarantine state
      setQuarantineRecords((prev) => prev.filter((r) => r.id !== id));
      toast('Record promoted to active status', 'success');
    } catch (e) {
      toast('Failed to promote record', 'error');
    }
  };

  return (
    <div className={styles.lifecycle}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Memory Lifecycle & Maintenance</h1>
          <p className={styles.subtitle}>
            Manage quarantine promotion schedules, trigger confidence decay policies, and run store cleanup routines
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchQuarantine}>
          Refresh ↻
        </button>
      </header>

      <div className={styles.layoutGrid}>
        {/* Left Column: Quarantine Queue */}
        <section className={styles.queueColumn}>
          <h2 className={styles.sectionTitle}>Quarantine Queue</h2>
          <p className={styles.sectionDesc}>
            Newly distilled skills/rules are quarantined for evaluation before promotion to active context. Failure records bypass quarantine and activate immediately.
          </p>

          <div className={styles.quarantineList}>
            {loading ? (
              <div className={styles.skeleton}>
                <SkeletonLoader height="100px" />
                <SkeletonLoader height="100px" />
              </div>
            ) : quarantineRecords.length === 0 ? (
              <div className={styles.emptyQueue}>
                ✨ Quarantine queue is empty. All current memory records are promoted.
              </div>
            ) : (
              quarantineRecords.map((q) => (
                <div key={q.id} className={styles.quarantineCard}>
                  <div className={styles.quarantineCardHeader}>
                    <div className={styles.quarantineCardMeta}>
                      <Badge variant="warn">{q.type.toUpperCase()}</Badge>
                      <span className={styles.quarantineId}>{q.id}</span>
                      <span className={styles.quarantineTime}>
                        Injected: {new Date(q.createdAt).toLocaleDateString()}
                      </span>
                    </div>
                    <Button variant="primary" size="sm" onClick={() => handleManualPromote(q.id)}>
                      Promote Now
                    </Button>
                  </div>
                  <div className={styles.quarantineContent}>{q.content}</div>
                  <div className={styles.quarantineFooter}>
                    Promotable after: <strong>{new Date(q.promotableAfter).toLocaleString()}</strong>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Right Column: Maintenance Panel */}
        <section className={styles.panelColumn}>
          <div className={styles.panelCard}>
            <h2 className={styles.sectionTitle}>Run Maintenance Loop</h2>
            <p className={styles.sectionDesc}>
              Manually trigger the core SDK curation process. This runs quarantine evaluation, increments confidence age, and purges low-performance stale memories.
            </p>

            <div className={styles.form}>
              <div className={styles.formGroup}>
                <label className={styles.label}>Quarantine Period (Hours)</label>
                <input
                  type="number"
                  value={quarantineHours}
                  onChange={(e) => setQuarantineHours(parseInt(e.target.value) || 24)}
                  className={styles.input}
                  min={1}
                />
              </div>

              <div className={styles.checkboxGroup}>
                <input
                  type="checkbox"
                  id="decayActive"
                  checked={decayActive}
                  onChange={(e) => setDecayActive(e.target.checked)}
                  className={styles.checkbox}
                />
                <label htmlFor="decayActive" className={styles.checkboxLabel}>
                  Decay active memories without usage (-0.05 confidence)
                </label>
              </div>

              <Button
                variant="primary"
                onClick={handleRunMaintenance}
                loading={runningMaintenance}
                className={styles.maintenanceBtn}
              >
                Run Curation Loop
              </Button>
            </div>

            {/* Results Output */}
            {maintenanceResult && (
              <div className={styles.resultsCard}>
                <h4 className={styles.resultsTitle}>Curation Results:</h4>
                <div className={styles.resultsGrid}>
                  <div className={styles.resultCell}>
                    <span className={styles.resultLabel}>Promoted to Active:</span>
                    <Badge variant="success">{maintenanceResult.promoted}</Badge>
                  </div>
                  <div className={styles.resultCell}>
                    <span className={styles.resultLabel}>Decayed Confidence:</span>
                    <Badge variant="info">{maintenanceResult.decayed}</Badge>
                  </div>
                  <div className={styles.resultCell}>
                    <span className={styles.resultLabel}>Staled (&lt; 0.3 conf):</span>
                    <Badge variant="warn">{maintenanceResult.staled}</Badge>
                  </div>
                  <div className={styles.resultCell}>
                    <span className={styles.resultLabel}>Purged/Deleted:</span>
                    <Badge variant="error">{maintenanceResult.purged}</Badge>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className={styles.policyCard}>
            <h3 className={styles.policyTitle}>Decay Policy Guidelines</h3>
            <p className={styles.policyText}>
              • Active records decay gradually when not retrieved to make room for newer, higher-quality trace patterns.
            </p>
            <p className={styles.policyText}>
              • Records whose confidence decays below <strong>0.30</strong> are classified as <strong>Stale</strong> and removed from the default context retrieval path.
            </p>
            <p className={styles.policyText}>
              • Stale records with excessive harm counts (&gt; 3) are automatically purged during the curation loop.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};
