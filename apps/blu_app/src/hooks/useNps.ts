import { useQuery } from '@tanstack/react-query';
import { getNpsScore, NpsScoreResponse } from '@/services/analyticsService';

interface UseNpsReturn {
    data: NpsScoreResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch the NPS score for the configured rolling window.
 * Backed by `public.get_nps_score`.
 */
export const useNps = (windowDays: number = 90): UseNpsReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['nps', windowDays],
        queryFn: () => getNpsScore(windowDays),
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
