import React, { useEffect, useState } from 'react';
import { client } from '../api/client';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import { AlertTriangle, Inbox } from '../components/icons';
import styles from './Playground.module.css';

interface PlaygroundDomain {
  key: string;
  label: string;
  example: string;
  record_count: number;
}

export const Playground: React.FC = () => {
  const [domains, setDomains] = useState<PlaygroundDomain[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>('');
  const [taskInput, setTaskInput] = useState<string>('');
  const [loadingDomains, setLoadingDomains] = useState(true);
  const [inspecting, setInspecting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const fetchDomains = async () => {
    try {
      setLoadingDomains(true);
      const data = await client.getPlaygroundDomains();
      setDomains(data);
      if (data.length > 0) {
        setSelectedDomain(data[0].key);
        setTaskInput(data[0].example);
      }
    } catch (e) {
      toast('Failed to load playground domains', 'error');
    } finally {
      setLoadingDomains(false);
    }
  };

  useEffect(() => {
    fetchDomains();
  }, []);

  const handleDomainChange = (key: string) => {
    setSelectedDomain(key);
    const dom = domains.find((d) => d.key === key);
    if (dom) {
      setTaskInput(dom.example);
    }
  };

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskInput.trim()) {
      toast('Please enter a query prompt', 'warn');
      return;
    }

    try {
      setInspecting(true);
      setResult(null);
      const res = await client.inspectPlaygroundTask(taskInput, selectedDomain);
      setResult(res);
      toast('Inspection completed successfully', 'success');
    } catch (e) {
      toast('Inspection query failed', 'error');
    } finally {
      setInspecting(false);
    }
  };

  return (
    <div className={styles.playground}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Playground</h1>
          <p className={styles.subtitle}>
            Submit tasks to see real-time classification, memory retrieval, and system context composition
          </p>
        </div>
      </header>

      <div className={styles.layout}>
        {/* Left column: input form */}
        <section className={styles.inputCard}>
          <h2 className={styles.cardTitle}>Run Inspection</h2>
          <form onSubmit={handleInspect} className={styles.form}>
            <div className={styles.formGroup}>
              <label className={styles.label}>Select Domain Store</label>
              {loadingDomains ? (
                <SkeletonLoader height="38px" />
              ) : (
                <select
                  value={selectedDomain}
                  onChange={(e) => handleDomainChange(e.target.value)}
                  className={styles.select}
                  aria-label="Select domain store"
                >
                  {domains.map((d) => (
                    <option key={d.key} value={d.key}>
                      {d.label} ({d.record_count} records)
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className={styles.formGroup}>
              <label className={styles.label}>Query Task / Prompt</label>
              <textarea
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                placeholder="Enter a task to run through the memory router..."
                className={styles.textarea}
                rows={6}
                required
              />
            </div>

            <Button variant="primary" type="submit" loading={inspecting}>
              Inspect Retrieval
            </Button>
          </form>
        </section>

        {/* Right column: inspect results */}
        <section className={styles.resultsColumn}>
          {inspecting ? (
            <div className={styles.loadingResult}>
              <SkeletonLoader height="40px" width="180px" />
              <SkeletonLoader height="120px" />
              <SkeletonLoader height="200px" />
            </div>
          ) : result ? (
            <div className={styles.resultDetails}>
              {/* Classification */}
              <div className={styles.resultSection}>
                <h3 className={styles.resultTitle}>1. Task Classification</h3>
                <div className={styles.classCard}>
                  <div className={styles.classRow}>
                    <span className={styles.metaLabel}>Determined Task Type:</span>
                    <Badge variant="accent">{result.classification.task_type}</Badge>
                  </div>
                  <div className={styles.classRow}>
                    <span className={styles.metaLabel}>Complexity:</span>
                    <Badge variant="neutral">{result.classification.complexity}</Badge>
                  </div>
                  <div className={styles.classRow}>
                    <span className={styles.metaLabel}>Identified Domains:</span>
                    <div className={styles.tagGroup}>
                      {Object.entries(result.classification.domains).map(([dom, weight]: any) => (
                        <Badge key={dom} variant="info">
                          {dom} ({Math.round(weight * 100)}%)
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Inference Mode */}
              <div className={styles.resultSection}>
                <h3 className={styles.resultTitle}>2. Memory Router Action</h3>
                <div className={styles.routerCard}>
                  <span className={styles.metaLabel}>Selected Inference Mode:</span>
                  <div className={styles.modeVal}>
                    <Badge variant={result.inference_mode === 'prescriptive' ? 'accent' : result.inference_mode === 'guided' ? 'info' : 'neutral'}>
                      {result.inference_mode.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Retrieved Records */}
              <div className={styles.resultSection}>
                <h3 className={styles.resultTitle}>3. Admitted Memory Records</h3>
                <div className={styles.recordsList}>
                  {result.records.map((r: any) => (
                    <div key={r.id} className={styles.recordItem}>
                      <div className={styles.recordMeta}>
                        <Badge variant="neutral">{r.id}</Badge>
                        <Badge variant={r.type === 'skill' ? 'accent' : 'error'}>{r.type}</Badge>
                        <span className={styles.confidence}>Confidence: <strong>{r.confidence}</strong></span>
                      </div>
                      <div className={styles.snippet}>{r.snippet}</div>
                    </div>
                  ))}
                  {result.records.length === 0 && (
                    <div className={styles.noRecords}>
                      <AlertTriangle size={15} /> No memories retrieved for this query. System will fall back to cold reasoning.
                    </div>
                  )}
                </div>
              </div>

              {/* Formatted Context Block */}
              <div className={styles.resultSection}>
                <h3 className={styles.resultTitle}>4. Formatted Prompt Context</h3>
                <pre className={styles.contextPre}>
                  <code>{result.context}</code>
                </pre>
              </div>
            </div>
          ) : (
            <div className={styles.noResult}>
              <Inbox size={16} /> Submit a task query to view the compiled LearnKit system prompt outputs.
            </div>
          )}
        </section>
      </div>
    </div>
  );
};
export default Playground;
