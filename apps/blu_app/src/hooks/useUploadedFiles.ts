import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import {
    getUploadedFiles,
    deleteUploadedFile,
    FileListResponse,
} from '@/services/connectorStatusService';

interface UseUploadedFilesReturn {
    files: FileListResponse | null;
    loading: boolean;
    error: Error | null;
    refetch: () => void;
    deleteFile: (fileId: string) => Promise<void>;
}

/**
 * Hook to fetch and manage uploaded files for the current user.
 */
export const useUploadedFiles = (): UseUploadedFilesReturn => {
    const auth = useContext(AuthContext);
    const [files, setFiles] = useState<FileListResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);
    const [refetchFlag, setRefetchFlag] = useState(0);

    useEffect(() => {
        if (!auth?.clientId) {
            setFiles(null);
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        getUploadedFiles(auth.clientId)
            .then((data) => {
                if (!cancelled) {
                    setFiles(data);
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

    const deleteFile = async (fileId: string) => {
        if (!auth?.clientId) return;
        await deleteUploadedFile(fileId, auth.clientId);
        setRefetchFlag((f) => f + 1);
    };

    return {
        files,
        loading,
        error,
        refetch: () => setRefetchFlag((f) => f + 1),
        deleteFile,
    };
};
