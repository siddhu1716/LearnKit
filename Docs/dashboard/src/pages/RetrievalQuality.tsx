import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import type { DashboardMetrics, CrowdedOutRecord } from '../types';
import styles from './RetrievalQuality.module.css';

export const RetrievalQuality: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [crowdedOut, setCrowdedOut] = useState<CrowdedOutRecord[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Slider state
  const [lambda, setLambda] = useState<number>(0.70);
  const [savingConfig, setSavingConfig] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [m, c] = await Promise.all([
        client.getMetrics(),
        client.getCrowdedOutRecords(),
      ]);
      setMetrics(m);
      setLambda(m.retrieval.diversityLambda);
      setCrowdedOut(c);
    } catch (e) {
      console.error('Error fetching quality metrics:', e);
      toast('Failed to load quality metrics', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleApplyLambda = async () => {
    try {
      setSavingConfig(true);
      await client.updateDiversityConfig(lambda);
      toast(`Diversity lambda updated to ${lambda}`, 'success');
      // Refresh metrics
      const m = await client.getMetrics();
      setMetrics(m);
    } catch (e) {
      toast('Failed to save diversity lambda', 'error');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleResetLambda = () => {
    if (metrics) {
      setLambda(metrics.retrieval.diversityLambda);
    }
  };

  const handleConsolidate = async (id: string, competitorId: string) => {
    try {
      toast(`Consolidating record ${id} with competitor ${competitorId}...`, 'info');
      // Remove crowded out record
      await client.deleteRecord(id);
      // Refresh crowded out list and metrics
      const c = await client.getCrowdedOutRecords();
      setCrowdedOut(c.filter((r) => r.id !== id));
      toast('Records consolidated successfully', 'success');
    } catch (e) {
      toast('Failed to consolidate records', 'error');
    }
  };

  if (loading || !metrics) {
    return (
      <div className={styles.loadingContainer}>
        <SkeletonLoader height="40px" width="300px" />
        <div className={styles.topMetricsGrid}>
          <SkeletonLoader height="140px" />
          <SkeletonLoader height="140px" />
          <SkeletonLoader height="140px" />
        </div>
        <SkeletonLoader height="180px" />
        <SkeletonLoader height="240px" />
      </div>
    );
  }

  const budgetUsedPercent = Math.round(
    (metrics.retrieval.avgRecordsInjected / metrics.retrieval.maxRecords) * 100
  );

  return (
    <div className={styles.quality}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Retrieval Quality & Diversity</h1>
          <p className={styles.subtitle}>
            Monitor context injection utilization, Jaccard redundancy, and MMR diversity parameters
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchData}>
          Refresh ↻
        </button>
      </header>

      {/* Top Cards: Context utilization, Redundancy, Inference mix */}
      <section className={styles.topMetricsGrid}>
        {/* Context Utilization */}
        <div className={styles.card}>
          <h2 className={styles.cardLabel}>Context Utilization</h2>
          <div className={styles.cardValGroup}>
            <div className={styles.cardVal}>
              {metrics.retrieval.avgRecordsInjected.toFixed(1)} / {metrics.retrieval.maxRecords}
              <span className={styles.unit}>records</span>
            </div>
            <div className={styles.cardSubVal}>
              ~{metrics.retrieval.avgTokensInjected} / {metrics.retrieval.maxTokens} tokens
            </div>
          </div>
          <div className={styles.progressWrap}>
            <div className={styles.progressBar} style={{ width: `${budgetUsedPercent}%` }} />
            <span className={styles.progressText}>{budgetUsedPercent}% budget used</span>
          </div>
        </div>

        {/* Redundancy Jaccard */}
        <div className={styles.card}>
          <h2 className={styles.cardLabel}>Redundancy (Avg Pairwise Jaccard)</h2>
          <div className={styles.cardValGroup}>
            <div className={styles.cardVal}>
              {metrics.retrieval.avgRedundancy.toFixed(2)}
              <span className={`${styles.statusBadge} ${styles.lowRedundancy}`}>🟢 low</span>
            </div>
            <div className={styles.cardSubVal}>
              Lower redundancy = more diverse & complementary info injected.
            </div>
          </div>
          <div className={styles.helperText}>
            Target: &lt; 0.25 to prevent repeating duplicate guidelines.
          </div>
        </div>

        {/* Inference Mode Mix */}
        <div className={styles.card}>
          <h2 className={styles.cardLabel}>Inference Mode Mix</h2>
          <div className={styles.mixList}>
            <div className={styles.mixRow}>
              <div className={styles.mixLabelRow}>
                <span className={styles.mixDot} style={{ backgroundColor: '#00ff88' }} />
                <span>Prescriptive (High Conf Skills)</span>
              </div>
              <span className={styles.mixVal}>{Math.round(metrics.inferenceModeMix.prescriptive * 100)}%</span>
            </div>
            <div className={styles.mixRow}>
              <div className={styles.mixLabelRow}>
                <span className={styles.mixDot} style={{ backgroundColor: '#f59e0b' }} />
                <span>Guided (Scaffolds)</span>
              </div>
              <span className={styles.mixVal}>{Math.round(metrics.inferenceModeMix.guided * 100)}%</span>
            </div>
            <div className={styles.mixRow}>
              <div className={styles.mixLabelRow}>
                <span className={styles.mixDot} style={{ backgroundColor: '#a78bfa' }} />
                <span>Exploratory (Full CoT)</span>
              </div>
              <span className={styles.mixVal}>{Math.round(metrics.inferenceModeMix.exploratory * 100)}%</span>
            </div>
          </div>
        </div>
      </section>

      {/* Diversity Lambda Slider */}
      <section className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>Diversity Control (router.diversity_lambda)</h2>
        <p className={styles.sectionDesc}>
          Controls the trade-off between semantic relevance and diversity (MMR). Adjusting this affects FUTURE retrievals only; it never rewrites stored records.
        </p>

        <div className={styles.sliderContainer}>
          <div className={styles.sliderLabels}>
            <span>Pure Diversity (0.0)</span>
            <span className={styles.currentLambda}>λ = {lambda.toFixed(2)} {lambda === metrics.retrieval.diversityLambda ? '(Active)' : '(Unsaved)'}</span>
            <span>Pure Relevance (1.0)</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="1.0"
            step="0.05"
            value={lambda}
            onChange={(e) => setLambda(parseFloat(e.target.value))}
            className={styles.slider}
            aria-label="Diversity lambda slider"
          />
          <div className={styles.sliderDetails}>
            {lambda === 1.0 ? (
              <span className={styles.warnText}>⚠️ Lambda=1.0: Near-duplicate guidelines will stack up and consume token space.</span>
            ) : lambda < 0.3 ? (
              <span className={styles.warnText}>⚠️ Low Lambda: Highly diverse records are injected, but they may be less relevant to the exact task query.</span>
            ) : (
              <span className={styles.successText}>🟢 Recommended range (0.6 - 0.8): Perfect balance of relevance and coverage.</span>
            )}
          </div>
        </div>

        <div className={styles.actionRow}>
          <Button variant="ghost" onClick={handleResetLambda} disabled={lambda === metrics.retrieval.diversityLambda}>
            Reset
          </Button>
          <Button variant="primary" onClick={handleApplyLambda} loading={savingConfig}>
            Apply Changes
          </Button>
        </div>
      </section>

      {/* Crowded Out Records */}
      <section className={styles.sectionCard}>
        <h2 className={styles.sectionTitle}>Most-Crowded-Out Records</h2>
        <p className={styles.sectionDesc}>
          High-relevance records that were excluded by MMR diversity re-ranking because they duplicate already-admitted content. Consider consolidating or merging these.
        </p>

        <div className={styles.crowdedList}>
          {crowdedOut.map((item) => (
            <div key={item.id} className={styles.crowdedItem}>
              <div className={styles.crowdedLeft}>
                <div className={styles.crowdedMeta}>
                  <Badge variant="neutral">{item.id}</Badge>
                  <span className={styles.crowdedScores}>
                    Relevance: <strong>{Math.round(item.relevance * 100)}%</strong> | Overlap: <strong>{Math.round(item.overlap * 100)}%</strong> w/ {item.competitorId}
                  </span>
                </div>
                <div className={styles.crowdedSnippet}>{item.snippet}</div>
              </div>
              <div className={styles.crowdedActions}>
                <Button variant="secondary" size="sm" onClick={() => navigate(`/memory?type=all`)}>
                  View
                </Button>
                <Button variant="accent" size="sm" onClick={() => handleConsolidate(item.id, item.competitorId)}>
                  Consolidate with {item.competitorId}
                </Button>
              </div>
            </div>
          ))}
          {crowdedOut.length === 0 && (
            <div className={styles.noCrowded}>
              🎉 No records are currently being crowded out. Diversity is perfectly configured.
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
