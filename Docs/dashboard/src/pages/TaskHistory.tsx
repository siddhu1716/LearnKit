import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { DataTable, Column } from '../components/ui/DataTable';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import type { Task } from '../types';
import styles from './TaskHistory.module.css';

export const TaskHistory: React.FC = () => {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

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
      width: '12%',
      render: (v) => <span className={styles.monoId}>{String(v)}</span>,
    },
    {
      key: 'input',
      label: 'Query / Input Task',
      width: '40%',
      render: (v) => <span className={styles.inputVal} title={String(v)}>{String(v)}</span>,
    },
    {
      key: 'status',
      label: 'Status',
      width: '13%',
      render: (v) => (
        <Badge variant={v === 'success' ? 'success' : 'error'}>
          {String(v).toUpperCase()}
        </Badge>
      ),
    },
    {
      key: 'score',
      label: 'Quality Score',
      width: '12%',
      render: (v) => <span className={styles.monoId}>{Number(v).toFixed(1)} / 5.0</span>,
    },
    {
      key: 'armName',
      label: 'Evaluation Arm',
      width: '13%',
      render: (v) => (
        <Badge variant={v === 'prescriptive' ? 'accent' : v === 'guided' ? 'info' : 'neutral'}>
          {String(v)}
        </Badge>
      ),
    },
    {
      key: 'timestamp',
      label: 'Time executed',
      width: '10%',
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
            Historical trace logs of all evaluated execution runs, outputs, and scores
          </p>
        </div>
        <button className={styles.refreshBtn} onClick={fetchTasks}>
          Refresh ↻
        </button>
      </header>

      {/* Filter and Search controls */}
      <div className={styles.controls}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}>🔍</span>
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
