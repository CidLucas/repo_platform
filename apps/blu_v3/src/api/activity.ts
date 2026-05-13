import { supabase } from './client'

export interface RecentActivityItem {
  kind: string
  title: string
  subtitle: string | null
  occurredAt: string
  severity: 'info' | 'warning' | 'error' | string
}

export interface DayStats {
  approvedToday: number
  agentActionsToday: number
}

export async function getRecentActivity(limit = 20): Promise<RecentActivityItem[]> {
  const { data, error } = await supabase.rpc('get_recent_activity', { p_limit: limit })
  if (error) throw new Error(error.message)

  return (data ?? []).map(
    (row: { kind: string; title: string; subtitle: string | null; occurred_at: string; severity: string }) => ({
      kind: row.kind,
      title: row.title,
      subtitle: row.subtitle,
      occurredAt: row.occurred_at,
      severity: row.severity,
    })
  )
}

export async function fetchDayStats(clientId: string): Promise<DayStats> {
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const iso = todayStart.toISOString()

  const [{ count: approvedToday }, { count: agentActionsToday }] = await Promise.all([
    supabase
      .from('approval_requests')
      .select('*', { count: 'exact', head: true })
      .eq('client_id', clientId)
      .eq('status', 'approved')
      .gte('updated_at', iso),
    supabase
      .from('audit_log')
      .select('*', { count: 'exact', head: true })
      .eq('client_id', clientId)
      .gte('created_at', iso),
  ])

  return {
    approvedToday: approvedToday ?? 0,
    agentActionsToday: agentActionsToday ?? 0,
  }
}
