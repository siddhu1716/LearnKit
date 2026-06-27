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

export interface Task {
  id: string;
  input: string;
  status: 'success' | 'failure';
  score: number;
  armName: string;
  timestamp: string;
  agentId?: string;
  toolCalls?: number;
  callsReduced?: number;
}

export interface Agent {
  id: string;
  name: string;
  taskCount: number;
  successRate: number;
  callsReduced: number;
  skillsLearned: number;
  avgScore: number | null;
  createdAt: string | null;
  lastActive: string | null;
}

export interface AgentCurvePoint {
  index: number;
  task: string;
  toolCalls: number;
  baselineCalls: number | null;
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
  curve: AgentCurvePoint[];
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
