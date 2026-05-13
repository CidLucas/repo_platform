/**
 * Service for Agent Builder admin operations.
 * Ported from apps/blu_app/src/services/agentBuilderService.ts
 */

const AGENT_API_URL = import.meta.env.VITE_STANDALONE_AGENT_API || 'http://localhost:8001'
const TOOL_POOL_API_URL = import.meta.env.VITE_TOOL_POOL_API_URL || 'http://localhost:8006'

// ── Types ──────────────────────────────────────────────────────

export interface AgentConfigData {
  name: string
  role: string
  elicitation_strategy?: string
  enabled_tools: string[]
  max_turns: number
  model?: string
  metadata?: Record<string, unknown>
}

export interface ContextFieldDefinition {
  field: string
  type: string
  required: boolean
  label: string
  prompt_hint?: string
}

export interface FileRequirements {
  csv?: { min: number; max: number; description: string }
  document?: { min: number; max: number; description: string }
}

export interface WorkflowNodeDef {
  id: string
  type: string
  position: { x: number; y: number }
  label?: string
}

export interface WorkflowEdgeDef {
  source: string
  target: string
  label?: string
  condition?: string
  animated?: boolean
}

export interface WorkflowGraph {
  nodes: WorkflowNodeDef[]
  edges: WorkflowEdgeDef[]
}

export interface CatalogNodeMetadata {
  name: string
  description: string
  category: string
  inputs: string[]
  outputs: string[]
}

export interface CatalogAgent {
  id: string
  name: string
  slug: string
  description: string | null
  category: string | null
  icon: string | null
  agent_config: AgentConfigData
  prompt_name: string
  required_context: ContextFieldDefinition[]
  required_files: FileRequirements
  requires_google: boolean
  tier_required: string
  is_active: boolean
  workflow_graph: WorkflowGraph | null
  created_at: string | null
  updated_at: string | null
}

export interface CatalogAgentCreate {
  name: string
  description?: string | null
  category?: string | null
  icon?: string | null
  agent_config: AgentConfigData
  prompt_name: string
  required_context?: ContextFieldDefinition[]
  required_files?: FileRequirements
  requires_google?: boolean
  tier_required?: string
  is_active?: boolean
  workflow_graph?: WorkflowGraph | null
}

export interface CatalogAgentUpdate {
  name?: string
  description?: string | null
  category?: string | null
  icon?: string | null
  agent_config?: AgentConfigData
  prompt_name?: string
  required_context?: ContextFieldDefinition[]
  required_files?: FileRequirements
  requires_google?: boolean
  tier_required?: string
  is_active?: boolean
  workflow_graph?: WorkflowGraph | null
}

export interface ToolMetadata {
  name: string
  description: string
  category: string
  tier_required: string
  requires_confirmation: boolean
  tags: string[]
  enabled?: boolean
}

export interface AvailableToolsResponse {
  tier: string
  tools: ToolMetadata[]
}

export interface ValidateToolsResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface PromptInfo {
  name: string
  source: string
  category: string | null
  description: string | null
}

export interface PromptDetail {
  name: string
  content: string
  version: number
  variables: string[]
  source: string
}

export interface PromptVersionInfo {
  version: number
  created_at: string | null
  labels: string[]
}

export interface PromptVersionsResponse {
  name: string
  versions: PromptVersionInfo[]
}

// ── Auth helpers ───────────────────────────────────────────────

function authHeaders(accessToken: string): Record<string, string> {
  return {
    Authorization: `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'Unknown error' }))
    const message =
      typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body)
    throw new Error(message)
  }
  return response.json()
}

// ── Catalog CRUD ───────────────────────────────────────────────

export async function fetchCatalogAgentsAdmin(accessToken: string): Promise<CatalogAgent[]> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/admin`, {
    headers: authHeaders(accessToken),
  })
  return handleResponse<CatalogAgent[]>(response)
}

export async function fetchCatalogAgent(agentId: string, accessToken: string): Promise<CatalogAgent> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/admin/${agentId}`, {
    headers: authHeaders(accessToken),
  })
  return handleResponse<CatalogAgent>(response)
}

export async function createCatalogAgent(data: CatalogAgentCreate, accessToken: string): Promise<CatalogAgent> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents`, {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify(data),
  })
  return handleResponse<CatalogAgent>(response)
}

export async function updateCatalogAgent(
  agentId: string,
  data: CatalogAgentUpdate,
  accessToken: string,
): Promise<CatalogAgent> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/${agentId}`, {
    method: 'PUT',
    headers: authHeaders(accessToken),
    body: JSON.stringify(data),
  })
  return handleResponse<CatalogAgent>(response)
}

export async function deleteCatalogAgent(agentId: string, accessToken: string): Promise<CatalogAgent> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/${agentId}`, {
    method: 'DELETE',
    headers: authHeaders(accessToken),
  })
  return handleResponse<CatalogAgent>(response)
}

export async function duplicateCatalogAgent(agentId: string, accessToken: string): Promise<CatalogAgent> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/agents/${agentId}/duplicate`, {
    method: 'POST',
    headers: authHeaders(accessToken),
  })
  return handleResponse<CatalogAgent>(response)
}

// ── Tool Fetching & Validation ─────────────────────────────────

export async function fetchAvailableTools(tier: string, accessToken: string): Promise<AvailableToolsResponse> {
  const response = await fetch(
    `${TOOL_POOL_API_URL}/admin/clients/available-tools/${encodeURIComponent(tier)}`,
    { headers: authHeaders(accessToken) },
  )
  return handleResponse<AvailableToolsResponse>(response)
}

export async function validateTools(
  enabledTools: string[],
  tier: string,
  accessToken: string,
): Promise<ValidateToolsResult> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/validate-tools`, {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: JSON.stringify({ enabled_tools: enabledTools, tier }),
  })
  return handleResponse<ValidateToolsResult>(response)
}

// ── Prompt Listing ─────────────────────────────────────────────

export async function fetchAvailablePrompts(accessToken: string): Promise<PromptInfo[]> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/prompts`, {
    headers: authHeaders(accessToken),
  })
  return handleResponse<PromptInfo[]>(response)
}

export async function fetchPromptDetail(promptName: string, accessToken: string): Promise<PromptDetail> {
  const response = await fetch(
    `${AGENT_API_URL}/v1/catalog/prompts/${encodeURIComponent(promptName)}`,
    { headers: authHeaders(accessToken) },
  )
  return handleResponse<PromptDetail>(response)
}

export async function updatePrompt(
  promptName: string,
  content: string,
  accessToken: string,
): Promise<PromptDetail> {
  const response = await fetch(
    `${AGENT_API_URL}/v1/catalog/prompts/${encodeURIComponent(promptName)}`,
    {
      method: 'PUT',
      headers: authHeaders(accessToken),
      body: JSON.stringify({ content }),
    },
  )
  return handleResponse<PromptDetail>(response)
}

export async function fetchPromptVersions(
  promptName: string,
  accessToken: string,
): Promise<PromptVersionsResponse> {
  const response = await fetch(
    `${AGENT_API_URL}/v1/catalog/prompts/${encodeURIComponent(promptName)}/versions`,
    { headers: authHeaders(accessToken) },
  )
  return handleResponse<PromptVersionsResponse>(response)
}

// ── Node Catalog ───────────────────────────────────────────────

export async function fetchCatalogNodes(accessToken: string): Promise<CatalogNodeMetadata[]> {
  const response = await fetch(`${AGENT_API_URL}/v1/catalog/nodes`, {
    headers: authHeaders(accessToken),
  })
  return handleResponse<CatalogNodeMetadata[]>(response)
}
