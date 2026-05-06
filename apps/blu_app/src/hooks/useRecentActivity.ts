import { useQuery } from '@tanstack/react-query';
import { getRecentActivity, RecentActivityItem } from '@/services/analyticsService';

interface UseRecentActivityReturn {
    data: RecentActivityItem[] | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch the recent activity feed (ingestion, agent runs, RFQs, uploads).
 * Backed by `public.get_recent_activity`.
 */
export const useRecentActivity = (limit: number = 10): UseRecentActivityReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['recentActivity', limit],
        queryFn: () => getRecentActivity(limit),
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
