import { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
import {
  getUploadedFiles,
  deleteUploadedFile,
  FileListResponse,
} from '../services/connectorStatusService';

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

    const fetchFiles = async () => {
      setLoading(true);
      setError(null);

      try {
        const data = await getUploadedFiles(auth.clientId!);
        setFiles(data);
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch files'));
      } finally {
        setLoading(false);
      }
    };

    fetchFiles();
  }, [auth?.clientId, refetchFlag]);

  const refetch = () => setRefetchFlag((prev) => prev + 1);

  const deleteFile = async (fileId: string) => {
    if (!auth?.clientId) throw new Error('User not authenticated');

    await deleteUploadedFile(fileId, auth.clientId);
    refetch();
  };

  return { files, loading, error, refetch, deleteFile };
};
