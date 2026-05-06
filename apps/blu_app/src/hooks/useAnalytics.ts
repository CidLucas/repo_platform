import { useQuery } from '@tanstack/react-query'
import { fetchKpiSnapshot, fetchTimeSeries, fetchRecentActivity } from '@/api/analytics'
import { QUERY_KEYS } from '@/utils/constants'
import type { KpiPeriod } from '@/types/analytics'

export function useKpiSnapshot(period: KpiPeriod = '30d') {
  return useQuery({
    queryKey: QUERY_KEYS.kpi(period),
    queryFn: () => fetchKpiSnapshot(period),
    staleTime: 120_000,
  })
}

export function useTimeSeries(period: KpiPeriod = '30d') {
  return useQuery({
    queryKey: QUERY_KEYS.timeSeries(period),
    queryFn: () => fetchTimeSeries(period),
    staleTime: 120_000,
  })
}

export function useRecentActivity(limit = 20) {
  return useQuery({
    queryKey: QUERY_KEYS.recentActivity,
    queryFn: () => fetchRecentActivity(limit),
    staleTime: 60_000,
  })
}
