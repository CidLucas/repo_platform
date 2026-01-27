/**
 * Service for admin operations - requires ADMIN tier.
 * Communicates with Tool Pool API admin endpoints.
 */

import { supabase } from "../lib/supabase";

const TOOL_POOL_API_URL = import.meta.env.VITE_TOOL_POOL_API_URL || 'http://localhost:8000';

// Types
export interface ClienteVizu {
  id: string;
  nome_empresa: string;
  tipo_cliente: string | null;
  tier: string | null;
  horario_funcionamento: Record<string, unknown> | null;
  prompt_base: string | null;
  enabled_tools: string[] | null;
  collection_rag: string | null;
  external_user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ClienteVizuCreate {
  nome_empresa: string;
  tipo_cliente?: string;
  tier?: string;
  horario_funcionamento?: Record<string, unknown>;
  prompt_base?: string;
  enabled_tools?: string[];
  collection_rag?: string;
  external_user_id?: string;
}

export interface ClienteVizuUpdate {
  nome_empresa?: string;
  tipo_cliente?: string;
  tier?: string;
  horario_funcionamento?: Record<string, unknown>;
  prompt_base?: string;
  enabled_tools?: string[];
  collection_rag?: string;
  external_user_id?: string;
}

export interface ClientListResponse {
  clients: ClienteVizu[];
  total: number;
  limit: number;
  offset: number;
}

export interface ToolMetadata {
  name: string;
  description: string;
  category: string;
  tier_required: string;
  requires_confirmation: boolean;
  tags: string[];
  enabled?: boolean;
}

export interface AvailableToolsResponse {
  tier: string;
  tools: ToolMetadata[];
}

export interface ToolValidationResult {
  is_valid: boolean;
  errors: string[];
}

// Tiers disponíveis
export const TIERS = ['FREE', 'BASIC', 'SME', 'PREMIUM', 'ENTERPRISE', 'ADMIN'] as const;
export type TierType = typeof TIERS[number];

// Resolve JWT token from Supabase
async function getAuthToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token ?? null;
}

async function buildAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Authentication required. Please log in.');
  }
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// Error handler
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));

    // Handle structured error responses
    if (error.detail) {
      if (typeof error.detail === 'object' && error.detail.message) {
        throw new Error(`${error.detail.message}: ${error.detail.errors?.join(', ') || ''}`);
      }
      throw new Error(typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail));
    }
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

// ============================================================================
// CLIENT MANAGEMENT
// ============================================================================

/**
 * List all clients (paginated)
 */
export async function listClients(
  limit: number = 100,
  offset: number = 0
): Promise<ClientListResponse> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients?limit=${limit}&offset=${offset}`,
    {
      method: 'GET',
      headers: await buildAuthHeaders(),
    }
  );
  return handleResponse<ClientListResponse>(response);
}

/**
 * Get a single client by ID
 */
export async function getClient(clientId: string): Promise<ClienteVizu> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/${clientId}`,
    {
      method: 'GET',
      headers: await buildAuthHeaders(),
    }
  );
  return handleResponse<ClienteVizu>(response);
}

/**
 * Create a new client
 */
export async function createClient(data: ClienteVizuCreate): Promise<ClienteVizu> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients`,
    {
      method: 'POST',
      headers: await buildAuthHeaders(),
      body: JSON.stringify(data),
    }
  );
  return handleResponse<ClienteVizu>(response);
}

/**
 * Update a client
 */
export async function updateClient(
  clientId: string,
  data: ClienteVizuUpdate
): Promise<ClienteVizu> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/${clientId}`,
    {
      method: 'PATCH',
      headers: await buildAuthHeaders(),
      body: JSON.stringify(data),
    }
  );
  return handleResponse<ClienteVizu>(response);
}

/**
 * Delete a client
 */
export async function deleteClient(clientId: string): Promise<void> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/${clientId}`,
    {
      method: 'DELETE',
      headers: await buildAuthHeaders(),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Failed to delete client');
  }
}

// ============================================================================
// TOOL MANAGEMENT
// ============================================================================

/**
 * Get all registered tools
 */
export async function getAllTools(): Promise<{ total: number; tools: ToolMetadata[] }> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/all-tools`,
    {
      method: 'GET',
      headers: await buildAuthHeaders(),
    }
  );
  return handleResponse<{ total: number; tools: ToolMetadata[] }>(response);
}

/**
 * Get tools available for a specific tier
 */
export async function getToolsForTier(tier: string): Promise<AvailableToolsResponse> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/available-tools/${tier}`,
    {
      method: 'GET',
      headers: await buildAuthHeaders(),
    }
  );
  return handleResponse<AvailableToolsResponse>(response);
}

/**
 * Validate tools for a tier
 */
export async function validateTools(
  enabledTools: string[],
  tier: string
): Promise<ToolValidationResult> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/validate-tools?tier=${tier}`,
    {
      method: 'POST',
      headers: await buildAuthHeaders(),
      body: JSON.stringify(enabledTools),
    }
  );
  return handleResponse<ToolValidationResult>(response);
}

// ============================================================================
// USER TIER CHECK
// ============================================================================

/**
 * Check if current user has admin tier
 * Returns the user's tier or throws if not authenticated
 */
export async function getCurrentUserTier(): Promise<string> {
  const token = await getAuthToken();
  if (!token) {
    throw new Error('Not authenticated');
  }

  // We can check by trying to access an admin endpoint
  // If it returns 403, user is not admin
  try {
    const response = await fetch(
      `${TOOL_POOL_API_URL}/admin/clients?limit=1`,
      {
        method: 'GET',
        headers: await buildAuthHeaders(),
      }
    );

    if (response.status === 403) {
      const error = await response.json();
      // Extract tier from error message like "Admin access required. Your tier: BASIC"
      const match = error.detail?.match(/Your tier: (\w+)/);
      return match ? match[1] : 'BASIC';
    }

    if (response.ok) {
      return 'ADMIN';
    }

    throw new Error('Failed to check user tier');
  } catch (error) {
    if (error instanceof Error && error.message.includes('Your tier:')) {
      const match = error.message.match(/Your tier: (\w+)/);
      return match ? match[1] : 'BASIC';
    }
    throw error;
  }
}

/**
 * Check if current user is admin
 */
export async function isCurrentUserAdmin(): Promise<boolean> {
  try {
    const tier = await getCurrentUserTier();
    return tier === 'ADMIN';
  } catch {
    return false;
  }
}
