/**
 * Service para gerenciamento de conectores de dados.
 * Comunica com a Data Ingestion API para configurar e sincronizar fontes de dados.
 */

import { supabase } from "../lib/supabase";

const API_BASE_URL = import.meta.env.VITE_DATA_INGESTION_API_URL || 'http://localhost:8000';

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
  nome_conexao: string;
  tipo_servico: string;
  credentials: CredentialPayload;
}

export interface CredentialResponse {
  id_credencial: string;
  secret_manager_id: string;
  nome_conexao: string;
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
  nome_conexao: string;
  status: 'connected' | 'pending' | 'error' | 'syncing';
  last_sync?: string;
  records_count?: number;
  error_message?: string;
}

// Resolve the current user's JWT from Supabase for authenticated ingestion calls.
async function getAuthToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token ?? null;
}

async function buildAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
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

  // Check if client_id is in app_metadata
  const clientId = user.app_metadata?.client_id;
  if (clientId) {
    return clientId;
  }

  // Fallback: look up in clientes_vizu table by user email
  const { data: cliente, error: clienteError } = await supabase
    .from('clientes_vizu')
    .select('client_id')
    .eq('email_admin', user.email)
    .single();

  if (clienteError || !cliente) {
    console.warn('Failed to find client_id in clientes_vizu:', clienteError);
    return null;
  }

  return cliente.client_id;
}

// Funções da API

/**
 * Testa a conexão com uma plataforma usando as credenciais fornecidas.
 * Não salva as credenciais, apenas valida.
 */
export async function testConnection(
  platform: ConnectorPlatform,
  payload: unknown
): Promise<TestConnectionResponse> {
  const isEcommerce = ['shopify', 'vtex', 'loja_integrada'].includes(platform);
  const endpoint = isEcommerce
    ? `${API_BASE_URL}/ecommerce/test-connection`
    : `${API_BASE_URL}/credentials/test-connection`;

  let body;
  if (platform === 'bigquery') {
    body = JSON.stringify(payload);
  } else {
    body = typeof payload === 'object' && payload !== null
      ? JSON.stringify({
        platform,
        tipo_servico: platform.toUpperCase(),
        credentials: payload,
        ...payload,
      })
      : JSON.stringify({
        platform,
        tipo_servico: platform.toUpperCase(),
        credentials: payload,
      });
  }

  const apiResponse = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
    body,
  });

  if (!apiResponse.ok) {
    const error = await apiResponse.json();
    // Handle FastAPI validation errors (422) and structured error details
    if (error?.detail) {
      if (Array.isArray(error.detail)) {
        const errorMessages = error.detail.map((err: any) => `${err.loc?.join('.') || 'field'}: ${err.msg}`).join('; ');
        throw new Error(errorMessages);
      }
      if (typeof error.detail === 'object') {
        throw new Error(JSON.stringify(error.detail));
      }
      throw new Error(error.detail);
    }
    throw new Error('Falha no teste de conexão');
  }

  return apiResponse.json();
}

/**
 * Cria uma nova credencial de conexão.
 * As credenciais são salvas de forma segura no Secret Manager.
 */
export async function createCredential(
  request: CreateCredentialRequest
): Promise<CredentialResponse> {
  // Use provided client_id, fallback to localStorage, then fetch from Supabase
  let resolvedClientId = request.client_id || localStorage.getItem('vizu_client_id') || '';

  if (!resolvedClientId) {
    // Last resort: resolve from Supabase auth
    const clientIdFromSupabase = await resolveClientIdFromSupabase();
    if (clientIdFromSupabase) {
      resolvedClientId = clientIdFromSupabase;
      localStorage.setItem('vizu_client_id', resolvedClientId);
    }
  }

  if (!resolvedClientId) {
    throw new Error('client_id is required; could not resolve from context, localStorage, or Supabase');
  }

  const tipoServicoUpper = (request.tipo_servico || '').toUpperCase();

  // Determina o endpoint baseado no tipo de serviço
  const isEcommerce = ['SHOPIFY', 'VTEX', 'LOJA_INTEGRADA'].includes(tipoServicoUpper);
  const endpoint = isEcommerce
    ? `${API_BASE_URL}/ecommerce/credentials`
    : `${API_BASE_URL}/credentials/create`;

  // Flatten the payload: backend expects credentials fields at root level, not nested
  // IMPORTANT: Use 'client_id' (not 'client_id') to match schema
  const payload = {
    client_id: resolvedClientId,
    nome_conexao: request.nome_conexao,
    tipo_servico: tipoServicoUpper,
    ...request.credentials, // Spread credentials fields to root level
  };

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json();
    // Handle FastAPI validation errors (422) which return an array of error objects
    if (error.detail && Array.isArray(error.detail)) {
      const errorMessages = error.detail.map((err: any) =>
        `${err.loc?.join('.') || 'field'}: ${err.msg}`
      ).join('; ');
      throw new Error(errorMessages);
    }
    throw new Error(error.detail || 'Falha ao criar credencial');
  }

  return response.json();
}

/**
 * Lista todas as credenciais/conexões configuradas para um cliente.
 */
export async function listConnections(clienteVizuId: string): Promise<ConnectorStatus[]> {
  const response = await fetch(
    `${API_BASE_URL}/credentials?client_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...(await buildAuthHeaders()),
      },
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha ao listar conexões');
  }

  return response.json();
}

/**
 * Extrai dados de uma conexão configurada.
 */
export async function extractData(
  request: ExtractDataRequest
): Promise<ExtractDataResponse> {
  const response = await fetch(`${API_BASE_URL}/ecommerce/extract`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha na extração de dados');
  }

  return response.json();
}

/**
 * Extração direta (sem credencial salva) - útil para testes.
 */
export async function extractDataDirect(
  platform: ConnectorPlatform,
  credentials: CredentialPayload,
  resource: string
): Promise<ExtractDataResponse> {
  const response = await fetch(`${API_BASE_URL}/ecommerce/extract-direct/${platform}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
    body: JSON.stringify({
      credentials,
      resource,
      limit: 10, // Preview com poucos registros
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha na extração de dados');
  }

  return response.json();
}

/**
 * Inicia a sincronização de dados para uma conexão.
 * Isso dispara o ETL job (Extract, Transform, Load).
 */
export async function startSync(
  credentialId: string,
  clienteVizuId: string,
  resourceType: string = 'invoices'
): Promise<{ status: string; message: string; rows_processed?: number }> {
  // Use provided client_id, fallback to localStorage, then fetch from Supabase
  let resolvedClientId = clienteVizuId || localStorage.getItem('vizu_client_id') || '';

  if (!resolvedClientId) {
    // Last resort: resolve from Supabase auth
    const clientIdFromSupabase = await resolveClientIdFromSupabase();
    if (clientIdFromSupabase) {
      resolvedClientId = clientIdFromSupabase;
      localStorage.setItem('vizu_client_id', resolvedClientId);
    }
  }

  if (!resolvedClientId) {
    throw new Error('client_id is required; could not resolve from context, localStorage, or Supabase');
  }

  const response = await fetch(`${API_BASE_URL}/etl/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
    body: JSON.stringify({
      credential_id: credentialId,
      client_id: resolvedClientId,
      resource_type: resourceType,
      limit: null, // No limit - process all data
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha ao iniciar sincronização');
  }

  return response.json();
}

/**
 * Obtém o status de uma sincronização em andamento.
 */
export async function getSyncStatus(jobId: string): Promise<{
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  records_processed?: number;
  error_message?: string;
}> {
  const response = await fetch(`${API_BASE_URL}/ingestion/status/${jobId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha ao obter status');
  }

  return response.json();
}

/**
 * Deleta uma conexão configurada.
 */
export async function deleteConnection(credentialId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/credentials/${credentialId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha ao deletar conexão');
  }
}

/**
 * Lista plataformas disponíveis e seus recursos.
 */
export async function getPlatformInfo(): Promise<{
  platforms: {
    id: ConnectorPlatform;
    name: string;
    resources: string[];
  }[];
}> {
  const response = await fetch(`${API_BASE_URL}/ecommerce/platforms`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(await buildAuthHeaders()),
    },
  });

  if (!response.ok) {
    // Fallback para dados estáticos se API não estiver disponível
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

  return response.json();
}
