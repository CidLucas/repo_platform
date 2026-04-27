import { useQuery } from '@tanstack/react-query';
import { getMyDashboardKpis } from '../services/analyticsService';

export interface DashboardKpiSlot {
  dimension: string;
  slot_index: number;
  slug: string;
  label: string;
  unit: string;
  formula: string;
  data_status: string;
  tier_required: string;
  is_enabled: boolean;
}

interface UseDashboardKpisReturn {
  data: DashboardKpiSlot[] | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch current dashboard KPI configuration per dimension.
 * Returns slots 0-4 for each dimension with fallback to defaults.
 *
 * @example
 * const { data: kpis, loading } = useDashboardKpis();
 */
export const useDashboardKpis = (): UseDashboardKpisReturn => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboardKpis'],
    queryFn: getMyDashboardKpis,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  return {
    data: data ?? null,
    loading: isLoading,
    error: error instanceof Error ? error.message : error ? String(error) : null,
    refetch: async () => {
      await refetch();
    },
  };
};
