import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/hooks/useAuth'
import { fetchApprovalStats } from '@/api/approval-stats'
import { QUERY_KEYS } from '@/utils/constants'
import type { ApprovalStats } from '@/api/approval-stats'

export type { ApprovalStats }

export function useApprovalStats() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: QUERY_KEYS.approvalStats(clientId ?? ''),
    queryFn: () => fetchApprovalStats(clientId!),
    enabled: !!clientId,
    staleTime: 30_000,
  })
}

// ── Milestone thresholds ──────────────────────────────────────────────────────

export const TRUST_MILESTONES = [
  {
    threshold: 10,
    trustLevel: 'similar_toggle' as const,
    title: 'Você aprovou 10 missões.',
    body: 'Quer automatizar aprovações similares em Compras?',
    ctaLabel: 'Configurar',
    storageKey: 'trust_milestone_10',
    showToast: false,
  },
  {
    threshold: 25,
    trustLevel: 'rules' as const,
    title: 'Você aprovou 25 missões.',
    body: 'Regras avançadas desbloqueadas — ex: aprovar automaticamente compras abaixo de R$ 500.',
    ctaLabel: 'Ver regras',
    storageKey: 'trust_milestone_25',
    showToast: false,
  },
  {
    threshold: 50,
    trustLevel: 'full_config' as const,
    title: 'Configuração completa desbloqueada.',
    body: 'Blu conhece o seu negócio.',
    ctaLabel: 'Explorar',
    storageKey: 'trust_milestone_50',
    showToast: true,
  },
] as const

export type TrustMilestone = (typeof TRUST_MILESTONES)[number]

/**
 * Returns milestones that have been crossed (total_approved >= threshold)
 * but NOT yet shown in this session (sessionStorage gate).
 */
export function getPendingMilestones(totalApproved: number): TrustMilestone[] {
  return TRUST_MILESTONES.filter((m) => {
    if (totalApproved < m.threshold) return false
    if (sessionStorage.getItem(m.storageKey)) return false
    return true
  })
}

/** Mark a milestone as shown so it won't re-appear on refresh */
export function markMilestoneShown(storageKey: string) {
  sessionStorage.setItem(storageKey, '1')
}
