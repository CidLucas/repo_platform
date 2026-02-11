import { useQuery } from '@tanstack/react-query';
import { getHomeMetrics, HomeMetricsResponse } from '../services/analyticsService';

interface UseHomeMetricsReturn {
    data: HomeMetricsResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch home dashboard metrics with React Query caching.
 * Data is cached for 5 minutes and stale-while-revalidate pattern is used.
 * 
 * @example
 * const { data, loading, error } = useHomeMetrics();
 */
export const useHomeMetrics = (): UseHomeMetricsReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['homeMetrics'],
        queryFn: getHomeMetrics,
        staleTime: 5 * 60 * 1000,  // 5 minutes - metrics don't change frequently
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
