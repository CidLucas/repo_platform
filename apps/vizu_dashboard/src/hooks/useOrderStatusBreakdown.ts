import { useQuery } from '@tanstack/react-query';
import { getOrderStatusBreakdown, PeriodType } from '../services/analyticsService';

export interface OrderStatusBreakdownItem {
    status: string;
    count: number;
}

interface UseOrderStatusBreakdownReturn {
    data: OrderStatusBreakdownItem[] | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch order status counts for a given period.
 * Backed by `analytics_v2.get_order_status_breakdown`.
 */
export const useOrderStatusBreakdown = (period: PeriodType = 'month'): UseOrderStatusBreakdownReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['orderStatusBreakdown', period],
        queryFn: () => getOrderStatusBreakdown(period),
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
