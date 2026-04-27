import { useQuery } from '@tanstack/react-query';
import {
  DIMENSION_RPC,
  type DimensionKey,
  type DimensionIndicatorMap,
  type PeriodType,
  type StandardPeriod,
} from '../services/analyticsService';

/**
 * useDimensionKpis — Phase 1 / K1.3 (BLU-MVP-004)
 *
 * Single hook that fans out to the correct per-dimension KPI RPC
 * (`analytics_v2.get_<dim>_indicators`) based on the `dimension` argument.
 * Works with the standardized period vocabulary from `PeriodSelector`
 * (`7d | 30d | 90d | mtd | ytd | custom`) and the legacy aliases.
 *
 * RLS scopes results to the current client via JWT. No client_id needed.
 */
export interface UseDimensionKpisResult<D extends DimensionKey> {
  data: DimensionIndicatorMap[D] | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useDimensionKpis<D extends DimensionKey>(
  dimension: D,
  period: PeriodType | StandardPeriod | string = '30d',
): UseDimensionKpisResult<D> {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dimensionKpis', dimension, period],
    queryFn: async () => {
      const fn = DIMENSION_RPC[dimension];
      const result = await fn(period);
      return result as DimensionIndicatorMap[D];
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  return {
    data: (data as DimensionIndicatorMap[D] | undefined) ?? null,
    loading: isLoading,
    error: error instanceof Error ? error.message : error ? String(error) : null,
    refetch: async () => { await refetch(); },
  };
}
