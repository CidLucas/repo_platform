import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import { fetchAgents, fetchAgentReadiness } from '../api/agents'

export function useAgents() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['agents', clientId],
    queryFn: () => fetchAgents(clientId!),
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}

export function useAgentReadiness() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['agentReadiness', clientId],
    queryFn: () => fetchAgentReadiness(clientId!),
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}
