import { supabase } from './client'

export interface DimensionKpi {
  id: string
  kpi_key: string
  label: string
  current_value: number | null
  target_value: number | null
  unit: string | null
  trend: 'up' | 'down' | 'flat' | null
  dimension: string
}

export interface EstrategiaHistoryItem {
  id: string
  title: string
  action: 'approved' | 'rejected' | 'snoozed' | 'other'
  created_at: string
  outcome_summary: string | null
}

export async function fetchDimensionKpis(clientId: string): Promise<DimensionKpi[]> {
  const { data, error } = await supabase
    .from('client_dimension_kpis')
    .select('id, kpi_key, label, current_value, target_value, unit, trend, dimension')
    .eq('client_id', clientId)
    .order('dimension')
    .order('label')

  if (error) throw error
  return (data ?? []).map((row) => ({
    id: row.id,
    kpi_key: row.kpi_key,
    label: row.label,
    current_value: row.current_value ?? null,
    target_value: row.target_value ?? null,
    unit: row.unit ?? null,
    trend: row.trend ?? null,
    dimension: row.dimension,
  }))
}

export async function fetchEstrategiaHistory(clientId: string): Promise<EstrategiaHistoryItem[]> {
  const { data, error } = await supabase
    .from('approval_requests')
    .select('id, title, status, created_at, payload')
    .eq('client_id', clientId)
    .eq('agent_slug', 'estrategia')
    .in('status', ['approved', 'rejected'])
    .order('created_at', { ascending: false })
    .limit(15)

  if (error) throw error

  return (data ?? []).map((row) => {
    const payload = (row.payload ?? {}) as Record<string, unknown>
    return {
      id: row.id,
      title: row.title,
      action: row.status as 'approved' | 'rejected',
      created_at: row.created_at,
      outcome_summary: typeof payload.outcome_summary === 'string' ? payload.outcome_summary : null,
    }
  })
}
