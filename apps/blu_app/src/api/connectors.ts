/**
 * Connector service for blu_app — adapted from blu_dashboard/connectorService.ts.
 * Uses blu_app's supabase client. clientId is already resolved (no resolveClientId needed).
 */

import { supabase } from '@/api/client'

export type ConnectorPlatform =
  | 'shopify'
  | 'vtex'
  | 'loja_integrada'
  | 'bigquery'
  | 'postgresql'
  | 'mysql'
  | 'whatsapp'
  | 'conta_azul'

export interface ShopifyCredentials {
  shop_name: string
  access_token: string
  api_version?: string
}

export interface VTEXCredentials {
  account_name: string
  app_key: string
  app_token: string
  environment?: string
}

export interface LojaIntegradaCredentials {
  api_key: string
  application_key?: string
}

export interface BigQueryCredentials {
  project_id: string
  dataset_id?: string
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

export interface WhatsAppCredentials {
  whatsapp_number: string
  contact_label?: string
}

export interface ContaAzulCredentials {
  client_id: string
  client_secret: string
  access_token: string
}

export type CredentialPayload =
  | ShopifyCredentials
  | VTEXCredentials
  | LojaIntegradaCredentials
  | BigQueryCredentials
  | SQLCredentials
  | WhatsAppCredentials
  | ContaAzulCredentials

export interface CreateCredentialRequest {
  client_id: string
  nome_servico: string
  tipo_servico: string
  credentials: CredentialPayload
}

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
  request: CreateCredentialRequest,
): Promise<CredentialResponse> {
  const tipoUpper = (request.tipo_servico || '').toUpperCase()

  // ── BigQuery — FDW setup via RPC ──────────────────────────────────────────
  if (tipoUpper === 'BIGQUERY') {
    const bq = request.credentials as BigQueryCredentials
    const { projectId, datasetId, tableName } = parseBigQueryTableRef(bq.table_name)
    const effectiveProject = projectId || bq.project_id
    const effectiveDataset = datasetId || bq.dataset_id || 'default'

    const { data: serverResult, error: serverError } = await supabase.rpc('create_bigquery_server', {
      p_client_id: request.client_id,
      p_service_account_key: bq.service_account_json,
      p_project_id: effectiveProject,
      p_dataset_id: effectiveDataset,
      p_location: bq.location || 'US',
    })

    if (serverError) throw new Error(serverError.message || 'Falha ao criar servidor BigQuery')

    const result = serverResult as { success?: boolean; vault_key_id?: string; error?: string }
    if (!result.success) throw new Error(result.error || 'Falha ao criar servidor BigQuery')
    if (!result.vault_key_id) throw new Error('Falha ao persistir credencial no Vault')

    const { data: cred, error: credError } = await supabase
      .from('credencial_servico_externo')
      .insert({
        client_id: request.client_id,
        nome_servico: request.nome_servico,
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
      await supabase.rpc('drop_bigquery_server', { p_client_id: request.client_id })
      throw new Error(credError.message || 'Falha ao registrar credencial')
    }

    // Register foreign table + trigger column discovery (async, non-blocking)
    supabase
      .rpc('create_bigquery_foreign_table', {
        p_client_id: request.client_id,
        p_table_name: tableName,
        p_bigquery_table: `${effectiveProject}.${effectiveDataset}.${tableName}`,
        p_location: bq.location || 'US',
        p_timeout_ms: 300000,
        p_credential_id: parseInt(String(cred.id), 10),
      })
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
            .catch((e) => console.warn('[connectors] discover-bigquery-columns:', e))
        }
      })
      .catch((e) => console.warn('[connectors] create_bigquery_foreign_table:', e))

    return {
      id: String(cred.id),
      nome_servico: cred.nome_servico,
      tipo_servico: cred.tipo_servico,
      status: cred.status,
    }
  }

  // ── All other connectors ──────────────────────────────────────────────────
  const { data: cred, error } = await supabase
    .from('credencial_servico_externo')
    .insert({
      client_id: request.client_id,
      nome_servico: request.nome_servico,
      tipo_servico: tipoUpper,
      status: tipoUpper === 'WHATSAPP' ? 'active' : 'pending',
      connection_metadata: { credentials: request.credentials },
    })
    .select('id, nome_servico, tipo_servico, status')
    .single()

  if (error) throw new Error(error.message || 'Falha ao criar credencial')

  return {
    id: String(cred.id),
    nome_servico: cred.nome_servico,
    tipo_servico: cred.tipo_servico,
    status: cred.status,
  }
}

export async function deleteConnection(credentialId: string, clientId: string): Promise<void> {
  const { data: cred } = await supabase
    .from('credencial_servico_externo')
    .select('tipo_servico, tipo')
    .eq('id', parseInt(credentialId, 10))
    .maybeSingle()

  const tipo = ((cred as { tipo_servico?: string; tipo?: string } | null)?.tipo ?? (cred as { tipo_servico?: string; tipo?: string } | null)?.tipo_servico ?? '').toUpperCase()

  if (tipo === 'BIGQUERY') {
    await supabase
      .rpc('drop_bigquery_server', { p_client_id: clientId })
      .catch((e) => console.warn('[connectors] drop_bigquery_server:', e))
  }

  const { error } = await supabase
    .from('credencial_servico_externo')
    .delete()
    .eq('id', parseInt(credentialId, 10))

  if (error) throw new Error(error.message || 'Falha ao deletar conexão')
}
