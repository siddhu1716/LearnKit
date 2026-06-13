import React, { useState, useMemo } from 'react';
import styles from './DataTable.module.css';

export interface Column<T> {
  key: keyof T | string;
  label: string;
  sortable?: boolean;
  width?: string;
  render?: (value: unknown, row: T) => React.ReactNode;
}

interface DataTableProps<T extends { id: string }> {
  columns: Column<T>[];
  rows: T[];
  onRowClick?: (row: T, index: number) => void;
  selectedRowId?: string;
  loading?: boolean;
  emptyMessage?: string;
  pagination?: { page: number; pageSize: number; total: number };
  onPaginationChange?: (page: number) => void;
}

type SortDir = 'asc' | 'desc';

export function DataTable<T extends { id: string }>({
  columns,
  rows,
  onRowClick,
  selectedRowId,
  loading,
  emptyMessage = 'No records found.',
  pagination,
  onPaginationChange,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  const sorted = useMemo(() => {
    if (!sortKey) return rows;
    return [...rows].sort((a, b) => {
      const av = (a as Record<string, unknown>)[sortKey];
      const bv = (b as Record<string, unknown>)[sortKey];
      if (av === bv) return 0;
      const cmp = av! < bv! ? -1 : 1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [rows, sortKey, sortDir]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const totalPages = pagination
    ? Math.ceil(pagination.total / pagination.pageSize)
    : 1;

  if (loading) {
    return (
      <div className={styles.tableWrap}>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className={styles.skeletonRow}>
            {columns.map((c) => (
              <div key={String(c.key)} className={styles.skeletonCell} style={{ width: c.width }} />
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.tableWrap}>
      <table className={styles.table} role="grid">
        <thead className={styles.thead}>
          <tr>
            {columns.map((col) => (
              <th
                key={String(col.key)}
                scope="col"
                style={{ width: col.width }}
                className={`${styles.th} ${col.sortable ? styles.sortable : ''}`}
                onClick={col.sortable ? () => handleSort(String(col.key)) : undefined}
                aria-sort={
                  sortKey === String(col.key)
                    ? sortDir === 'asc'
                      ? 'ascending'
                      : 'descending'
                    : 'none'
                }
              >
                <span>{col.label}</span>
                {col.sortable && (
                  <span className={styles.sortIcon} aria-hidden="true">
                    {sortKey === String(col.key) ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ' ↕'}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.empty}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sorted.map((row, idx) => (
              <tr
                key={row.id}
                className={`${styles.tr} ${onRowClick ? styles.clickable : ''} ${
                  selectedRowId === row.id ? styles.selected : ''
                }`}
                onClick={onRowClick ? () => onRowClick(row, idx) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                onKeyDown={
                  onRowClick
                    ? (e) => e.key === 'Enter' && onRowClick(row, idx)
                    : undefined
                }
                aria-selected={selectedRowId === row.id}
              >
                {columns.map((col) => (
                  <td key={String(col.key)} className={styles.td}>
                    {col.render
                      ? col.render((row as Record<string, unknown>)[String(col.key)], row)
                      : String((row as Record<string, unknown>)[String(col.key)] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {pagination && totalPages > 1 && (
        <div className={styles.pagination} role="navigation" aria-label="Table pagination">
          <button
            className={styles.pageBtn}
            disabled={pagination.page <= 1}
            onClick={() => onPaginationChange?.(pagination.page - 1)}
            aria-label="Previous page"
          >
            ←
          </button>
          <span className={styles.pageInfo}>
            Page {pagination.page} of {totalPages}
          </span>
          <button
            className={styles.pageBtn}
            disabled={pagination.page >= totalPages}
            onClick={() => onPaginationChange?.(pagination.page + 1)}
            aria-label="Next page"
          >
            →
          </button>
        </div>
      )}
    </div>
  );
}
