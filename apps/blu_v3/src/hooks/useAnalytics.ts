import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@blu/auth'
import {
  getHomeMetrics,
  getRecentActivity,
  getPendencias,
  getInsights,
  dismissInsight,
  getAgentRunsToday,
  getNpsScore,
  getAgendaEvents,
  getCommercialRevenueByChannel,
  getCommercialTopClients,
  listKpiCatalog,
  setClientDimensionKpis,
  getMyDashboardKpis,
  getAnnualMetrics,
  getFinanceIndicators,
  getCommercialIndicators,
  getInventoryIndicators,
  getSupplyIndicators,
  getMarketingIndicators,
  getAdminIndicators,
  type DimensionKey,
} from '../api/analytics'

// All analytics hooks require an authenticated clientId.
// Including clientId in every query key ensures cache isolation between users/sessions.

export function useHomeMetrics() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'homeMetrics'],
    queryFn: getHomeMetrics,
    enabled: !!clientId,
    staleTime: 3 * 60 * 1000,
  })
}

/** Analytics feed of recent events — distinct from the activity-log useRecentActivity in useRecentActivity.ts */
export function useAnalyticsActivity(limit = 10) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'recentActivity', limit],
    queryFn: () => getRecentActivity(limit),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  })
}

export function usePendencias() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'pendencias'],
    queryFn: getPendencias,
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}

export function useInsights(limit = 5) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'insights', limit],
    queryFn: () => getInsights(limit),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useDismissInsight() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (insightId: string) => dismissInsight(insightId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analytics', clientId, 'insights'] })
    },
  })
}

export function useAgentRunsToday() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'agentRunsToday'],
    queryFn: getAgentRunsToday,
    enabled: !!clientId,
    staleTime: 60 * 1000,
  })
}

export function useNpsScore(windowDays = 90) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'npsScore', windowDays],
    queryFn: () => getNpsScore(windowDays),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAgendaEvents(rangeDays = 7) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'agendaEvents', rangeDays],
    queryFn: () => getAgendaEvents(rangeDays),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useCommercialRevenueByChannel(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'revenueByChannel', period],
    queryFn: () => getCommercialRevenueByChannel(period),
    enabled: !!clientId,
    staleTime: 3 * 60 * 1000,
  })
}

export function useCommercialTopClients(period = '30d', limit = 10) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'topClients', period, limit],
    queryFn: () => getCommercialTopClients(period, limit),
    enabled: !!clientId,
    staleTime: 3 * 60 * 1000,
  })
}

export function useKpiCatalog(dimension: DimensionKey | null = null, onlyEnabled = true) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'kpiCatalog', dimension, onlyEnabled],
    queryFn: () => listKpiCatalog(dimension, onlyEnabled),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSetClientDimensionKpis() {
  const { clientId } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dimension, slugs }: { dimension: DimensionKey; slugs: string[] }) =>
      setClientDimensionKpis(dimension, slugs),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analytics', clientId, 'dashboardKpis'] })
    },
  })
}

export function useMyDashboardKpis() {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'dashboardKpis'],
    queryFn: getMyDashboardKpis,
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useAnnualMetrics(metric: string) {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'annualMetrics', metric],
    queryFn: () => getAnnualMetrics(metric),
    enabled: !!clientId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useFinanceIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'financeIndicators', period],
    queryFn: () => getFinanceIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useCommercialIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'commercialIndicators', period],
    queryFn: () => getCommercialIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useInventoryIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'inventoryIndicators', period],
    queryFn: () => getInventoryIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useSupplyIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'supplyIndicators', period],
    queryFn: () => getSupplyIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useMarketingIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'marketingIndicators', period],
    queryFn: () => getMarketingIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}

export function useAdminIndicators(period = '30d') {
  const { clientId } = useAuth()
  return useQuery({
    queryKey: ['analytics', clientId, 'adminIndicators', period],
    queryFn: () => getAdminIndicators(period),
    enabled: !!clientId,
    staleTime: 2 * 60 * 1000,
  })
}
