/**
 * Service for connector status, sync history, and dashboard statistics.
 *
 * Schema baseline 2026-04-28:
 * - connector_sync_history removed → analytics_v2.reg_jobs (job_type = 'connector_sync')
 * - client_data_uploads removed → public.uploaded_files_metadata
 * - credencial_servico_externo: nome_servico→nome, tipo_servico→tipo, status(text)→ativo(bool)
 * - Storage bucket: client-uploads → file-uploads
 */

import { supabase } from "../lib/supabase";
import { resolveClientId } from "../lib/auth";

// --- Types ---

export type ConnectorStatus = 'active' | 'inactive' | 'error' | 'pending';
export type SyncStatus = 'running' | 'completed' | 'failed' | 'cancelled' | 'pending';
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

// --- API Functions ---

/**
 * Get all connectors with sync status for a client.
 * Sync history sourced from analytics_v2.reg_jobs (job_type = 'connector_sync').
 */
export async function getConnectorStatus(
    ClienteBluId: string
): Promise<ConnectorListResponse> {
    const resolvedClientId = await resolveClientId(ClienteBluId);

    const { data: credenciais, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('id, nome, tipo, ativo, created_at, updated_at')
        .eq('client_id', resolvedClientId)
        .order('created_at', { ascending: false });

    if (credError) {
        throw new Error(credError.message || 'Failed to fetch connector status');
    }

    const credentials = credenciais || [];
    const credentialIds = credentials.map(c => c.id);

    // Latest sync per credential from reg_jobs
    const { data: jobs } = await supabase
        .schema('analytics_v2')
        .from('reg_jobs')
        .select('credential_id, status, completed_at, rows_inserted, error_message')
        .eq('job_type', 'connector_sync')
        .in('credential_id', credentialIds)
        .order('completed_at', { ascending: false });

    type JobRow = {
        credential_id: number;
        status: string | null;
        completed_at: string | null;
        rows_inserted: number | null;
        error_message: string | null;
    };
    const latestJobMap = new Map<number, JobRow>();
    for (const job of (jobs || []) as JobRow[]) {
        if (!latestJobMap.has(job.credential_id)) {
            latestJobMap.set(job.credential_id, job);
        }
    }

    const connectors: ConnectorStatusResponse[] = credentials.map(c => {
        const latestJob = latestJobMap.get(c.id);
        const status: ConnectorStatus = c.ativo ? 'active' : 'inactive';

        return {
            credential_id: c.id,
            nome_servico: c.nome || '',
            tipo_servico: c.tipo || '',
            status,
            last_sync_at: latestJob?.completed_at || null,
            last_sync_status: (latestJob?.status as SyncStatus) || null,
            records_count: latestJob?.rows_inserted || null,
            error_message: latestJob?.error_message || null,
            created_at: c.created_at,
            updated_at: c.updated_at,
        };
    });

    return {
        connectors,
        total_connected: connectors.filter(c => c.status === 'active').length,
        total_configured: connectors.length,
    };
}

/**
 * Get sync history for a specific connector from analytics_v2.reg_jobs.
 */
export async function getSyncHistory(
    credentialId: number,
    limit: number = 10
): Promise<SyncHistoryResponse[]> {
    const { data: jobs, error } = await supabase
        .schema('analytics_v2')
        .from('reg_jobs')
        .select('job_id, credential_id, status, started_at, completed_at, rows_inserted, resource_type, error_message, created_at')
        .eq('job_type', 'connector_sync')
        .eq('credential_id', credentialId)
        .order('started_at', { ascending: false })
        .limit(limit);

    if (error) {
        throw new Error(error.message || 'Failed to fetch sync history');
    }

    return (jobs || []).map(j => ({
        id: String(j.job_id),
        credential_id: j.credential_id,
        status: j.status as SyncStatus,
        sync_started_at: j.started_at || j.created_at,
        sync_completed_at: j.completed_at,
        records_processed: Number(j.rows_inserted) || 0,
        records_inserted: Number(j.rows_inserted) || 0,
        records_updated: 0,
        records_failed: j.status === 'failed' ? 1 : 0,
        resource_type: j.resource_type,
        error_message: j.error_message,
        created_at: j.created_at,
    }));
}

/**
 * Get uploaded files for a client from public.uploaded_files_metadata.
 */
export async function getUploadedFiles(
    ClienteBluId: string
): Promise<FileListResponse> {
    const resolvedClientId = await resolveClientId(ClienteBluId);

    const { data: uploads, error } = await supabase
        .from('uploaded_files_metadata')
        .select('id, file_name, size_bytes, mime_type, status, storage_path, created_at, updated_at')
        .eq('client_id', resolvedClientId)
        .order('created_at', { ascending: false });

    if (error) {
        console.warn('Failed to fetch uploaded files:', error);
        return { files: [], total_files: 0, total_size_bytes: 0 };
    }

    const files: UploadedFileResponse[] = (uploads || []).map(u => ({
        id: String(u.id),
        file_name: u.file_name || '',
        file_size_bytes: u.size_bytes || 0,
        file_type: u.mime_type,
        status: (u.status as FileStatus) || 'uploaded',
        records_count: 0,
        records_imported: 0,
        uploaded_at: u.created_at,
        processed_at: u.updated_at || null,
        storage_path: u.storage_path || '',
        download_url: null,
    }));

    return {
        files,
        total_files: files.length,
        total_size_bytes: files.reduce((sum, f) => sum + f.file_size_bytes, 0),
    };
}

/**
 * Delete an uploaded file from storage and database.
 */
export async function deleteUploadedFile(
    fileId: string,
    ClienteBluId: string
): Promise<void> {
    const resolvedClientId = await resolveClientId(ClienteBluId);

    const { data: fileRecord, error: fetchError } = await supabase
        .from('uploaded_files_metadata')
        .select('storage_path')
        .eq('id', fileId)
        .eq('client_id', resolvedClientId)
        .maybeSingle();

    if (fetchError || !fileRecord) {
        throw new Error(fetchError?.message || 'Failed to find file');
    }

    if (fileRecord?.storage_path) {
        const { error: storageError } = await supabase.storage
            .from('file-uploads')
            .remove([fileRecord.storage_path]);

        if (storageError) {
            console.warn('Failed to delete file from storage:', storageError);
        }
    }

    const { error: deleteError } = await supabase
        .from('uploaded_files_metadata')
        .delete()
        .eq('id', fileId)
        .eq('client_id', resolvedClientId);

    if (deleteError) {
        throw new Error(deleteError.message || 'Failed to delete file record');
    }
}

/**
 * Get dashboard statistics for admin home page.
 * Sync counts sourced from analytics_v2.reg_jobs.
 */
export async function getDashboardStats(
    ClienteBluId: string
): Promise<DashboardStatsResponse> {
    const resolvedClientId = await resolveClientId(ClienteBluId);

    const { data: credenciais, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('id, ativo')
        .eq('client_id', resolvedClientId);

    if (credError) {
        throw new Error(credError.message || 'Failed to fetch dashboard stats');
    }

    const connectors = credenciais || [];
    const totalConnectors = connectors.length;
    const connectedConnectors = connectors.filter(c => c.ativo === true).length;
    const pendingConnectors = 0;
    const errorConnectors = 0;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const { data: syncsToday } = await supabase
        .schema('analytics_v2')
        .from('reg_jobs')
        .select('job_id, started_at')
        .eq('client_id', resolvedClientId)
        .eq('job_type', 'connector_sync')
        .gte('created_at', today.toISOString());

    const { data: lastJob } = await supabase
        .schema('analytics_v2')
        .from('reg_jobs')
        .select('completed_at')
        .eq('client_id', resolvedClientId)
        .eq('job_type', 'connector_sync')
        .not('completed_at', 'is', null)
        .order('completed_at', { ascending: false })
        .limit(1)
        .maybeSingle();

    const filesResponse = await getUploadedFiles(resolvedClientId);

    const { data: resumo } = await supabase
        .schema('analytics_v2')
        .from('v_resumo_dashboard')
        .select('total_pedidos')
        .limit(1)
        .maybeSingle();

    const storageUsage: StorageUsageResponse = {
        database_size_bytes: 0,
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
        last_sync_at: lastJob?.completed_at || null,
        total_syncs_today: syncsToday?.length || 0,
    };
}

/**
 * Start a sync job for a connector.
 */
export async function startSyncJob(
    credentialId: number,
    _resourceType?: string
): Promise<{ sync_id: string; status: string; message: string }> {
    const { data: credencial, error: credError } = await supabase
        .from('credencial_servico_externo')
        .select('client_id')
        .eq('id', credentialId)
        .maybeSingle();

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
