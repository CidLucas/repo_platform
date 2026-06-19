/**
 * useBusinessMemory — React Query hook for business memory data
 *
 * T5.1: Data-fetching hook with mock data initially.
 * To switch to real API, change USE_MOCK in ../api/businessMemory.ts.
 */

import { useQuery } from '@tanstack/react-query'
import { fetchBusinessMemory, type BusinessMemoryListResponse } from '../api/businessMemory'

export interface UseBusinessMemoryOptions {
  entityType?: string
  entityName?: string
  limit?: number
  offset?: number
  enabled?: boolean
}

/**
 * Hook to fetch business memory records.
 *
 * @param options - Filter and pagination options
 * @returns React Query result with list of business memory records
 *
 * Usage:
 *   const { data, isLoading, error } = useBusinessMemory()
 *   const { data, isLoading } = useBusinessMemory({ entityType: 'snapshot' })
 */
export function useBusinessMemory(options: UseBusinessMemoryOptions = {}) {
  const { entityType, entityName, limit = 100, offset = 0, enabled = true } = options

  return useQuery<BusinessMemoryListResponse>({
    queryKey: ['business-memory', { entityType, entityName, limit, offset }],
    queryFn: () => fetchBusinessMemory(entityType, entityName, limit, offset),
    staleTime: 2 * 60 * 1000, // 2 minutes
    enabled,
  })
}
