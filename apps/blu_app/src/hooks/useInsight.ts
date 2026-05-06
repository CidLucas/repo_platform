import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchInsights, dismissInsight } from '@/api/insights'
import { QUERY_KEYS } from '@/utils/constants'

export function useInsights(limit = 5) {
  return useQuery({
    queryKey: [...QUERY_KEYS.insights, limit],
    queryFn: () => fetchInsights(limit),
    staleTime: 5 * 60 * 1000,
  })
}

export function useDismissInsight() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => dismissInsight(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.insights })
    },
  })
}
