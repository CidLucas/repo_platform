import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import {
    getDashboardStats,
    DashboardStatsResponse,
} from '@/services/connectorStatusService';

interface UseDashboardStatsReturn {
    stats: DashboardStatsResponse | null;
    loading: boolean;
    error: Error | null;
    refetch: () => void;
}

/**
 * Hook to fetch dashboard statistics for admin home page.
 */
export const useDashboardStats = (): UseDashboardStatsReturn => {
    const auth = useContext(AuthContext);
    const [stats, setStats] = useState<DashboardStatsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const [refetchFlag, setRefetchFlag] = useState(0);

    useEffect(() => {
        if (!auth?.clientId) {
            setStats(null);
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        getDashboardStats(auth.clientId)
            .then((data) => {
                if (!cancelled) {
                    setStats(data);
                    setLoading(false);
                }
            })
            .catch((err: Error) => {
                if (!cancelled) {
                    setError(err);
                    setLoading(false);
                }
            });

        return () => { cancelled = true; };
    }, [auth?.clientId, refetchFlag]);

    return {
        stats,
        loading,
        error,
        refetch: () => setRefetchFlag((f) => f + 1),
    };
};
