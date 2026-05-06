import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import {
    getConnectorStatus,
    ConnectorListResponse,
} from '@/services/connectorStatusService';

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

        let cancelled = false;
        setLoading(true);
        setError(null);

        getConnectorStatus(auth.clientId)
            .then((data) => {
                if (!cancelled) {
                    setConnectors(data);
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
        connectors,
        loading,
        error,
        refetch: () => setRefetchFlag((f) => f + 1),
    };
};
