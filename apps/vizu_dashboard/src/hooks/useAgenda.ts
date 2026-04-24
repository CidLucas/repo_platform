import { useQuery } from '@tanstack/react-query';
import { getAgendaEvents, AgendaResponse } from '../services/analyticsService';

interface UseAgendaReturn {
    data: AgendaResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch the upcoming Google Calendar events for the dashboard Agenda card.
 * Backed by the `google-calendar-events` Edge Function.
 *
 * Returns `data.disabled === true` with a typed `reason` when the integration
 * is off / missing — UI should render an onboarding CTA instead of an error.
 */
export const useAgenda = (rangeDays: number = 7): UseAgendaReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['agenda', rangeDays],
        queryFn: () => getAgendaEvents(rangeDays),
        staleTime: 2 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
