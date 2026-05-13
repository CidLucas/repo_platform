import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import { getSyncHistory, startSync } from '../api/connectors'

export function useConnectorStatus(credentialId: string | null, pollIntervalMs = 10_000) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['connectorSyncHistory', clientId, credentialId],
    queryFn: () => getSyncHistory(credentialId!, 5),
    enabled: !!credentialId && !!clientId,
    refetchInterval: pollIntervalMs,
    staleTime: 5_000,
  })
}

export function useStartSync() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (credentialId: string) => startSync(credentialId),
    onSuccess: (_data, credentialId) => {
      qc.invalidateQueries({ queryKey: ['connectorSyncHistory', clientId, credentialId] })
    },
  })
}
