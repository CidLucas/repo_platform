import { supabase } from './client'

export interface DimensionKpi {
  slug: string
  label: string
  unit: string
  dimension: string
  description: string | null
}

export interface EstrategiaHistoryItem {
  id: string
  title: string
  action: 'approved' | 'rejected'
  created_at: string
  outcome_summary: string | null
}

export async function fetchDimensionKpis(clientId: string): Promise<DimensionKpi[]> {
  const { data, error } = await supabase
    .from('client_dimension_kpis')
    .select('slug, dimension, kpi_catalog!inner(label, unit, description)')
    .eq('client_id', clientId)
    .order('dimension')

  if (error) throw error

  return (data ?? []).map((row) => {
    const catalog = (row.kpi_catalog as unknown) as { label: string; unit: string; description: string | null }
    return {
      slug: row.slug,
      dimension: row.dimension,
      label: catalog.label,
      unit: catalog.unit,
      description: catalog.description ?? null,
    }
  })
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
    const meta = (row.payload ?? {}) as Record<string, unknown>
    return {
      id: row.id,
      title: row.title,
      action: row.status as 'approved' | 'rejected',
      created_at: row.created_at,
      outcome_summary: typeof meta.outcome_summary === 'string' ? meta.outcome_summary : null,
    }
  })
}
