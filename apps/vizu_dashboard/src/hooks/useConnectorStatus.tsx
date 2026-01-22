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
    if (!auth?.clientId) {
      setConnectors(null);
      setLoading(false);
      return;
    }

    const fetchConnectors = async () => {
      setLoading(true);
      setError(null);

      try {
        // Use real client_id from clientes_vizu table
        const data = await getConnectorStatus(auth.clientId!);
        setConnectors(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch connectors'));
      } finally {
        setLoading(false);
      }
    };

    fetchConnectors();
  }, [auth?.clientId, refetchFlag]);

  const refetch = () => setRefetchFlag((prev) => prev + 1);

  return { connectors, loading, error, refetch };
};
