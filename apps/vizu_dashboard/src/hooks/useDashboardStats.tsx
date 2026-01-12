import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import {
  getDashboardStats,
  DashboardStatsResponse,
} from '../services/connectorStatusService';

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
    if (!auth?.user?.id) {
      setStats(null);
      setLoading(false);
      return;
    }

    const fetchStats = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getDashboardStats(auth.user!.id);
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch dashboard stats'));
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [auth?.user?.id, refetchFlag]);

  const refetch = () => setRefetchFlag((prev) => prev + 1);

  return { stats, loading, error, refetch };
};
