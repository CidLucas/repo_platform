import { useState, useEffect } from 'react';
import { getGeoClusters, GeoClustersResponse } from '../services/analyticsService';

export const useGeoClusters = (groupBy: 'state' | 'city' | 'cep' = 'state') => {
  const [data, setData] = useState<GeoClustersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getGeoClusters(groupBy);
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch geo clusters'));
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [groupBy]);

  return { data, loading, error };
};
