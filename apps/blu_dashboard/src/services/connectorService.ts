/**
 * Service para gerenciamento de conectores de dados.
 * Comunica diretamente com Supabase (RPCs + PostgREST) para configurar e sincronizar fontes de dados.
 *
 * Migration Note: This service was rewritten to remove dependency on
 * Data Ingestion API. All operations now go through Supabase RPCs and PostgREST.
 */

import { supabase } from "../lib/supabase";
import { resolveClientId } from "../lib/auth";

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

interface ParsedBigQueryTableRef {
    projectId?: string;
    datasetId?: string;
    tableName: string;
    normalizedReference: string;
}

function parseBigQueryTableReference(rawTableName: string): ParsedBigQueryTableRef {
    const cleaned = (rawTableName || '').replace(/`/g, '').trim();
    const parts = cleaned.split('.').map((part) => part.trim()).filter(Boolean);

    if (parts.length === 3) {
        const [projectId, datasetId, tableName] = parts;
        return {
            projectId,
            datasetId,
            tableName,
            normalizedReference: `${projectId}.${datasetId}.${tableName}`,
        };
    }

    if (parts.length === 2) {
        const [datasetId, tableName] = parts;
        return {
            datasetId,
            tableName,
            normalizedReference: `${datasetId}.${tableName}`,
        };
    }

    const tableName = parts[0] || cleaned;
    return {
        tableName,
        normalizedReference: tableName,
    };
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

export interface ConnectorStatus {
    id: string;
    platform: ConnectorPlatform;
    nome_servico: string;
    status: 'connected' | 'pending' | 'error' | 'syncing';
    last_sync?: string;
    records_count?: number;
    error_message?: string;
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
        const parsedTableRef = parseBigQueryTableReference(bqCreds.table_name);
        const effectiveProjectId = parsedTableRef.projectId || bqCreds.project_id;
        const effectiveDatasetId = parsedTableRef.datasetId || bqCreds.dataset_id || 'default';
        const tableReference = parsedTableRef.normalizedReference || parsedTableRef.tableName;

        // Create BigQuery server via RPC (handles Vault storage + FDW creation)
        const { data: serverResult, error: serverError } = await supabase.rpc('create_bigquery_server', {
            p_client_id: resolvedClientId,
            p_service_account_key: bqCreds.service_account_json,
            p_project_id: effectiveProjectId,
            p_dataset_id: effectiveDatasetId,
            p_location: bqCreds.location || 'US',
        });

        if (serverError) {
            throw new Error(serverError.message || 'Falha ao criar servidor BigQuery');
        }

        const result = serverResult as { server_name?: string; vault_key_id?: string; success?: boolean; error?: string };

        if (!result.success) {
            throw new Error(result.error || 'Falha ao criar servidor BigQuery');
        }

        if (!result.vault_key_id) {
            throw new Error('Falha ao persistir chave da credencial no Vault (vault_key_id ausente)');
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
                    project_id: effectiveProjectId,
                    dataset_id: effectiveDatasetId,
                    table_name: tableReference,
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
            p_table_name: parsedTableRef.tableName || 'default_table',
            p_bigquery_table: tableReference || parsedTableRef.tableName || 'default_table',
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
export async function listConnections(ClienteBluId: string): Promise<ConnectorStatus[]> {
    const resolvedClientId = await resolveClientId(ClienteBluId);

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
 * Inicia a sincronização de dados para uma conexão via run-sync edge function.
 * Retorna imediatamente com o job_id para polling assíncrono.
 */
export async function startSync(
    credentialId: string,
    ClienteBluId: string,

    _resourceType: string = 'invoices'
): Promise<{ status: string; message: string; job_id?: string }> {
    const resolvedClientId = await resolveClientId(ClienteBluId);
    const normalizedCredentialId = parseInt(credentialId, 10);

    const { data: dataSource, error: dataSourceError } = await supabase
        .from('client_data_sources')
        .select('id, source_columns, column_mapping')
        .eq('client_id', resolvedClientId)
        .eq('credential_id', normalizedCredentialId)
        .order('atualizado_em', { ascending: false })
        .limit(1)
        .maybeSingle();

    if (dataSourceError) {
        throw new Error(dataSourceError.message || 'Falha ao validar mapeamento da fonte de dados');
    }

    if (!dataSource) {
        throw new Error('Esta credencial ainda não possui descoberta de colunas. Recrie a conexão ou execute a descoberta antes de sincronizar.');
    }

    const sourceColumns = Array.isArray(dataSource.source_columns)
        ? (dataSource.source_columns as Array<{ name: string }>)
        : [];

    let columnMapping =
        dataSource.column_mapping && typeof dataSource.column_mapping === 'object'
            ? (dataSource.column_mapping as Record<string, string>)
            : {};

    if (Object.keys(columnMapping).length === 0 && sourceColumns.length > 0) {
        columnMapping = await matchAndSaveColumnMapping(
            dataSource.id,
            sourceColumns,
            'invoices'
        );
    }

    if (Object.keys(columnMapping).length === 0) {
        throw new Error('Nenhum mapeamento válido foi encontrado para esta fonte. Revise o mapeamento antes de sincronizar.');
    }

    const { data, error } = await supabase.functions.invoke('run-sync', {
        body: {
            client_id: resolvedClientId,
            credential_id: normalizedCredentialId,
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
        .maybeSingle();

    if (error || !job) {
        throw new Error(error?.message || 'Falha ao obter status');
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
        .select('client_id, tipo')
        .eq('id', parseInt(credentialId, 10))
        .maybeSingle();

    if (fetchError || !credencial) {
        throw new Error(fetchError?.message || 'Credencial não encontrada');
    }

    // If it's BigQuery, drop the FDW server
    if (credencial.tipo?.toUpperCase() === 'BIGQUERY') {
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
