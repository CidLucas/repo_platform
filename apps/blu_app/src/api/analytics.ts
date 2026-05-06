/**
 * Analytics API — mirrors blu_dashboard's analyticsService pattern.
 * Queries analytics_v2 schema directly. RLS policies filter by client
 * from the JWT automatically — no clientId parameter needed.
 */
import { supabase } from './client'
import type { ClientKpiSnapshot, KpiMetrics, KpiPeriod, TimeSeriesPoint, ActivityEntry } from '@/types/analytics'

const ANALYTICS_SCHEMA = 'analytics_v2'

// ── KPI snapshot ──────────────────────────────────────────────────────────────

function num(v: unknown): number | undefined {
  if (v == null) return undefined
  const n = Number(v)
  return isNaN(n) ? undefined : n === 0 ? undefined : n
}

export async function fetchKpiSnapshot(_period: KpiPeriod): Promise<ClientKpiSnapshot | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .limit(1)
    .maybeSingle()

  if (error) {
    console.error('[analytics] v_resumo_dashboard:', error.code, error.message)
    return null
  }
  if (!data) return null

  const d = data as Record<string, unknown>
  const metrics: KpiMetrics = {
    faturamento:     num(d.receita_total),
    pedidos:         num(d.total_pedidos),
    clientes_ativos: num(d.clientes_ativos),
    ticket_medio:    num(d.ticket_medio),
    fornecedores:    num(d.total_fornecedores),
    produtos:        num(d.total_produtos),
    faturamento_trend: d.crescimento_receita != null ? Number(d.crescimento_receita) : undefined,
    pedidos_delta:     d.crescimento_pedidos  != null ? Number(d.crescimento_pedidos)  : undefined,
    clientes_delta:    d.crescimento_clientes != null ? Number(d.crescimento_clientes) : undefined,
  }

  return { id: 'live', client_id: '', period: _period, metrics, generated_at: new Date().toISOString() }
}

// ── Time series ───────────────────────────────────────────────────────────────

interface SeriesRow { tipo_grafico: string; periodo: string; total: number | null }

const VALID_SERIES_KEYS = new Set(['receita', 'despesas', 'entrada', 'saida'])

function pivotSeries(rows: SeriesRow[]): TimeSeriesPoint[] {
  const map = new Map<string, TimeSeriesPoint>()
  for (const row of rows) {
    if (!map.has(row.periodo)) map.set(row.periodo, { date: row.periodo })
    if (VALID_SERIES_KEYS.has(row.tipo_grafico)) {
      const point = map.get(row.periodo)!;
      (point as Record<string, unknown>)[row.tipo_grafico] = Number(row.total) || 0
    }
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
}

export async function fetchTimeSeries(_period: KpiPeriod): Promise<TimeSeriesPoint[]> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('tipo_grafico, periodo, total')
    .order('periodo', { ascending: true })

  if (error) {
    console.error('[analytics] v_series_temporal:', error.code, error.message)
    return []
  }
  return pivotSeries((data ?? []) as SeriesRow[])
}

// ── Recent activity ───────────────────────────────────────────────────────────

export async function fetchRecentActivity(limit = 20): Promise<ActivityEntry[]> {
  const { data, error } = await supabase.rpc('get_recent_activity', { p_limit: limit })

  if (error) {
    if (error.code === '42883') return []  // RPC not deployed yet
    console.error('[analytics] get_recent_activity:', error.message)
    return []
  }

  return ((data ?? []) as Array<{
    kind: string
    title: string
    subtitle: string | null
    occurred_at: string
    severity: string
  }>).map((row, i) => ({
    id: `${row.occurred_at}-${i}`,
    kind: row.kind,
    title: row.title,
    subtitle: row.subtitle ?? null,
    occurredAt: row.occurred_at,
    severity: row.severity,
  }))
}
