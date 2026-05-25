import { supabase } from './client'

// ── Integration types ──────────────────────────────────────────────────────

export type IntegrationStatus = 'connected' | 'error' | 'disconnected'

export interface Integration {
  id: string
  client_id: string
  provider: string
  name: string | null
  status: IntegrationStatus
  last_synced_at: string | null
  error_message: string | null
  created_at: string
  connection_detail: string | null
}

// ── Audit log types ────────────────────────────────────────────────────────

export interface AuditEntry {
  id: string
  client_id: string
  agent_slug: string | null
  action: string
  entity_type: string | null
  entity_id: string | null
  actor: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

// ── Helpers ────────────────────────────────────────────────────────────────

function normalizeStatus(status: string | null, ativo: boolean | null): IntegrationStatus {
  if (status === 'error') return 'error'
  if (status === 'active' || ativo === true) return 'connected'
  if (status === 'disconnected') return 'disconnected'
  return 'disconnected'
}

function buildConnectionDetail(provider: string, meta: Record<string, unknown>): string | null {
  if (provider === 'bigquery') {
    const parts = [meta.project_id, meta.dataset_id, meta.table_name].filter(Boolean)
    return parts.length ? parts.join(' › ') : null
  }
  if (provider === 'postgresql' || provider === 'mysql') {
    const host = meta.host as string | null
    const db = meta.database as string | null
    return host && db ? `${host} / ${db}` : (host ?? db ?? null)
  }
  if (provider === 'whatsapp') return (meta.whatsapp_number as string | null) ?? null
  if (provider === 'shopify') return (meta.shop_name as string | null) ?? null
  if (provider === 'vtex') return (meta.account_name as string | null) ?? null
  return null
}

// ── Integrations ───────────────────────────────────────────────────────────

export async function fetchIntegrations(clientId: string): Promise<Integration[]> {
  const [credResult, tokenResult, polpResult] = await Promise.all([
    supabase
      .from('credencial_servico_externo')
      .select('id, client_id, tipo, nome, tipo_servico, nome_servico, status, ativo, connection_metadata, created_at, updated_at')
      .eq('client_id', clientId)
      .order('created_at', { ascending: false }),
    supabase
      .from('integration_tokens')
      .select('id, client_id, provider, account_email, scopes, updated_at, created_at')
      .eq('client_id', clientId),
    supabase
      .from('polp_integrations')
      .select('id, client_id, polp_integration_id, institution_id, status, execution_status, error, last_updated_at, created_at, updated_at')
      .eq('client_id', clientId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle(),
  ])

  if (credResult.error) throw credResult.error

  // Deduplicate credentials by provider — keep latest row per provider type
  const seenProviders = new Set<string>()
  const deduped = (credResult.data ?? []).filter((row) => {
    const provider = (
      (row.tipo as string | null) ??
      (row.tipo_servico as string | null) ??
      (row.nome as string | null) ??
      (row.nome_servico as string | null) ??
      'unknown'
    ).toLowerCase()
    if (seenProviders.has(provider)) return false
    seenProviders.add(provider)
    return true
  })

  const credIntegrations: Integration[] = deduped.map((row) => {
    const rawProvider =
      (row.tipo as string | null) ??
      (row.tipo_servico as string | null) ??
      (row.nome as string | null) ??
      (row.nome_servico as string | null) ??
      'unknown'
    const meta = (row.connection_metadata as Record<string, unknown> | null) ?? {}
    return {
      id: String(row.id),
      client_id: row.client_id as string,
      provider: rawProvider.toLowerCase(),
      name: ((row.nome as string | null) ?? (row.nome_servico as string | null)) || null,
      status: normalizeStatus(row.status as string | null, row.ativo as boolean | null),
      last_synced_at: (row.updated_at as string | null) ?? null,
      error_message: (meta.error_message as string | null) ?? null,
      created_at: row.created_at as string,
      connection_detail: buildConnectionDetail(rawProvider.toLowerCase(), meta),
    }
  })

  // Synthesize OAuth token integrations from integration_tokens
  const oauthIntegrations: Integration[] = []
  for (const token of (tokenResult.data ?? [])) {
    const tokenId = String(token.id)

    if (token.provider === 'google') {
      const scopes = (token.scopes as string[] | null) ?? []

      if (scopes.some((s: string) => s.includes('drive'))) {
        oauthIntegrations.push({
          id: `oauth:${tokenId}`,
          client_id: token.client_id as string,
          provider: 'google_drive',
          name: token.account_email as string | null,
          status: 'connected',
          last_synced_at: token.updated_at as string | null,
          error_message: null,
          created_at: token.created_at as string,
          connection_detail: token.account_email as string | null,
        })
      }

      if (scopes.some((s: string) => s.includes('calendar'))) {
        oauthIntegrations.push({
          id: `oauth:${tokenId}`,
          client_id: token.client_id as string,
          provider: 'google_calendar',
          name: token.account_email as string | null,
          status: 'connected',
          last_synced_at: token.updated_at as string | null,
          error_message: null,
          created_at: token.created_at as string,
          connection_detail: token.account_email as string | null,
        })
      }
    }

    // Non-OAuth API token integrations (Slack, Monday, etc.)
    if (!['google'].includes(token.provider)) {
      oauthIntegrations.push({
        id: `oauth:${tokenId}`,
        client_id: token.client_id as string,
        provider: token.provider as string,
        name: token.account_email as string | null,
        status: 'connected' as IntegrationStatus,
        last_synced_at: token.updated_at as string | null,
        error_message: null,
        created_at: token.created_at as string,
        connection_detail: token.account_email as string | null,
      })
    }
  }

  // Exclude credential rows whose provider is now covered by an OAuth token
  const oauthProviderSet = new Set(oauthIntegrations.map((i) => i.provider))
  const filteredCreds = credIntegrations.filter((i) => !oauthProviderSet.has(i.provider))

  // Synthesize Polp Open Finance integration entry from polp_integrations table
  const polpIntegrations: Integration[] = []
  const polpRow = polpResult.data
  if (polpRow) {
    const polpStatus = polpRow.status as string
    let status: IntegrationStatus = 'disconnected'
    if (polpStatus === 'UPDATED') status = 'connected'
    else if (polpStatus === 'LOGIN_ERROR' || polpRow.error) status = 'error'
    else if (polpStatus === 'UPDATING' || polpStatus === 'WAITING_USER_INPUT') status = 'disconnected'
    polpIntegrations.push({
      id: String(polpRow.id),
      client_id: polpRow.client_id as string,
      provider: 'polp',
      name: 'Open Finance',
      status,
      last_synced_at: (polpRow.last_updated_at as string | null) ?? (polpRow.updated_at as string | null),
      error_message: (polpRow.error as string | null) ?? null,
      created_at: polpRow.created_at as string,
      connection_detail: polpStatus === 'UPDATING' ? 'Sincronizando…' : polpStatus === 'WAITING_USER_INPUT' ? 'Aguardando autenticação' : null,
    })
  }

  return [...filteredCreds, ...oauthIntegrations, ...polpIntegrations]
}

export async function disconnectIntegration(integrationId: string): Promise<void> {
  // OAuth token integrations use the `oauth:<uuid>` prefix
  if (integrationId.startsWith('oauth:')) {
    const tokenId = integrationId.slice(6)
    const { error } = await supabase.from('integration_tokens').delete().eq('id', tokenId)
    if (error) throw error
    return
  }
  const { error } = await supabase
    .from('credencial_servico_externo')
    .update({ status: 'disconnected', ativo: false })
    .eq('id', integrationId)
  if (error) throw error
}

// ── Team members ──────────────────────────────────────────────────────────

export interface TeamMember {
  id: string
  client_id: string
  auth_user_id: string | null
  name: string | null
  email: string
  role: 'owner' | 'admin' | 'manager' | 'member'
  agent_permissions: Record<string, boolean>
  action_permissions: Record<string, boolean>
  invited_at: string | null
  accepted_at: string | null
  created_at: string
}

export async function fetchTeamMembers(clientId: string): Promise<TeamMember[]> {
  const { data, error } = await supabase
    .from('client_users')
    .select('id, client_id, auth_user_id, name, email, role, agent_permissions, action_permissions, invited_at, accepted_at, created_at')
    .eq('client_id', clientId)
    .order('created_at', { ascending: true })

  if (error) throw error
  return (data ?? []) as TeamMember[]
}

export async function ensureOwnerRow(
  clientId: string,
  authUserId: string,
  email: string,
  name: string | null
): Promise<void> {
  const { error } = await supabase
    .from('client_users')
    .upsert(
      {
        client_id: clientId,
        auth_user_id: authUserId,
        email,
        name,
        role: 'owner',
        accepted_at: new Date().toISOString(),
      },
      { onConflict: 'client_id,email', ignoreDuplicates: true }
    )
  if (error) throw error
}

export async function inviteUser(
  clientId: string,
  email: string,
  name: string | null,
  role: string
): Promise<void> {
  const { error } = await supabase
    .from('client_users')
    .insert({ client_id: clientId, email, name, role })
  if (error) throw error
}

export async function fetchMyRole(
  clientId: string,
  authUserId: string
): Promise<TeamMember['role'] | null> {
  const { data } = await supabase
    .from('client_users')
    .select('role')
    .eq('client_id', clientId)
    .eq('auth_user_id', authUserId)
    .maybeSingle()
  return (data?.role as TeamMember['role']) ?? null
}

export async function updateUserPermissions(
  userId: string,
  clientId: string,
  patch: { agent_permissions?: Record<string, boolean>; action_permissions?: Record<string, boolean> }
): Promise<void> {
  const { error } = await supabase
    .from('client_users')
    .update(patch)
    .eq('id', userId)
    .eq('client_id', clientId)
  if (error) throw error
}

// ── Audit log ──────────────────────────────────────────────────────────────

export async function fetchAuditLog(
  clientId: string,
  page = 1,
  pageSize = 50
): Promise<{ entries: AuditEntry[]; total: number }> {
  const from = (page - 1) * pageSize
  const to = from + pageSize - 1

  const { data, error, count } = await supabase
    .from('audit_log')
    .select('*', { count: 'exact' })
    .eq('client_id', clientId)
    .order('created_at', { ascending: false })
    .range(from, to)

  if (error) throw error
  return { entries: (data ?? []) as AuditEntry[], total: count ?? 0 }
}

// ── LGPD ──────────────────────────────────────────────────────────────────

export async function requestDataExport(clientId: string): Promise<void> {
  const { error } = await supabase.functions.invoke('lgpd-export', {
    body: { client_id: clientId },
  })
  if (error) throw error
}

export async function requestDataDeletion(clientId: string): Promise<void> {
  const { error } = await supabase.functions.invoke('lgpd-delete', {
    body: { client_id: clientId },
  })
  if (error) throw error
}
