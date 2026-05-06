import { useQuery } from '@tanstack/react-query';
import { getHomeMetrics, HomeMetricsResponse } from '@/services/analyticsService';

interface UseHomeMetricsReturn {
    data: HomeMetricsResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch home dashboard metrics with React Query caching.
 * Data is cached for 5 minutes and stale-while-revalidate pattern is used.
 */
export const useHomeMetrics = (): UseHomeMetricsReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['homeMetrics'],
        queryFn: getHomeMetrics,
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
