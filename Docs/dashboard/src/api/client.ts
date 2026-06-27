// ============================================================
// LearnKit Dashboard — API Client
// Tries to connect to the FastAPI backend at /api/v1/
// Falls back to mock data & localStorage state if backend is offline.
// ============================================================

import type {
  DashboardMetrics,
  MemoryRecord,
  Task,
  TraceDetail,
  QuarantineRecord,
  SuccessRatePoint,
  TopSkill,
  ProblematicFailure,
  ActivityEvent,
  CrowdedOutRecord,
  Agent,
  AgentStats,
  ObservabilitySummary,
} from '../types';

import {
  MOCK_METRICS,
  MOCK_RECORDS,
  MOCK_TASKS,
  MOCK_TRACE,
  MOCK_QUARANTINE,
  MOCK_CROWDED_OUT,
  MOCK_SUCCESS_TREND,
  MOCK_TOP_SKILLS,
  MOCK_PROBLEM_FAILURES,
  MOCK_ACTIVITY,
  MOCK_AGENTS,
  MOCK_AGENT_STATS,
  MOCK_OBSERVABILITY,
} from '../data/mockData';

const BASE_URL = '/api/v1';

// Key names for localStorage fallback
const STORAGE_KEYS = {
  METRICS: 'learnkit_metrics',
  RECORDS: 'learnkit_records',
  TASKS: 'learnkit_tasks',
  TRACE: 'learnkit_trace',
  QUARANTINE: 'learnkit_quarantine',
  CROWDED_OUT: 'learnkit_crowded_out',
  DIVERSITY_LAMBDA: 'learnkit_diversity_lambda',
  ACTIVITY: 'learnkit_activity',
};

// Initialize localStorage with mock data if not already present
function initLocalStorage() {
  if (!localStorage.getItem(STORAGE_KEYS.METRICS)) {
    localStorage.setItem(STORAGE_KEYS.METRICS, JSON.stringify(MOCK_METRICS));
  }
  if (!localStorage.getItem(STORAGE_KEYS.RECORDS)) {
    localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(MOCK_RECORDS));
  }
  if (!localStorage.getItem(STORAGE_KEYS.TASKS)) {
    localStorage.setItem(STORAGE_KEYS.TASKS, JSON.stringify(MOCK_TASKS));
  }
  if (!localStorage.getItem(STORAGE_KEYS.QUARANTINE)) {
    localStorage.setItem(STORAGE_KEYS.QUARANTINE, JSON.stringify(MOCK_QUARANTINE));
  }
  if (!localStorage.getItem(STORAGE_KEYS.CROWDED_OUT)) {
    localStorage.setItem(STORAGE_KEYS.CROWDED_OUT, JSON.stringify(MOCK_CROWDED_OUT));
  }
  if (!localStorage.getItem(STORAGE_KEYS.DIVERSITY_LAMBDA)) {
    localStorage.setItem(STORAGE_KEYS.DIVERSITY_LAMBDA, JSON.stringify({ diversityLambda: 0.70 }));
  }
  if (!localStorage.getItem(STORAGE_KEYS.ACTIVITY)) {
    localStorage.setItem(STORAGE_KEYS.ACTIVITY, JSON.stringify(MOCK_ACTIVITY));
  }
}

initLocalStorage();

function toArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function parseEnvelopeArray<T>(payload: unknown, key: string): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === 'object') {
    const data = (payload as Record<string, unknown>)[key];
    if (Array.isArray(data)) return data as T[];
  }
  return [];
}

function toDomains(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((v) => String(v));
  if (value && typeof value === 'object') return Object.keys(value as Record<string, unknown>);
  if (typeof value === 'string' && value.trim()) return [value];
  return [];
}

function toContent(value: unknown): string {
  if (typeof value === 'string') return value;
  if (value == null) return '';
  if (Array.isArray(value)) return value.map((v) => String(v)).join(' | ');
  if (typeof value === 'object') {
    const obj = value as Record<string, unknown>;
    const preferred = [
      obj.description,
      obj.lesson_title,
      obj.summary,
      obj.workflow,
      obj.what_to_avoid,
    ].find((v) => typeof v === 'string' && String(v).trim().length > 0);
    if (preferred) return String(preferred);
    return JSON.stringify(obj);
  }
  return String(value);
}

function normalizeRecord(raw: any): MemoryRecord {
  return {
    id: String(raw?.id ?? `rec-${Math.floor(1000 + Math.random() * 9000)}`),
    type: String(raw?.type ?? 'skill') as MemoryRecord['type'],
    taskType: String(raw?.taskType ?? raw?.task_type ?? 'generic'),
    domains: toDomains(raw?.domains),
    confidence: Number(raw?.confidence ?? 0.5),
    content: toContent(raw?.content),
    scope: String(raw?.scope ?? 'user'),
    status: String(raw?.status ?? 'active') as MemoryRecord['status'],
    retrievalCount: Number(raw?.retrievalCount ?? raw?.retrieval_count ?? 0),
    reuseCount: Number(raw?.reuseCount ?? raw?.reuse_count ?? 0),
    helpCount: Number(raw?.helpCount ?? raw?.help_count ?? 0),
    harmCount: Number(raw?.harmCount ?? raw?.harm_count ?? 0),
    neutralCount: Number(raw?.neutralCount ?? raw?.neutral_count ?? 0),
    generality: Number(raw?.generality ?? 0.5),
    taskOverlap: Number(raw?.taskOverlap ?? raw?.task_overlap ?? 0.0),
    qualityScore: Number(raw?.qualityScore ?? raw?.quality_score ?? 0.0),
    tags: toArray<string>(raw?.tags),
    createdAt: String(raw?.createdAt ?? raw?.created_at ?? new Date().toISOString()),
    expiresAt: raw?.expiresAt ?? raw?.expires_at ?? null,
  };
}

// Helper to make API calls with fallback
async function apiRequest<T>(
  url: string,
  options?: RequestInit,
  localStorageKey?: string,
  mockFallback?: T | (() => T)
): Promise<T> {
  try {
    const res = await fetch(url, options);
    if (res.ok) {
      return await res.json();
    }
  } catch (error) {
    console.warn(`API request to ${url} failed, falling back to local simulation:`, error);
  }

  // Fallback to localStorage if key provided
  if (localStorageKey) {
    const data = localStorage.getItem(localStorageKey);
    if (data) {
      return JSON.parse(data) as T;
    }
  }

  // Fallback to static mock data
  if (mockFallback !== undefined) {
    return typeof mockFallback === 'function' ? (mockFallback as Function)() : mockFallback;
  }

  throw new Error(`Request failed and no fallback available for ${url}`);
}

export const client = {
  // 1. Dashboard Metrics
  async getMetrics(): Promise<DashboardMetrics> {
    const metrics = await apiRequest<DashboardMetrics>(`${BASE_URL}/metrics`, undefined, STORAGE_KEYS.METRICS, MOCK_METRICS);
    // Sync with record counts in storage
    const records = await this.getRecords();
    const counts = {
      skill: records.filter((r) => r.type === 'skill').length,
      failure: records.filter((r) => r.type === 'failure').length,
      fact: records.filter((r) => r.type === 'fact').length,
      strategy: records.filter((r) => r.type === 'strategy').length,
      preference: records.filter((r) => r.type === 'preference').length,
      heuristic: records.filter((r) => r.type === 'heuristic').length,
      trace: records.filter((r) => r.type === 'trace').length,
    };
    metrics.recordCounts = counts;
    localStorage.setItem(STORAGE_KEYS.METRICS, JSON.stringify(metrics));
    return metrics;
  },

  // 2. Memory Records
  async getRecords(params?: {
    type?: string;
    status?: string;
    page?: number;
    pageSize?: number;
    sort?: string;
    order?: 'asc' | 'desc';
  }): Promise<MemoryRecord[]> {
    const payload = await apiRequest<MemoryRecord[] | { records: MemoryRecord[] }>(
      `${BASE_URL}/records`,
      undefined,
      STORAGE_KEYS.RECORDS,
      MOCK_RECORDS
    );
    const allRecords = parseEnvelopeArray<MemoryRecord>(payload, 'records').map(normalizeRecord);

    let filtered = [...allRecords];

    if (params?.type && params.type !== 'all') {
      filtered = filtered.filter((r) => r.type === params.type);
    }
    if (params?.status) {
      filtered = filtered.filter((r) => r.status === params.status);
    }

    if (params?.sort) {
      const key = params.sort as keyof MemoryRecord;
      const orderMultiplier = params.order === 'desc' ? -1 : 1;
      filtered.sort((a, b) => {
        const valA = a[key];
        const valB = b[key];
        if (typeof valA === 'number' && typeof valB === 'number') {
          return (valA - valB) * orderMultiplier;
        }
        return String(valA || '').localeCompare(String(valB || '')) * orderMultiplier;
      });
    }

    return filtered;
  },

  async getRecord(id: string): Promise<MemoryRecord> {
    const records = await this.getRecords();
    const record = records.find((r) => r.id === id);
    if (!record) throw new Error(`Record ${id} not found`);
    return normalizeRecord(record);
  },

  async createRecord(recordData: Partial<MemoryRecord>): Promise<MemoryRecord> {
    try {
      const res = await fetch(`${BASE_URL}/records`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(recordData),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('POST /records failed, simulating locally');
    }

    const records = await this.getRecords();
    const prefix = recordData.type === 'skill' ? 'sk' : recordData.type === 'failure' ? 'fr' : 'rec';
    const newId = `${prefix}-${Math.floor(1000 + Math.random() * 9000)}`;

    const newRecord: MemoryRecord = {
      id: newId,
      type: recordData.type || 'skill',
      taskType: recordData.taskType || 'generic',
      domains: recordData.domains || [],
      confidence: recordData.confidence ?? 0.5,
      content: recordData.content || '',
      scope: recordData.scope || 'user',
      status: recordData.status || 'active',
      retrievalCount: 0,
      reuseCount: 0,
      helpCount: 0,
      harmCount: 0,
      neutralCount: 0,
      generality: 0.5,
      taskOverlap: 0.1,
      qualityScore: 0.5,
      tags: recordData.tags || [],
      createdAt: new Date().toISOString(),
      expiresAt: null,
    };

    records.unshift(newRecord);
    localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(records));

    // Log activity
    await this.logActivity(`New ${newRecord.type} created: "${newRecord.content.slice(0, 30)}..."`, 'distill');

    return newRecord;
  },

  async updateRecord(id: string, recordData: Partial<MemoryRecord>): Promise<MemoryRecord> {
    try {
      const res = await fetch(`${BASE_URL}/records/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(recordData),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn(`PATCH /records/${id} failed, simulating locally`);
    }

    const records = await this.getRecords();
    const index = records.findIndex((r) => r.id === id);
    if (index === -1) throw new Error(`Record ${id} not found`);

    records[index] = { ...records[index], ...recordData };
    localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(records));

    return records[index];
  },

  async deleteRecord(id: string): Promise<{ deleted: boolean }> {
    try {
      const res = await fetch(`${BASE_URL}/records/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn(`DELETE /records/${id} failed, simulating locally`);
    }

    const records = await this.getRecords();
    const filtered = records.filter((r) => r.id !== id);
    localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(filtered));

    await this.logActivity(`Record ${id} deleted`, 'purge');

    return { deleted: true };
  },

  // 3. Retrieval Quality & Diversity Config
  async getDiversityConfig(): Promise<{ diversityLambda: number }> {
    return apiRequest<{ diversityLambda: number }>(
      `${BASE_URL}/config/diversity`,
      undefined,
      STORAGE_KEYS.DIVERSITY_LAMBDA,
      { diversityLambda: 0.70 }
    );
  },

  async updateDiversityConfig(diversityLambda: number): Promise<{ diversityLambda: number }> {
    try {
      const res = await fetch(`${BASE_URL}/config/diversity`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ diversityLambda }),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('PUT /config/diversity failed, simulating locally');
    }

    const config = { diversityLambda };
    localStorage.setItem(STORAGE_KEYS.DIVERSITY_LAMBDA, JSON.stringify(config));

    // Update metrics too
    const metrics = await this.getMetrics();
    metrics.retrieval.diversityLambda = diversityLambda;
    localStorage.setItem(STORAGE_KEYS.METRICS, JSON.stringify(metrics));

    await this.logActivity(`Diversity lambda updated to ${diversityLambda}`, 'maintain');

    return config;
  },

  async getCrowdedOutRecords(): Promise<CrowdedOutRecord[]> {
    const payload = await apiRequest<CrowdedOutRecord[] | { records: CrowdedOutRecord[] }>(
      `${BASE_URL}/metrics/crowded-out`,
      undefined,
      STORAGE_KEYS.CROWDED_OUT,
      MOCK_CROWDED_OUT
    );
    return parseEnvelopeArray<CrowdedOutRecord>(payload, 'records');
  },

  // 4. Tasks & Trace Playbacks
  async getTasks(params?: { status?: string }): Promise<Task[]> {
    const payload = await apiRequest<Task[] | { tasks: Task[] }>(
      `${BASE_URL}/tasks`,
      undefined,
      STORAGE_KEYS.TASKS,
      MOCK_TASKS
    );
    const tasks = parseEnvelopeArray<Task>(payload, 'tasks');
    if (params?.status && params.status !== 'all') {
      return tasks.filter((t) => t.status === params.status);
    }
    return tasks;
  },

  async getTraceDetail(taskId: string): Promise<TraceDetail> {
    try {
      const res = await fetch(`${BASE_URL}/tasks/${taskId}/trace`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn(`GET /tasks/${taskId}/trace failed, simulating locally`);
    }

    // Adapt mock trace detail to the requested taskId
    const tasks = await this.getTasks();
    const task = tasks.find((t) => t.id === taskId);
    if (!task) throw new Error(`Task ${taskId} not found`);

    return {
      ...MOCK_TRACE,
      taskId: task.id,
      input: task.input,
      status: task.status,
      score: task.score,
    } as unknown as TraceDetail;
  },

  async reinforceRecord(recordId: string, taskId: string): Promise<{ id: string; confidence: number }> {
    try {
      const res = await fetch(`${BASE_URL}/records/${recordId}/reinforce`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId }),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('POST reinforce failed, simulating locally');
    }

    const record = await this.getRecord(recordId);
    const newConf = Math.min(1.0, record.confidence + 0.05);
    await this.updateRecord(recordId, {
      confidence: Number(newConf.toFixed(2)),
      reuseCount: record.reuseCount + 1,
      helpCount: record.helpCount + 1,
    });

    await this.logActivity(`Reinforced memory ${recordId} via task ${taskId}`, 'reinforce');

    return { id: recordId, confidence: newConf };
  },

  async demoteRecord(recordId: string, taskId: string): Promise<{ id: string; confidence: number }> {
    try {
      const res = await fetch(`${BASE_URL}/records/${recordId}/demote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ taskId }),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('POST demote failed, simulating locally');
    }

    const record = await this.getRecord(recordId);
    const newConf = Math.max(0.0, record.confidence - 0.1);
    await this.updateRecord(recordId, {
      confidence: Number(newConf.toFixed(2)),
      reuseCount: record.reuseCount + 1,
      harmCount: record.harmCount + 1,
    });

    await this.logActivity(`Demoted memory ${recordId} via task ${taskId}`, 'failure');

    return { id: recordId, confidence: newConf };
  },

  // 5. Memory Lifecycle & Maintenance
  async getQuarantineRecords(): Promise<QuarantineRecord[]> {
    const payload = await apiRequest<QuarantineRecord[] | { records: QuarantineRecord[] }>(
      `${BASE_URL}/lifecycle/quarantine`,
      undefined,
      STORAGE_KEYS.QUARANTINE,
      MOCK_QUARANTINE
    );
    return parseEnvelopeArray<QuarantineRecord>(payload, 'records');
  },

  async runMaintenance(params: { quarantineHours?: number; decay?: boolean }): Promise<{
    promoted: number;
    decayed: number;
    staled: number;
    purged: number;
  }> {
    try {
      const res = await fetch(`${BASE_URL}/maintain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn('POST /maintain failed, simulating locally');
    }

    // Simulate maintenance locally
    const quarantine = await this.getQuarantineRecords();
    const records = await this.getRecords();

    let promotedCount = 0;
    let decayedCount = 0;
    let staledCount = 0;
    let purgedCount = 0;

    // Promote quarantine records that have passed their promotableAfter date
    const now = new Date();
    const remainingQuarantine: QuarantineRecord[] = [];

    for (const q of quarantine) {
      if (new Date(q.promotableAfter) <= now) {
        // Promote to active records!
        await this.createRecord({
          type: q.type,
          content: q.content,
          confidence: q.confidence,
          status: 'active',
        });
        promotedCount++;
      } else {
        remainingQuarantine.push(q);
      }
    }

    localStorage.setItem(STORAGE_KEYS.QUARANTINE, JSON.stringify(remainingQuarantine));

    // Decaying active records
    if (params.decay) {
      const updatedRecords = await Promise.all(
        records.map(async (r) => {
          if (r.status === 'active' && r.confidence > 0.3) {
            let decayAmount = 0.05;
            // Decay more if it has high harmCount or low retrievalCount
            if (r.harmCount > 2) decayAmount = 0.15;
            const newConf = Math.max(0.1, r.confidence - decayAmount);
            let newStatus: MemoryRecord['status'] = r.status;
            if (newConf < 0.3) {
              newStatus = 'stale';
              staledCount++;
            } else {
              decayedCount++;
            }
            return {
              ...r,
              confidence: Number(newConf.toFixed(2)),
              status: newStatus,
            };
          }
          return r;
        })
      );
      localStorage.setItem(STORAGE_KEYS.RECORDS, JSON.stringify(updatedRecords));
    }

    await this.logActivity(
      `Maintenance completed: ${promotedCount} promoted, ${decayedCount} decayed, ${staledCount} staled, ${purgedCount} purged`,
      'maintain'
    );

    return {
      promoted: promotedCount,
      decayed: decayedCount,
      staled: staledCount,
      purged: purgedCount,
    };
  },

  // 6. Helpers / Utilities
  async getSuccessRateTrend(): Promise<SuccessRatePoint[]> {
    return MOCK_SUCCESS_TREND;
  },

  async getTopSkills(): Promise<TopSkill[]> {
    // Dynamically query based on real records in localStorage
    const records = await this.getRecords();
    const skills = records.filter((r) => r.type === 'skill');
    return skills
      .map((s) => ({
        id: s.id,
        name: s.taskType.replace('pbe_', '').replace(/_/g, ' '),
        helpRate: s.reuseCount > 0 ? Number((s.helpCount / s.reuseCount).toFixed(2)) : s.confidence,
      }))
      .sort((a, b) => b.helpRate - a.helpRate)
      .slice(0, 5);
  },

  async getProblematicFailures(): Promise<ProblematicFailure[]> {
    // Dynamically query based on real records
    const records = await this.getRecords();
    const failures = records.filter((r) => r.type === 'failure');
    return failures
      .map((f) => ({
        id: f.id,
        name: f.taskType.replace('pbe_', '').replace(/_/g, ' '),
        hurtRate: f.reuseCount > 0 ? Number((f.harmCount / f.reuseCount).toFixed(2)) : 1 - f.confidence,
      }))
      .sort((a, b) => b.hurtRate - a.hurtRate)
      .slice(0, 5);
  },

  async getActivityFeed(): Promise<ActivityEvent[]> {
    return apiRequest<ActivityEvent[]>(
      `${BASE_URL}/activity`,
      undefined,
      STORAGE_KEYS.ACTIVITY,
      MOCK_ACTIVITY
    );
  },

  async logActivity(message: string, icon = 'reinforce') {
    const feed = await this.getActivityFeed();
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    feed.unshift({ time, icon, message });
    localStorage.setItem(STORAGE_KEYS.ACTIVITY, JSON.stringify(feed.slice(0, 10)));
  },

  // 6b. Agents — live agent-learning registry & per-agent learning curves
  async getAgents(): Promise<Agent[]> {
    const payload = await apiRequest<Agent[] | { agents: Agent[] }>(
      `${BASE_URL}/agents`,
      undefined,
      undefined,
      MOCK_AGENTS
    );
    return parseEnvelopeArray<Agent>(payload, 'agents');
  },

  async getAgentStats(agentId: string): Promise<AgentStats> {
    try {
      const res = await fetch(`${BASE_URL}/agents/${agentId}/stats`);
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn(`GET /agents/${agentId}/stats failed, falling back to mock`);
    }
    return MOCK_AGENT_STATS[agentId] ?? {
      agentId,
      agentName: agentId,
      taskCount: 0,
      successRate: 0,
      callsReduced: 0,
      totalToolCalls: 0,
      skillsLearned: 0,
      curve: [],
    };
  },

  // 6c. Observability — LLM token/latency/cost telemetry
  async getObservability(agentId?: string): Promise<ObservabilitySummary> {
    const url = agentId
      ? `${BASE_URL}/observability?agentId=${encodeURIComponent(agentId)}`
      : `${BASE_URL}/observability`;
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = (await res.json()) as ObservabilitySummary;
        // An empty live store should still show the illustrative mock so the
        // page is never blank during local development.
        if (data && data.totals && data.totals.runs > 0) return data;
      }
    } catch (e) {
      console.warn('GET /observability failed, falling back to mock');
    }
    return MOCK_OBSERVABILITY;
  },

  // 7. Playground Integrations
  async getPlaygroundDomains(): Promise<{ key: string; label: string; example: string; record_count: number }[]> {
    try {
      const res = await fetch('/api/domains');
      if (res.ok) {
        const data = await res.json();
        return data.domains;
      }
    } catch (e) {
      console.warn('GET /api/domains failed, falling back to static playground domains');
    }
    return [
      { key: 'python_debugging', label: 'Python debugging', example: 'Why does my multiprocessing.Pool().map() hang on macOS Python 3.12?', record_count: 12 },
      { key: 'contract_summarization', label: 'Contract summarization', example: 'Summarize obligations, term, termination, and liability cap for a SaaS agreement with 99.9% uptime and a 12-month auto-renew.', record_count: 8 },
      { key: 'sql_authoring', label: 'SQL authoring', example: 'Write Postgres SQL for the top 3 orders per customer using a window function.', record_count: 15 }
    ];
  },

  async inspectPlaygroundTask(task: string, domain: string): Promise<any> {
    try {
      const res = await fetch('/api/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task, domain }),
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (e) {
      console.warn('POST /api/inspect failed, simulating locally');
    }
    
    // Simulate inspect logic using mock data
    const records = await this.getRecords({ type: 'all' });
    const matching = records.slice(0, 3).map(r => ({
      id: r.id,
      type: r.type,
      task_type: r.taskType,
      domains: r.domains,
      confidence: r.confidence,
      reuse_count: r.reuseCount,
      status: r.status,
      snippet: r.content
    }));

    return {
      task,
      classification: {
        task_type: 'auto',
        domains: { [domain.replace('_', ' ')]: 0.9 },
        complexity: 'medium'
      },
      inference_mode: 'guided',
      records: matching,
      context: `The system has learned from similar tasks:\n` + matching.map(m => `• [${m.type.toUpperCase()}] ${m.snippet}`).join('\n'),
      context_chars: 400,
      notes: { classifier: 'stub_offline' }
    };
  }
};
