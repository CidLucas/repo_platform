import { supabase } from './client'

// ─── Catalog routine (cross_agent_routines based) ────────────────────────────

export interface ClientRoutine {
  id: string
  client_id: string
  routine_id: string
  active: boolean
  status: 'active' | 'inactive' | 'pending_approval' | 'draft'
  source: 'catalog' | 'custom'
  config: Record<string, unknown>
  last_run_at: string | null
  cross_agent_routines: {
    name: string
    trigger_domain: string
    config_schema: ConfigSchemaField[]
  } | null
}

export interface ConfigSchemaField {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'select'
  default?: unknown
  required?: boolean
  options?: { value: string; label: string }[]
}

// ─── Custom routine ───────────────────────────────────────────────────────────

export interface RoutineStep {
  step: number
  agent: string
  action: string
  output?: string
  label?: string
}

export interface CustomRoutine {
  id: string
  client_id: string
  source: 'custom'
  status: 'active' | 'inactive' | 'pending_approval' | 'draft'
  active: boolean
  name: string
  description: string | null
  steps: RoutineStep[]
  trigger_type: 'manual' | 'document' | 'schedule' | 'event'
  trigger_config: Record<string, unknown>
  created_by_ai: boolean
  config: Record<string, unknown>
  created_at: string
}

// ─── Agent action catalog ─────────────────────────────────────────────────────

export interface AgentAction {
  id: string
  agent_slug: string
  action_id: string
  label: string
  description: string | null
  input_schema: { name: string; type: string; label: string; required?: boolean }[]
  output_doc_type_id: string | null
  trigger_capable: boolean
  sort_order: number
}

// ─── Fetch functions ──────────────────────────────────────────────────────────

export async function fetchRoutines(
  clientId: string,
  domain?: string
): Promise<ClientRoutine[]> {
  const { data, error } = await supabase
    .from('client_routines')
    .select('*, cross_agent_routines(name, trigger_domain, config_schema)')
    .eq('client_id', clientId)
    .eq('source', 'catalog')
    .order('routine_id')

  if (error) throw error

  const rows = (data ?? []) as ClientRoutine[]
  if (domain) return rows.filter(r => r.cross_agent_routines?.trigger_domain === domain)
  return rows
}

export async function fetchCustomRoutines(clientId: string, _domain?: string): Promise<CustomRoutine[]> {
  const { data, error } = await supabase
    .from('client_routines')
    .select('*')
    .eq('client_id', clientId)
    .eq('source', 'custom')
    .order('created_at', { ascending: false })

  if (error) throw error

  const rows = (data ?? []) as CustomRoutine[]
  // domain filter: custom routines don't have cross_agent_routines; filter by config if needed
  return rows
}

export async function fetchAgentActions(agentSlug?: string): Promise<AgentAction[]> {
  let query = supabase
    .from('agent_action_catalog')
    .select('*')
    .eq('is_active', true)
    .order('sort_order')

  if (agentSlug) query = query.eq('agent_slug', agentSlug)

  const { data, error } = await query
  if (error) throw error
  return (data ?? []) as AgentAction[]
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export async function toggleRoutine(
  id: string,
  clientId: string,
  enabled: boolean
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update({ active: enabled, status: enabled ? 'active' : 'inactive' })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function createCustomRoutine(
  clientId: string,
  draft: {
    name: string
    description?: string
    steps: RoutineStep[]
    trigger_type?: CustomRoutine['trigger_type']
    trigger_config?: Record<string, unknown>
    created_by_ai?: boolean
  }
): Promise<CustomRoutine> {
  const { data, error } = await supabase
    .from('client_routines')
    .insert({
      client_id: clientId,
      routine_id: `custom.${Date.now()}`,  // unique placeholder
      source: 'custom',
      status: 'pending_approval',
      active: false,
      name: draft.name,
      description: draft.description ?? null,
      steps: draft.steps,
      trigger_type: draft.trigger_type ?? 'manual',
      trigger_config: draft.trigger_config ?? {},
      created_by_ai: draft.created_by_ai ?? false,
    })
    .select()
    .single()

  if (error) throw error
  return data as CustomRoutine
}

export async function updateCustomRoutine(
  id: string,
  clientId: string,
  patch: Partial<Pick<CustomRoutine, 'name' | 'description' | 'steps' | 'trigger_type' | 'trigger_config'>>
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update(patch)
    .eq('id', id)
    .eq('client_id', clientId)
    .eq('source', 'custom')

  if (error) throw error
}

export async function deleteCustomRoutine(id: string, clientId: string): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .delete()
    .eq('id', id)
    .eq('client_id', clientId)
    .eq('source', 'custom')

  if (error) throw error
}

// Submit custom routine for admin approval — creates an approval_request
export async function submitRoutineForApproval(
  clientId: string,
  clientRoutineId: string,
  routineName: string
): Promise<void> {
  const { error } = await supabase.from('approval_requests').insert({
    client_id: clientId,
    action_type: 'routine_activation',
    agent_slug: 'sistema',
    title: `Ativar rotina: ${routineName}`,
    body: `Sua rotina personalizada "${routineName}" foi criada e aguarda aprovação para ser ativada.`,
    payload: { client_routine_id: clientRoutineId },
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  })

  if (error) throw error

  // Set status to pending_approval
  await supabase
    .from('client_routines')
    .update({ status: 'pending_approval' })
    .eq('id', clientRoutineId)
    .eq('client_id', clientId)
}

// ─── Room config (unchanged) ──────────────────────────────────────────────────

export async function fetchRoutineConfig(
  clientId: string,
  domain: string
): Promise<Record<string, unknown>> {
  const routineId = `${domain}.config`
  const { data, error } = await supabase
    .from('client_routines')
    .select('config')
    .eq('client_id', clientId)
    .eq('routine_id', routineId)
    .maybeSingle()
  if (error) throw error
  return (data?.config as Record<string, unknown>) ?? {}
}

export async function upsertRoutineConfig(
  clientId: string,
  domain: string,
  config: Record<string, unknown>
): Promise<void> {
  const routineId = `${domain}.config`
  const { error } = await supabase
    .from('client_routines')
    .upsert(
      { client_id: clientId, routine_id: routineId, config, active: true },
      { onConflict: 'client_id,routine_id' }
    )
  if (error) throw error
}

