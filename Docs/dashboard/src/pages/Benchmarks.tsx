import React, { useEffect, useState } from 'react';
import { client } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { Gauge, TrendingDown, CheckCircle2, XCircle, ChevronRight, ChevronDown } from '../components/icons';
import type { BenchmarkMatrix, BenchmarkModelRow, BenchmarkTasks } from '../types';
import styles from './Benchmarks.module.css';

const fmtPct = (n?: number) => (n == null ? '—' : `−${n}%`);

interface PerTaskRow {
  index?: number;
  arm?: string;
  task?: string;
  llm_calls?: number;
  tool_calls?: number;
  success?: boolean;
  replayed?: boolean;
  guided?: boolean;
}

/** Per-task (react) and per-round (evolution) learning flow, when the run
 *  captured it. Real data only — nothing is shown if the run didn't emit it. */
const TaskFlow: React.FC<{ tasks?: BenchmarkTasks }> = ({ tasks }) => {
  const react = tasks?.react_live as { per_task?: PerTaskRow[] } | undefined;
  const evo = tasks?.evolution_live as { per_round?: Array<Record<string, unknown>> } | undefined;
  const perTask = react?.per_task;
  const perRound = evo?.per_round;

  if (!perTask?.length && !perRound?.length) {
    return (
      <div className={styles.flowHint}>
        Per-task flow appears here after a run captures it — re-run
        <code>python -m benchmarks.make_results --run</code> then
        <code>python -m benchmarks.seed_dashboard</code>.
      </div>
    );
  }

  return (
    <div className={styles.flow}>
      {perTask?.length ? (
        <div className={styles.flowBlock}>
          <div className={styles.flowTitle}>react_live — per-task flow</div>
          <div className={styles.flowTable}>
            <div className={`${styles.flowRow} ${styles.flowHead}`}>
              <span>#</span><span>arm</span><span>task</span><span>LLM</span><span>tools</span><span>state</span>
            </div>
            {perTask.map((t, i) => (
              <div className={styles.flowRow} key={i}>
                <span>{t.index ?? i}</span>
                <span>{t.arm}</span>
                <span className={styles.flowTask} title={t.task}>{t.task}</span>
                <span className={styles.mono}>{t.llm_calls}</span>
                <span className={styles.mono}>{t.tool_calls}</span>
                <span>
                  {t.replayed ? '♻️ replayed' : t.guided ? '🧭 guided' : t.arm === 'cold' ? '🧊 cold' : '•'}
                  {t.success === false ? ' ✗' : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {perRound?.length ? (
        <div className={styles.flowBlock}>
          <div className={styles.flowTitle}>evolution_live — per-round durability</div>
          <div className={styles.flowTable}>
            <div className={`${styles.flowRow} ${styles.flowHeadRound}`}>
              <span>round</span><span>cold LLM</span><span>warm LLM</span><span>warm success</span><span>replayed</span>
            </div>
            {perRound.map((r, i) => {
              const cold = (r.cold ?? {}) as Record<string, number>;
              const warm = (r.warmed ?? {}) as Record<string, number>;
              return (
                <div className={`${styles.flowRow} ${styles.flowRowRound}`} key={i}>
                  <span>{String((r.round as number) ?? i)}</span>
                  <span className={styles.mono}>{cold.llm_calls ?? '—'}</span>
                  <span className={styles.mono}>{warm.llm_calls ?? '—'}</span>
                  <span className={styles.mono}>{warm.successes ?? '—'}</span>
                  <span className={styles.mono}>{warm.replayed ?? 0}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
};

/** One expandable row = one model, with per-task drill-down. */
const ModelRow: React.FC<{ row: BenchmarkModelRow }> = ({ row }) => {
  const [open, setOpen] = useState(false);
  const pass = row.gate.pass;
  const rl = row.tasks?.react_live as Record<string, number | boolean> | undefined;
  const ev = row.tasks?.evolution_live as Record<string, number | boolean> | undefined;
  const ij = row.tasks?.injection_ablation as Record<string, number | boolean> | undefined;

  return (
    <>
      <div
        className={`${styles.row} ${open ? styles.rowOpen : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setOpen((o) => !o)}
      >
        <div className={styles.cellModel}>
          <span className={styles.chevron}>{open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</span>
          <div>
            <div className={styles.modelName}>{row.display}</div>
            <div className={styles.modelId}>{row.model}</div>
          </div>
        </div>
        <div className={styles.cell}>
          <Badge variant={pass ? 'success' : 'error'}>
            {pass ? '✓ PASS' : '✗ FAIL'}
          </Badge>
        </div>
        <div className={`${styles.cell} ${styles.good}`}>+{row.quality_lift}</div>
        <div className={styles.cell}>
          <span className={styles.mono}>{row.react.cold_llm_calls} → {row.react.warmed_llm_calls}</span>
          <span className={styles.reduction}>{fmtPct(row.react.reduction_pct)}</span>
        </div>
        <div className={styles.cell}>
          <span className={styles.mono}>{row.evolution.cold_llm_calls} → {row.evolution.warmed_llm_calls}</span>
          <span className={styles.reduction}>{fmtPct(row.evolution.reduction_pct)}</span>
        </div>
        <div className={styles.cell}>
          <span className={styles.mono}>{row.combined_llm_calls.cold} → {row.combined_llm_calls.warmed}</span>
          <span className={styles.reduction}>{fmtPct(row.combined_llm_calls.reduction_pct)}</span>
        </div>
      </div>

      {open && (
        <div className={styles.detail}>
          <div className={styles.taskGrid}>
            {/* react_live */}
            <div className={styles.taskCard}>
              <div className={styles.taskTitle}>react_live<span>single-shot tool-call reduction</span></div>
              <dl className={styles.kv}>
                <div><dt>Success (warm)</dt><dd>{row.react.success}</dd></div>
                <div><dt>LLM calls</dt><dd className={styles.mono}>{row.react.cold_llm_calls} → {row.react.warmed_llm_calls}</dd></div>
                <div><dt>Reduction</dt><dd className={styles.good}>{fmtPct(row.react.reduction_pct)}</dd></div>
                {rl && 'cold_tools_per_task' in rl && (
                  <div><dt>Tools / task</dt><dd className={styles.mono}>{String(rl.cold_tools_per_task)} → {String(rl.warmed_tools_per_task)}</dd></div>
                )}
              </dl>
            </div>

            {/* evolution_live */}
            <div className={styles.taskCard}>
              <div className={styles.taskTitle}>evolution_live<span>multi-round durability</span></div>
              <dl className={styles.kv}>
                <div><dt>Success (warm)</dt><dd>{row.evolution.success}</dd></div>
                <div><dt>LLM calls</dt><dd className={styles.mono}>{row.evolution.cold_llm_calls} → {row.evolution.warmed_llm_calls}</dd></div>
                <div><dt>Reduction</dt><dd className={styles.good}>{fmtPct(row.evolution.reduction_pct)}</dd></div>
                <div><dt>Evolved</dt><dd>{row.evolution.evolved ? 'yes' : 'no'}</dd></div>
                {ev && 'cold_tool_calls' in ev && (
                  <div><dt>Tool calls</dt><dd className={styles.mono}>{String(ev.cold_tool_calls)} → {String(ev.warmed_tool_calls)}</dd></div>
                )}
              </dl>
            </div>

            {/* injection_ablation */}
            <div className={styles.taskCard}>
              <div className={styles.taskTitle}>injection_ablation<span>quality lift (the gate)</span></div>
              <dl className={styles.kv}>
                <div><dt>Procedure score</dt><dd className={styles.mono}>{row.injection.procedure_avg_score} / 3</dd></div>
                <div><dt>Playbook score</dt><dd className={styles.mono}>{row.injection.playbook_avg_score} / 3</dd></div>
                <div><dt>Quality lift</dt><dd className={styles.good}>+{row.quality_lift}</dd></div>
                <div><dt>pass^k (full)</dt><dd>{row.injection.pass_k_full}</dd></div>
                {ij && 'timed_out' in ij && (
                  <div><dt>Timed out</dt><dd>{ij.timed_out ? 'yes' : 'no'}</dd></div>
                )}
              </dl>
            </div>
          </div>
          <div className={styles.provenance}>
            Source: <code>{row.provenance.source}</code>
            {row.run_generated_at ? ` · run ${new Date(row.run_generated_at).toLocaleString()}` : ''}
            {' · endpoint '}<code>{row.base_url}</code>
          </div>

          <TaskFlow tasks={row.tasks} />
        </div>
      )}
    </>
  );
};

export const Benchmarks: React.FC = () => {
  const [data, setData] = useState<BenchmarkMatrix | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await client.getBenchmarks());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className={styles.page}>
        <SkeletonLoader width="280px" height="40px" />
        <SkeletonLoader height="120px" />
        <SkeletonLoader height="320px" />
      </div>
    );
  }

  if (!data || !data.available) {
    return (
      <div className={styles.page}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Benchmarks</h1>
            <p className={styles.subtitle}>Reproducible agentic benchmark matrix</p>
          </div>
        </header>
        <div className={styles.emptyState}>
          <XCircle size={28} />
          <p>{data?.reason ?? 'Benchmark results are unavailable.'}</p>
          <pre className={styles.cmd}>python -m benchmarks.make_results</pre>
        </div>
      </div>
    );
  }

  const s = data.summary;
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Benchmarks</h1>
          <p className={styles.subtitle}>
            Reproducible agentic matrix — derived from committed raw runs, not mock data
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchData}>Refresh ↻</button>
      </header>

      {/* Summary strip */}
      <section className={styles.summaryStrip}>
        <div className={styles.summaryCard}>
          <span className={styles.summaryValue}>
            <CheckCircle2 size={18} /> {s?.models_passing}/{s?.models_total}
          </span>
          <span className={styles.summaryLabel}>Models PASS the {data.gate?.metric} ≥ {data.gate?.threshold} gate</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={`${styles.summaryValue} ${styles.good}`}>
            <Gauge size={18} /> +{s?.best_quality_lift}
          </span>
          <span className={styles.summaryLabel}>Best quality lift ({s?.best_quality_lift_model})</span>
        </div>
        <div className={styles.summaryCard}>
          <span className={`${styles.summaryValue} ${styles.good}`}>
            <TrendingDown size={18} /> {fmtPct(s?.pooled_llm_call_reduction_pct)}
          </span>
          <span className={styles.summaryLabel}>Pooled LLM-call reduction across passing models</span>
        </div>
      </section>

      {/* Matrix table */}
      <section className={styles.tableCard}>
        <div className={`${styles.row} ${styles.tableHead}`}>
          <div className={styles.cellModel}>Model</div>
          <div className={styles.cell}>Gate</div>
          <div className={styles.cell}>Quality lift</div>
          <div className={styles.cell}>react (cold→warm)</div>
          <div className={styles.cell}>evolution (cold→warm)</div>
          <div className={styles.cell}>combined</div>
        </div>
        {data.models.map((m) => (
          <ModelRow key={m.name} row={m} />
        ))}
      </section>

      {/* Reproduce */}
      <section className={styles.reproduce}>
        <h2>Reproduce</h2>
        <p>Derive this table offline from the committed raw runs (no GPU needed):</p>
        <pre className={styles.cmd}>python -m benchmarks.make_results</pre>
        <p>Run the matrix against your own model endpoints, then re-derive:</p>
        <pre className={styles.cmd}>{data.reproduce_command}</pre>
        {data.run_config && (
          <p className={styles.runConfig}>
            Run config: trials={data.run_config.trials}, k={data.run_config.k}, seed={data.run_config.seed},
            temperature={data.run_config.temperature}, max_output_tokens={data.run_config.max_output_tokens}.
          </p>
        )}
      </section>
    </div>
  );
};
