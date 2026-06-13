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
  { time: '14:32', icon: '📚', message: 'New skill distilled: "Handle Refunds"' },
  { time: '14:15', icon: '❌', message: 'Failure pattern created: "Max Retries Exceeded"' },
  { time: '13:48', icon: '✅', message: 'Task completed: Help rate +1 for "Order Flow"' },
  { time: '13:22', icon: '🗑️', message: 'Low-quality record auto-purged (quality_score 0.2)' },
  { time: '12:55', icon: '🔄', message: 'Skill sk-0012 confidence updated: 0.78 → 0.83' },
  { time: '12:30', icon: '📊', message: 'Memory maintenance complete: 3 promoted, 1 staled' },
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

export const MOCK_TASKS: Task[] = [
  { id: 't-047', input: 'Refund Request Processing for ORD-12345', status: 'success', score: 5.0, armName: 'warmed', timestamp: '2026-06-13T14:32:00Z' },
  { id: 't-046', input: 'Apply discount code SUMMER20 to cart', status: 'success', score: 4.8, armName: 'warmed', timestamp: '2026-06-13T14:15:00Z' },
  { id: 't-045', input: 'Escalate complaint about delayed shipment', status: 'success', score: 4.2, armName: 'guided', timestamp: '2026-06-13T13:48:00Z' },
  { id: 't-044', input: 'Handle API max retries during checkout', status: 'failure', score: 1.5, armName: 'warmed', timestamp: '2026-06-13T13:22:00Z' },
  { id: 't-043', input: 'Generate monthly sales report summary', status: 'success', score: 4.9, armName: 'warmed', timestamp: '2026-06-13T12:55:00Z' },
  { id: 't-042', input: 'Answer customer question about return policy', status: 'success', score: 5.0, armName: 'prescriptive', timestamp: '2026-06-13T12:30:00Z' },
  { id: 't-041', input: 'Process bulk order for enterprise client', status: 'failure', score: 2.1, armName: 'exploratory', timestamp: '2026-06-13T11:45:00Z' },
  { id: 't-040', input: 'Update customer preference for email frequency', status: 'success', score: 4.7, armName: 'warmed', timestamp: '2026-06-13T11:20:00Z' },
];

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
