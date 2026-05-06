import { useQuery } from '@tanstack/react-query';
import { getAgentRunsToday, AgentRunsTodayResponse } from '@/services/analyticsService';

interface UseAgentRunsTodayReturn {
    data: AgentRunsTodayResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch today's agent run count + per-agent breakdown.
 * Backed by `public.get_agent_runs_today`. 1-min stale time because runs
 * arrive throughout the day.
 */
export const useAgentRunsToday = (): UseAgentRunsTodayReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['agentRunsToday'],
        queryFn: getAgentRunsToday,
        staleTime: 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
