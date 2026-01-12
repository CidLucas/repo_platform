import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import {
  getConnectorStatus,
  ConnectorListResponse,
} from '../services/connectorStatusService';

interface UseConnectorStatusReturn {
  connectors: ConnectorListResponse | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
}

/**
 * Hook to fetch connector status for the current user.
 */
export const useConnectorStatus = (): UseConnectorStatusReturn => {
  const auth = useContext(AuthContext);
  const [connectors, setConnectors] = useState<ConnectorListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [refetchFlag, setRefetchFlag] = useState(0);

  useEffect(() => {
    if (!auth?.user?.id) {
      setConnectors(null);
      setLoading(false);
      return;
    }

    const fetchConnectors = async () => {
      setLoading(true);
      setError(null);

      try {
        // Use user.id as client_id
        const data = await getConnectorStatus(auth.user!.id);
        setConnectors(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch connectors'));
      } finally {
        setLoading(false);
      }
    };

    fetchConnectors();
  }, [auth?.user?.id, refetchFlag]);

  const refetch = () => setRefetchFlag((prev) => prev + 1);

  return { connectors, loading, error, refetch };
};
