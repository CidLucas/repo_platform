/**
 * Service para gerenciamento de conectores de dados.
 * Comunica diretamente com Supabase (RPCs + PostgREST) para configurar e sincronizar fontes de dados.
 *
 * Migration Note: This service was rewritten to remove dependency on
 * Data Ingestion API. All operations now go through Supabase RPCs and PostgREST.
 */

import { supabase } from "../lib/supabase";

// Tipos
export type ConnectorPlatform = 'shopify' | 'vtex' | 'loja_integrada' | 'bigquery' | 'postgresql' | 'mysql';

export interface ShopifyCredentials {
    shop_name: string;
    access_token: string;
    api_version?: string;
    api_key?: string;
    api_secret?: string;
}

export interface VTEXCredentials {
    account_name: string;
    app_key: string;
    app_token: string;
    environment?: string;
}

export interface LojaIntegradaCredentials {
    api_key: string;
    application_key?: string;
}

export interface BigQueryCredentials {
    project_id: string;
    dataset_id?: string;
    table_name: string;
    location?: string;
    service_account_json: Record<string, unknown>;
}

export interface SQLCredentials {
    host: string;
    port: number;
    database: string;
    user: string;
    password: string;
}

export type CredentialPayload =
    | ShopifyCredentials
    | VTEXCredentials
    | LojaIntegradaCredentials
    | BigQueryCredentials
    | SQLCredentials;

export interface CreateCredentialRequest {
    client_id: string;
    nome_servico: string;
    tipo_servico: string;
    credentials: CredentialPayload;
}

export interface CredentialResponse {
    id: string;
    secret_manager_id: string;
    nome_servico: string;
    tipo_servico: string;
    status: string;
}

export interface TestConnectionRequest {
    platform: ConnectorPlatform;
    credentials: CredentialPayload;
}

export interface TestConnectionResponse {
    success: boolean;
    message: string;
    platform: string;
    connection_string?: string;
}

export interface ExtractDataRequest {
    credential_id: string;
    resource: 'products' | 'orders' | 'customers' | 'inventory';
    limit?: number;
    page?: number;
    filters?: Record<string, unknown>;
}

export interface ExtractDataResponse {
    success: boolean;
    resource: string;
    total_records: number;
    page: number;
    has_more: boolean;
    data: unknown[];
}

export interface ConnectorStatus {
    id: string;
    platform: ConnectorPlatform;
    nome_servico: string;
    status: 'connected' | 'pending' | 'error' | 'syncing';
    last_sync?: string;
    records_count?: number;
    error_message?: string;
}

/**
 * Resolve client_id from Supabase auth session.
 * Falls back to clientes_vizu table lookup by user email.
 */
async function resolveClientIdFromSupabase(): Promise<string | null> {
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
        console.warn('Failed to get user from Supabase auth:', error);
        return null;
    }

    const clientId = user.app_metadata?.client_id || user.user_metadata?.client_id;
    if (clientId) {
        return clientId;
    }

    const { data: byExternalUserId, error: byExternalUserIdError } = await supabase
        .from('clientes_vizu')
        .select('client_id')
        .eq('external_user_id', user.id)
        .maybeSingle();

    if (byExternalUserIdError) {
        console.warn('Failed to find client_id by external_user_id:', byExternalUserIdError);
    }

    if (byExternalUserId?.client_id) {
        return byExternalUserId.client_id;
    }

    if (!user.email) {
        return null;
    }

    const { data: cliente, error: clienteError } = await supabase
        .from('clientes_vizu')
        .select('client_id')
        .ilike('email', user.email)
        .maybeSingle();

    if (clienteError) {
        console.warn('Failed to find client_id in clientes_vizu by email:', clienteError);
        return null;
    }

    return cliente?.client_id ?? null;
}

/**
 * Resolve client_id from various sources, caching in localStorage.
 */
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
        throw new Error('client_id is required; could not resolve from context, localStorage, or Supabase');
    }

    return resolvedClientId;
}

// Funções da API

/**
 * Testa a conexão com uma plataforma usando as credenciais fornecidas.
 * Para BigQuery, valida a conexão via RPC.
 * Para outras plataformas, retorna sucesso (validação acontece no sync).
 */
export async function testConnection(
    platform: ConnectorPlatform,
    payload: unknown
): Promise<TestConnectionResponse> {
    if (platform === 'bigquery') {
        // BigQuery: The RPC validate_bigquery_connection requires an existing server
        // For testing before creation, we just validate the payload structure
        const bqPayload = payload as BigQueryCredentials;

        if (!bqPayload.project_id || !bqPayload.service_account_json) {
            return {
                success: false,
                message: 'project_id e service_account_json são obrigatórios',
                platform: 'bigquery',
            };
        }

        // Validate service_account_json has required fields
        const saJson = bqPayload.service_account_json;
        if (!saJson.type || !saJson.project_id || !saJson.private_key) {
            return {
                success: false,
                message: 'service_account_json inválido. Verifique os campos type, project_id e private_key.',
                platform: 'bigquery',
            };
        }

        return {
            success: true,
            message: 'Credenciais BigQuery válidas. A conexão será testada ao criar o servidor.',
            platform: 'bigquery',
        };
    }

    // For e-commerce platforms, basic validation only
    // Full validation happens during sync
    return {
        success: true,
        message: `Formato de credenciais válido para ${platform}`,
        platform,
    };
}

/**
 * Calls the match-columns Edge Function and persists the mapping to client_data_sources.
 * This is a standalone function (not a React hook) for use in the service layer.
 *
 * Flow: source columns → Edge Function (fuzzy match) → column_mapping saved to DB
 * The sync function (sincronizar_dados_cliente) reads column_mapping to route BQ columns to canonical targets.
 */
async function matchAndSaveColumnMapping(
    dataSourceId: string,
    sourceColumns: Array<{ name: string }>,
    schemaType: string = 'invoices'
): Promise<Record<string, string>> {
    const columnNames = sourceColumns.map(c => c.name);
    console.log('[matchAndSaveColumnMapping] Matching', columnNames.length, 'columns for schema:', schemaType);

    // Use supabase.functions.invoke — handles Authorization + apikey headers automatically
    const { data: matchResult, error: fnError } = await supabase.functions.invoke('match-columns', {
        body: {
            source_columns: columnNames,
            schema_type: schemaType,
        },
    });

    if (fnError) {
        console.warn('[matchAndSaveColumnMapping] Edge function error:', fnError);
        throw new Error(fnError.message || 'match-columns edge function failed');
    }

    const columnMapping: Record<string, string> = matchResult?.matched || {};

    console.log('[matchAndSaveColumnMapping] Matched', Object.keys(columnMapping).length, 'of', columnNames.length, 'columns');

    // Persist column_mapping to client_data_sources
    const { error: updateError } = await supabase
        .from('client_data_sources')
        .update({
            column_mapping: columnMapping,
            sync_status: 'mapping_complete',
            atualizado_em: new Date().toISOString(),
        })
        .eq('id', dataSourceId);

    if (updateError) {
        console.warn('[matchAndSaveColumnMapping] Failed to save mapping:', updateError);
        throw new Error(updateError.message || 'Failed to save column mapping');
    }

    console.log('[matchAndSaveColumnMapping] Mapping saved to client_data_sources:', dataSourceId);
    return columnMapping;
}

/**
 * Cria uma nova credencial de conexão BigQuery via Supabase RPC.
 * Para BigQuery: cria server FDW via create_bigquery_server RPC.
 * Credenciais são armazenadas no Supabase Vault.
 */
export async function createCredential(
    request: CreateCredentialRequest
): Promise<CredentialResponse> {
    const resolvedClientId = await resolveClientId(request.client_id);
    const tipoServicoUpper = (request.tipo_servico || '').toUpperCase();

    if (tipoServicoUpper === 'BIGQUERY') {
        const bqCreds = request.credentials as BigQueryCredentials;

        // Create BigQuery server via RPC (handles Vault storage + FDW creation)
        const { data: serverResult, error: serverError } = await supabase.rpc('create_bigquery_server', {
            p_client_id: resolvedClientId,
            p_service_account_key: bqCreds.service_account_json,
            p_project_id: bqCreds.project_id,
            p_dataset_id: bqCreds.dataset_id || 'default',
            p_location: bqCreds.location || 'US',
        });

        if (serverError) {
            throw new Error(serverError.message || 'Falha ao criar servidor BigQuery');
        }

        const result = serverResult as { server_name?: string; vault_key_id?: string; success?: boolean; error?: string };

        if (!result.success) {
            throw new Error(result.error || 'Falha ao criar servidor BigQuery');
        }

        // Also insert into credencial_servico_externo for tracking
        const { data: credencial, error: credError } = await supabase
            .from('credencial_servico_externo')
            .insert({
                client_id: resolvedClientId,
                nome_servico: request.nome_servico,
                tipo_servico: 'BIGQUERY',
                status: 'active',
                vault_key_id: result.vault_key_id,
                connection_metadata: {
                    project_id: bqCreds.project_id,
                    dataset_id: bqCreds.dataset_id,
                    table_name: bqCreds.table_name,
                    location: bqCreds.location || 'US',
                },
            })
            .select('id, vault_key_id, nome_servico, tipo_servico, status')
            .single();

        if (credError) {
            // Rollback: drop the server we just created
            await supabase.rpc('drop_bigquery_server', { p_client_id: resolvedClientId });
            throw new Error(credError.message || 'Falha ao registrar credencial');
        }

        // Create foreign table with two-step FDW discovery (discovers columns from BigQuery INFORMATION_SCHEMA)
        const { data: foreignTableResult, error: ftError } = await supabase.rpc('create_bigquery_foreign_table', {
            p_client_id: resolvedClientId,
            p_table_name: bqCreds.table_name || 'default_table',
            p_bigquery_table: bqCreds.table_name || 'default_table',
            p_location: bqCreds.location || 'US',
            p_timeout_ms: 300000,
            p_credential_id: parseInt(String(credencial.id), 10),
        });

        if (ftError) {
            console.warn('Warning: Foreign table creation RPC error:', ftError);
        } else {
            const ftResult = foreignTableResult as {
                success?: boolean;
                error?: string;
                columns?: Array<{ name: string }>;
                data_source_id?: string;
            };

            if (ftResult.success) {
                console.log('Foreign table created successfully:', ftResult.data_source_id);

                // ─── AUTO COLUMN MATCHING ───
                // Call match-columns edge function to map BigQuery columns → canonical schema
                // Then save the mapping to client_data_sources.column_mapping
                if (ftResult.columns && ftResult.data_source_id) {
                    try {
                        const mapping = await matchAndSaveColumnMapping(
                            ftResult.data_source_id,
                            ftResult.columns,
                            'invoices' // default schema type
                        );
                        console.log('Column mapping saved:', Object.keys(mapping).length, 'mappings');
                    } catch (matchErr) {
                        // Non-fatal: user can still map manually via AdminConnectorMappingPage
                        console.warn('Auto column matching failed (manual mapping still available):', matchErr);
                    }
                }
            } else {
                // Function returned {success: false} — log the actual error from the DB function
                console.warn('Warning: Foreign table creation returned failure:', ftResult.error);
                // trigger_column_discovery will retry the FDW creation
            }
        }

        return {
            id: String(credencial.id),
            secret_manager_id: credencial.vault_key_id || '',
            nome_servico: credencial.nome_servico,
            tipo_servico: credencial.tipo_servico,
            status: credencial.status,
        };
    }

    // For non-BigQuery platforms, insert into credencial_servico_externo
    // E-commerce integrations would need additional setup
    const { data: credencial, error: credError } = await supabase
        .from('credencial_servico_externo')
        .insert({
            client_id: resolvedClientId,
            nome_servico: request.nome_servico,
            tipo_servico: tipoServicoUpper,
            status: 'pending',
            connection_metadata: {
                credentials: request.credentials,
            },
        })
        .select('id, vault_key_id, nome_servico, tipo_servico, status')
        .single();

    if (credError) {
        throw new Error(credError.message || 'Falha ao criar credencial');
    }

    return {
        id: String(credencial.id),
        secret_manager_id: credencial.vault_key_id || '',
        nome_servico: credencial.nome_servico,
        tipo_servico: credencial.tipo_servico,
        status: credencial.status,
    };
}

/**
 * Lista todas as credenciais/conexões configuradas para um cliente.
 */
export async function listConnections(clienteVizuId: string): Promise<ConnectorStatus[]> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    const { data: credenciais, error } = await supabase
        .from('credencial_servico_externo')
        .select(`
      id,
      nome_servico,
      tipo_servico,
      status,
      created_at,
      updated_at
    `)
        .eq('client_id', resolvedClientId)
        .order('created_at', { ascending: false });

    if (error) {
        throw new Error(error.message || 'Falha ao listar conexões');
    }

    // Get latest sync info for each credential
    const credentialIds = (credenciais || []).map(c => c.id);

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

    return (credenciais || []).map(c => {
        const latestSync = latestSyncMap.get(c.id);
        let connectorStatus: ConnectorStatus['status'] = 'pending';

        if (c.status === 'active') {
            connectorStatus = latestSync?.status === 'running' ? 'syncing' : 'connected';
        } else if (c.status === 'error' || latestSync?.status === 'failed') {
            connectorStatus = 'error';
        }

        return {
            id: String(c.id),
            platform: c.tipo_servico?.toLowerCase() as ConnectorPlatform,
            nome_servico: c.nome_servico,
            status: connectorStatus,
            last_sync: latestSync?.sync_completed_at || undefined,
            records_count: latestSync?.records_processed || undefined,
            error_message: latestSync?.error_message || undefined,
        };
    });
}

/**
 * Extrai dados de uma conexão configurada.
 * Note: This function is deprecated. Use startSync instead for data ingestion.
 * @deprecated Use startSync instead
 */
export async function extractData(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _request: ExtractDataRequest
): Promise<ExtractDataResponse> {
    console.warn('extractData is deprecated. Use startSync for data ingestion.');
    return {
        success: false,
        resource: '',
        total_records: 0,
        page: 0,
        has_more: false,
        data: [],
    };
}

/**
 * Extração direta (sem credencial salva) - deprecado.
 * @deprecated Use startSync instead
 */
export async function extractDataDirect(
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _platform: ConnectorPlatform,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _credentials: CredentialPayload,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _resource: string
): Promise<ExtractDataResponse> {
    console.warn('extractDataDirect is deprecated. Use startSync for data ingestion.');
    return {
        success: false,
        resource: '',
        total_records: 0,
        page: 0,
        has_more: false,
        data: [],
    };
}

/**
 * Inicia a sincronização de dados para uma conexão via run-sync edge function.
 * Retorna imediatamente com o job_id para polling assíncrono.
 */
export async function startSync(
    credentialId: string,
    clienteVizuId: string,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _resourceType: string = 'invoices'
): Promise<{ status: string; message: string; job_id?: string }> {
    const resolvedClientId = await resolveClientId(clienteVizuId);

    const { data, error } = await supabase.functions.invoke('run-sync', {
        body: {
            client_id: resolvedClientId,
            credential_id: parseInt(credentialId, 10),
            force_full_sync: false,
        },
    });

    if (error) {
        throw new Error(error.message || 'Falha ao iniciar sincronização');
    }

    if (!data?.job_id) {
        throw new Error('Falha ao criar job de sincronização');
    }

    return {
        status: 'running',
        message: 'Sincronização iniciada. Acompanhe o progresso pelo job_id.',
        job_id: data.job_id,
    };
}

/**
 * Obtém o status de uma sincronização via analytics_v2.reg_jobs.
 */
export async function getSyncStatus(jobId: string): Promise<{
    job_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress?: number;
    records_processed?: number;
    error_message?: string;
    result?: Record<string, unknown>;
}> {
    const { data: job, error } = await supabase
        .schema('analytics_v2')
        .from('reg_jobs')
        .select('job_id, status, progress_pct, result, error_message')
        .eq('job_id', jobId)
        .single();

    if (error) {
        throw new Error(error.message || 'Falha ao obter status');
    }

    const result = job.result as Record<string, unknown> | null;

    return {
        job_id: job.job_id,
        status: job.status as 'pending' | 'running' | 'completed' | 'failed',
        progress: job.progress_pct || 0,
        records_processed: result?.rows_inserted as number | undefined,
        error_message: job.error_message || undefined,
        result: result || undefined,
    };
}

/**
 * Deleta uma conexão configurada.
 * Para BigQuery: também remove o servidor FDW via drop_bigquery_server.
 */
export async function deleteConnection(credentialId: string): Promise<void> {
    // Get credential info first
    const { data: credencial, error: fetchError } = await supabase
        .from('credencial_servico_externo')
        .select('client_id, tipo_servico')
        .eq('id', parseInt(credentialId, 10))
        .single();

    if (fetchError) {
        throw new Error(fetchError.message || 'Credencial não encontrada');
    }

    // If it's BigQuery, drop the FDW server
    if (credencial.tipo_servico?.toUpperCase() === 'BIGQUERY') {
        const { data: dropResult, error: dropError } = await supabase.rpc('drop_bigquery_server', {
            p_client_id: credencial.client_id,
        });

        if (dropError) {
            console.warn('Failed to drop BigQuery server:', dropError);
            // Continue to delete credential anyway
        } else {
            const result = dropResult as { success?: boolean; error?: string };
            if (!result.success) {
                console.warn('drop_bigquery_server returned error:', result.error);
            }
        }
    }

    // Delete the credential record
    const { error: deleteError } = await supabase
        .from('credencial_servico_externo')
        .delete()
        .eq('id', parseInt(credentialId, 10));

    if (deleteError) {
        throw new Error(deleteError.message || 'Falha ao deletar conexão');
    }
}

/**
 * Lista plataformas disponíveis e seus recursos.
 * Agora retorna dados estáticos (não depende de API externa).
 */
export async function getPlatformInfo(): Promise<{
    platforms: {
        id: ConnectorPlatform;
        name: string;
        resources: string[];
    }[];
}> {
    return {
        platforms: [
            { id: 'shopify', name: 'Shopify', resources: ['products', 'orders', 'customers', 'inventory'] },
            { id: 'vtex', name: 'VTEX', resources: ['products', 'orders', 'customers', 'inventory', 'categories'] },
            { id: 'loja_integrada', name: 'Loja Integrada', resources: ['products', 'orders', 'customers', 'inventory'] },
            { id: 'bigquery', name: 'BigQuery', resources: ['tables', 'views'] },
            { id: 'postgresql', name: 'PostgreSQL', resources: ['tables', 'views'] },
            { id: 'mysql', name: 'MySQL', resources: ['tables', 'views'] },
        ],
    };
}
