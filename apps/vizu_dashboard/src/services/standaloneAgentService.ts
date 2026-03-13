/**
 * Service para gerenciamento de Agentes Standalone.
 * Comunica com standalone_agent_api para:
 * - Carregar catálogo de agentes
 * - Criar / recuperar sessões
 * - Upload de arquivos CSV e documentos
 * - SSE streaming com Config Helper e agentes
 */

import { supabase } from "../lib/supabase";

const AGENT_API_URL = import.meta.env.VITE_STANDALONE_AGENT_API || 'http://localhost:8001';
const TOOL_POOL_API_URL = import.meta.env.VITE_TOOL_POOL_API_URL || 'http://localhost:8006';

// ── Types ──────────────────────────────────────────────────────

export interface AgentCatalogEntry {
    id: string;
    name: string;
    slug: string;
    description: string;
    category: string;
    icon: string;
    agent_config: {
        name: string;
        role: string;
        elicitation_strategy?: string;
        enabled_tools: string[];
        max_turns: number;
        model?: string;
        metadata?: Record<string, unknown>;
    };
    prompt_name: string;
    required_context: Array<{
        field: string;
        type: string;
        required: boolean;
        label: string;
        prompt_hint?: string;
    }>;
    required_files: {
        csv?: { min: number; max: number; description: string };
        text?: { min: number; max: number; description: string };
    };
    requires_google: boolean;
    tier_required: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface StandaloneAgentSession {
    id: string;
    client_id: string;
    agent_catalog_id: string;
    session_id: string;
    config_status: 'configuring' | 'ready' | 'active' | 'archived';
    collected_context: Record<string, string | boolean>;
    uploaded_file_ids: string[];
    uploaded_document_ids: string[];
    google_account_email: string | null;
    metadata: Record<string, unknown>;
    created_at: string;
    updated_at: string;
}

export interface UploadedFile {
    id: string;
    file_name: string;
    storage_path: string;
    columns_schema?: Array<{
        name: string;
        type: string;
        sample: unknown[];
    }>;
    records_count: number;
    status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface RequirementsStatus {
    total_fields: number;
    filled_fields: number;
    missing: Array<{
        field_name: string;
        label: string;
        type: string;
    }>;
    files_required: {
        csv: { min: number; max: number; current: number };
        text: { min: number; max: number; current: number };
    };
    google_required: boolean;
    google_connected: boolean;
    completion_pct: number;
}

// ── SSE Event Types ──────────────────────────────────────────

export type ConfigHelperEventType = 'token' | 'tool_start' | 'tool_end' | 'done' | 'error';
export type AgentEventType = 'token' | 'tool_start' | 'tool_end' | 'done' | 'error' | 'structured_data';

export interface StreamEvent {
    event: ConfigHelperEventType | AgentEventType;
    data: string | ToolEvent | DoneData | ErrorData | StructuredDataEvent;
}

export interface ToolEvent {
    tool: string;
    input?: Record<string, unknown>;
}

export interface DoneData {
    final_response: string;
    structured_data?: Record<string, unknown>;
    message_id: string;
}

export interface ErrorData {
    error: string;
    details?: string;
}

export interface StructuredDataEvent {
    title: string;
    columns: Array<{ name: string; type: string }>;
    rows: Array<Record<string, unknown>>;
}

// ── Catalog API ────────────────────────────────────────────────

/**
 * Fetch list of available agents filtered by tier
 */
export async function fetchAgentCatalog(
    accessToken: string,
    tier?: string
): Promise<AgentCatalogEntry[]> {
    const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents`, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch agent catalog: ${response.status}`);
    }

    return response.json();
}

/**
 * Get details about a specific agent including requirements
 */
export async function fetchAgentDetails(
    agentId: string,
    accessToken: string
): Promise<AgentCatalogEntry> {
    const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/${agentId}`, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch agent details: ${response.status}`);
    }

    return response.json();
}

// ── Session API ────────────────────────────────────────────────

/**
 * Create a new session for an agent
 */
export async function createSession(
    agentCatalogId: string,
    accessToken: string
): Promise<StandaloneAgentSession> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ agent_catalog_id: agentCatalogId }),
    });

    if (!response.ok) {
        throw new Error(`Failed to create session: ${response.status}`);
    }

    return response.json();
}

/**
 * Fetch user's sessions list
 */
export async function fetchSessions(accessToken: string): Promise<StandaloneAgentSession[]> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions`, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch sessions: ${response.status}`);
    }

    return response.json();
}

/**
 * Get session details including requirements status
 */
export async function fetchSessionStatus(
    sessionId: string,
    accessToken: string
): Promise<StandaloneAgentSession & { requirements: RequirementsStatus }> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}`, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch session status: ${response.status}`);
    }

    return response.json();
}

/**
 * Update a configuration field in session
 */
export async function saveConfigField(
    sessionId: string,
    fieldName: string,
    value: string | boolean,
    accessToken: string
): Promise<void> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/config/${fieldName}`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ value }),
    });

    if (!response.ok) {
        throw new Error(`Failed to save config field: ${response.status}`);
    }
}

/**
 * Finalize configuration and mark session as ready
 */
export async function finalizeConfig(
    sessionId: string,
    accessToken: string
): Promise<StandaloneAgentSession> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/config/finalize`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to finalize config: ${response.status}`);
    }

    return response.json();
}

// ── File Upload API ────────────────────────────────────────────

/**
 * Upload CSV file to session
 */
export async function uploadCsvFile(
    sessionId: string,
    file: File,
    accessToken: string
): Promise<UploadedFile> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/csv`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Failed to upload CSV: ${response.status}`);
    }

    return response.json();
}

/**
 * Upload document/text file to session for RAG
 */
export async function uploadDocument(
    sessionId: string,
    file: File,
    accessToken: string
): Promise<{ document_id: string; status: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/documents`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Failed to upload document: ${response.status}`);
    }

    return response.json();
}

/**
 * Link a document (uploaded via knowledge base) to a session
 */
export async function linkDocumentToSession(
    sessionId: string,
    documentId: string,
    accessToken: string
): Promise<void> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/documents/link`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ document_id: documentId }),
    });

    if (!response.ok) {
        throw new Error(`Failed to link document to session: ${response.status}`);
    }
}

/**
 * Peek at CSV columns without running full query
 */
export async function peekCsvColumns(
    fileId: string,
    sessionId: string,
    accessToken: string
): Promise<{
    columns: Array<{ name: string; type: string }>;
    sample_rows: Array<Record<string, unknown>>;
}> {
    const response = await fetch(
        `${AGENT_API_URL}/v1/sessions/${sessionId}/csv/${fileId}/peek`,
        {
            headers: {
                Authorization: `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
        }
    );

    if (!response.ok) {
        throw new Error(`Failed to peek CSV: ${response.status}`);
    }

    return response.json();
}

// ── Streaming API ──────────────────────────────────────────────

/**
 * Stream config helper chat SSE
 * Yields StreamEvent objects as they arrive
 */
export async function* streamConfigHelperChat(
    sessionId: string,
    message: string,
    accessToken: string
): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/chat/config`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
    });

    if (!response.ok) {
        throw new Error(`Failed to stream config helper: ${response.status}`);
    }

    if (!response.body) {
        throw new Error('Response body is empty');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        let done = false;
        while (!done) {
            const { value, done: streamDone } = await reader.read();
            done = streamDone;

            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6)) as StreamEvent;
                            yield event;
                        } catch (e) {
                            console.error('Failed to parse SSE event:', line, e);
                        }
                    }
                }

                buffer = lines[lines.length - 1];
            }
        }

        // Process remaining buffer
        if (buffer.trim().startsWith('data: ')) {
            try {
                const event = JSON.parse(buffer.trim().slice(6)) as StreamEvent;
                yield event;
            } catch (e) {
                console.error('Failed to parse final SSE event:', buffer, e);
            }
        }
    } finally {
        reader.releaseLock();
    }
}

/**
 * Stream agent chat SSE
 * Yields StreamEvent objects as they arrive
 */
export async function* streamAgentChat(
    sessionId: string,
    message: string,
    accessToken: string
): AsyncGenerator<StreamEvent> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/chat/agent`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
    });

    if (!response.ok) {
        throw new Error(`Failed to stream agent: ${response.status}`);
    }

    if (!response.body) {
        throw new Error('Response body is empty');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        let done = false;
        while (!done) {
            const { value, done: streamDone } = await reader.read();
            done = streamDone;

            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6)) as StreamEvent;
                            yield event;
                        } catch (e) {
                            console.error('Failed to parse SSE event:', line, e);
                        }
                    }
                }

                buffer = lines[lines.length - 1];
            }
        }

        // Process remaining buffer
        if (buffer.trim().startsWith('data: ')) {
            try {
                const event = JSON.parse(buffer.trim().slice(6)) as StreamEvent;
                yield event;
            } catch (e) {
                console.error('Failed to parse final SSE event:', buffer, e);
            }
        }
    } finally {
        reader.releaseLock();
    }
}

// ── Google OAuth ───────────────────────────────────────────────

/**
 * Initiate Google OAuth flow via tool_pool_api
 */
export async function initiateGoogleAuth(
    accessToken: string
): Promise<{ auth_url: string; state: string }> {
    const response = await fetch(`${TOOL_POOL_API_URL}/integrations/google/auth/initiate`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to initiate Google auth: ${response.status}`);
    }

    return response.json();
}

/**
 * Fetch Google accounts from tool_pool_api
 */
export async function fetchGoogleAccounts(
    accessToken: string
): Promise<Array<{ account_email: string; account_name: string; is_default: boolean }>> {
    const response = await fetch(`${TOOL_POOL_API_URL}/integrations/google/accounts`, {
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to fetch Google accounts: ${response.status}`);
    }

    return response.json();
}

/**
 * Link Google account email to a standalone agent session
 */
export async function linkGoogleToSession(
    sessionId: string,
    email: string,
    accessToken: string
): Promise<void> {
    const response = await fetch(
        `${AGENT_API_URL}/v1/sessions/${sessionId}/google?email=${encodeURIComponent(email)}`,
        {
            method: 'PATCH',
            headers: {
                Authorization: `Bearer ${accessToken}`,
                'Content-Type': 'application/json',
            },
        }
    );

    if (!response.ok) {
        throw new Error(`Failed to link Google account: ${response.status}`);
    }
}

// ── Session Activation ─────────────────────────────────────────

/**
 * Activate a session (mark as ready → active)
 */
export async function activateSession(
    sessionId: string,
    accessToken: string
): Promise<StandaloneAgentSession> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/activate`, {
        method: 'POST',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to activate session: ${response.status}`);
    }

    return response.json();
}

/**
 * Delete uploaded file from session
 */
export async function deleteFile(
    sessionId: string,
    fileId: string,
    accessToken: string
): Promise<void> {
    const response = await fetch(`${AGENT_API_URL}/v1/sessions/${sessionId}/files/${fileId}`, {
        method: 'DELETE',
        headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        },
    });

    if (!response.ok) {
        throw new Error(`Failed to delete file: ${response.status}`);
    }
}
