import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import type { TraceDetail } from '../types';
import styles from './TracePlayback.module.css';

export const TracePlayback: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Collapse toggle states
  const [retrievalOpen, setRetrievalOpen] = useState(true);
  const [reasoningOpen, setReasoningOpen] = useState(true);

  // Keep track of feedback clicks
  const [reinforcedIds, setReinforcedIds] = useState<Record<string, boolean>>({});
  const [demotedIds, setDemotedIds] = useState<Record<string, boolean>>({});

  const fetchTrace = async () => {
    if (!taskId) return;
    try {
      setLoading(true);
      const data = await client.getTraceDetail(taskId);
      setTrace(data);
    } catch (e) {
      console.error('Error fetching trace detail:', e);
      toast('Failed to load trace playback details', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTrace();
  }, [taskId]);

  const handleReinforce = async (recordId: string) => {
    if (!taskId || reinforcedIds[recordId]) return;
    try {
      await client.reinforceRecord(recordId, taskId);
      setReinforcedIds((prev) => ({ ...prev, [recordId]: true }));
      toast(`Successfully reinforced memory ${recordId}`, 'success');
    } catch (e) {
      toast('Failed to reinforce memory record', 'error');
    }
  };

  const handleDemote = async (recordId: string) => {
    if (!taskId || demotedIds[recordId]) return;
    try {
      await client.demoteRecord(recordId, taskId);
      setDemotedIds((prev) => ({ ...prev, [recordId]: true }));
      toast(`Demoted memory record ${recordId}`, 'warn');
    } catch (e) {
      toast('Failed to demote memory record', 'error');
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <SkeletonLoader height="40px" width="300px" />
        <SkeletonLoader height="120px" />
        <SkeletonLoader height="180px" />
        <SkeletonLoader height="180px" />
        <SkeletonLoader height="120px" />
      </div>
    );
  }

  if (!trace) {
    return (
      <div className={styles.errorContainer}>
        <h2>Trace Not Found</h2>
        <p>The trace log for task #{taskId} could not be retrieved.</p>
        <Button variant="primary" onClick={() => navigate('/tasks')}>
          Back to Task History
        </Button>
      </div>
    );
  }

  return (
    <div className={styles.tracePlayback}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.backBtn} onClick={() => navigate('/tasks')} aria-label="Go back to tasks list">
            ← Tasks
          </button>
          <div>
            <h1 className={styles.title}>
              Task Run #{trace.taskId}
            </h1>
            <p className={styles.subtitle}>
              Playback of retrieval weight, system prompts, reasoning steps, and model attribution outcomes
            </p>
          </div>
        </div>
        <div className={styles.headerRight}>
          <Badge variant={trace.score >= 4.0 ? 'success' : 'error'}>
            {trace.score >= 4.0 ? 'Success' : 'Failure'}
          </Badge>
          <span className={styles.headerScore}>Score: {trace.score.toFixed(1)} / 5.0</span>
        </div>
      </header>

      {/* Timeline Section */}
      <div className={styles.timeline}>
        {/* Step 1: Input Query */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineLine} />
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--secondary)' }}>1</div>
          <div className={styles.timelineContentCard}>
            <h3 className={styles.cardTitle}>Input query / parameters</h3>
            <div className={styles.inputBox}>
              {trace.input}
            </div>
          </div>
        </div>

        {/* Step 2: Memory Retrieval */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineLine} />
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--accent)' }}>2</div>
          <div className={styles.timelineContentCard}>
            <div className={styles.cardHeaderToggle}>
              <h3 className={styles.cardTitle}>Memory Retrieval Details</h3>
              <button
                className={styles.toggleBtn}
                onClick={() => setRetrievalOpen(!retrievalOpen)}
                aria-expanded={retrievalOpen}
              >
                {retrievalOpen ? 'Collapse ▲' : 'Expand ▼'}
              </button>
            </div>
            
            {retrievalOpen && (
              <div className={styles.cardDetails}>
                <div className={styles.retrievalSummaryRow}>
                  <div>
                    <span className={styles.metaLabel}>Inference Mode:</span>
                    <Badge variant={trace.inferenceMode === 'prescriptive' ? 'accent' : trace.inferenceMode === 'guided' ? 'info' : 'neutral'}>
                      {trace.inferenceMode.toUpperCase()}
                    </Badge>
                  </div>
                  <div>
                    <span className={styles.metaLabel}>MMR Lambda:</span>
                    <span className={styles.mono}>{trace.memoryRetrieval.budget.diversityLambda.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className={styles.metaLabel}>Token Budget:</span>
                    <span className={styles.mono}>
                      {trace.memoryRetrieval.budget.tokensUsed} / {trace.memoryRetrieval.budget.maxTokens} tok
                    </span>
                  </div>
                  <div>
                    <span className={styles.metaLabel}>Redundancy Jaccard:</span>
                    <span className={styles.mono} style={{ color: 'var(--success)' }}>
                      {trace.memoryRetrieval.budget.redundancy.toFixed(2)} (low)
                    </span>
                  </div>
                </div>

                <div className={styles.matchesTableWrap}>
                  <h4 className={styles.subTitle}>Retrieved Matches</h4>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Record ID</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Relevance Score</th>
                        <th>Retrieval Key Reason</th>
                        <th>MMR Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {trace.memoryRetrieval.matches.map((m) => (
                        <tr key={m.recordId} className={m.droppedByMmr ? styles.droppedRow : undefined}>
                          <td className={styles.mono}>{m.recordId}</td>
                          <td>
                            <Badge variant={m.type === 'skill' ? 'accent' : m.type === 'failure' ? 'error' : 'info'}>
                              {m.type}
                            </Badge>
                          </td>
                          <td className={styles.mono}>{m.confidence.toFixed(2)}</td>
                          <td className={styles.mono}>{m.score.toFixed(2)}</td>
                          <td className={styles.reasonCol}>{m.reason}</td>
                          <td>
                            {m.droppedByMmr ? (
                              <span className={styles.droppedText}>Dropped (MMR Redundancy)</span>
                            ) : (
                              <span className={styles.admittedText}>Injected</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Step 3: Prompt Injection */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineLine} />
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--accent)' }}>3</div>
          <div className={styles.timelineContentCard}>
            <h3 className={styles.cardTitle}>Injected Context</h3>
            <p className={styles.cardDesc}>
              The following distilled guidelines were automatically formatted and composed into the system instructions:
            </p>
            <div className={styles.contextBox}>
              <div className={styles.contextHeader}>System memory guidelines:</div>
              <ul className={styles.contextList}>
                {trace.memoryRetrieval.matches
                  .filter((m) => !m.droppedByMmr)
                  .map((m) => (
                    <li key={m.recordId} className={styles.contextListItem}>
                      <strong>[{m.type.toUpperCase()} - {m.recordId}]:</strong> For {m.reason.toLowerCase()}, verify that you apply optimal logic.
                    </li>
                  ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Step 4: Model Reasoning */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineLine} />
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--secondary)' }}>4</div>
          <div className={styles.timelineContentCard}>
            <div className={styles.cardHeaderToggle}>
              <h3 className={styles.cardTitle}>Model Reasoning Trace</h3>
              <button
                className={styles.toggleBtn}
                onClick={() => setReasoningOpen(!reasoningOpen)}
                aria-expanded={reasoningOpen}
              >
                {reasoningOpen ? 'Collapse ▲' : 'Expand ▼'}
              </button>
            </div>

            {reasoningOpen && (
              <div className={styles.cardDetails}>
                {trace.reasoning.attempts.map((attempt, index) => (
                  <div key={index} className={styles.attemptBox}>
                    <div className={styles.attemptHeader}>Chain-of-Thought (CoT) Attempt #{index + 1}:</div>
                    <pre className={styles.preBlock}>
                      <code>{attempt.response}</code>
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Step 5: Output & Evaluation */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineLine} />
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--success)' }}>5</div>
          <div className={styles.timelineContentCard}>
            <h3 className={styles.cardTitle}>Ground Truth Alignment</h3>
            <div className={styles.outcomesGrid}>
              <div>
                <span className={styles.metaLabel}>Final Output:</span>
                <div className={styles.codeSnippet}>{trace.output}</div>
              </div>
              <div>
                <span className={styles.metaLabel}>Expected Output:</span>
                <div className={styles.codeSnippet}>{trace.expected}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 6: Memory Attribution */}
        <div className={styles.timelineItem}>
          <div className={styles.timelineMarker} style={{ backgroundColor: 'var(--accent)' }}>6</div>
          <div className={styles.timelineContentCard}>
            <h3 className={styles.cardTitle}>Record Attribution & Reinforcement Feedback</h3>
            <p className={styles.cardDesc}>
              LearnKit attributes the task score to injected records. Submit human feedback to manually refine confidence values in the store.
            </p>

            <div className={styles.attributionList}>
              {trace.attribution.map((attr) => (
                <div key={attr.recordId} className={styles.attributionRow}>
                  <div className={styles.attributionInfo}>
                    <Badge variant={attr.primary ? 'accent' : 'neutral'}>
                      {attr.primary ? 'PRIMARY' : 'SECONDARY'}
                    </Badge>
                    <span className={styles.mono}>{attr.recordId}</span>
                    <span className={styles.attrStats}>
                      Reuse count: <strong>{attr.reuseCount}</strong>
                    </span>
                  </div>
                  <div className={styles.attributionFeedback}>
                    <Button
                      variant={reinforcedIds[attr.recordId] ? 'primary' : 'secondary'}
                      size="sm"
                      onClick={() => handleReinforce(attr.recordId)}
                      disabled={reinforcedIds[attr.recordId] || demotedIds[attr.recordId]}
                    >
                      {reinforcedIds[attr.recordId] ? 'Reinforced' : 'Reinforce'}
                    </Button>
                    <Button
                      variant={demotedIds[attr.recordId] ? 'danger' : 'secondary'}
                      size="sm"
                      onClick={() => handleDemote(attr.recordId)}
                      disabled={reinforcedIds[attr.recordId] || demotedIds[attr.recordId]}
                    >
                      {demotedIds[attr.recordId] ? 'Demoted' : 'Demote'}
                    </Button>
                  </div>
                </div>
              ))}
              {trace.attribution.length === 0 && (
                <span className={styles.noAttribution}>No active record attributions calculated for this run.</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
