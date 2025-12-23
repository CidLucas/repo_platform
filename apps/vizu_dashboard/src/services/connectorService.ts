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
  cliente_vizu_id: string;
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
    headers: { 'Content-Type': 'application/json' },
    body,
  });

  if (!apiResponse.ok) {
    const error = await apiResponse.json();
    throw new Error(error.detail || 'Falha no teste de conexão');
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
  // Determina o endpoint baseado no tipo de serviço
  const isEcommerce = ['SHOPIFY', 'VTEX', 'LOJA_INTEGRADA'].includes(request.tipo_servico);
  const endpoint = isEcommerce 
    ? `${API_BASE_URL}/ecommerce/credentials`
    : `${API_BASE_URL}/credentials/create`;

  // Busca o token do usuário autenticado no Supabase
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Falha ao criar credencial');
  }

  return response.json();
}

/**
 * Lista todas as credenciais/conexões configuradas para um cliente.
 */
export async function listConnections(clienteVizuId: string): Promise<ConnectorStatus[]> {
  const response = await fetch(
    `${API_BASE_URL}/credentials?cliente_vizu_id=${clienteVizuId}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
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
 * Isso dispara o worker de ingestão.
 */
export async function startSync(
  credentialId: string, 
  connectorType: string = 'BIGQUERY',
  resources?: string[]
): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/ingestion/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      client_id: credentialId,
      connector_type: connectorType.toUpperCase(),
      target_resource: 'all',
      resources: resources, // Para e-commerce
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
