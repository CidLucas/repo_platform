import { useState, useCallback, useEffect } from 'react';
import { useAuth } from './useAuth';
import {
    listDocuments,
    deleteDocument,
    uploadFile,
    type KBDocument,
    type UploadOptions,
} from '@/services/knowledgeBaseService';

const POLL_INTERVAL_MS = 5_000;
const MAX_PROCESSING_MS = 5 * 60 * 1000;

export function useKnowledgeBase() {
    const { clientId } = useAuth();
    const [documents, setDocuments] = useState<KBDocument[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchDocuments = useCallback(async () => {
        if (!clientId) return;
        try {
            const docs = await listDocuments(clientId);
            setDocuments(docs);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Erro desconhecido');
        }
    }, [clientId]);

    // Initial load
    useEffect(() => {
        if (!clientId) return;
        setLoading(true);
        fetchDocuments().finally(() => setLoading(false));
    }, [clientId, fetchDocuments]);

    // Poll while any doc is processing
    useEffect(() => {
        const hasProcessing = documents.some(
            (d) => d.status === 'processing' || d.status === 'pending',
        );
        if (!hasProcessing) return;

        const started = Date.now();
        const interval = setInterval(() => {
            if (Date.now() - started > MAX_PROCESSING_MS) {
                clearInterval(interval);
                return;
            }
            fetchDocuments();
        }, POLL_INTERVAL_MS);

        return () => clearInterval(interval);
    }, [documents, fetchDocuments]);

    const upload = useCallback(
        async (file: File, forceComplex = false, options?: UploadOptions) => {
            if (!clientId) return;
            setUploading(true);
            setError(null);
            try {
                await uploadFile(file, clientId, forceComplex, 'upload', options);
                await fetchDocuments();
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Erro no upload');
            } finally {
                setUploading(false);
            }
        },
        [clientId, fetchDocuments],
    );

    const remove = useCallback(
        async (doc: KBDocument) => {
            try {
                await deleteDocument(doc.id, doc.storage_path);
                setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Erro ao deletar');
            }
        },
        [],
    );

    return {
        documents,
        loading,
        uploading,
        error,
        upload,
        remove,
        refetch: fetchDocuments,
    };
}
