import { useState, useCallback, useEffect, useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';
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
} from '../services/standaloneAgentService';
import { uploadFile as kbUploadFile, deleteDocument as kbDeleteDocument, getDocumentProgress } from '../services/knowledgeBaseService';
import { useToast } from '@chakra-ui/react';

export interface StandaloneAgentState {
    // Catalog
    agents: AgentCatalogEntry[];
    selectedAgent: AgentCatalogEntry | null;
    loadingCatalog: boolean;
    catalogError: string | null;

    // Sessions
    sessions: StandaloneAgentSession[];
    currentSession: StandaloneAgentSession | null;

    // Configuration
    configStatus: 'configuring' | 'ready' | 'active' | 'archived';
    requirements: RequirementsStatus | null;
    collectedContext: Record<string, string | boolean>;

    // Files
    uploadedCsvs: UploadedFile[];
    uploadedDocuments: UploadedFile[];
    uploadingFile: boolean;
    uploadError: string | null;

    // Google
    googleConnected: boolean;
    googleEmail: string | null;

    // Loading states
    creating: boolean;
    activating: boolean;
    savingField: boolean;
}

/**
 * Hook to manage standalone agent configuration and chat state
 */
export function useStandaloneAgent() {
    const auth = useContext(AuthContext);
    const toast = useToast();

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
    });

    const accessToken = auth?.session?.access_token;
    const clientId = auth?.clientId;

    // Load agent catalog on mount
    useEffect(() => {
        if (!accessToken) return;

        const loadCatalog = async () => {
            try {
                setState((prev) => ({ ...prev, loadingCatalog: true, catalogError: null }));
                const agents = await fetchAgentCatalog(accessToken);
                setState((prev) => ({
                    ...prev,
                    agents,
                    loadingCatalog: false,
                }));
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to load agents';
                setState((prev) => ({
                    ...prev,
                    catalogError: message,
                    loadingCatalog: false,
                }));
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        };

        loadCatalog();
    }, [accessToken, toast]);

    // Load user's sessions on mount
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
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [accessToken, toast]
    );

    const createNewSession = useCallback(
        async (agentId: string) => {
            if (!accessToken) return;

            try {
                setState((prev) => ({ ...prev, creating: true }));
                const session = await createSession(agentId, accessToken);

                // Fetch full session details with requirements
                const sessionWithRequirements = await fetchSessionStatus(session.id, accessToken);

                setState((prev) => ({
                    ...prev,
                    currentSession: session,
                    configStatus: session.config_status,
                    requirements: sessionWithRequirements.requirements,
                    collectedContext: session.collected_context,
                    uploadedCsvs: [], // Will be populated from session
                    uploadedDocuments: [], // Will be populated from session
                    googleConnected: !!session.google_account_email,
                    googleEmail: session.google_account_email,
                    creating: false,
                }));

                toast({ title: 'Sessão criada!', status: 'success', duration: 2000 });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to create session';
                setState((prev) => ({ ...prev, creating: false }));
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [accessToken, toast]
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

                // Load agent details
                await selectAgent(session.agent_catalog_id);
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to resume session';
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [accessToken, toast, selectAgent]
    );

    const saveField = useCallback(
        async (fieldName: string, value: string | boolean) => {
            if (!state.currentSession || !accessToken) return;

            try {
                setState((prev) => ({ ...prev, savingField: true }));
                await saveConfigField(state.currentSession.id, fieldName, value, accessToken);

                // Refresh requirements from backend to recompute completion
                const updated = await fetchSessionStatus(state.currentSession.id, accessToken);

                // Update local state
                setState((prev) => ({
                    ...prev,
                    collectedContext: {
                        ...prev.collectedContext,
                        [fieldName]: value,
                    },
                    requirements: updated.requirements,
                    savingField: false,
                }));

                toast({ title: 'Campo salvo!', status: 'success', duration: 1500 });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to save field';
                setState((prev) => ({ ...prev, savingField: false }));
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, accessToken, toast]
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

                toast({
                    title: 'CSV enviado!',
                    description: `${file.name} foi processado com sucesso`,
                    status: 'success',
                    duration: 2000,
                });

                return uploadedFile;
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to upload CSV';
                setState((prev) => ({
                    ...prev,
                    uploadingFile: false,
                    uploadError: message,
                }));
                toast({ title: 'Erro no upload', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, accessToken, toast]
    );

    const uploadDoc = useCallback(
        async (file: File) => {
            if (!state.currentSession || !clientId || !accessToken) return;

            try {
                setState((prev) => ({ ...prev, uploadingFile: true, uploadError: null }));

                // 1. Upload via knowledgeBaseService (handles embedding)
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

                // 2. Link document to session in backend
                try {
                    await linkDocumentToSession(state.currentSession.id, documentId, accessToken);
                } catch (linkErr) {
                    console.error('Failed to link document to session:', linkErr);
                }

                toast({
                    title: 'Documento enviado!',
                    description: `${file.name} está sendo processado`,
                    status: 'success',
                    duration: 2000,
                });

                // 3. Poll for embedding completion
                const pollId = setInterval(async () => {
                    try {
                        const progress = await getDocumentProgress(documentId);

                        // Stop polling on failure
                        if (progress.status === 'failed') {
                            clearInterval(pollId);
                            setState((prev) => ({
                                ...prev,
                                uploadedDocuments: prev.uploadedDocuments.map((d) =>
                                    d.id === documentId
                                        ? { ...d, status: 'failed' as const }
                                        : d
                                ),
                            }));
                            toast({ title: 'Erro no processamento', description: `Falha ao processar ${file.name}`, status: 'error', duration: 5000 });
                            return;
                        }

                        // Stop polling on completion (check both progress and status)
                        if (progress.progress_pct >= 100 || progress.status === 'completed') {
                            clearInterval(pollId);
                            setState((prev) => ({
                                ...prev,
                                uploadedDocuments: prev.uploadedDocuments.map((d) =>
                                    d.id === documentId
                                        ? { ...d, status: 'completed' as const, records_count: progress.total_chunks }
                                        : d
                                ),
                            }));
                            // Refresh requirements to update doc count
                            if (state.currentSession) {
                                const updated = await fetchSessionStatus(state.currentSession.id, accessToken);
                                setState((prev) => ({
                                    ...prev,
                                    requirements: updated.requirements,
                                }));
                            }
                        }
                    } catch {
                        // Silently continue polling
                    }
                }, 3000);

                // Stop polling after 5 minutes
                setTimeout(() => clearInterval(pollId), 5 * 60 * 1000);

                return uploadedFile;
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to upload document';
                setState((prev) => ({
                    ...prev,
                    uploadingFile: false,
                    uploadError: message,
                }));
                toast({ title: 'Erro no upload', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, clientId, accessToken, toast]
    );

    const removeFile = useCallback(
        async (fileId: string, type: 'csv' | 'document') => {
            if (!state.currentSession) return;

            try {
                if (type === 'document') {
                    // Find the document to get its storage_path
                    const doc = state.uploadedDocuments.find((f) => f.id === fileId);
                    await kbDeleteDocument(fileId, doc?.storage_path ?? null);
                }
                // TODO: CSV deletion via backend when route is added

                setState((prev) => ({
                    ...prev,
                    [type === 'csv' ? 'uploadedCsvs' : 'uploadedDocuments']: (
                        type === 'csv' ? prev.uploadedCsvs : prev.uploadedDocuments
                    ).filter((f) => f.id !== fileId),
                }));

                toast({ title: 'Arquivo removido!', status: 'success', duration: 1500 });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to remove file';
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, state.uploadedDocuments, toast]
    );

    const finalize = useCallback(
        async () => {
            if (!state.currentSession || !accessToken) return;

            try {
                const updated = await finalizeConfig(state.currentSession.id, accessToken);

                setState((prev) => ({
                    ...prev,
                    currentSession: updated,
                    configStatus: updated.config_status,
                }));

                toast({ title: 'Configuração finalizada!', status: 'success', duration: 2000 });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to finalize config';
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, accessToken, toast]
    );

    const connectGoogle = useCallback(
        async () => {
            if (!state.currentSession || !accessToken) return;

            try {
                // 1. Call tool_pool_api to get auth URL
                const { auth_url } = await initiateGoogleAuth(accessToken);

                // 2. Open popup for Google OAuth
                const popup = window.open(
                    auth_url,
                    'google-oauth',
                    'width=600,height=700,scrollbars=yes'
                );

                if (!popup) {
                    toast({ title: 'Erro', description: 'Popup bloqueado pelo navegador', status: 'error', duration: 3000 });
                    return;
                }

                // 3. Poll for popup close, then check for Google accounts
                const pollInterval = setInterval(async () => {
                    if (popup.closed) {
                        clearInterval(pollInterval);
                        try {
                            const accounts = await fetchGoogleAccounts(accessToken);
                            if (accounts.length > 0) {
                                const defaultAccount = accounts.find(a => a.is_default) || accounts[0];
                                // Link to session
                                await linkGoogleToSession(
                                    state.currentSession!.id,
                                    defaultAccount.account_email,
                                    accessToken
                                );

                                setState((prev) => ({
                                    ...prev,
                                    googleConnected: true,
                                    googleEmail: defaultAccount.account_email,
                                }));

                                // Refresh requirements
                                const updated = await fetchSessionStatus(state.currentSession!.id, accessToken);
                                setState((prev) => ({
                                    ...prev,
                                    requirements: updated.requirements,
                                }));

                                toast({ title: 'Google conectado!', description: defaultAccount.account_email, status: 'success', duration: 3000 });
                            }
                        } catch (err) {
                            const message = err instanceof Error ? err.message : 'Failed to verify Google connection';
                            toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
                        }
                    }
                }, 1000);

                // Safety: stop polling after 5 minutes
                setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to start Google auth';
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, accessToken, toast]
    );

    const activate = useCallback(
        async () => {
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

                toast({
                    title: 'Agente ativado!',
                    description: 'Você pode começar a conversa agora',
                    status: 'success',
                    duration: 2000,
                });
            } catch (err) {
                const message = err instanceof Error ? err.message : 'Failed to activate session';
                setState((prev) => ({ ...prev, activating: false }));
                toast({ title: 'Erro', description: message, status: 'error', duration: 3000 });
            }
        },
        [state.currentSession, accessToken, toast]
    );

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
    };
}
