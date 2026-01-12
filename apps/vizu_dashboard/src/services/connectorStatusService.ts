/**
 * Service for connector status, sync history, and dashboard statistics.
 */

import { supabase } from "../lib/supabase";

const API_BASE_URL = import.meta.env.VITE_DATA_INGESTION_API_URL || 'http://localhost:8000';

// --- Types ---

export type ConnectorStatus = 'active' | 'inactive' | 'error' | 'pending';
export type SyncStatus = 'running' | 'completed' | 'failed' | 'cancelled';
export type FileStatus = 'uploaded' | 'processing' | 'completed' | 'failed' | 'deleted';

export interface ConnectorStatusResponse {
  credential_id: number;
  nome_conexao: string;
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

async function getAuthToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token || null;
}

/**
 * Get all connectors with sync status for a client.
 */
export async function getConnectorStatus(
  clienteVizuId: string
): Promise<ConnectorListResponse> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/status?client_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch connector status' }));
    throw new Error(error.detail || 'Failed to fetch connector status');
  }

  return response.json();
}

/**
 * Get sync history for a specific connector.
 */
export async function getSyncHistory(
  credentialId: number,
  limit: number = 10
): Promise<SyncHistoryResponse[]> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/${credentialId}/sync-history?limit=${limit}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch sync history' }));
    throw new Error(error.detail || 'Failed to fetch sync history');
  }

  return response.json();
}

/**
 * Get uploaded files for a client.
 */
export async function getUploadedFiles(
  clienteVizuId: string
): Promise<FileListResponse> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/files?client_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch files' }));
    throw new Error(error.detail || 'Failed to fetch files');
  }

  return response.json();
}

/**
 * Delete an uploaded file.
 */
export async function deleteUploadedFile(
  fileId: string,
  clienteVizuId: string
): Promise<void> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/files/${fileId}?client_id=${clienteVizuId}`,
    {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete file' }));
    throw new Error(error.detail || 'Failed to delete file');
  }
}

/**
 * Get dashboard statistics for admin home page.
 */
export async function getDashboardStats(
  clienteVizuId: string
): Promise<DashboardStatsResponse> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/dashboard-stats?client_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch dashboard stats' }));
    throw new Error(error.detail || 'Failed to fetch dashboard stats');
  }

  return response.json();
}

/**
 * Start a sync job for a connector.
 */
export async function startSyncJob(
  credentialId: number,
  resourceType?: string
): Promise<{ sync_id: string; status: string; message: string }> {
  const token = await getAuthToken();

  const response = await fetch(
    `${API_BASE_URL}/connectors/sync/start`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        credential_id: credentialId,
        resource_type: resourceType,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to start sync' }));
    throw new Error(error.detail || 'Failed to start sync');
  }

  return response.json();
}
