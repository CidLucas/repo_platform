import { supabase } from './client'

export interface ClientInsight {
  id: string
  dimension: string | null
  kpi: string | null
  severity: string
  title: string
  observation: string
  recommendation: string | null
  status: string
  createdAt: string
}

export async function fetchInsights(limit = 5): Promise<ClientInsight[]> {
  const { data, error } = await supabase.rpc('get_my_insights', {
    p_limit: limit,
    p_status: 'active',
  })

  if (error) {
    if (error.code === '42883') return [] // RPC not deployed yet
    throw error
  }

  return ((data ?? []) as Array<Record<string, unknown>>).map((row) => ({
    id: String(row.id),
    dimension: (row.dimension as string) ?? null,
    kpi: (row.kpi as string) ?? null,
    severity: String(row.severity ?? 'low'),
    title: String(row.title),
    observation: String(row.observation),
    recommendation: (row.recommendation as string) ?? null,
    status: String(row.status),
    createdAt: String(row.created_at),
  }))
}

export async function dismissInsight(id: string): Promise<void> {
  const { error } = await supabase.rpc('dismiss_insight', { p_insight_id: id })
  if (error) throw error
}
