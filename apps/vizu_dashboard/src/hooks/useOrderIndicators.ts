import { useQuery } from '@tanstack/react-query';
import { getOrderIndicators, OrderMetricsResponse, PeriodType } from '../services/analyticsService';

interface UseOrderIndicatorsReturn {
    data: OrderMetricsResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch order indicators for a given period.
 * Backed by `analytics_v2.get_order_indicators` + `get_order_status_breakdown`.
 */
export const useOrderIndicators = (period: PeriodType = 'month'): UseOrderIndicatorsReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['orderIndicators', period],
        queryFn: () => getOrderIndicators(period),
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
