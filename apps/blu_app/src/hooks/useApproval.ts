import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import {
  fetchPendingApprovals,
  fetchApprovalsByAgent,
  approveRequest,
  rejectRequest,
  snoozeApproval,
} from '@/api/approvals'
import { fetchApprovalStats } from '@/api/approval-stats'
import { getPendingMilestones } from '@/hooks/useApprovalStats'
import { QUERY_KEYS } from '@/utils/constants'

export function usePendingApprovals() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.approvals(clientId ?? ''),
    queryFn: () => fetchPendingApprovals(clientId!),
    enabled: !!clientId,
  })
}

export function useApprovalsByAgent(agentSlug: string) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.approvalsByAgent(agentSlug, clientId ?? ''),
    queryFn: () => fetchApprovalsByAgent(agentSlug, clientId!),
    enabled: !!clientId,
  })
}

/** After approve/reject, re-fetch approval stats and detect milestone crossings */
async function detectMilestones(
  clientId: string,
  onMilestone: (totalApproved: number) => void
) {
  try {
    const stats = await fetchApprovalStats(clientId)
    if (stats) {
      const pending = getPendingMilestones(stats.total_approved)
      if (pending.length > 0) {
        onMilestone(stats.total_approved)
      }
    }
  } catch {
    // Non-critical — don't block the UI
  }
}

export function useApproveRequest(onMilestone?: (totalApproved: number) => void) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => approveRequest(id, clientId!),
    onSuccess: async () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['agents', clientId] })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.approvalStats(clientId ?? '') })
      if (onMilestone && clientId) {
        await detectMilestones(clientId, onMilestone)
      }
    },
  })
}

export function useRejectRequest(onMilestone?: (totalApproved: number) => void) {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => rejectRequest(id, clientId!),
    onSuccess: async () => {
      qc.invalidateQueries({ queryKey: ['approvals'] })
      qc.invalidateQueries({ queryKey: ['agents', clientId] })
      qc.invalidateQueries({ queryKey: QUERY_KEYS.approvalStats(clientId ?? '') })
      if (onMilestone && clientId) {
        await detectMilestones(clientId, onMilestone)
      }
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
