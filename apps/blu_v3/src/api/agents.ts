import { supabase } from '@blu/auth'

export interface ClientEnabledAgent {
  client_id: string
  agent_slug: string
  current_status: string
  last_activity_at: string | null
  pending_count: number
  agent_catalog: {
    name: string
    description: string | null
  } | null
}

export interface AgentReadiness {
  agent_slug: string
  is_ready: boolean
  missing_requirements: string[]
  readiness_score: number
}

export async function fetchAgents(clientId: string): Promise<ClientEnabledAgent[]> {
  const { data, error } = await supabase
    .from('client_enabled_agents')
    .select(`
      client_id,
      agent_slug,
      current_status,
      last_activity_at,
      pending_count,
      agent_catalog (
        name,
        description
      )
    `)
    .eq('client_id', clientId)
    .order('agent_slug')

  if (error) throw error
  return (data ?? []) as unknown as ClientEnabledAgent[]
}

export async function fetchAgentReadiness(clientId: string): Promise<AgentReadiness[]> {
  const { data, error } = await supabase.rpc('get_agent_readiness', {
    p_client_id: clientId,
  })
  if (error) throw error
  return (data ?? []) as AgentReadiness[]
}
