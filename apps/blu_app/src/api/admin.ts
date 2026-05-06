import { supabase } from './client'
import type { ClienteBlu } from '@/types/user'

// ── Integration / credential types ─────────────────────────────────────────

export type IntegrationStatus = 'connected' | 'error' | 'disconnected'

export interface Integration {
  id: string
  client_id: string
  // Display fields — normalized from real DB columns (tipo_servico, ativo, updated_at)
  provider: string
  /** Human-readable connection name (e.g. table name for BigQuery) */
  name: string | null
  status: IntegrationStatus
  last_synced_at: string | null
  error_message: string | null
  created_at: string
  /** Raw connection_metadata for showing connection-specific details (project, table, etc.) */
  connection_detail: string | null
}

function normalizeStatus(status: string | null, ativo: boolean | null): IntegrationStatus {
  if (status === 'error') return 'error'
  if (status === 'active' || ativo === true) return 'connected'
  if (status === 'disconnected') return 'disconnected'
  return 'disconnected' // 'pending' and any unknown → not yet connected
}

// ── Audit log ──────────────────────────────────────────────────────────────

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

// ── Notification preferences ───────────────────────────────────────────────

export interface NotificationPreference {
  id: string
  client_id: string
  channel: 'email' | 'push' | 'in_app'
  notification_type: string
  enabled: boolean
}

// ── Integrations ───────────────────────────────────────────────────────────

export async function fetchIntegrations(clientId: string): Promise<Integration[]> {
  const { data, error } = await supabase
    .from('credencial_servico_externo')
    // Select both new column names (tipo, nome) and old aliases (tipo_servico, nome_servico)
    // for forward/backward compatibility across schema migrations.
    .select('id, client_id, tipo, nome, tipo_servico, nome_servico, status, ativo, connection_metadata, created_at, updated_at')
    .eq('client_id', clientId)
    // Newest first so deduplication keeps the latest row per provider.
    .order('created_at', { ascending: false })

  if (error) throw error

  const rows = data ?? []
  // Deduplicate by provider — keep only the latest row per provider type.
  // The ingestion pipeline can create multiple rows for the same provider on
  // each sync attempt; we only want to show one card per connector type.
  const seenProviders = new Set<string>()
  const deduped = rows.filter((row) => {
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

  return deduped.map((row) => {
    const rawProvider =
      (row.tipo as string | null) ??
      (row.tipo_servico as string | null) ??
      (row.nome as string | null) ??
      (row.nome_servico as string | null) ??
      'unknown'
    const meta = (row.connection_metadata as Record<string, unknown> | null) ?? {}
    const connectionDetail = buildConnectionDetail(rawProvider.toLowerCase(), meta)
    return {
      id: String(row.id),
      client_id: row.client_id as string,
      provider: rawProvider.toLowerCase(),
      name: ((row.nome as string | null) ?? (row.nome_servico as string | null)) || null,
      status: normalizeStatus(row.status as string | null, row.ativo as boolean | null),
      last_synced_at: (row.updated_at as string | null) ?? null,
      error_message: (meta.error_message as string | null) ?? null,
      created_at: row.created_at as string,
      connection_detail: connectionDetail,
    }
  })
}

function buildConnectionDetail(
  provider: string,
  meta: Record<string, unknown>,
): string | null {
  if (provider === 'bigquery') {
    const parts = [meta.project_id, meta.dataset_id, meta.table_name].filter(Boolean)
    return parts.length ? parts.join(' › ') : null
  }
  if (provider === 'shopify') return (meta.shop_name as string | null) ?? null
  if (provider === 'vtex') return (meta.account_name as string | null) ?? null
  if (provider === 'postgresql' || provider === 'mysql') {
    const host = meta.host as string | null
    const db = meta.database as string | null
    return host && db ? `${host} / ${db}` : (host ?? db ?? null)
  }
  if (provider === 'whatsapp') return (meta.whatsapp_number as string | null) ?? null
  return null
}

export async function syncIntegration(integrationId: string): Promise<void> {
  const { error } = await supabase.functions.invoke('sync-integration', {
    body: { integration_id: integrationId },
  })
  if (error) throw error
}

export async function disconnectIntegration(integrationId: string): Promise<void> {
  const { error } = await supabase
    .from('credencial_servico_externo')
    .update({ status: 'disconnected' })
    .eq('id', integrationId)

  if (error) throw error
}

// ── Users ──────────────────────────────────────────────────────────────────

export async function fetchClientUsers(clientId: string): Promise<ClienteBlu[]> {
  const { data, error } = await supabase
    .from('clientes_blu')
    .select('*')
    .eq('id', clientId)

  if (error) throw error
  return (data ?? []) as ClienteBlu[]
}

// ── Audit log ──────────────────────────────────────────────────────────────

export async function fetchAuditLog(
  clientId: string,
  page: number = 1,
  pageSize: number = 50
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

// ── Notification preferences ───────────────────────────────────────────────

export async function fetchNotificationPreferences(
  clientId: string
): Promise<NotificationPreference[]> {
  const { data, error } = await supabase
    .from('client_notification_preferences')
    .select('*')
    .eq('client_id', clientId)

  if (error) throw error
  return (data ?? []) as NotificationPreference[]
}

export async function updateNotificationPreference(
  id: string,
  enabled: boolean
): Promise<void> {
  const { error } = await supabase
    .from('client_notification_preferences')
    .update({ enabled })
    .eq('id', id)

  if (error) throw error
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
