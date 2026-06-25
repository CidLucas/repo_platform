import { supabase } from './client'

// ─── Catalog routine (cross_agent_routines based) ────────────────────────────

export interface CatalogStep {
  id?: string
  step: number
  type?: 'function' | 'skill' | 'artifact'
  // legacy fields
  agent?: string
  action?: string
  output?: string
  // modern fields
  function?: string
  skill_slug?: string
  task_template?: string
  artifact_type?: string
  inputs?: Record<string, unknown>
  outputs?: Record<string, unknown> | string[]
  on_failure?: 'halt' | 'continue'
  label?: string
}

export interface ClientRoutine {
  id: string
  client_id: string
  routine_id: string
  active: boolean
  status: 'active' | 'inactive' | 'pending_approval' | 'draft'
  source: 'catalog' | 'custom' | 'system'
  config: Record<string, unknown>
  trigger_type: 'manual' | 'schedule' | 'event' | 'numeric' | 'cron'
  trigger_config: Record<string, unknown>
  last_run_at: string | null
  cross_agent_routines: {
    name: string
    room: string
    trigger_type: string
    trigger_config: Record<string, unknown>
    config_schema: ConfigSchemaField[]
    steps: CatalogStep[]
  } | null
}

export interface ConfigSchemaField {
  key: string
  label: string
  type: 'text' | 'number' | 'boolean' | 'select' | 'dict'
  default?: unknown
  required?: boolean
  options?: { value: string; label: string }[]
  max_entries?: number
}

// ─── Custom routine ───────────────────────────────────────────────────────────

/** @deprecated Use CatalogStep for new routines */
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
  steps: CatalogStep[]
  trigger_type: 'manual' | 'document' | 'schedule' | 'event' | 'numeric'
  trigger_config: Record<string, unknown>
  created_by_ai: boolean
  config: Record<string, unknown>
  created_at: string
}

// ─── Live routine catalog (from agent_api registries) ─────────────────────────

export interface ActionParam {
  key: string
  type: 'str' | 'int' | 'float' | 'bool' | 'list' | 'dict' | 'select'
  description: string
  default?: unknown
  required?: boolean
  options?: { value: string; label: string }[]
}

export interface ActionDef {
  id: string
  label: string
  description: string
  inputs: ActionParam[]
  outputs: ActionParam[]
}

export interface SkillDef {
  id: string
  label: string
  description: string
  tags?: string[]
  /** 'l3_skill' for SKILL_REGISTRY entries; undefined for agent-executor slugs */
  kind?: 'l3_skill'
}

export interface TriggerDef {
  id: string
  label: string
  description: string
  config_schema: ActionParam[]
}

export interface RoutineCatalog {
  functions: ActionDef[]
  artifacts: ActionDef[]
  skills: SkillDef[]
  /** L3 narrative skills from SKILL_REGISTRY — invoked by orchestrator/context-gatherer */
  l3_skills: SkillDef[]
  triggers: TriggerDef[]
  /** @deprecated use skills */
  skill_slugs: string[]
}

export async function fetchRoutineCatalog(): Promise<RoutineCatalog> {
  const baseUrl = (import.meta.env.VITE_ATENDENTE_CORE as string | undefined) ?? ''
  const res = await fetch(`${baseUrl}/v1/routines/catalog`)
  if (!res.ok) throw new Error(`Failed to fetch routine catalog: ${res.status}`)
  return res.json() as Promise<RoutineCatalog>
}

// ─── Execution history ────────────────────────────────────────────────────────

export interface RoutineExecution {
  id: string
  routine_id: string
  status: 'pending' | 'dispatched' | 'executing' | 'completed' | 'failed'
  triggered_by: string
  created_at: string
  completed_at: string | null
  result_text: string | null
  worker_slug: string | null
  // joined from client_routines or cross_agent_routines
  routine_name?: string
}

// ─── Fetch functions ──────────────────────────────────────────────────────────

export async function fetchRoutines(clientId: string, domain?: string, platform?: string): Promise<ClientRoutine[]> {
  let query = supabase
    .from('client_routines')
    .select('*, cross_agent_routines(name, room, trigger_type, trigger_config, config_schema, steps)')
    .eq('client_id', clientId)
    .eq('source', 'catalog')
    .order('routine_id')

  const { data, error } = await query
  if (error) throw error

  const rows = (data ?? []) as ClientRoutine[]
  if (platform) return rows.filter(r => r.cross_agent_routines?.room === platform)
  if (domain) return rows.filter(r => r.cross_agent_routines?.room === domain)
  return rows
}

export async function fetchActiveRoutines(
  clientId: string,
  domain?: string
): Promise<ClientRoutine[]> {
  const { data, error } = await supabase
    .from('client_routines')
    .select('*, cross_agent_routines(name, room, trigger_type, trigger_config, config_schema, steps)')
    .eq('client_id', clientId)
    .eq('active', true)
    .eq('status', 'active')
    .order('last_run_at', { ascending: false, nullsFirst: false })

  if (error) throw error

  const rows = (data ?? []) as ClientRoutine[]
  if (domain) return rows.filter(r => r.cross_agent_routines?.room === domain)
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
  return (data ?? []) as CustomRoutine[]
}

export async function fetchLastExecution(
  clientId: string,
  routineId: string
): Promise<RoutineExecution | null> {
  const { data, error } = await supabase
    .from('client_routine_executions')
    .select('*')
    .eq('client_id', clientId)
    .eq('routine_id', routineId)
    .eq('status', 'completed')
    .order('completed_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  if (error) throw error
  return data as RoutineExecution | null
}

export async function fetchExecutionHistory(
  clientId: string,
  _domain?: string,
  limit = 20
): Promise<RoutineExecution[]> {
  const { data, error } = await supabase
    .from('client_routine_executions')
    .select('*')
    .eq('client_id', clientId)
    .in('status', ['completed', 'failed'])
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw error

  // If domain filter requested, we need to know which routine_ids belong to that domain.
  // For now return all and let the component filter by joining with catalog data.
  // A future view/RPC can do this server-side.
  return (data ?? []) as RoutineExecution[]
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

export async function updateRoutineConfig(
  id: string,
  clientId: string,
  config: Record<string, unknown>
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update({ config })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function createCustomRoutine(
  clientId: string,
  draft: {
    name: string
    description?: string
    steps: CatalogStep[]
    trigger_type?: CustomRoutine['trigger_type']
    trigger_config?: Record<string, unknown>
    created_by_ai?: boolean
  }
): Promise<CustomRoutine> {
  const { data, error } = await supabase
    .from('client_routines')
    .insert({
      client_id: clientId,
      routine_id: `custom.${Date.now()}`,
      source: 'custom',
      status: 'draft',
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

// Submit custom routine for owner approval
export async function submitRoutineForApproval(
  clientId: string,
  clientRoutineId: string,
  routineName: string,
  steps: CatalogStep[] = []
): Promise<void> {
  const { error: approvalError } = await supabase.from('approval_requests').insert({
    client_id: clientId,
    action_type: 'routine_activation',
    assigned_role: 'owner',
    agent_slug: 'sistema',
    title: `Ativar rotina: ${routineName}`,
    body: `Revise e aprove a rotina personalizada "${routineName}" para ativá-la.`,
    payload: {
      client_routine_id: clientRoutineId,
      routine_name: routineName,
      steps,
      source: 'custom',
    },
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  })

  if (approvalError) throw approvalError

  const { error: statusError } = await supabase
    .from('client_routines')
    .update({ status: 'pending_approval' })
    .eq('id', clientRoutineId)
    .eq('client_id', clientId)

  if (statusError) throw statusError
}

export async function activateRoutine(
  clientRoutineId: string,
  clientId: string
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update({ status: 'active', active: true })
    .eq('id', clientRoutineId)
    .eq('client_id', clientId)

  if (error) throw error
}

export async function renameRoutine(
  id: string,
  clientId: string,
  newName: string
): Promise<void> {
  return updateCustomRoutine(id, clientId, { name: newName })
}

export async function updateRoutineTrigger(
  id: string,
  clientId: string,
  triggerType: ClientRoutine['trigger_type'],
  triggerConfig: Record<string, unknown>
): Promise<void> {
  const { error } = await supabase
    .from('client_routines')
    .update({ trigger_type: triggerType, trigger_config: triggerConfig })
    .eq('id', id)
    .eq('client_id', clientId)

  if (error) throw error
}

// ─── Room config (agent-level settings, separate from routine config) ─────────

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
