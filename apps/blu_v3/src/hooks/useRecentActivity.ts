import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import { getRecentActivity, fetchDayStats } from '../api/activity'

/**
 * Activity-log feed from the reg_agent_actions table.
 * Distinct from useAnalyticsActivity (useAnalytics.ts) which reads the analytics RPC.
 */
export function useRecentActivity(limit = 20) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['recentActivity', clientId, limit],
    queryFn: () => getRecentActivity(limit),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  })
}

export function useDayStats() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['dayStats', clientId],
    queryFn: () => fetchDayStats(clientId!),
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}
