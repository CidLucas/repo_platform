/**
 * Service for connector status, sync history, and dashboard statistics.
 *
 * Migration Note: This service was rewritten to remove dependency on
 * Data Ingestion API. All operations now use Supabase PostgREST queries.
 */

import { supabase } from "../lib/supabase";

// --- Types ---

export type ConnectorStatus = 'active' | 'inactive' | 'error' | 'pending';
export type SyncStatus = 'running' | 'completed' | 'failed' | 'cancelled';
export type FileStatus = 'uploaded' | 'processing' | 'completed' | 'failed' | 'deleted';

export interface ConnectorStatusResponse {
    credential_id: number;
    nome_servico: string;
    tipo_servico: string;
    status: ConnectorStatus;
    last_sync_at: string | null;
    last_sync_status: SyncStatus | null;
    records_count: number | null;
    error_message: string | null;
    created_at: string;
    updated_at: string;
}

export interface ConnectorListResponse {
    connectors: ConnectorStatusResponse[];
    total_connected: number;
    total_configured: number;
}

export interface SyncHistoryResponse {
    id: string;
    credential_id: number;
    status: SyncStatus;
    sync_started_at: string;
    sync_completed_at: string | null;
    records_processed: number;
    records_inserted: number;
    records_updated: number;
    records_failed: number;
    resource_type: string | null;
    error_message: string | null;
    created_at: string;
}

export interface UploadedFileResponse {
    id: string;
    file_name: string;
    file_size_bytes: number;
    file_type: string | null;
    status: FileStatus;
    records_count: number;
    records_imported: number;
    uploaded_at: string;
    processed_at: string | null;
    storage_path: string;
    download_url: string | null;
}

export interface FileListResponse {
    files: UploadedFileResponse[];
    total_files: number;
    total_size_bytes: number;
}

export interface StorageUsageResponse {
    database_size_bytes: number;
    database_size_mb: number;
    file_storage_bytes: number;
    file_storage_mb: number;
    total_storage_bytes: number;
    total_storage_mb: number;
    total_storage_gb: number;
    quota_gb: number | null;
    usage_percentage: number | null;
    total_files: number;
    total_records: number;
}

export interface DashboardStatsResponse {
    total_connectors: number;
    connected_connectors: number;
    pending_connectors: number;
    error_connectors: number;
    storage_usage: StorageUsageResponse;
    last_sync_at: string | null;
    total_syncs_today: number;
}

// --- Helper Functions ---

/**
 * Resolve client_id from Supabase auth session.
 */
async function resolveClientIdFromSupabase(): Promise<string | null> {
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
        return null;
    }

    const clientId = user.app_metadata?.client_id;
    if (clientId) {
        return clientId;
    }

    const { data: cliente } = await supabase
        .from('clientes_vizu')
        .select('client_id')
        .eq('email', user.email)
        .single();

    return cliente?.client_id || null;
}

async function resolveClientId(providedClientId?: string): Promise<string> {
    let resolvedClientId = providedClientId || localStorage.getItem('vizu_client_id') || '';

    if (!resolvedClientId) {
        const clientIdFromSupabase = await resolveClientIdFromSupabase();
        if (clientIdFromSupabase) {
            resolvedClientId = clientIdFromSupabase;
            localStorage.setItem('vizu_client_id', resolvedClientId);
        }
    }

    if (!resolvedClientId) {
        throw new Error('client_id is required');
    }

    return resolvedClientId;
}

// --- API Functions ---

/**
 * Get all connectors with sync status for a client.
 */
export async function getConnectorStatus(
    clienteVizuId: string
): Promise<ConnectorListResponse> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    // Get all credentials for the client
    const { data: credenciais, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('id, nome_servico, tipo_servico, status, created_at, updated_at')
        .eq('client_id', resolvedClientId)
        .order('created_at', { ascending: false });

    if (credError) {
        throw new Error(credError.message || 'Failed to fetch connector status');
    }

    const credentials = credenciais || [];
    const credentialIds = credentials.map(c => c.id);

    // Get latest sync info for each credential
    const { data: syncHistory } = await supabase
        .from('connector_sync_history')
        .select('credential_id, status, sync_completed_at, records_processed, error_message')
        .in('credential_id', credentialIds)
        .order('sync_completed_at', { ascending: false });

    // Build a map of latest sync per credential
    type SyncHistoryItem = { credential_id: number; status: string | null; sync_completed_at: string | null; records_processed: number | null; error_message: string | null };
    const latestSyncMap = new Map<number, SyncHistoryItem>();
    for (const sync of syncHistory || []) {
        if (!latestSyncMap.has(sync.credential_id)) {
            latestSyncMap.set(sync.credential_id, sync);
        }
    }

    // Map to response format
    const connectors: ConnectorStatusResponse[] = credentials.map(c => {
        const latestSync = latestSyncMap.get(c.id);

        return {
            credential_id: c.id,
            nome_servico: c.nome_servico || '',
            tipo_servico: c.tipo_servico || '',
            status: c.status as ConnectorStatus,
            last_sync_at: latestSync?.sync_completed_at || null,
            last_sync_status: (latestSync?.status as SyncStatus) || null,
            records_count: latestSync?.records_processed || null,
            error_message: latestSync?.error_message || null,
            created_at: c.created_at,
            updated_at: c.updated_at,
        };
    });

    const totalConnected = connectors.filter(c => c.status === 'active').length;
    const totalConfigured = connectors.length;

    return {
        connectors,
        total_connected: totalConnected,
        total_configured: totalConfigured,
    };
}

/**
 * Get sync history for a specific connector.
 */
export async function getSyncHistory(
    credentialId: number,
    limit: number = 10
): Promise<SyncHistoryResponse[]> {
    const { data: history, error } = await supabase
        .from('connector_sync_history')
        .select(`
      id,
      credential_id,
      status,
      sync_started_at,
      sync_completed_at,
      records_processed,
      records_inserted,
      records_updated,
      records_failed,
      resource_type,
      error_message,
      created_at
    `)
        .eq('credential_id', credentialId)
        .order('sync_started_at', { ascending: false })
        .limit(limit);

    if (error) {
        throw new Error(error.message || 'Failed to fetch sync history');
    }

    return (history || []).map(h => ({
        id: String(h.id),
        credential_id: h.credential_id,
        status: h.status as SyncStatus,
        sync_started_at: h.sync_started_at,
        sync_completed_at: h.sync_completed_at,
        records_processed: h.records_processed || 0,
        records_inserted: h.records_inserted || 0,
        records_updated: h.records_updated || 0,
        records_failed: h.records_failed || 0,
        resource_type: h.resource_type,
        error_message: h.error_message,
        created_at: h.created_at,
    }));
}

/**
 * Get uploaded files for a client.
 * Note: Files are stored in Supabase Storage and tracked in client_data_uploads table.
 */
export async function getUploadedFiles(
    clienteVizuId: string
): Promise<FileListResponse> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    // Query client_data_uploads or similar table
    const { data: uploads, error } = await supabase
        .from('client_data_uploads')
        .select('*')
        .eq('client_id', resolvedClientId)
        .order('created_at', { ascending: false });

    if (error) {
        // Table might not exist yet, return empty
        console.warn('Failed to fetch uploaded files:', error);
        return {
            files: [],
            total_files: 0,
            total_size_bytes: 0,
        };
    }

    const files: UploadedFileResponse[] = (uploads || []).map(u => ({
        id: String(u.id),
        file_name: u.file_name || '',
        file_size_bytes: u.file_size_bytes || 0,
        file_type: u.file_type,
        status: u.status as FileStatus,
        records_count: u.records_count || 0,
        records_imported: u.records_imported || 0,
        uploaded_at: u.created_at,
        processed_at: u.processed_at,
        storage_path: u.storage_path || '',
        download_url: u.download_url,
    }));

    const totalSizeBytes = files.reduce((sum, f) => sum + f.file_size_bytes, 0);

    return {
        files,
        total_files: files.length,
        total_size_bytes: totalSizeBytes,
    };
}

/**
 * Delete an uploaded file.
 */
export async function deleteUploadedFile(
    fileId: string,
    clienteVizuId: string
): Promise<void> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    // Get the file record first to get storage path
    const { data: fileRecord, error: fetchError } = await supabase
        .from('client_data_uploads')
        .select('storage_path')
        .eq('id', parseInt(fileId, 10))
        .eq('client_id', resolvedClientId)
        .single();

    if (fetchError) {
        throw new Error(fetchError.message || 'Failed to find file');
    }

    // Delete from storage if path exists
    if (fileRecord?.storage_path) {
        const { error: storageError } = await supabase.storage
            .from('client-uploads')
            .remove([fileRecord.storage_path]);

        if (storageError) {
            console.warn('Failed to delete file from storage:', storageError);
        }
    }

    // Delete the database record
    const { error: deleteError } = await supabase
        .from('client_data_uploads')
        .delete()
        .eq('id', parseInt(fileId, 10))
        .eq('client_id', resolvedClientId);

    if (deleteError) {
        throw new Error(deleteError.message || 'Failed to delete file record');
    }
}

/**
 * Get dashboard statistics for admin home page.
 */
export async function getDashboardStats(
    clienteVizuId: string
): Promise<DashboardStatsResponse> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    // Get connector counts
    const { data: credenciais, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('id, status')
        .eq('client_id', resolvedClientId);

    if (credError) {
        throw new Error(credError.message || 'Failed to fetch dashboard stats');
    }

    const connectors = credenciais || [];
    const totalConnectors = connectors.length;
    const connectedConnectors = connectors.filter(c => c.status === 'active').length;
    const pendingConnectors = connectors.filter(c => c.status === 'pending').length;
    const errorConnectors = connectors.filter(c => c.status === 'error').length;

    // Get today's sync count
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const { data: syncsToday, error: syncError } = await supabase
        .from('connector_sync_history')
        .select('id, sync_started_at')
        .eq('client_id', resolvedClientId)
        .gte('sync_started_at', today.toISOString());

    if (syncError) {
        console.warn('Failed to fetch today syncs:', syncError);
    }

    // Get last sync
    const { data: lastSync } = await supabase
        .from('connector_sync_history')
        .select('sync_completed_at')
        .eq('client_id', resolvedClientId)
        .order('sync_completed_at', { ascending: false })
        .limit(1)
        .single();

    // Get file storage stats
    const filesResponse = await getUploadedFiles(resolvedClientId);

    // Get record count from analytics
    const { data: resumo } = await supabase
        .schema('analytics_v2')
        .from('v_resumo_dashboard')
        .select('total_pedidos')
        .single();

    const storageUsage: StorageUsageResponse = {
        database_size_bytes: 0, // Would need admin access to get this
        database_size_mb: 0,
        file_storage_bytes: filesResponse.total_size_bytes,
        file_storage_mb: filesResponse.total_size_bytes / (1024 * 1024),
        total_storage_bytes: filesResponse.total_size_bytes,
        total_storage_mb: filesResponse.total_size_bytes / (1024 * 1024),
        total_storage_gb: filesResponse.total_size_bytes / (1024 * 1024 * 1024),
        quota_gb: null,
        usage_percentage: null,
        total_files: filesResponse.total_files,
        total_records: resumo?.total_pedidos || 0,
    };

    return {
        total_connectors: totalConnectors,
        connected_connectors: connectedConnectors,
        pending_connectors: pendingConnectors,
        error_connectors: errorConnectors,
        storage_usage: storageUsage,
        last_sync_at: lastSync?.sync_completed_at || null,
        total_syncs_today: syncsToday?.length || 0,
    };
}

/**
 * Start a sync job for a connector.
 * Calls run-sync edge function (fire-and-forget).
 */
export async function startSyncJob(
    credentialId: number,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _resourceType?: string
): Promise<{ sync_id: string; status: string; message: string }> {
    // Get client_id from credential
    const { data: credencial, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('client_id')
        .eq('id', credentialId)
        .single();

    if (credError || !credencial) {
        throw new Error('Credential not found');
    }

    const { data, error } = await supabase.functions.invoke('run-sync', {
        body: {
            client_id: credencial.client_id,
            credential_id: credentialId,
            force_full_sync: false,
        },
    });

    if (error) {
        throw new Error(error.message || 'Failed to start sync');
    }

    if (!data?.job_id) {
        throw new Error('Failed to create sync job');
    }

    return {
        sync_id: data.job_id,
        status: 'running',
        message: 'Sync started successfully',
    };
}
