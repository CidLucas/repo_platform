import { supabase } from './client'

export interface AgentSession {
  id: string
  session_id: string
  agent_catalog_id: string
  config_status: string | null
  created_at: string
  updated_at: string
  metadata: Record<string, unknown> | null
}

export interface SessionMessage {
  id: string
  session_id: string | null
  channel: string
  direction: string | null
  role: string | null
  body: string | null
  status: string | null
  created_at: string
}

export interface SyncJob {
  job_id: string
  job_type: string
  credential_id: number | null
  resource_type: string | null
  sync_mode: string | null
  status: string
  progress_pct: number | null
  rows_inserted: number | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  retry_count: number
  created_at: string
}

export interface Credential {
  id: number
  nome: string | null
  nome_servico: string | null
  tipo_servico: string | null
  tipo: string | null
  status: string | null
  ativo: boolean
  created_at: string
  updated_at: string
}

export async function fetchAgentSessions(clientId: string): Promise<AgentSession[]> {
  const { data, error } = await supabase
    .from('standalone_agent_sessions')
    .select('id, session_id, agent_catalog_id, config_status, created_at, updated_at, metadata')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })
    .limit(100)
  if (error) throw error
  return data ?? []
}

export async function fetchSessionMessages(sessionId: string, clientId: string): Promise<SessionMessage[]> {
  const { data, error } = await supabase
    .from('messages')
    .select('id, session_id, channel, direction, role, body, status, created_at')
    .eq('session_id', sessionId)
    .eq('client_id', clientId)
    .order('created_at', { ascending: true })
    .limit(200)
  if (error) throw error
  return data ?? []
}

export async function fetchSyncJobs(): Promise<SyncJob[]> {
  const { data, error } = await supabase.rpc('ops_list_sync_jobs')
  if (error) throw error
  return (data ?? []) as SyncJob[]
}

export async function retryJob(jobId: string): Promise<void> {
  const { error } = await supabase.rpc('ops_retry_job', { p_job_id: jobId })
  if (error) throw error
}

export async function fetchCredentials(clientId: string): Promise<Credential[]> {
  const { data, error } = await supabase
    .from('credencial_servico_externo')
    .select('id, nome, nome_servico, tipo_servico, tipo, status, ativo, created_at, updated_at')
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })
  if (error) throw error
  return data ?? []
}

export async function toggleCredential(id: number, ativo: boolean): Promise<void> {
  const { error } = await supabase
    .from('credencial_servico_externo')
    .update({ ativo, updated_at: new Date().toISOString() })
    .eq('id', id)
  if (error) throw error
}
