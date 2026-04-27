import { useQuery } from '@tanstack/react-query';
import {
  getDashboardIndicators,
  DashboardIndicatorsResponse,
  PeriodType,
} from '../services/analyticsService';

interface UseDashboardIndicatorsReturn {
  data: DashboardIndicatorsResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Hook for the HomePage period toggle (week / month / quarter / year).
 * Reads analytics_v2.get_dashboard_indicators(p_period) and returns the
 * rolling-window KPIs scoped by RLS to the current client.
 *
 * Note: The default "Este mês" view on HomePage uses calendar-month values
 * from v_resumo_dashboard via useHomeMetrics. This hook is for non-default
 * periods where rolling windows make sense.
 */
export const useDashboardIndicators = (
  period: PeriodType | string = 'month',
): UseDashboardIndicatorsReturn => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboardIndicators', period],
    queryFn: () => getDashboardIndicators(period),
    staleTime: 5 * 60 * 1000,
  });

  return {
    data: data ?? null,
    loading: isLoading,
    error: error instanceof Error ? error.message : error ? String(error) : null,
    refetch: async () => { await refetch(); },
  };
};
