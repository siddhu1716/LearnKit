import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { DataTable, Column } from '../components/ui/DataTable';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import { Search, RefreshCw } from '../components/icons';
import type { Task } from '../types';
import { useDashboardMode } from '../context/DashboardModeContext';
import styles from './TaskHistory.module.css';

const fmtTokens = (n?: number) => (n == null ? '—' : n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);
const fmtCost = (n?: number) => (n == null ? '—' : `$${n.toFixed(4)}`);
const fmtMs = (n?: number | null) => (n == null ? '—' : `${Math.round(n)} ms`);

export const TaskHistory: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const { mode } = useDashboardMode();
  const isAgent = mode === 'agent_learn';

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const data = await client.getTasks();
      setTasks(data);
    } catch (e) {
      console.error('Error fetching tasks:', e);
      toast('Failed to load task history', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
      const matchesSearch =
        searchQuery === '' ||
        t.input.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.armName.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesStatus && matchesSearch;
    });
  }, [tasks, statusFilter, searchQuery]);

  const handleRowClick = (row: Task) => {
    navigate(`/tasks/${row.id}`);
  };

  const columns: Column<Task>[] = [
    {
      key: 'id',
      label: 'ID',
      width: '11%',
      render: (v) => <span className={styles.monoId}>{String(v)}</span>,
    },
    {
      key: 'input',
      label: 'Query / Input Task',
      width: '24%',
      render: (v) => <span className={styles.inputVal} title={String(v)}>{String(v)}</span>,
    },
    {
      key: 'mode',
      label: 'Mode',
      width: '9%',
      render: (_v, row) => (
        <Badge variant={row.mode === 'agent_learn' ? 'accent' : 'info'}>
          {row.mode === 'agent_learn' ? 'Agent' : 'Learn'}
        </Badge>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      width: '9%',
      render: (v) => (
        <Badge variant={v === 'success' ? 'success' : 'error'}>
          {String(v).toUpperCase()}
        </Badge>
      ),
    },
    {
      key: 'score',
      label: 'Score',
      width: '8%',
      render: (v) => <span className={styles.monoId}>{Number(v).toFixed(1)} / 5.0</span>,
    },
    ...(isAgent
      ? ([
          {
            key: 'callsReduced',
            label: 'Calls ↓',
            width: '8%',
            render: (_v, row) => (
              <span className={styles.monoId}>
                {row.callsReduced && row.callsReduced > 0 ? `-${Math.round(row.callsReduced)}` : '—'}
              </span>
            ),
          },
        ] as Column<Task>[])
      : []),
    {
      key: 'tokens',
      label: 'Tokens',
      width: '8%',
      render: (_v, row) => <span className={styles.monoId}>{fmtTokens(row.telemetry?.totalTokens)}</span>,
    },
    {
      key: 'cost',
      label: 'Cost',
      width: '8%',
      render: (_v, row) => <span className={styles.monoId}>{fmtCost(row.telemetry?.costUsd)}</span>,
    },
    {
      key: 'latency',
      label: 'Latency',
      width: '9%',
      render: (_v, row) => <span className={styles.monoId}>{fmtMs(row.telemetry?.latencyMs)}</span>,
    },
    {
      key: 'model',
      label: 'Model',
      width: '12%',
      render: (_v, row) => (
        <span className={styles.modelCell} title={row.telemetry?.model ?? ''}>
          {row.telemetry?.model ? row.telemetry.model.split('/').pop() : '—'}
        </span>
      ),
    },
    {
      key: 'timestamp',
      label: 'Time',
      width: '9%',
      render: (v) => (
        <span className={styles.timeVal}>
          {new Date(String(v)).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
  ];

  return (
    <div className={styles.taskHistory}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Task History</h1>
          <p className={styles.subtitle}>
            {isAgent
              ? 'Agent-path runs (tool use, replays & calls reduced) — outputs and scores'
              : 'Model-path runs (answer quality) — historical outputs and scores'}
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchTasks}>
          <RefreshCw size={14} /> Refresh
        </button>
      </header>

      {/* Filter and Search controls */}
      <div className={styles.controls}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}><Search size={15} /></span>
          <input
            type="text"
            placeholder="Search tasks, query prompt, evaluation arm..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        <div className={styles.filters}>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={styles.select}
            aria-label="Status filter"
          >
            <option value="all">All Outcomes</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </div>
      </div>

      {/* DataTable */}
      <div className={styles.tableCard}>
        {loading ? (
          <div className={styles.skeleton}>
            <SkeletonLoader height="40px" />
            <SkeletonLoader height="250px" />
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className={styles.empty}>No tasks recorded matching filters.</div>
        ) : (
          <DataTable
            columns={columns}
            rows={filteredTasks}
            onRowClick={handleRowClick}
          />
        )}
      </div>
    </div>
  );
};
