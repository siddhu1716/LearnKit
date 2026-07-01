import React, { useEffect, useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { client } from '../api/client';
import { DataTable, Column } from '../components/ui/DataTable';
import { ConfidenceBadge } from '../components/ui/ConfidenceBadge';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { SkeletonLoader } from '../components/ui/SkeletonLoader';
import { toast } from '../components/ui/Toast';
import { Search } from '../components/icons';
import type { MemoryRecord, RecordType, RecordStatus } from '../types';
import { useDashboardMode } from '../context/DashboardModeContext';
import styles from './MemoryExplorer.module.css';

export const MemoryExplorer: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Parse type from query param
  const queryType = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return (params.get('type') || 'all') as RecordType | 'all';
  }, [location.search]);

  const [records, setRecords] = useState<MemoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  
  // Modals state
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editFormData, setEditFormData] = useState<Partial<MemoryRecord>>({});
  const [addFormData, setAddFormData] = useState<Partial<MemoryRecord>>({
    type: 'skill',
    taskType: '',
    content: '',
    confidence: 0.70,
    scope: 'user',
    domains: [],
    tags: [],
  });

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [procFilter, setProcFilter] = useState<'all' | 'procedural' | 'declarative'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const { mode } = useDashboardMode();
  const isAgent = mode === 'agent_learn';

  const selectedRecord = useMemo(() => {
    return records.find((r) => r.id === selectedRecordId) || null;
  }, [records, selectedRecordId]);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const data = await client.getRecords({
        type: queryType === 'all' ? undefined : queryType,
        sort: 'confidence',
        order: 'desc',
      });
      setRecords(data);
      // Auto select first record on desktop if details empty and records exist
      if (data.length > 0 && !selectedRecordId) {
        setSelectedRecordId(data[0].id);
      }
    } catch (error) {
      console.error('Error fetching records:', error);
      toast('Error fetching memory records', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [queryType]);

  // Filter records based on filters in React memory
  const filteredRecords = useMemo(() => {
    return records.filter((r) => {
      const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
      const matchesProc =
        procFilter === 'all' ||
        (procFilter === 'procedural' && r.isProcedural) ||
        (procFilter === 'declarative' && !r.isProcedural);
      const matchesSearch =
        searchQuery === '' ||
        r.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.taskType.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.domains.some((d) => d.toLowerCase().includes(searchQuery.toLowerCase()));
      return matchesStatus && matchesProc && matchesSearch;
    });
  }, [records, statusFilter, procFilter, searchQuery]);

  const handleRowClick = (row: MemoryRecord) => {
    setSelectedRecordId(row.id);
  };

  const handleOpenEdit = () => {
    if (!selectedRecord) return;
    setEditFormData({ ...selectedRecord });
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editFormData.id) return;

    try {
      const updated = await client.updateRecord(editFormData.id, {
        content: editFormData.content,
        confidence: editFormData.confidence,
        status: editFormData.status,
        scope: editFormData.scope,
      });

      // Update state
      setRecords((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      setIsEditModalOpen(false);
      toast('Record updated successfully', 'success');
    } catch (e) {
      toast('Failed to update record', 'error');
    }
  };

  const handleSaveAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addFormData.content || !addFormData.taskType) {
      toast('Please fill out all required fields', 'warn');
      return;
    }

    try {
      const created = await client.createRecord(addFormData);
      setRecords((prev) => [created, ...prev]);
      setSelectedRecordId(created.id);
      setIsAddModalOpen(false);
      toast('Record created successfully', 'success');
      // Reset form
      setAddFormData({
        type: 'skill',
        taskType: '',
        content: '',
        confidence: 0.70,
        scope: 'user',
        domains: [],
        tags: [],
      });
    } catch (e) {
      toast('Failed to create record', 'error');
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(`Are you sure you want to delete ${id}?`)) return;

    try {
      await client.deleteRecord(id);
      setRecords((prev) => prev.filter((r) => r.id !== id));
      setSelectedRecordId(null);
      toast('Record deleted successfully', 'success');
    } catch (e) {
      toast('Failed to delete record', 'error');
    }
  };

  const columns: Column<MemoryRecord>[] = [
    {
      key: 'id',
      label: 'ID',
      width: '15%',
      render: (v) => <span className={styles.monoId}>{String(v)}</span>,
    },
    {
      key: 'taskType',
      label: 'Task Type',
      width: '30%',
      render: (v) => <span className={styles.taskType}>{String(v).replace('pbe_', '').replace(/_/g, ' ')}</span>,
    },
    {
      key: 'confidence',
      label: 'Confidence',
      width: '25%',
      render: (v) => <ConfidenceBadge value={Number(v)} size="small" showBar />,
    },
    {
      key: 'reuseCount',
      label: 'Usage (Help/Total)',
      width: '20%',
      render: (_, row) => (
        <span className={styles.usage}>
          {row.helpCount}/{row.reuseCount}
        </span>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      width: '10%',
      render: (v) => (
        <Badge variant={v === 'active' ? 'success' : v === 'quarantine' ? 'warn' : 'neutral'}>
          {String(v)}
        </Badge>
      ),
    },
  ];

  return (
    <div className={styles.explorer}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Memory Explorer</h1>
          <p className={styles.subtitle}>
            Catalog of {queryType === 'all' ? 'all' : queryType} learned patterns
          </p>
        </div>
        <Button variant="primary" onClick={() => setIsAddModalOpen(true)}>
          Add Record +
        </Button>
      </header>

      {/* Tabs */}
      <div className={styles.tabs} role="tablist">
        {['all', 'skill', 'failure', 'fact', 'strategy', 'preference', 'heuristic', 'trace'].map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={queryType === t}
            className={`${styles.tab} ${queryType === t ? styles.activeTab : ''}`}
            onClick={() => navigate(`/memory?type=${t}`)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}s
          </button>
        ))}
      </div>

      {/* Filter and Search controls */}
      <div className={styles.controls}>
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon}><Search size={15} /></span>
          <input
            type="text"
            placeholder="Search content, task type, domains..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        <div className={styles.filters}>
          {isAgent && (
            <select
              value={procFilter}
              onChange={(e) => setProcFilter(e.target.value as 'all' | 'procedural' | 'declarative')}
              className={styles.select}
              aria-label="Procedural filter"
              title="Procedural skills carry an ordered tool-call sequence; declarative records do not."
            >
              <option value="all">All Memory</option>
              <option value="procedural">Procedural (tool steps)</option>
              <option value="declarative">Declarative</option>
            </select>
          )}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={styles.select}
            aria-label="Status filter"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="quarantine">Quarantine</option>
            <option value="stale">Stale</option>
          </select>
        </div>
      </div>

      {/* 2-Column layout: Table & Detail Pane */}
      <div className={styles.layoutGrid}>
        <div className={styles.tableColumn}>
          {loading ? (
            <div className={styles.tableSkeleton}>
              <SkeletonLoader height="40px" />
              <SkeletonLoader height="300px" />
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className={styles.empty}>No records found matching filters.</div>
          ) : (
            <DataTable
              columns={columns}
              rows={filteredRecords}
              selectedRowId={selectedRecordId || undefined}
              onRowClick={handleRowClick}
            />
          )}
        </div>

        {/* Right side Detail Pane */}
        <div className={styles.detailColumn}>
          {selectedRecord ? (
            <div className={styles.detailPane}>
              <div className={styles.detailHeader}>
                <div>
                  <div className={styles.detailIdRow}>
                    <Badge variant="accent">{selectedRecord.type.toUpperCase()}</Badge>
                    <span className={styles.detailId}>{selectedRecord.id}</span>
                  </div>
                  <h2 className={styles.detailTitle}>
                    {selectedRecord.taskType.replace('pbe_', '').replace(/_/g, ' ')}
                  </h2>
                </div>
                <div className={styles.detailActions}>
                  <Button variant="secondary" size="sm" onClick={handleOpenEdit}>
                    Edit
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(selectedRecord.id)}>
                    Delete
                  </Button>
                </div>
              </div>

              <div className={styles.detailSection}>
                <h3 className={styles.sectionLabel}>Generality & Performance</h3>
                <div className={styles.badgeRow}>
                  <div>
                    <span className={styles.badgeLabel}>Confidence</span>
                    <ConfidenceBadge value={selectedRecord.confidence} size="medium" showBar />
                  </div>
                  <div>
                    <span className={styles.badgeLabel}>Generality Score</span>
                    <span className={styles.badgeVal}>{Math.round(selectedRecord.generality * 100)}%</span>
                  </div>
                  <div>
                    <span className={styles.badgeLabel}>Task Overlap</span>
                    <span className={styles.badgeVal}>{Math.round(selectedRecord.taskOverlap * 100)}%</span>
                  </div>
                </div>
              </div>

              <div className={styles.detailSection}>
                <h3 className={styles.sectionLabel}>Domains</h3>
                <div className={styles.tagWrap}>
                  {selectedRecord.domains.map((d) => (
                    <Badge key={d} variant="info">
                      {d}
                    </Badge>
                  ))}
                  {selectedRecord.domains.length === 0 && (
                    <span className={styles.noTags}>No domains assigned</span>
                  )}
                </div>
              </div>

              <div className={styles.detailSection}>
                <h3 className={styles.sectionLabel}>Content Description</h3>
                <div className={styles.contentBlock}>
                  {selectedRecord.content}
                </div>
              </div>

              <div className={styles.detailSection}>
                <h3 className={styles.sectionLabel}>Metadata Stats</h3>
                <div className={styles.metaGrid}>
                  <div className={styles.metaCell}>
                    <span className={styles.metaLabel}>Usage Count:</span>
                    <span className={styles.metaVal}>{selectedRecord.reuseCount} times</span>
                  </div>
                  <div className={styles.metaCell}>
                    <span className={styles.metaLabel}>Help Rate:</span>
                    <span className={styles.metaVal}>
                      {selectedRecord.reuseCount > 0
                        ? `${Math.round((selectedRecord.helpCount / selectedRecord.reuseCount) * 100)}%`
                        : 'N/A'}
                    </span>
                  </div>
                  <div className={styles.metaCell}>
                    <span className={styles.metaLabel}>Quality Score:</span>
                    <span className={styles.metaVal}>
                      {selectedRecord.qualityScore ? `${Math.round(selectedRecord.qualityScore * 100)}%` : 'N/A'}
                    </span>
                  </div>
                  <div className={styles.metaCell}>
                    <span className={styles.metaLabel}>Created:</span>
                    <span className={styles.metaVal}>
                      {new Date(selectedRecord.createdAt).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.noSelection}>Select a row to view full details.</div>
          )}
        </div>
      </div>

      {/* Edit Modal */}
      {isEditModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Edit Record: {editFormData.id}</h2>
              <button className={styles.closeBtn} onClick={() => setIsEditModalOpen(false)}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveEdit}>
              <div className={styles.formGroup}>
                <label className={styles.label}>Content Description</label>
                <textarea
                  className={styles.textarea}
                  value={editFormData.content || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, content: e.target.value })}
                  required
                  rows={4}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>
                  Confidence (0.00–1.00): <span className={styles.confNum}>{editFormData.confidence}</span>
                </label>
                <input
                  type="range"
                  min="0.0"
                  max="1.0"
                  step="0.05"
                  value={editFormData.confidence || 0}
                  onChange={(e) => setEditFormData({ ...editFormData, confidence: parseFloat(e.target.value) })}
                  className={styles.slider}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label className={styles.label}>Status</label>
                  <select
                    value={editFormData.status || 'active'}
                    onChange={(e) => setEditFormData({ ...editFormData, status: e.target.value as RecordStatus })}
                    className={styles.select}
                  >
                    <option value="active">Active</option>
                    <option value="quarantine">Quarantine</option>
                    <option value="stale">Stale</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.label}>Scope</label>
                  <select
                    value={editFormData.scope || 'user'}
                    onChange={(e) => setEditFormData({ ...editFormData, scope: e.target.value })}
                    className={styles.select}
                  >
                    <option value="user">User (Local)</option>
                    <option value="team">Team (Registry)</option>
                  </select>
                </div>
              </div>

              <div className={styles.modalActions}>
                <Button variant="secondary" onClick={() => setIsEditModalOpen(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit">
                  Save Changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Modal */}
      {isAddModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Add Memory Record</h2>
              <button className={styles.closeBtn} onClick={() => setIsAddModalOpen(false)}>
                ✕
              </button>
            </div>
            <form onSubmit={handleSaveAdd}>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label className={styles.label}>Record Type</label>
                  <select
                    value={addFormData.type}
                    onChange={(e) => setAddFormData({ ...addFormData, type: e.target.value as RecordType })}
                    className={styles.select}
                  >
                    <option value="skill">Skill</option>
                    <option value="failure">Failure</option>
                    <option value="fact">Fact</option>
                    <option value="strategy">Strategy</option>
                    <option value="preference">Preference</option>
                    <option value="heuristic">Heuristic</option>
                    <option value="trace">Trace</option>
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label}>Task Type (Key)</label>
                  <input
                    type="text"
                    placeholder="e.g. pbe_refund"
                    value={addFormData.taskType}
                    onChange={(e) => setAddFormData({ ...addFormData, taskType: e.target.value })}
                    className={styles.input}
                    required
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.label}>Content Description</label>
                <textarea
                  className={styles.textarea}
                  placeholder="Explain the learned skill, policy fact, or failure mode detail here..."
                  value={addFormData.content}
                  onChange={(e) => setAddFormData({ ...addFormData, content: e.target.value })}
                  required
                  rows={4}
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label className={styles.label}>
                    Confidence (0.0–1.0): <span className={styles.confNum}>{addFormData.confidence}</span>
                  </label>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.05"
                    value={addFormData.confidence}
                    onChange={(e) => setAddFormData({ ...addFormData, confidence: parseFloat(e.target.value) })}
                    className={styles.slider}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label className={styles.label}>Domains (Comma separated)</label>
                  <input
                    type="text"
                    placeholder="e.g. support, api"
                    onChange={(e) =>
                      setAddFormData({
                        ...addFormData,
                        domains: e.target.value.split(',').map((x) => x.trim()).filter(Boolean),
                      })
                    }
                    className={styles.input}
                  />
                </div>
              </div>

              <div className={styles.modalActions}>
                <Button variant="secondary" onClick={() => setIsAddModalOpen(false)} type="button">
                  Cancel
                </Button>
                <Button variant="primary" type="submit">
                  Create Record
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
