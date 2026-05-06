import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { fetchAgents, fetchAgentReadiness } from '@/api/agents'
import { QUERY_KEYS, AGENT_MAP } from '@/utils/constants'
import type { AgentDefinition, AgentReadiness } from '@/types/agent'

export function useAgents() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.agents(clientId ?? ''),
    queryFn: () => fetchAgents(clientId!),
    enabled: !!clientId,
  })
}

/** Fetches knowledge readiness (ready/partial/blocked) for all enabled agents. */
export function useAgentReadiness() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.agentReadiness(clientId ?? ''),
    queryFn: () => fetchAgentReadiness(clientId!),
    enabled: !!clientId,
    staleTime: 60_000,
  })
}

/** Returns a slug → readiness map for O(1) lookups in components. */
export function useAgentReadinessMap(): Record<string, AgentReadiness> {
  const { data = [] } = useAgentReadiness()
  return Object.fromEntries(data.map((r) => [r.agent_slug, r]))
}

/** Returns the static definition for an agent slug */
export function useAgentDefinition(slug: string): AgentDefinition | undefined {
  return AGENT_MAP[slug]
}
