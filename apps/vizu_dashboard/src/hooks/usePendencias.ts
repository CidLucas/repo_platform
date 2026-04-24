import { useQuery } from '@tanstack/react-query';
import { getPendencias, PendenciaItem } from '../services/analyticsService';

interface UsePendenciasReturn {
    data: PendenciaItem[] | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

/**
 * Hook to fetch open pendências (pending RFQs, connector errors, data source issues).
 * Backed by `public.get_pendencias`.
 */
export const usePendencias = (): UsePendenciasReturn => {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['pendencias'],
        queryFn: getPendencias,
        staleTime: 5 * 60 * 1000,
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};
