import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import {
  fetchPendingApprovals,
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
} from '../api/approvals'

export function usePendingApprovals() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['approvals', 'pending', clientId],
    queryFn: () => fetchPendingApprovals(clientId!),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  })
}

export function useApprovalsByAgent(agentSlug: string) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['approvals', agentSlug, clientId],
    queryFn: () => fetchApprovalsByAgent(agentSlug, clientId!),
    enabled: !!clientId,
  })
}

export function useApproveRequest() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
    },
  })
}

export function useRejectRequest() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
    },
  })
}

export function useSnoozeRequest() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, snoozeUntil }: { id: string; snoozeUntil: string }) =>
      snoozeApproval(id, clientId!, snoozeUntil),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
    },
  })
}
