import { useState, useCallback, useEffect, useContext } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import {
    fetchAgentCatalog,
    fetchAgentDetails,
    createSession,
    fetchSessionStatus,
    fetchSessions,
    saveConfigField,
    finalizeConfig,
    uploadCsvFile,
    activateSession,
    initiateGoogleAuth,
    fetchGoogleAccounts,
    linkGoogleToSession,
    linkDocumentToSession,
    type AgentCatalogEntry,
    type StandaloneAgentSession,
    type RequirementsStatus,
    type UploadedFile,
} from '@/services/standaloneAgentService';
import {
    uploadFile as kbUploadFile,
    deleteDocument as kbDeleteDocument,
    getDocumentProgress,
} from '@/services/knowledgeBaseService';

export interface StandaloneAgentState {
    agents: AgentCatalogEntry[];
    selectedAgent: AgentCatalogEntry | null;
    loadingCatalog: boolean;
    catalogError: string | null;

    sessions: StandaloneAgentSession[];
    currentSession: StandaloneAgentSession | null;

    configStatus: 'configuring' | 'ready' | 'active' | 'archived';
    requirements: RequirementsStatus | null;
    collectedContext: Record<string, string | boolean>;

    uploadedCsvs: UploadedFile[];
    uploadedDocuments: UploadedFile[];
    uploadingFile: boolean;
    uploadError: string | null;

    googleConnected: boolean;
    googleEmail: string | null;

    creating: boolean;
    activating: boolean;
    savingField: boolean;

    // Error state returned instead of toast
    lastError: string | null;
}

/**
 * Hook to manage standalone agent configuration and chat state.
 * Errors are surfaced via `lastError` instead of toast notifications.
 */
export function useStandaloneAgent() {
    const auth = useContext(AuthContext);

    const [state, setState] = useState<StandaloneAgentState>({
        agents: [],
        selectedAgent: null,
        loadingCatalog: true,
        catalogError: null,
        sessions: [],
        currentSession: null,
        configStatus: 'configuring',
        requirements: null,
        collectedContext: {},
        uploadedCsvs: [],
        uploadedDocuments: [],
        uploadingFile: false,
        uploadError: null,
        googleConnected: false,
        googleEmail: null,
        creating: false,
        activating: false,
        savingField: false,
        lastError: null,
    });

    const accessToken = auth?.session?.access_token;
    const clientId = auth?.clientId;

    const reloadCatalog = useCallback(async () => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingCatalog: true, catalogError: null }));
            const agents = await fetchAgentCatalog(accessToken);
            setState((prev) => ({ ...prev, agents, loadingCatalog: false }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load agents';
            setState((prev) => ({ ...prev, catalogError: message, loadingCatalog: false, lastError: message }));
        }
    }, [accessToken]);

    useEffect(() => {
        reloadCatalog();
    }, [reloadCatalog]);

    useEffect(() => {
        if (!accessToken) return;
        const loadSessions = async () => {
            try {
                const sessions = await fetchSessions(accessToken);
                setState((prev) => ({ ...prev, sessions }));
            } catch (err) {
                console.error('Failed to load sessions:', err);
            }
        };
        loadSessions();
    }, [accessToken]);

    const selectAgent = useCallback(
        async (agentId: string) => {
            if (!accessToken) return;
            try {
                const agent = await fetchAgentDetails(agentId, accessToken);
                setState((prev) => ({ ...prev, selectedAgent: agent }));
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to load agent details';
                setState((prev) => ({ ...prev, lastError: message }));
            }
        },
        [accessToken],
    );

    const createNewSession = useCallback(
        async (agentId: string) => {
            if (!accessToken) return;
            try {
                setState((prev) => ({ ...prev, creating: true }));
                const session = await createSession(agentId, accessToken);
                const sessionWithRequirements = await fetchSessionStatus(session.id, accessToken);
                setState((prev) => ({
                    ...prev,
                    currentSession: session,
                    configStatus: session.config_status,
                    requirements: sessionWithRequirements.requirements,
                    collectedContext: session.collected_context,
                    uploadedCsvs: [],
                    uploadedDocuments: [],
                    googleConnected: !!session.google_account_email,
                    googleEmail: session.google_account_email,
                    creating: false,
                }));
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to create session';
                setState((prev) => ({ ...prev, creating: false, lastError: message }));
            }
        },
        [accessToken],
    );

    const resumeSession = useCallback(
        async (sessionId: string) => {
            if (!accessToken) return;
            try {
                const session = await fetchSessionStatus(sessionId, accessToken);
                setState((prev) => ({
                    ...prev,
                    currentSession: session,
                    configStatus: session.config_status,
                    requirements: session.requirements,
                    collectedContext: session.collected_context,
                    googleConnected: !!session.google_account_email,
                    googleEmail: session.google_account_email,
                }));
                await selectAgent(session.agent_catalog_id);
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to resume session';
                setState((prev) => ({ ...prev, lastError: message }));
            }
        },
        [accessToken, selectAgent],
    );

    const saveField = useCallback(
        async (fieldName: string, value: string | boolean) => {
            if (!state.currentSession || !accessToken) return;
            try {
                setState((prev) => ({ ...prev, savingField: true }));
                await saveConfigField(state.currentSession.id, fieldName, value, accessToken);
                const updated = await fetchSessionStatus(state.currentSession.id, accessToken);
                setState((prev) => ({
                    ...prev,
                    collectedContext: { ...prev.collectedContext, [fieldName]: value },
                    requirements: updated.requirements,
                    savingField: false,
                }));
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to save field';
                setState((prev) => ({ ...prev, savingField: false, lastError: message }));
            }
        },
        [state.currentSession, accessToken],
    );

    const uploadCsv = useCallback(
        async (file: File) => {
            if (!state.currentSession || !accessToken) return;
            try {
                setState((prev) => ({ ...prev, uploadingFile: true, uploadError: null }));
                const uploadedFile = await uploadCsvFile(state.currentSession.id, file, accessToken);
                setState((prev) => ({
                    ...prev,
                    uploadedCsvs: [...prev.uploadedCsvs, uploadedFile],
                    uploadingFile: false,
                }));
                return uploadedFile;
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to upload CSV';
                setState((prev) => ({ ...prev, uploadingFile: false, uploadError: message }));
            }
        },
        [state.currentSession, accessToken],
    );

    const uploadDoc = useCallback(
        async (file: File) => {
            if (!state.currentSession || !clientId || !accessToken) return;
            try {
                setState((prev) => ({ ...prev, uploadingFile: true, uploadError: null }));

                const documentId = await kbUploadFile(file, clientId, false, 'upload', {
                    category: 'contexto_empresa',
                });

                const uploadedFile: UploadedFile = {
                    id: documentId,
                    file_name: file.name,
                    storage_path: file.name,
                    records_count: 0,
                    status: 'processing',
                };

                setState((prev) => ({
                    ...prev,
                    uploadedDocuments: [...prev.uploadedDocuments, uploadedFile],
                    uploadingFile: false,
                }));

                try {
                    await linkDocumentToSession(state.currentSession.id, documentId, accessToken);
                } catch (linkErr) {
                    console.error('Failed to link document to session:', linkErr);
                }

                let pollErrors = 0;
                const MAX_POLL_ERRORS = 5;
                const pollId = setInterval(async () => {
                    try {
                        const progress = await getDocumentProgress(documentId);
                        pollErrors = 0;

                        if (progress.status === 'failed') {
                            clearInterval(pollId);
                            setState((prev) => ({
                                ...prev,
                                uploadedDocuments: prev.uploadedDocuments.map((d) =>
                                    d.id === documentId ? { ...d, status: 'failed' as const } : d,
                                ),
                            }));
                            return;
                        }

                        if (progress.progress_pct >= 100 || progress.status === 'completed') {
                            clearInterval(pollId);
                            setState((prev) => ({
                                ...prev,
                                uploadedDocuments: prev.uploadedDocuments.map((d) =>
                                    d.id === documentId
                                        ? { ...d, status: 'completed' as const, records_count: progress.total_chunks }
                                        : d,
                                ),
                            }));
                            if (state.currentSession) {
                                const updated = await fetchSessionStatus(state.currentSession.id, accessToken);
                                setState((prev) => ({ ...prev, requirements: updated.requirements }));
                            }
                        }
                    } catch {
                        pollErrors++;
                        if (pollErrors >= MAX_POLL_ERRORS) {
                            clearInterval(pollId);
                        }
                    }
                }, 3000);

                setTimeout(() => clearInterval(pollId), 5 * 60 * 1000);

                return uploadedFile;
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to upload document';
                setState((prev) => ({ ...prev, uploadingFile: false, uploadError: message }));
            }
        },
        [state.currentSession, clientId, accessToken],
    );

    const removeFile = useCallback(
        async (fileId: string, type: 'csv' | 'document') => {
            if (!state.currentSession) return;
            try {
                if (type === 'document') {
                    const doc = state.uploadedDocuments.find((f) => f.id === fileId);
                    await kbDeleteDocument(fileId, doc?.storage_path ?? null);
                }
                setState((prev) => ({
                    ...prev,
                    [type === 'csv' ? 'uploadedCsvs' : 'uploadedDocuments']: (
                        type === 'csv' ? prev.uploadedCsvs : prev.uploadedDocuments
                    ).filter((f) => f.id !== fileId),
                }));
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to remove file';
                setState((prev) => ({ ...prev, lastError: message }));
            }
        },
        [state.currentSession, state.uploadedDocuments],
    );

    const finalize = useCallback(async () => {
        if (!state.currentSession || !accessToken) return;
        try {
            const updated = await finalizeConfig(state.currentSession.id, accessToken);
            setState((prev) => ({
                ...prev,
                currentSession: updated,
                configStatus: updated.config_status,
            }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to finalize config';
            setState((prev) => ({ ...prev, lastError: message }));
        }
    }, [state.currentSession, accessToken]);

    const connectGoogle = useCallback(async () => {
        if (!state.currentSession || !accessToken) return;
        try {
            const { auth_url } = await initiateGoogleAuth(accessToken);
            const popup = window.open(auth_url, 'google-oauth', 'width=600,height=700,scrollbars=yes');

            if (!popup) {
                setState((prev) => ({ ...prev, lastError: 'Popup bloqueado pelo navegador' }));
                return;
            }

            const pollInterval = setInterval(async () => {
                if (popup.closed) {
                    clearInterval(pollInterval);
                    try {
                        const accounts = await fetchGoogleAccounts(accessToken);
                        if (accounts.length > 0) {
                            const defaultAccount = accounts.find((a) => a.is_default) || accounts[0];
                            await linkGoogleToSession(
                                state.currentSession!.id,
                                defaultAccount.account_email,
                                accessToken,
                            );
                            setState((prev) => ({
                                ...prev,
                                googleConnected: true,
                                googleEmail: defaultAccount.account_email,
                            }));
                            const updated = await fetchSessionStatus(state.currentSession!.id, accessToken);
                            setState((prev) => ({ ...prev, requirements: updated.requirements }));
                        }
                    } catch (err) {
                        const message = err instanceof Error ? err.message : 'Failed to verify Google connection';
                        setState((prev) => ({ ...prev, lastError: message }));
                    }
                }
            }, 1000);

            setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to start Google auth';
            setState((prev) => ({ ...prev, lastError: message }));
        }
    }, [state.currentSession, accessToken]);

    const activate = useCallback(async () => {
        if (!state.currentSession || !accessToken) return;
        try {
            setState((prev) => ({ ...prev, activating: true }));
            const updated = await activateSession(state.currentSession.id, accessToken);
            setState((prev) => ({
                ...prev,
                currentSession: updated,
                configStatus: updated.config_status,
                activating: false,
            }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to activate session';
            setState((prev) => ({ ...prev, activating: false, lastError: message }));
        }
    }, [state.currentSession, accessToken]);

    const clearError = useCallback(() => {
        setState((prev) => ({ ...prev, lastError: null }));
    }, []);

    return {
        ...state,
        selectAgent,
        createNewSession,
        resumeSession,
        saveField,
        uploadCsv,
        uploadDoc,
        removeFile,
        finalize,
        activate,
        connectGoogle,
        reloadCatalog,
        clearError,
    };
}
