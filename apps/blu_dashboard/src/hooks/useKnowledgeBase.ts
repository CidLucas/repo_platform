import { useState, useEffect, useCallback, useRef } from "react";
import useAuth from "./useAuth";
import {
    listDocuments,
    deleteDocument,
    uploadFile,
    type KBDocument,
    type UploadOptions,
} from "../services/knowledgeBaseService";

const POLL_INTERVAL_MS = 5_000;
const MAX_PROCESSING_MS = 5 * 60 * 1000; // 5 minutes — safety timeout for stuck documents

export function useKnowledgeBase() {
    const { clientId } = useAuth();
    const [documents, setDocuments] = useState<KBDocument[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // ── Fetch ────────────────────────────────────────────────
    const fetchDocuments = useCallback(async () => {
        if (!clientId) return;
        try {
            const docs = await listDocuments(clientId);
            setDocuments(docs);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Erro desconhecido");
        } finally {
            setLoading(false);
        }
    }, [clientId]);

    // ── Initial load ─────────────────────────────────────────
    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    // ── Auto-poll while any document is processing/pending ───
    useEffect(() => {
        const hasInProgress = documents.some((d) => {
            if (d.status !== "pending" && d.status !== "processing") return false;
            // Safety timeout: if stuck for more than MAX_PROCESSING_MS, stop polling
            const elapsed = Date.now() - new Date(d.updated_at).getTime();
            return elapsed < MAX_PROCESSING_MS;
        });

        if (hasInProgress) {
            if (!pollRef.current) {
                pollRef.current = setInterval(fetchDocuments, POLL_INTERVAL_MS);
            }
        } else {
            if (pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        }

        return () => {
            if (pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        };
    }, [documents, fetchDocuments]);

    // ── Upload ───────────────────────────────────────────────
    const upload = useCallback(
        async (files: File[], forceComplex = false, options?: UploadOptions) => {
            if (!clientId) return;
            setUploading(true);
            try {
                for (const file of files) {
                    await uploadFile(file, clientId, forceComplex, "upload", options);
                }
                // Refresh list after uploading
                await fetchDocuments();
            } catch (err) {
                setError(err instanceof Error ? err.message : "Erro no upload");
            } finally {
                setUploading(false);
            }
        },
        [clientId, fetchDocuments]
    );

    // ── Delete ───────────────────────────────────────────────
    const remove = useCallback(
        async (doc: KBDocument) => {
            try {
                await deleteDocument(doc.id, doc.storage_path);
                setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
            } catch (err) {
                setError(err instanceof Error ? err.message : "Erro ao deletar");
            }
        },
        []
    );

    // ── Refresh manual ───────────────────────────────────────
    const refresh = useCallback(() => {
        setLoading(true);
        fetchDocuments();
    }, [fetchDocuments]);

    return {
        documents,
        loading,
        uploading,
        error,
        upload,
        remove,
        refresh,
    };
}

export default useKnowledgeBase;
