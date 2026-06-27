// ============================================================
// LearnKit Dashboard — Mock Data
// All mock data for UI shell — replace with real API calls once
// production branch ships Part 5 endpoints.
// ============================================================

import type {
  DashboardMetrics,
  MemoryRecord,
  Task,
  TraceDetail,
  QuarantineRecord,
  ActivityEvent,
  SuccessRatePoint,
  TopSkill,
  ProblematicFailure,
  CrowdedOutRecord,
  Agent,
  AgentStats,
  ObservabilitySummary,
  RunTelemetry,
} from '../types';

export const MOCK_METRICS: DashboardMetrics = {
  recordCounts: {
    skill: 47,
    failure: 12,
    fact: 189,
    strategy: 8,
    preference: 5,
    heuristic: 14,
    trace: 60,
  },
  lastUpdated: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  successRate: 0.35,
  avgTokens: 2800,
  retryReduction: 0.40,
  primaryDistribution: { skill: 0.79, failure: 0.15, fact: 0.06 },
  inferenceModeMix: { prescriptive: 0.71, guided: 0.22, exploratory: 0.07 },
  retrieval: {
    avgRecordsInjected: 6.2,
    maxRecords: 8,
    avgTokensInjected: 980,
    maxTokens: 1200,
    avgRedundancy: 0.18,
    diversityLambda: 0.70,
  },
};

export const MOCK_SUCCESS_TREND: SuccessRatePoint[] = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  control: 28 + Math.sin(i * 0.4) * 6 + Math.random() * 3,
  coldStart: 32 + Math.sin(i * 0.3 + 1) * 8 + Math.random() * 4,
  warmedStart: 38 + Math.sin(i * 0.25 + 2) * 10 + i * 0.5 + Math.random() * 3,
}));

export const MOCK_TOP_SKILLS: TopSkill[] = [
  { name: 'Order Placement', helpRate: 0.92, id: 'sk-0001' },
  { name: 'Discount Code', helpRate: 0.87, id: 'sk-0002' },
  { name: 'Refund Process', helpRate: 0.75, id: 'sk-0003' },
  { name: 'Upsell Strategy', helpRate: 0.71, id: 'sk-0011' },
  { name: 'Account Reset', helpRate: 0.68, id: 'sk-0015' },
];

export const MOCK_PROBLEM_FAILURES: ProblematicFailure[] = [
  { name: 'Max Retries', hurtRate: 0.22, id: 'fr-001' },
  { name: 'Rate Limit', hurtRate: 0.33, id: 'fr-003' },
  { name: 'Timeout Error', hurtRate: 0.17, id: 'fr-002' },
];

export const MOCK_ACTIVITY: ActivityEvent[] = [
  { time: '14:32', icon: 'distill', message: 'New skill distilled: "Handle Refunds"' },
  { time: '14:15', icon: 'failure', message: 'Failure pattern created: "Max Retries Exceeded"' },
  { time: '13:48', icon: 'success', message: 'Task completed: Help rate +1 for "Order Flow"' },
  { time: '13:22', icon: 'purge', message: 'Low-quality record auto-purged (quality_score 0.2)' },
  { time: '12:55', icon: 'reinforce', message: 'Skill sk-0012 confidence updated: 0.78 → 0.83' },
  { time: '12:30', icon: 'maintain', message: 'Memory maintenance complete: 3 promoted, 1 staled' },
];

export const MOCK_RECORDS: MemoryRecord[] = [
  {
    id: 'sk-0001', type: 'skill', taskType: 'pbe_order_processing',
    domains: ['customer_support', 'ecommerce'], confidence: 0.92,
    content: 'When customers request refunds, check: 1. Order age (< 30 days for full refund) 2. Return reason (legitimate vs abuse) 3. Refund method (original payment method)',
    scope: 'user', status: 'active', retrievalCount: 12, reuseCount: 12, helpCount: 11,
    harmCount: 0, neutralCount: 1, generality: 0.8, taskOverlap: 0.25, qualityScore: 0.94,
    tags: ['customer_support', 'high_confidence'], createdAt: '2026-06-01T10:00:00Z', expiresAt: null,
  },
  {
    id: 'sk-0002', type: 'skill', taskType: 'pbe_discount_apply',
    domains: ['promotions'], confidence: 0.75,
    content: 'To apply discount codes: 1. Validate code format 2. Check expiry date 3. Apply to eligible items 4. Confirm with customer',
    scope: 'user', status: 'active', retrievalCount: 8, reuseCount: 8, helpCount: 6,
    harmCount: 1, neutralCount: 1, generality: 0.6, taskOverlap: 0.15, qualityScore: 0.78,
    tags: ['promotions'], createdAt: '2026-06-03T14:00:00Z', expiresAt: null,
  },
  {
    id: 'fr-001', type: 'failure', taskType: 'pbe_api_call',
    domains: ['api_errors'], confidence: 0.88,
    content: 'Do not retry immediately after a max-retries error. Wait 60 seconds before retrying.',
    scope: 'user', status: 'active', retrievalCount: 9, reuseCount: 9, helpCount: 7,
    harmCount: 2, neutralCount: 0, generality: 0.5, taskOverlap: 0.10, qualityScore: 0.71,
    tags: ['api', 'retry'], createdAt: '2026-06-02T09:00:00Z', expiresAt: null,
  },
  {
    id: 'ft-0001', type: 'fact', taskType: 'pbe_refund',
    domains: ['policy'], confidence: 0.95,
    content: 'Refund window is 30 days from purchase date for all standard orders.',
    scope: 'user', status: 'active', retrievalCount: 15, reuseCount: 15, helpCount: 13,
    harmCount: 0, neutralCount: 2, generality: 0.9, taskOverlap: 0.30, qualityScore: 0.97,
    tags: ['policy'], createdAt: '2026-05-28T11:00:00Z', expiresAt: null,
  },
  {
    id: 'st-0001', type: 'strategy', taskType: 'pbe_customer_escalation',
    domains: ['customer_support'], confidence: 0.72,
    content: 'For angry customers: 1. Acknowledge frustration 2. Apologize without admitting fault 3. Offer concrete resolution within 24h 4. Follow up',
    scope: 'user', status: 'active', retrievalCount: 5, reuseCount: 5, helpCount: 4,
    harmCount: 0, neutralCount: 1, generality: 0.7, taskOverlap: 0.20, qualityScore: 0.85,
    tags: ['customer_support', 'escalation'], createdAt: '2026-06-04T16:00:00Z', expiresAt: null,
  },
  {
    id: 'pr-0001', type: 'preference', taskType: 'pbe_communication',
    domains: ['tone'], confidence: 0.99,
    content: 'Customer prefers formal English, avoids emoji in professional communication.',
    scope: 'user', status: 'active', retrievalCount: 22, reuseCount: 22, helpCount: 22,
    harmCount: 0, neutralCount: 0, generality: 1.0, taskOverlap: 0.80, qualityScore: 0.99,
    tags: ['preference', 'tone'], createdAt: '2026-05-25T08:00:00Z', expiresAt: null,
  },
  {
    id: 'hu-0001', type: 'heuristic', taskType: 'pbe_review',
    domains: ['quality'], confidence: 0.65,
    content: 'Short responses (< 50 words) usually score lower on customer satisfaction. Aim for 80–200 words.',
    scope: 'user', status: 'quarantine', retrievalCount: 3, reuseCount: 3, helpCount: 2,
    harmCount: 1, neutralCount: 0, generality: 0.6, taskOverlap: 0.12, qualityScore: 0.60,
    tags: ['heuristic', 'quality'], createdAt: '2026-06-10T12:00:00Z', expiresAt: '2026-07-10T12:00:00Z',
  },
  {
    id: 'tr-0001', type: 'trace', taskType: 'pbe_refund',
    domains: ['customer_support'], confidence: 0.55,
    content: 'Trace of successful refund processing for ORD-12345: checked age (5d < 30d ✓), verified reason, processed to original card.',
    scope: 'user', status: 'active', retrievalCount: 2, reuseCount: 2, helpCount: 2,
    harmCount: 0, neutralCount: 0, generality: 0.3, taskOverlap: 0.05, qualityScore: 0.80,
    tags: ['trace', 'refund'], createdAt: '2026-06-05T14:32:00Z', expiresAt: '2026-09-05T14:32:00Z',
  },
  {
    id: 'fr-002', type: 'failure', taskType: 'pbe_api_call',
    domains: ['api_errors'], confidence: 0.72,
    content: 'Timeout errors on the /checkout endpoint are transient. Add a 3-second delay and retry once.',
    scope: 'user', status: 'active', retrievalCount: 6, reuseCount: 6, helpCount: 5,
    harmCount: 1, neutralCount: 0, generality: 0.4, taskOverlap: 0.08, qualityScore: 0.75,
    tags: ['api', 'timeout'], createdAt: '2026-06-01T15:00:00Z', expiresAt: null,
  },
  {
    id: 'fr-003', type: 'failure', taskType: 'pbe_api_call',
    domains: ['api_errors'], confidence: 0.65,
    content: 'Rate limit (HTTP 429): wait 60 seconds before retrying. Immediate retry will fail.',
    scope: 'user', status: 'active', retrievalCount: 12, reuseCount: 12, helpCount: 8,
    harmCount: 4, neutralCount: 0, generality: 0.5, taskOverlap: 0.10, qualityScore: 0.62,
    tags: ['api', 'rate-limit'], createdAt: '2026-06-02T09:30:00Z', expiresAt: null,
  },
];

const tel = (
  latencyMs: number,
  total: number,
  cost: number,
  model: string,
  labels: string[],
): RunTelemetry => ({
  latencyMs,
  promptTokens: Math.round(total * 0.82),
  completionTokens: Math.round(total * 0.18),
  totalTokens: total,
  contextTokens: Math.round(total * 0.3),
  costUsd: cost,
  model,
  models: { classifier: model, evaluator: model, distiller: model },
  estimated: true,
  labels,
});

export const MOCK_TASKS: Task[] = [
  { id: 't-047', input: 'Refund Request Processing for ORD-12345', status: 'success', score: 5.0, armName: 'warmed', timestamp: '2026-06-13T14:32:00Z', agentId: 'agent-support', toolCalls: 3, callsReduced: 4, telemetry: tel(1840, 1920, 0.0021, 'anthropic/claude-haiku-4-5', ['replayed', 'refund', 'calls-reduced']) },
  { id: 't-046', input: 'Apply discount code SUMMER20 to cart', status: 'success', score: 4.8, armName: 'warmed', timestamp: '2026-06-13T14:15:00Z', agentId: 'agent-support', toolCalls: 2, callsReduced: 3, telemetry: tel(1520, 1610, 0.0017, 'anthropic/claude-haiku-4-5', ['replayed', 'discount', 'calls-reduced']) },
  { id: 't-045', input: 'Escalate complaint about delayed shipment', status: 'success', score: 4.2, armName: 'guided', timestamp: '2026-06-13T13:48:00Z', agentId: 'agent-support', toolCalls: 5, callsReduced: 1, telemetry: tel(2630, 2840, 0.0036, 'anthropic/claude-haiku-4-5', ['escalation']) },
  { id: 't-044', input: 'Handle API max retries during checkout', status: 'failure', score: 1.5, armName: 'warmed', timestamp: '2026-06-13T13:22:00Z', agentId: 'agent-sql', toolCalls: 7, callsReduced: 0, telemetry: tel(3920, 3450, 0.0044, 'anthropic/claude-haiku-4-5', ['replayed', 'api']) },
  { id: 't-043', input: 'Generate monthly sales report summary', status: 'success', score: 4.9, armName: 'warmed', timestamp: '2026-06-13T12:55:00Z', agentId: 'agent-sql', toolCalls: 2, callsReduced: 5, telemetry: tel(2180, 2950, 0.0061, 'anthropic/claude-sonnet-4', ['sql', 'calls-reduced']) },
  { id: 't-042', input: 'Answer customer question about return policy', status: 'success', score: 5.0, armName: 'prescriptive', timestamp: '2026-06-13T12:30:00Z', agentId: 'agent-support', toolCalls: 1, callsReduced: 4, telemetry: tel(1190, 980, 0.0011, 'anthropic/claude-haiku-4-5', ['replayed', 'policy', 'calls-reduced']) },
  { id: 't-041', input: 'Process bulk order for enterprise client', status: 'failure', score: 2.1, armName: 'exploratory', timestamp: '2026-06-13T11:45:00Z', agentId: 'agent-sql', toolCalls: 8, callsReduced: 0, telemetry: tel(4510, 4120, 0.0078, 'anthropic/claude-sonnet-4', ['bulk']) },
  { id: 't-040', input: 'Update customer preference for email frequency', status: 'success', score: 4.7, armName: 'warmed', timestamp: '2026-06-13T11:20:00Z', agentId: 'agent-support', toolCalls: 2, callsReduced: 3, telemetry: tel(1430, 1280, 0.0014, 'anthropic/claude-haiku-4-5', ['replayed', 'preference', 'calls-reduced']) },
];

export const MOCK_AGENTS: Agent[] = [
  { id: 'agent-support', name: 'Support Agent', taskCount: 5, successRate: 1.0, callsReduced: 17, skillsLearned: 4, avgScore: 4.84, totalTokens: 8770, totalCost: 0.0074, avgLatencyMs: 1474, createdAt: '2026-06-13T11:20:00Z', lastActive: '2026-06-13T14:32:00Z' },
  { id: 'agent-sql', name: 'SQL Authoring Agent', taskCount: 3, successRate: 0.33, callsReduced: 5, skillsLearned: 1, avgScore: 2.83, totalTokens: 10520, totalCost: 0.0183, avgLatencyMs: 3650, createdAt: '2026-06-13T11:45:00Z', lastActive: '2026-06-13T13:22:00Z' },
];

export const MOCK_AGENT_STATS: Record<string, AgentStats> = {
  'agent-support': {
    agentId: 'agent-support', agentName: 'Support Agent', taskCount: 5,
    successRate: 1.0, callsReduced: 17, totalToolCalls: 10, skillsLearned: 4,
    curve: [
      { index: 1, task: 'Update customer preference', toolCalls: 6, baselineCalls: 6, callsReduced: 0, replayed: false, outcome: 'success', score: 4.7, cumulativeSkills: 1, successRate: 1.0, timestamp: '2026-06-13T11:20:00Z' },
      { index: 2, task: 'Answer return policy question', toolCalls: 3, baselineCalls: 6, callsReduced: 3, replayed: false, outcome: 'success', score: 5.0, cumulativeSkills: 2, successRate: 1.0, timestamp: '2026-06-13T12:30:00Z' },
      { index: 3, task: 'Escalate complaint', toolCalls: 5, baselineCalls: 6, callsReduced: 1, replayed: true, outcome: 'success', score: 4.2, cumulativeSkills: 2, successRate: 1.0, timestamp: '2026-06-13T13:48:00Z' },
      { index: 4, task: 'Apply discount code', toolCalls: 2, baselineCalls: 5, callsReduced: 3, replayed: true, outcome: 'success', score: 4.8, cumulativeSkills: 2, successRate: 1.0, timestamp: '2026-06-13T14:15:00Z' },
      { index: 5, task: 'Refund request processing', toolCalls: 1, baselineCalls: 5, callsReduced: 4, replayed: true, outcome: 'success', score: 5.0, cumulativeSkills: 2, successRate: 1.0, timestamp: '2026-06-13T14:32:00Z' },
    ],
  },
  'agent-sql': {
    agentId: 'agent-sql', agentName: 'SQL Authoring Agent', taskCount: 3,
    successRate: 0.33, callsReduced: 5, totalToolCalls: 17, skillsLearned: 1,
    curve: [
      { index: 1, task: 'Generate sales report summary', toolCalls: 2, baselineCalls: 7, callsReduced: 5, replayed: false, outcome: 'success', score: 4.9, cumulativeSkills: 1, successRate: 1.0, timestamp: '2026-06-13T12:55:00Z' },
      { index: 2, task: 'Process bulk order', toolCalls: 8, baselineCalls: 7, callsReduced: 0, replayed: false, outcome: 'failure', score: 2.1, cumulativeSkills: 1, successRate: 0.5, timestamp: '2026-06-13T11:45:00Z' },
      { index: 3, task: 'Handle API max retries', toolCalls: 7, baselineCalls: 7, callsReduced: 0, replayed: true, outcome: 'failure', score: 1.5, cumulativeSkills: 1, successRate: 0.33, timestamp: '2026-06-13T13:22:00Z' },
    ],
  },
};

export const MOCK_OBSERVABILITY: ObservabilitySummary = {
  lastUpdated: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  estimated: true,
  totals: {
    runs: 8,
    promptTokens: 15820,
    completionTokens: 3470,
    totalTokens: 19290,
    costUsd: 0.0282,
    avgTokensPerRun: 2411,
    avgCostPerRun: 0.0035,
  },
  latency: { avgMs: 2402, p50Ms: 2010, p95Ms: 4380, p99Ms: 4510 },
  models: [
    { model: 'anthropic/claude-haiku-4-5', runs: 6, tokens: 9670, costUsd: 0.0118 },
    { model: 'anthropic/claude-sonnet-4', runs: 2, tokens: 9620, costUsd: 0.0164 },
  ],
  timeseries: [
    { date: '2026-06-09', tokens: 4200, costUsd: 0.0061, runs: 2, avgLatencyMs: 2200 },
    { date: '2026-06-10', tokens: 5100, costUsd: 0.0074, runs: 3, avgLatencyMs: 2480 },
    { date: '2026-06-11', tokens: 3600, costUsd: 0.0052, runs: 1, avgLatencyMs: 1980 },
    { date: '2026-06-12', tokens: 2900, costUsd: 0.0041, runs: 1, avgLatencyMs: 3650 },
    { date: '2026-06-13', tokens: 3490, costUsd: 0.0054, runs: 1, avgLatencyMs: 1840 },
  ],
};

export const MOCK_TRACE: TraceDetail = {
  taskId: 't-047',
  input: 'Customer john@example.com requesting refund for ORD-12345 ($125.00). "I want to return items, had a processing issue"',
  inferenceMode: 'prescriptive',
  memoryRetrieval: {
    budget: { recordsUsed: 4, maxRecords: 8, tokensUsed: 640, maxTokens: 1200, diversityLambda: 0.70, redundancy: 0.12 },
    matches: [
      { recordId: 'sk-0001', type: 'skill', confidence: 0.92, score: 1.02, reason: 'Skill bonus +0.10', droppedByMmr: false, primary: true },
      { recordId: 'fr-003', type: 'failure', confidence: 0.70, score: 0.70, reason: 'Direct failure match', droppedByMmr: false, primary: false },
      { recordId: 'ft-0001', type: 'fact', confidence: 0.65, score: 0.65, reason: 'Fact about refund policy', droppedByMmr: false, primary: false },
      { recordId: 'tr-0001', type: 'trace', confidence: 0.55, score: 0.55, reason: 'Similar past trace', droppedByMmr: false, primary: false },
    ],
  },
  reasoning: {
    attempts: [{
      prompt: 'Customer requests $125 refund for ORD-12345...',
      response: 'Checking order status... Order placed 5 days ago ✓\nReason appears legitimate ✓\nProcessing refund to original card... ✓\nNotifying customer... ✓\n[RESPONSE] "Your $125 refund has been processed."',
      feedback: 'Match: YES | Score: 5.0',
    }],
  },
  output: 'Your $125 refund has been processed.',
  expected: 'Your $125 refund has been processed.',
  score: 5.0,
  attribution: [
    { recordId: 'sk-0001', rank: 1, primary: true, reuseCount: 11, helped: true },
    { recordId: 'fr-003', rank: 2, primary: false, reuseCount: 3, helped: null },
  ],
};

export const MOCK_QUARANTINE: QuarantineRecord[] = [
  {
    id: 'hu-0001', type: 'heuristic',
    content: 'Short responses (< 50 words) usually score lower. Aim for 80–200 words.',
    confidence: 0.65,
    createdAt: '2026-06-10T12:00:00Z',
    promotableAfter: '2026-06-11T12:00:00Z',
  },
  {
    id: 'sk-0099', type: 'skill',
    content: 'New approach for handling bulk discounts with tiered pricing...',
    confidence: 0.55,
    createdAt: '2026-06-12T09:00:00Z',
    promotableAfter: '2026-06-13T09:00:00Z',
  },
];

export const MOCK_CROWDED_OUT: CrowdedOutRecord[] = [
  { id: 'sk-0044', snippet: '"upsert variant B" — alternative refund path', relevance: 0.88, overlap: 0.91, competitorId: 'sk-0001' },
  { id: 'ft-0022', snippet: 'Refund deadline is 30 days (duplicate phrasing)', relevance: 0.82, overlap: 0.87, competitorId: 'ft-0001' },
];
