import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import styles from './DocsHub.module.css';
import markdownStyles from './Markdown.module.css';
import { FileText, BookOpen, Server, Network, GitBranch, type LucideIcon } from 'lucide-react';

interface DocSection {
  id: string;
  label: string;
  icon: LucideIcon;
  body: string;
}

const DOC_SECTIONS: DocSection[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: BookOpen,
    body: `# LearnKit Dashboard

The dashboard is a local-first control room for an agent's self-improving
memory. It talks to the FastAPI server in \`Docs/server.py\` and gracefully
falls back to mock data + \`localStorage\` when the backend is offline.

## Pages at a glance

- **Dashboard** — record counts, success rate, and live activity.
- **Observability** — token usage, latency percentiles, cost, and model
  breakdown for every run.
- **Agents** — per-agent learning curves (tool calls down, skills up).
- **Memory Explorer** — browse skills, facts, failures, and more by type.
- **Retrieval Quality** — diversity and redundancy of injected context.
- **Task History / Trace** — replay any run with its retrieved memories.
- **Memory Lifecycle** — quarantine, promotion, decay, and purge.

> Everything renders in this single-page app — docs and blog included — so you
> never lose your place by opening a new tab.`,
  },
  {
    id: 'api',
    label: 'API contract',
    icon: Network,
    body: `# API contract

The dashboard reads from the \`/api/v1\` namespace. Each call falls back to
local simulation if the request fails.

## Core endpoints

\`\`\`text
GET  /healthz
GET  /api/domains
POST /api/inspect
GET  /api/v1/metrics
GET  /api/v1/records            ?type= &status=
GET  /api/v1/records/{id}
GET  /api/v1/tasks              ?status= &agentId=
GET  /api/v1/tasks/{id}/trace
GET  /api/v1/agents
GET  /api/v1/agents/{id}/stats
GET  /api/v1/observability      ?agentId=
GET  /api/v1/activity
\`\`\`

## Observability payload

\`/api/v1/observability\` returns token, latency, and cost aggregates plus a
per-model breakdown and a daily time series:

\`\`\`json
{
  "estimated": true,
  "totals": { "totalTokens": 19290, "costUsd": 0.0282 },
  "latency": { "avgMs": 2402, "p95Ms": 4380 },
  "models": [{ "model": "anthropic/claude-haiku-4-5", "tokens": 9670 }],
  "timeseries": [{ "date": "2026-06-13", "tokens": 3490 }]
}
\`\`\``,
  },
  {
    id: 'telemetry',
    label: 'Telemetry',
    icon: Server,
    body: `# How telemetry is captured

LearnKit calls models through DSPy, which does not expose per-call token usage
in a stable way. Rather than show nothing, the platform measures what it can and
estimates the rest — clearly flagged with an \`est.\` badge.

## Measured directly

- **Latency** — wall-clock time around each run via \`time.perf_counter()\`.
- **Model names** — resolved from config and environment overrides.
- **Context size** — characters of injected context, converted to tokens.

## Estimated

- **Prompt / completion tokens** — sized from the text volume across the
  classify, judge, and distill stages (~4 chars per token).
- **Cost** — each stage priced against a per-model rate table in
  \`learnkit/observability.py\`.

## Storage

Telemetry is persisted alongside each run in the \`runs\` table
(\`latency_ms\`, \`total_tokens\`, \`cost_usd\`, \`models\`, \`estimated\`),
with an automatic column migration for older databases.`,
  },
  {
    id: 'branches',
    label: 'Branch plan',
    icon: GitBranch,
    body: `# Branch plan

The repo splits ownership cleanly:

- **production** — owns backend endpoints, persistence, and the memory loop.
- **frontend** — owns the React dashboard and shared UI components.

Keep the API contract above as the seam between the two. Frontend work should
degrade gracefully when an endpoint is missing; backend work should keep the
contract stable and additive.`,
  },
];

export const DocsHub: React.FC = () => {
  const [active, setActive] = useState(DOC_SECTIONS[0].id);
  const section = DOC_SECTIONS.find((s) => s.id === active) ?? DOC_SECTIONS[0];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <FileText size={22} className={styles.titleIcon} />
          <h1 className={styles.title}>Documentation</h1>
        </div>
        <p className={styles.subtitle}>
          Dashboard guide, API contract, and telemetry internals — all in-app.
        </p>
      </header>

      <div className={styles.layout}>
        <nav className={styles.toc} aria-label="Documentation sections">
          {DOC_SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <button
                key={s.id}
                className={`${styles.tocItem} ${active === s.id ? styles.tocActive : ''}`}
                onClick={() => setActive(s.id)}
              >
                <Icon size={16} />
                <span>{s.label}</span>
              </button>
            );
          })}
        </nav>

        <article className={styles.content}>
          <div className={markdownStyles.markdown}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.body}</ReactMarkdown>
          </div>
        </article>
      </div>
    </div>
  );
};

export default DocsHub;

