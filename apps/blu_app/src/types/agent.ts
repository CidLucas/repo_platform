export type AgentSlug =
  | 'compras'
  | 'financeiro'
  | 'agenda'
  | 'documentos'
  | 'estrategia'
  | 'clientes'

export type AgentStatus = 'idle' | 'working' | 'attention' | 'offline'

export type KnowledgeReadinessStatus = 'ready' | 'partial' | 'blocked'

export type OrbShape =
  | 'hexagon'
  | 'circle'
  | 'triangle'
  | 'square'
  | 'diamond'
  | 'pentagon'

export interface AgentDefinition {
  slug: AgentSlug
  name: string
  route: string
  shape: OrbShape
  /** Orb inner fill color (hex) */
  color: string
  /** Orb glow rgba string */
  glowColor: string
}

export interface ClientEnabledAgent {
  client_id: string
  agent_slug: AgentSlug
  current_status: AgentStatus
  last_activity_at: string | null
  pending_count: number
  agent_catalog: {
    name: string
    description: string | null
  } | null
}

/** Returned by get_agent_readiness RPC */
export interface AgentReadiness {
  agent_slug: AgentSlug
  agent_name: string
  tier_required: string | null
  is_enabled: boolean
  status: KnowledgeReadinessStatus
  capability: 'full' | 'partial'
  min_coverage_pct: number
  nice_coverage_pct: number
  /** Names of minimum-requirement docs that are still missing */
  missing_docs: string[]
}
