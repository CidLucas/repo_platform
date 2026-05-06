import {
  createContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react'
import { useApprovalStats, getPendingMilestones, markMilestoneShown } from '@/hooks/useApprovalStats'
import type { TrustMilestone } from '@/hooks/useApprovalStats'
import type { ApprovalStats } from '@/api/approval-stats'

export type ActiveMilestone = TrustMilestone & {
  id: string // unique per session show
}

interface TrustContextValue {
  stats: ApprovalStats | null | undefined
  trustLevel: string
  activeMilestone: ActiveMilestone | null
  dismissMilestone: () => void
  /** Call after an approval mutation to detect milestone crossings */
  checkMilestones: (totalApproved: number) => void
}

export const TrustContext = createContext<TrustContextValue | null>(null)
export type { TrustContextValue }

export function TrustProvider({ children }: { children: ReactNode }) {
  const { data: stats } = useApprovalStats()
  const [activeMilestone, setActiveMilestone] = useState<ActiveMilestone | null>(null)

  // Detect milestones whenever stats update (e.g. after realtime refresh)
  useEffect(() => {
    if (stats?.total_approved == null) return
    checkMilestones(stats.total_approved)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stats?.total_approved])

  const checkMilestones = useCallback((totalApproved: number) => {
    const pending = getPendingMilestones(totalApproved)
    if (pending.length === 0) return
    // Show the highest threshold that was crossed
    const next = pending[pending.length - 1]
    markMilestoneShown(next.storageKey)
    setActiveMilestone({ ...next, id: `${next.storageKey}_${Date.now()}` })
  }, [])

  const dismissMilestone = useCallback(() => {
    setActiveMilestone(null)
  }, [])

  return (
    <TrustContext.Provider
      value={{
        stats: stats,
        trustLevel: stats?.trust_level ?? 'none',
        activeMilestone,
        dismissMilestone,
        checkMilestones,
      }}
    >
      {children}
    </TrustContext.Provider>
  )
}

