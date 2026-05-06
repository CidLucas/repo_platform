import type { AgentDefinition } from '@/types/agent'

export const AGENTS: AgentDefinition[] = [
  {
    slug: 'compras',
    name: 'Compras',
    route: '/compras',
    shape: 'circle',
    color: '#f59e0b',
    glowColor: 'rgba(245,158,11,0.5)',
  },
  {
    slug: 'financeiro',
    name: 'Financeiro',
    route: '/financeiro',
    shape: 'circle',
    color: '#10b981',
    glowColor: 'rgba(16,185,129,0.5)',
  },
  {
    slug: 'agenda',
    name: 'Agenda',
    route: '/agenda',
    shape: 'circle',
    color: '#a855f7',
    glowColor: 'rgba(168,85,247,0.5)',
  },
  {
    slug: 'documentos',
    name: 'Documentos',
    route: '/documentos',
    shape: 'circle',
    color: '#06b6d4',
    glowColor: 'rgba(6,182,212,0.5)',
  },
  {
    slug: 'estrategia',
    name: 'Estratégia',
    route: '/estrategia',
    shape: 'circle',
    color: '#3b82f6',
    glowColor: 'rgba(59,130,246,0.5)',
  },
  {
    slug: 'clientes',
    name: 'Clientes',
    route: '/clientes',
    shape: 'circle',
    color: '#f97316',
    glowColor: 'rgba(249,115,22,0.5)',
  },
]

export const AGENT_MAP = Object.fromEntries(
  AGENTS.map((a) => [a.slug, a])
) as Record<string, AgentDefinition>

export const ORB_SIZES = {
  nav: 20,
  card: 24,
  room: 32,
  hero: 48,
} as const

export const QUERY_KEYS = {
  approvals: (clientId: string) => ['approvals', 'pending', clientId] as const,
  approvalsByAgent: (agentSlug: string, clientId: string) =>
    ['approvals', agentSlug, clientId] as const,
  // analytics_v2 — RLS filters by JWT, no clientId needed
  insights: ['insights'] as const,
  kpi: (period: string) => ['kpi', period] as const,
  timeSeries: (period: string) => ['timeseries', period] as const,
  recentActivity: ['recent-activity'] as const,
  // client-scoped
  agents: (clientId: string) => ['agents', clientId] as const,
  agentReadiness: (clientId: string) => ['agent-readiness', clientId] as const,
  notifications: (clientId: string) => ['notifications', clientId] as const,
  approvalStats: (clientId: string) => ['approval-stats', clientId] as const,
} as const
