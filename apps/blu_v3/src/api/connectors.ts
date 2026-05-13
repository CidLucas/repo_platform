/**
 * Connector service for blu_v3 — mirrors apps/blu_app/src/api/connectors.ts.
 * Uses @blu/auth supabase singleton; clientId must be passed explicitly.
 */

import { supabase } from '@blu/auth'

export type ConnectorPlatform =
  | 'shopify'
  | 'vtex'
  | 'loja_integrada'
  | 'bigquery'
  | 'postgresql'
  | 'mysql'
  | 'conta_azul'

export interface ShopifyCredentials {
  shop_name: string
  access_token: string
}

export interface VTEXCredentials {
  account_name: string
  app_key: string
  app_token: string
}

export interface BigQueryCredentials {
  project_id: string
  dataset_id: string
  table_name: string
  location?: string
  service_account_json: Record<string, unknown>
}

export interface SQLCredentials {
  host: string
  port: number
  database: string
  user: string
  password: string
}

export interface ContaAzulCredentials {
  username: string
  password: string
}

export type CredentialPayload =
  | ShopifyCredentials
  | VTEXCredentials
  | BigQueryCredentials
  | SQLCredentials
  | ContaAzulCredentials

export interface CredentialResponse {
  id: string
  nome_servico: string
  tipo_servico: string
  status: string
}

function parseBigQueryTableRef(rawTableName: string): {
  projectId?: string
  datasetId?: string
  tableName: string
} {
  const cleaned = (rawTableName || '').replace(/`/g, '').trim()
  const parts = cleaned.split('.').map((p) => p.trim()).filter(Boolean)
  if (parts.length === 3) return { projectId: parts[0], datasetId: parts[1], tableName: parts[2] }
  if (parts.length === 2) return { datasetId: parts[0], tableName: parts[1] }
  return { tableName: parts[0] || cleaned }
}

export async function createCredential(
  clientId: string,
  platform: ConnectorPlatform,
  nomServico: string,
  credentials: CredentialPayload,
): Promise<CredentialResponse> {
  const tipoUpper = platform.toUpperCase()

  if (tipoUpper === 'BIGQUERY') {
    const bq = credentials as BigQueryCredentials
    const { projectId, datasetId, tableName } = parseBigQueryTableRef(bq.table_name)
    const effectiveProject = projectId || bq.project_id
    const effectiveDataset = datasetId || bq.dataset_id || 'default'

    const { data: serverResult, error: serverError } = await supabase.rpc('create_bigquery_server', {
      p_client_id: clientId,
      p_service_account_key: bq.service_account_json,
      p_project_id: effectiveProject,
      p_dataset_id: effectiveDataset,
      p_location: bq.location || 'US',
    })
    if (serverError) throw new Error(serverError.message)

    const result = serverResult as { success?: boolean; vault_key_id?: string; error?: string }
    if (!result.success) throw new Error(result.error || 'Falha ao criar servidor BigQuery')
    if (!result.vault_key_id) throw new Error('Falha ao persistir credencial no Vault')

    const { data: cred, error: credError } = await supabase
      .from('credencial_servico_externo')
      .insert({
        client_id: clientId,
        nome_servico: nomServico,
        tipo_servico: 'BIGQUERY',
        status: 'active',
        vault_key_id: result.vault_key_id,
        connection_metadata: {
          project_id: effectiveProject,
          dataset_id: effectiveDataset,
          table_name: tableName,
          location: bq.location || 'US',
        },
      })
      .select('id, nome_servico, tipo_servico, status')
      .single()

    if (credError) {
      await supabase.rpc('drop_bigquery_server', { p_client_id: clientId })
      throw new Error(credError.message)
    }

    // Non-blocking: foreign table + column discovery
    Promise.resolve(supabase
      .rpc('create_bigquery_foreign_table', {
        p_client_id: clientId,
        p_table_name: tableName,
        p_bigquery_table: `${effectiveProject}.${effectiveDataset}.${tableName}`,
        p_location: bq.location || 'US',
        p_timeout_ms: 300000,
        p_credential_id: parseInt(String(cred.id), 10),
      }))
      .then(({ data: ftResult }) => {
        const r = ftResult as { success?: boolean } | null
        if (r?.success) {
          supabase.functions
            .invoke('discover-bigquery-columns', {
              body: {
                credential_id: parseInt(String(cred.id), 10),
                service_account_json: bq.service_account_json,
                project_id: effectiveProject,
                dataset_id: effectiveDataset,
                table_name: tableName,
              },
            })
            .catch((e: unknown) => console.warn('[connectors] discover-bigquery-columns:', e))
        }
      })
      .catch((e: unknown) => console.warn('[connectors] create_bigquery_foreign_table:', e))

    return { id: String(cred.id), nome_servico: cred.nome_servico, tipo_servico: cred.tipo_servico, status: cred.status }
  }

  // All other platforms
  const { data: cred, error } = await supabase
    .from('credencial_servico_externo')
    .insert({
      client_id: clientId,
      nome_servico: nomServico,
      tipo_servico: tipoUpper,
      status: 'pending',
      connection_metadata: { credentials },
    })
    .select('id, nome_servico, tipo_servico, status')
    .single()

  if (error) throw new Error(error.message)
  return { id: String(cred.id), nome_servico: cred.nome_servico, tipo_servico: cred.tipo_servico, status: cred.status }
}

/**
 * Onboarding variant: creates the BigQuery credential and awaits column discovery
 * so the mapping step has real data before the user sees it.
 *
 * Flow (mirrors blu_app createCredential for BigQuery):
 *   1. create_bigquery_server RPC  — stores service account in vault
 *   2. insert credencial_servico_externo — get credential_id
 *   3. discover-bigquery-columns (blocking) — hit BigQuery API, return column names
 *   4. Non-blocking: create_bigquery_foreign_table — creates FDW table for sync
 */
export async function createBigQueryCredentialWithDiscovery(
  clientId: string,
  nomServico: string,
  credentials: BigQueryCredentials,
): Promise<{ credentialId: number; columns: string[] }> {
  const { projectId, datasetId, tableName } = parseBigQueryTableRef(credentials.table_name)
  const effectiveProject = projectId || credentials.project_id
  const effectiveDataset = datasetId || credentials.dataset_id || 'default'

  // 1. Vault + FDW server
  const { data: serverResult, error: serverError } = await supabase.rpc('create_bigquery_server', {
    p_client_id: clientId,
    p_service_account_key: credentials.service_account_json,
    p_project_id: effectiveProject,
    p_dataset_id: effectiveDataset,
    p_location: credentials.location || 'US',
  })
  if (serverError) throw new Error(serverError.message)
  const sr = serverResult as { success?: boolean; vault_key_id?: string; error?: string }
  if (!sr.success) throw new Error(sr.error || 'Falha ao criar servidor BigQuery')
  if (!sr.vault_key_id) throw new Error('Falha ao persistir credencial no Vault')

  // 2. Credential row
  const { data: cred, error: credError } = await supabase
    .from('credencial_servico_externo')
    .insert({
      client_id: clientId,
      nome_servico: nomServico,
      tipo_servico: 'BIGQUERY',
      status: 'active',
      vault_key_id: sr.vault_key_id,
      connection_metadata: {
        project_id: effectiveProject,
        dataset_id: effectiveDataset,
        table_name: tableName,
        location: credentials.location || 'US',
      },
    })
    .select('id')
    .single()
  if (credError) {
    await supabase.rpc('drop_bigquery_server', { p_client_id: clientId })
    throw new Error(credError.message)
  }

  const credentialId = parseInt(String(cred.id), 10)

  // 3. Register foreign table metadata — must happen before discover so that
  //    discover-bigquery-columns can call create_bigquery_foreign_table_from_schema
  try {
    await supabase.rpc('create_bigquery_foreign_table', {
      p_client_id: clientId,
      p_table_name: tableName,
      p_bigquery_table: `${effectiveProject}.${effectiveDataset}.${tableName}`,
      p_location: credentials.location || 'US',
      p_timeout_ms: 300000,
      p_credential_id: credentialId,
    })
  } catch (e: unknown) {
    console.warn('[connectors] create_bigquery_foreign_table:', e)
  }

  // 4. Discover columns (blocking) — hits BigQuery API, updates bigquery_foreign_tables
  //    with real column schema via create_bigquery_foreign_table_from_schema
  const { data: discoverData, error: discoverError } = await supabase.functions.invoke(
    'discover-bigquery-columns',
    {
      body: {
        credential_id: credentialId,
        service_account_json: credentials.service_account_json,
        project_id: effectiveProject,
        dataset_id: effectiveDataset,
        table_name: tableName,
      },
    },
  )
  if (discoverError) throw new Error(discoverError.message)
  const columns: string[] = (discoverData?.columns ?? []).map(
    (c: { name: string } | string) => (typeof c === 'string' ? c : c.name),
  )

  return { credentialId, columns }
}

// --- Sync operations ---

export async function startSync(credentialId: string): Promise<void> {
  const { error } = await supabase.functions.invoke('run-sync-etl', {
    body: { credential_id: credentialId, force_full_sync: false },
  })
  if (error) throw new Error(error.message)
}

export interface SyncHistoryRow {
  id: string
  credential_id: string
  status: 'pending' | 'running' | 'success' | 'failed' | string
  started_at: string | null
  finished_at: string | null
  rows_processed: number | null
  error_message: string | null
  created_at: string
}

export async function getSyncHistory(credentialId: string, limit = 10): Promise<SyncHistoryRow[]> {
  const { data, error } = await supabase
    .schema('analytics_v2')
    .from('reg_jobs')
    .select('*')
    .eq('credential_id', credentialId)
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw new Error(error.message)
  return (data ?? []) as SyncHistoryRow[]
}

// --- Uploaded files ---

export interface UploadedFileMeta {
  id: string
  client_id: string
  file_name: string
  file_size: number | null
  mime_type: string | null
  storage_path: string | null
  status: string
  created_at: string
}

export async function getUploadedFiles(clientId: string): Promise<UploadedFileMeta[]> {
  const { data, error } = await supabase
    .from('uploaded_files_metadata')
    .select('*')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })

  if (error) throw new Error(error.message)
  return (data ?? []) as UploadedFileMeta[]
}

export async function deleteUploadedFile(fileId: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('uploaded_files_metadata')
    .delete()
    .eq('id', fileId)
    .eq('client_id', clientId)

  if (error) throw new Error(error.message)
}
