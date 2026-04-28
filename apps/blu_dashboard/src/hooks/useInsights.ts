import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dismissInsight, getInsights, InsightItem } from '../services/analyticsService';

interface UseInsightsReturn {
    data: InsightItem[] | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    dismiss: (insightId: string) => Promise<void>;
    dismissing: boolean;
}

/**
 * Hook to fetch active insights produced by `routine.daily_insights`.
 * Backed by `public.get_my_insights` (Phase 2 / I2.2).
 */
export const useInsights = (limit: number = 5): UseInsightsReturn => {
    const queryClient = useQueryClient();
    const queryKey = ['insights', limit];

    const { data, isLoading, error, refetch } = useQuery({
        queryKey,
        queryFn: () => getInsights(limit),
        staleTime: 5 * 60 * 1000,
    });

    const mutation = useMutation({
        mutationFn: (insightId: string) => dismissInsight(insightId),
        onMutate: async (insightId: string) => {
            await queryClient.cancelQueries({ queryKey });
            const previous = queryClient.getQueryData<InsightItem[]>(queryKey);
            queryClient.setQueryData<InsightItem[]>(queryKey, (prev) =>
                (prev ?? []).filter((item) => item.id !== insightId),
            );
            return { previous };
        },
        onError: (_err, _id, context) => {
            if (context?.previous) {
                queryClient.setQueryData(queryKey, context.previous);
            }
        },
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey });
        },
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
        dismiss: async (insightId: string) => { await mutation.mutateAsync(insightId); },
        dismissing: mutation.isPending,
    };
};
