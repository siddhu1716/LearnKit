// ============================================================
// LearnKit Dashboard — TypeScript types
// Mirrors API contract from FRONTEND_DESIGN_DOCUMENT.md Part 5
// ============================================================

export type RecordType =
  | 'skill'
  | 'fact'
  | 'failure'
  | 'strategy'
  | 'preference'
  | 'heuristic'
  | 'trace';

export type RecordStatus = 'active' | 'quarantine' | 'stale';

export interface MemoryRecord {
  id: string;
  type: RecordType;
  taskType: string;
  domains: string[];
  confidence: number;
  content: string;
  scope: string;
  status: RecordStatus;
  retrievalCount: number;
  reuseCount: number;
  helpCount: number;
  harmCount: number;
  neutralCount: number;
  generality: number;
  taskOverlap: number;
  qualityScore: number;
  tags: string[];
  createdAt: string;
  expiresAt: string | null;
  isProcedural?: boolean;
  stepCount?: number;
}

export interface RecordCounts {
  skill: number;
  failure: number;
  fact: number;
  strategy: number;
  preference: number;
  heuristic: number;
  trace: number;
}

export interface RetrievalMetrics {
  avgRecordsInjected: number;
  maxRecords: number;
  avgTokensInjected: number;
  maxTokens: number;
  avgRedundancy: number;
  diversityLambda: number;
}

export interface DashboardMetrics {
  recordCounts: RecordCounts;
  lastUpdated: string;
  successRate: number;
  avgTokens: number;
  retryReduction: number;
  primaryDistribution: { skill: number; failure: number; fact: number };
  inferenceModeMix: { prescriptive: number; guided: number; exploratory: number };
  retrieval: RetrievalMetrics;
}

export interface RunTelemetry {
  latencyMs: number | null;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  contextTokens: number;
  costUsd: number;
  model: string | null;
  models: Record<string, string>;
  estimated: boolean;
  labels: string[];
}

export interface Task {
  id: string;
  input: string;
  status: 'success' | 'failure';
  score: number;
  armName: string;
  timestamp: string;
  agentId?: string;
  mode?: 'learn' | 'agent_learn';
  toolCalls?: number;
  llmCalls?: number;
  callsReduced?: number;
  telemetry?: RunTelemetry;
}

export interface Agent {
  id: string;
  name: string;
  taskCount: number;
  successRate: number;
  callsReduced: number;
  skillsLearned: number;
  avgScore: number | null;
  totalTokens?: number;
  totalCost?: number;
  avgLatencyMs?: number | null;
  createdAt: string | null;
  lastActive: string | null;
}

export interface AgentCurvePoint {
  index: number;
  task: string;
  toolCalls: number;
  baselineCalls: number | null;
  llmCalls: number;
  baselineLlmCalls: number | null;
  callsReduced: number;
  replayed: boolean;
  outcome: string | null;
  score: number;
  cumulativeSkills: number;
  successRate: number;
  timestamp: string | null;
}

export interface AgentStats {
  agentId: string;
  agentName: string;
  taskCount: number;
  successRate: number;
  callsReduced: number;
  totalToolCalls: number;
  skillsLearned: number;
  totalTokens?: number;
  totalCost?: number;
  avgLatencyMs?: number | null;
  curve: AgentCurvePoint[];
}

export interface ModelUsage {
  model: string;
  runs: number;
  tokens: number;
  costUsd: number;
}

export interface ObservabilityPoint {
  date: string;
  tokens: number;
  costUsd: number;
  runs: number;
  avgLatencyMs: number | null;
}

export interface ObservabilitySummary {
  lastUpdated: string;
  estimated: boolean;
  totals: {
    runs: number;
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    costUsd: number;
    avgTokensPerRun: number;
    avgCostPerRun: number;
  };
  latency: {
    avgMs: number | null;
    p50Ms: number | null;
    p95Ms: number | null;
    p99Ms: number | null;
  };
  models: ModelUsage[];
  timeseries: ObservabilityPoint[];
}

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  author: string;
  date: string;
  readingMinutes: number;
  tags: string[];
  body: string;
}

export interface TraceMatch {
  recordId: string;
  type: RecordType;
  confidence: number;
  score: number;
  reason: string;
  droppedByMmr: boolean;
  primary: boolean;
}

export interface TraceDetail {
  taskId: string;
  input: string;
  inferenceMode: 'prescriptive' | 'guided' | 'exploratory';
  memoryRetrieval: {
    budget: {
      recordsUsed: number;
      maxRecords: number;
      tokensUsed: number;
      maxTokens: number;
      diversityLambda: number;
      redundancy: number;
    };
    matches: TraceMatch[];
  };
  reasoning: { attempts: { prompt: string; response: string; feedback: string }[] };
  output: string;
  expected: string;
  score: number;
  attribution: {
    recordId: string;
    rank: number;
    primary: boolean;
    reuseCount: number;
    helped: boolean | null;
  }[];
}

export interface QuarantineRecord {
  id: string;
  type: RecordType;
  content: string;
  confidence: number;
  createdAt: string;
  promotableAfter: string;
}

export interface ActivityEvent {
  time: string;
  icon: string;
  message: string;
}

export interface SuccessRatePoint {
  day: number;
  control: number;
  coldStart: number;
  warmedStart: number;
}

export interface TopSkill {
  name: string;
  helpRate: number;
  id: string;
}

export interface ProblematicFailure {
  name: string;
  hurtRate: number;
  id: string;
}

export interface CrowdedOutRecord {
  id: string;
  snippet: string;
  relevance: number;
  overlap: number;
  competitorId: string;
}

// --- Benchmark matrix (reproducible proof artifact) ---

export interface BenchmarkReact {
  cold_llm_calls: number;
  warmed_llm_calls: number;
  reduction_pct: number;
  success: string;
}

export interface BenchmarkEvolution extends BenchmarkReact {
  evolved: boolean;
}

export interface BenchmarkCombined {
  cold: number;
  warmed: number;
  reduction_pct: number;
}

export interface BenchmarkInjection {
  procedure_avg_score: number;
  playbook_avg_score: number;
  pass_k_full: number;
}

export interface BenchmarkGate {
  metric: string;
  threshold: number;
  observed: number;
  pass: boolean;
}

/** Raw per-task benchmark blocks captured in the pinned suite-summary. */
export interface BenchmarkTasks {
  react_live?: Record<string, number | boolean>;
  evolution_live?: Record<string, number | boolean | unknown>;
  injection_ablation?: Record<string, number | boolean>;
}

export interface BenchmarkModelRow {
  name: string;
  display: string;
  model: string;
  base_url: string;
  gate: BenchmarkGate;
  quality_lift: number;
  react: BenchmarkReact;
  evolution: BenchmarkEvolution;
  combined_llm_calls: BenchmarkCombined;
  injection: BenchmarkInjection;
  provenance: { source: string; run_generated_at: string | null };
  tasks?: BenchmarkTasks;
  run_generated_at?: string | null;
}

export interface BenchmarkMatrix {
  available: boolean;
  reason?: string;
  suite?: string;
  generated_at?: string;
  gate?: { metric: string; threshold: number; definition: string };
  run_config?: { trials: number; k: number; seed: number; temperature: number; max_output_tokens: number };
  reproduce_command?: string;
  summary?: {
    models_total: number;
    models_passing: number;
    best_quality_lift: number | null;
    best_quality_lift_model: string | null;
    pooled_llm_call_reduction_pct: number;
  };
  models: BenchmarkModelRow[];
}

