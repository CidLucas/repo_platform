/**
 * Analytics API — Supabase-native API calls
 *
 * Ported from apps/blu_app/src/services/analyticsService.ts
 * Uses @blu/auth supabase singleton; RLS policies filter by client_id from JWT.
 */

import { supabase } from '@blu/auth'

const ANALYTICS_SCHEMA = 'analytics_v2'

// --- Type Definitions ---

export type PeriodType = 'week' | 'month' | 'quarter' | 'year'
export type StandardPeriod = '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'custom'

export interface RecentActivityItem {
  kind: 'ingestion' | 'agent_session' | 'rfq' | 'upload' | string
  title: string
  subtitle: string | null
  occurredAt: string
  severity: 'info' | 'warning' | 'error' | string
}

export interface PendenciaItem {
  kind: 'rfq_pending' | 'connector_error' | 'data_source_issue' | string
  title: string
  severity: 'info' | 'warning' | 'error' | string
  occurredAt: string | null
  targetRoute: string
}

export interface InsightItem {
  id: string
  runDate: string
  room: 'financeiro' | 'clientes' | 'compras' | 'agenda' | 'estrategia' | 'home' | string
  kpi: string
  severity: 'info' | 'warning' | 'error' | string
  title: string
  observation: string
  recommendation: string | null
  metricValue: number | null
  baselineValue: number | null
  variancePct: number | null
  status: 'active' | 'dismissed' | 'expired' | string
  createdAt: string
}

export interface AgentRunsTodayResponse {
  total: number
  byAgent: Record<string, number>
}

export interface NpsScoreResponse {
  score: number
  totalResponses: number
  promoters: number
  passives: number
  detractors: number
}

export interface AgendaEvent {
  id: string
  title: string
  startsAt: string
  endsAt: string
  type: 'meeting' | 'call' | 'deadline'
  location: string | null
  attendeesCount: number
  hangoutLink: string | null
}

export interface AgendaResponse {
  events: AgendaEvent[]
  disabled: boolean
  reason?: string
  fetchedAt: string | null
  rangeDays: number
}

export interface ChartDataPoint {
  name: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any
}

export interface ChartData {
  id: string
  title: string
  data: ChartDataPoint[]
}

export interface HomeScorecards {
  receita_total: number
  receita_mes_atual: number
  total_fornecedores: number
  total_produtos: number
  total_regioes: number
  total_clientes: number
  total_pedidos: number
  pedidos_mes_atual?: number
  ticket_medio?: number
  crescimento_receita?: number
  crescimento_pedidos?: number
  crescimento_clientes?: number
  crescimento_produtos?: number
  frequencia_media_fornecedores?: number
  ultimo_mes?: string
  clientes_ativos?: number
  clientes_novos?: number
  quantidade_total_vendida?: number
}

export interface HomeMetricsResponse {
  scorecards: HomeScorecards
  charts: ChartData[]
}

// --- Helpers ---

const num = (v: unknown): number => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}
const numOrNull = (v: unknown): number | null => {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

async function callDimensionRpc<T>(rpc: string, period: string): Promise<T> {
  const { data, error } = await supabase
    .rpc(rpc, { p_period: period })
  if (error) throw new Error(`${rpc}: ${error.message}`)
  return (Array.isArray(data) ? data[0] : data) as T
}

// --- API Functions ---

export const getHomeMetrics = async (): Promise<HomeMetricsResponse> => {
  const { data: resumo, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .limit(1)
    .maybeSingle()

  if (error) console.error('[Dashboard] v_resumo_dashboard FAILED:', error.message)

  const { data: series, error: seriesError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .order('data_periodo', { ascending: true })

  if (seriesError) console.error('[Dashboard] v_series_temporal FAILED:', seriesError.message)

  const dashboard = resumo || {}

  const scorecards: HomeScorecards = {
    receita_total: Number(dashboard.receita_total) || 0,
    receita_mes_atual: Number(dashboard.receita_mes_atual) || 0,
    total_fornecedores: Number(dashboard.total_fornecedores) || 0,
    total_produtos: Number(dashboard.total_produtos) || 0,
    total_regioes: Number(dashboard.total_regioes) || 0,
    total_clientes: Number(dashboard.total_clientes) || 0,
    total_pedidos: Number(dashboard.total_pedidos) || 0,
    pedidos_mes_atual: Number(dashboard.pedidos_mes_atual ?? dashboard.total_pedidos) || 0,
    ticket_medio: Number(dashboard.ticket_medio) || 0,
    crescimento_receita: dashboard.crescimento_receita != null ? Number(dashboard.crescimento_receita) : undefined,
    crescimento_pedidos: dashboard.crescimento_pedidos != null ? Number(dashboard.crescimento_pedidos) : undefined,
    crescimento_clientes: dashboard.crescimento_clientes != null ? Number(dashboard.crescimento_clientes) : undefined,
    crescimento_produtos: dashboard.crescimento_produtos != null ? Number(dashboard.crescimento_produtos) : undefined,
    frequencia_media_fornecedores: Number(dashboard.frequencia_media_fornecedores) || 0,
    ultimo_mes: dashboard.ultimo_mes || undefined,
    clientes_ativos: Number(dashboard.clientes_ativos) || 0,
    clientes_novos: Number(dashboard.clientes_novos) || 0,
    quantidade_total_vendida: Number(dashboard.quantidade_total_vendida) || 0,
  }

  const receitaNoTempo = (series || [])
    .filter((s) => s.tipo_grafico === 'receita')
    .map((s) => ({ name: s.periodo, total: Number(s.total) || 0 }))

  const charts: ChartData[] = [
    { id: 'receita_no_tempo', title: 'Receita no Tempo', data: receitaNoTempo },
  ]

  return { scorecards, charts }
}

export const getRecentActivity = async (limit = 10): Promise<RecentActivityItem[]> => {
  const { data, error } = await supabase.rpc('get_recent_activity', { p_limit: limit })
  if (error) throw new Error(error.message)
  return (data || []).map(
    (row: { kind: string; title: string; subtitle: string | null; occurred_at: string; severity: string }) => ({
      kind: row.kind,
      title: row.title,
      subtitle: row.subtitle,
      occurredAt: row.occurred_at,
      severity: row.severity,
    }),
  )
}

export const getPendencias = async (): Promise<PendenciaItem[]> => {
  const { data, error } = await supabase.rpc('get_pendencias')
  if (error) throw new Error(error.message)
  return (data || []).map(
    (row: { kind: string; title: string; severity: string; occurred_at: string | null; target_route: string }) => ({
      kind: row.kind,
      title: row.title,
      severity: row.severity,
      occurredAt: row.occurred_at,
      targetRoute: row.target_route,
    }),
  )
}

export const getInsights = async (limit = 5): Promise<InsightItem[]> => {
  const { data, error } = await supabase.rpc('get_my_insights', {
    p_limit: limit,
    p_status: 'active',
  })
  if (error) throw new Error(error.message)
  return (data || []).map(
    (row: {
      id: string
      run_date: string
      room: string
      kpi: string
      severity: string
      title: string
      observation: string
      recommendation: string | null
      metric_value: number | string | null
      baseline_value: number | string | null
      variance_pct: number | string | null
      status: string
      created_at: string
    }) => ({
      id: row.id,
      runDate: row.run_date,
      room: row.room,
      kpi: row.kpi,
      severity: row.severity,
      title: row.title,
      observation: row.observation,
      recommendation: row.recommendation,
      metricValue: row.metric_value !== null ? Number(row.metric_value) : null,
      baselineValue: row.baseline_value !== null ? Number(row.baseline_value) : null,
      variancePct: row.variance_pct !== null ? Number(row.variance_pct) : null,
      status: row.status,
      createdAt: row.created_at,
    }),
  )
}

export const dismissInsight = async (insightId: string): Promise<void> => {
  const { error } = await supabase.rpc('dismiss_insight', { p_insight_id: insightId })
  if (error) throw new Error(error.message)
}

export const getAgentRunsToday = async (): Promise<AgentRunsTodayResponse> => {
  const { data, error } = await supabase.rpc('get_agent_runs_today')
  if (error) throw new Error(error.message)
  const row = (Array.isArray(data) ? data[0] : data) as
    | { total?: number | string; by_agent?: Record<string, number> | null }
    | null
    | undefined
  return {
    total: Number(row?.total) || 0,
    byAgent: (row?.by_agent ?? {}) as Record<string, number>,
  }
}

export const getNpsScore = async (windowDays = 90): Promise<NpsScoreResponse> => {
  const { data, error } = await supabase.rpc('get_nps_score', { p_window_days: windowDays })
  if (error) throw new Error(error.message)
  const row = (Array.isArray(data) ? data[0] : data) as
    | { score?: number | string; total_responses?: number | string; promoters?: number | string; passives?: number | string; detractors?: number | string }
    | null
    | undefined
  return {
    score: Number(row?.score) || 0,
    totalResponses: Number(row?.total_responses) || 0,
    promoters: Number(row?.promoters) || 0,
    passives: Number(row?.passives) || 0,
    detractors: Number(row?.detractors) || 0,
  }
}

export const getAgendaEvents = async (rangeDays = 7): Promise<AgendaResponse> => {
  const { data, error } = await supabase.functions.invoke('google-calendar-events', {
    body: { rangeDays },
  })
  if (error) {
    return { events: [], disabled: true, reason: 'function_error', fetchedAt: null, rangeDays }
  }
  const payload = (data ?? {}) as {
    events?: Array<{ id: string; title: string; starts_at: string; ends_at: string; type: string; location: string | null; attendees_count: number; hangout_link: string | null }>
    disabled?: boolean
    reason?: string
    fetched_at?: string
    range_days?: number
  }
  return {
    events: (payload.events ?? []).map((ev) => ({
      id: ev.id,
      title: ev.title,
      startsAt: ev.starts_at,
      endsAt: ev.ends_at,
      type: (ev.type as AgendaEvent['type']) ?? 'meeting',
      location: ev.location,
      attendeesCount: Number(ev.attendees_count) || 0,
      hangoutLink: ev.hangout_link,
    })),
    disabled: Boolean(payload.disabled),
    reason: payload.reason,
    fetchedAt: payload.fetched_at ?? null,
    rangeDays: Number(payload.range_days ?? rangeDays),
  }
}

// --- Dimension Indicator Types & RPCs ---

export type DimensionKey = 'finance' | 'commercial' | 'inventory' | 'supply' | 'marketing' | 'admin'

export interface FinanceIndicators {
  receita_liquida: number
  custo_total: number | null
  margem_bruta_perc: number | null
  margem_operacional_perc: number | null
  ticket_medio: number
  receita_yoy_perc: number | null
  crescimento_receita_perc: number | null
  total_pedidos: number
  dso_dias: number | null
  dpo_dias: number | null
  ccc_dias: number | null
  working_capital_ratio: number | null
  burn_rate_mensal: number | null
  runway_meses: number | null
  cash_flow_30d: number | null
  period: string
}

export interface CommercialIndicators {
  pedidos_periodo: number
  receita_periodo: number
  ticket_medio: number
  clientes_unicos: number
  clientes_novos: number
  clientes_recorrentes: number
  recencia_media_dias: number
  frequencia_media_mensal: number
  churn_60d_perc: number | null
  crescimento_receita_perc: number | null
  win_rate_perc: number | null
  ciclo_venda_dias: number | null
  nrr_perc: number | null
  clv: number | null
  checkout_conversion_perc: number | null
  nps: number | null
  period: string
}

export interface InventoryIndicators {
  skus_ativos: number
  skus_total: number
  quantidade_vendida_periodo: number
  receita_skus_periodo: number
  giro_estimado: number | null
  ticket_medio_sku: number
  cobertura_top20_perc: number | null
  stockout_rate_perc: number | null
  crescimento_quantidade_perc: number | null
  dio_dias: number | null
  cobertura_dias: number | null
  fill_rate_perc: number | null
  sell_through_perc: number | null
  gmroi: number | null
  acuracidade_perc: number | null
  period: string
}

export interface SupplyIndicators {
  rfqs_abertas: number
  rfqs_enviadas: number
  rfqs_respondidas: number
  taxa_resposta_perc: number | null
  tempo_resposta_medio_h: number | null
  pos_aprovadas: number
  pos_pendentes_aprovacao: number
  spend_periodo: number
  fornecedores_ativos: number
  concentracao_top_perc: number | null
  cycle_time_medio_h: number | null
  cost_savings_perc: number | null
  ppv: number | null
  otif_perc: number | null
  lead_time_medio_dias: number | null
  maverick_spend_perc: number | null
  spend_under_management_perc: number | null
  period: string
}

export interface MarketingIndicators {
  novos_clientes_periodo: number
  receita_novos_clientes: number
  conversao_campanha_perc: number | null
  engajamento_whatsapp_perc: number | null
  taxa_optout_perc: number | null
  cac: number | null
  ltv_cac_ratio: number | null
  roas: number | null
  ctr_perc: number | null
  cac_payback_meses: number | null
  share_of_voice_perc: number | null
  period: string
}

export interface AdminIndicators {
  aprovacoes_pendentes: number
  lead_time_aprovacao_h: number | null
  sla_aprovacao_perc: number | null
  documentos_pendentes: number
  cobertura_rotinas_perc: number | null
  frescor_dados_h: number | null
  audit_coverage_perc: number | null
  period: string
}

export const getFinanceIndicators = async (period: string = '30d'): Promise<FinanceIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_finance_indicators', period)
  return {
    receita_liquida: num(r?.receita_liquida),
    custo_total: numOrNull(r?.custo_total),
    margem_bruta_perc: numOrNull(r?.margem_bruta_perc),
    margem_operacional_perc: numOrNull(r?.margem_operacional_perc),
    ticket_medio: num(r?.ticket_medio),
    receita_yoy_perc: numOrNull(r?.receita_yoy_perc),
    crescimento_receita_perc: numOrNull(r?.crescimento_receita_perc),
    total_pedidos: num(r?.total_pedidos),
    dso_dias: numOrNull(r?.dso_dias),
    dpo_dias: numOrNull(r?.dpo_dias),
    ccc_dias: numOrNull(r?.ccc_dias),
    working_capital_ratio: numOrNull(r?.working_capital_ratio),
    burn_rate_mensal: numOrNull(r?.burn_rate_mensal),
    runway_meses: numOrNull(r?.runway_meses),
    cash_flow_30d: numOrNull(r?.cash_flow_30d),
    period: String(r?.period ?? period),
  }
}

export const getCommercialIndicators = async (period: string = '30d'): Promise<CommercialIndicators> => {
  let r: Record<string, unknown>
  try {
    r = await callDimensionRpc<Record<string, unknown>>('get_commercial_indicators', period)
  } catch (_) {
    r = { period }
  }
  return {
    pedidos_periodo: num(r?.pedidos_periodo),
    receita_periodo: num(r?.receita_periodo),
    ticket_medio: num(r?.ticket_medio),
    clientes_unicos: num(r?.clientes_unicos),
    clientes_novos: num(r?.clientes_novos),
    clientes_recorrentes: num(r?.clientes_recorrentes),
    recencia_media_dias: num(r?.recencia_media_dias),
    frequencia_media_mensal: num(r?.frequencia_media_mensal),
    churn_60d_perc: numOrNull(r?.churn_60d_perc),
    crescimento_receita_perc: numOrNull(r?.crescimento_receita_perc),
    win_rate_perc: numOrNull(r?.win_rate_perc),
    ciclo_venda_dias: numOrNull(r?.ciclo_venda_dias),
    nrr_perc: numOrNull(r?.nrr_perc),
    clv: numOrNull(r?.clv),
    checkout_conversion_perc: numOrNull(r?.checkout_conversion_perc),
    nps: numOrNull(r?.nps),
    period: String(r?.period ?? period),
  }
}

export const getInventoryIndicators = async (period: string = '30d'): Promise<InventoryIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_inventory_indicators', period)
  return {
    skus_ativos: num(r?.skus_ativos),
    skus_total: num(r?.skus_total),
    quantidade_vendida_periodo: num(r?.quantidade_vendida_periodo),
    receita_skus_periodo: num(r?.receita_skus_periodo),
    giro_estimado: numOrNull(r?.giro_estimado),
    ticket_medio_sku: num(r?.ticket_medio_sku),
    cobertura_top20_perc: numOrNull(r?.cobertura_top20_perc),
    stockout_rate_perc: numOrNull(r?.stockout_rate_perc),
    crescimento_quantidade_perc: numOrNull(r?.crescimento_quantidade_perc),
    dio_dias: numOrNull(r?.dio_dias),
    cobertura_dias: numOrNull(r?.cobertura_dias),
    fill_rate_perc: numOrNull(r?.fill_rate_perc),
    sell_through_perc: numOrNull(r?.sell_through_perc),
    gmroi: numOrNull(r?.gmroi),
    acuracidade_perc: numOrNull(r?.acuracidade_perc),
    period: String(r?.period ?? period),
  }
}

export const getSupplyIndicators = async (period: string = '30d'): Promise<SupplyIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_supply_indicators', period)
  return {
    rfqs_abertas: num(r?.rfqs_abertas),
    rfqs_enviadas: num(r?.rfqs_enviadas),
    rfqs_respondidas: num(r?.rfqs_respondidas),
    taxa_resposta_perc: numOrNull(r?.taxa_resposta_perc),
    tempo_resposta_medio_h: numOrNull(r?.tempo_resposta_medio_h),
    pos_aprovadas: num(r?.pos_aprovadas),
    pos_pendentes_aprovacao: num(r?.pos_pendentes_aprovacao),
    spend_periodo: num(r?.spend_periodo),
    fornecedores_ativos: num(r?.fornecedores_ativos),
    concentracao_top_perc: numOrNull(r?.concentracao_top_perc),
    cycle_time_medio_h: numOrNull(r?.cycle_time_medio_h),
    cost_savings_perc: numOrNull(r?.cost_savings_perc),
    ppv: numOrNull(r?.ppv),
    otif_perc: numOrNull(r?.otif_perc),
    lead_time_medio_dias: numOrNull(r?.lead_time_medio_dias),
    maverick_spend_perc: numOrNull(r?.maverick_spend_perc),
    spend_under_management_perc: numOrNull(r?.spend_under_management_perc),
    period: String(r?.period ?? period),
  }
}

export const getMarketingIndicators = async (period: string = '30d'): Promise<MarketingIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_marketing_indicators', period)
  return {
    novos_clientes_periodo: num(r?.novos_clientes_periodo),
    receita_novos_clientes: num(r?.receita_novos_clientes),
    conversao_campanha_perc: numOrNull(r?.conversao_campanha_perc),
    engajamento_whatsapp_perc: numOrNull(r?.engajamento_whatsapp_perc),
    taxa_optout_perc: numOrNull(r?.taxa_optout_perc),
    cac: numOrNull(r?.cac),
    ltv_cac_ratio: numOrNull(r?.ltv_cac_ratio),
    roas: numOrNull(r?.roas),
    ctr_perc: numOrNull(r?.ctr_perc),
    cac_payback_meses: numOrNull(r?.cac_payback_meses),
    share_of_voice_perc: numOrNull(r?.share_of_voice_perc),
    period: String(r?.period ?? period),
  }
}

export const getAdminIndicators = async (period: string = '30d'): Promise<AdminIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_admin_indicators', period)
  return {
    aprovacoes_pendentes: num(r?.aprovacoes_pendentes),
    lead_time_aprovacao_h: numOrNull(r?.lead_time_aprovacao_h),
    sla_aprovacao_perc: numOrNull(r?.sla_aprovacao_perc),
    documentos_pendentes: num(r?.documentos_pendentes),
    cobertura_rotinas_perc: numOrNull(r?.cobertura_rotinas_perc),
    frescor_dados_h: numOrNull(r?.frescor_dados_h),
    audit_coverage_perc: numOrNull(r?.audit_coverage_perc),
    period: String(r?.period ?? period),
  }
}

// --- Commercial breakdowns ---

export interface RevenueByChannelRow {
  channel: string
  receita: number
  pedidos: number
  share_perc: number | null
  period: string
}

export const getCommercialRevenueByChannel = async (period: string = '30d'): Promise<RevenueByChannelRow[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_commercial_revenue_by_channel', { p_period: period })
  if (error) throw new Error(`get_commercial_revenue_by_channel: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    channel: String(r?.channel ?? 'sem_canal'),
    receita: num(r?.receita),
    pedidos: num(r?.pedidos),
    share_perc: numOrNull(r?.share_perc),
    period: String(r?.period ?? period),
  }))
}

export interface TopClientRow {
  client_id: number
  nome: string | null
  receita: number
  pedidos: number
  share_perc: number | null
  period: string
}

export const getCommercialTopClients = async (period: string = '30d', limit = 10): Promise<TopClientRow[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_commercial_top_clients', { p_period: period, p_limit: limit })
  if (error) throw new Error(`get_commercial_top_clients: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    client_id: num(r?.client_id),
    nome: r?.nome == null ? null : String(r.nome),
    receita: num(r?.receita),
    pedidos: num(r?.pedidos),
    share_perc: numOrNull(r?.share_perc),
    period: String(r?.period ?? period),
  }))
}

// --- KPI Catalog ---

export type KpiUnit = 'number' | 'currency' | 'percent' | 'days' | 'hours' | 'ratio' | 'count'
export type KpiDataStatus = 'live' | 'proxy' | 'external' | 'pending_data'
export type KpiTier = 'BASIC' | 'SME' | 'PRO' | 'PREMIUM' | 'ENTERPRISE' | 'ADMIN'

export interface KpiCatalogEntry {
  slug: string
  dimension: DimensionKey
  label: string
  formula: string
  unit: KpiUnit
  is_leading: boolean
  tier_required: KpiTier
  data_status: KpiDataStatus
  rpc_column: string | null
  description: string | null
  references_url: string | null
  sort_order: number
  is_enabled: boolean
}

export interface DashboardKpiSlot {
  dimension: DimensionKey
  slot_index: number
  slug: string
  label: string
  unit: KpiUnit
  formula: string
  data_status: KpiDataStatus
  tier_required: KpiTier
  is_enabled: boolean
}

export const listKpiCatalog = async (dimension: DimensionKey | null = null, onlyEnabled = true): Promise<KpiCatalogEntry[]> => {
  const { data, error } = await supabase.rpc('list_kpi_catalog', {
    p_dimension: dimension,
    p_only_enabled: onlyEnabled,
  })
  if (error) throw new Error(`list_kpi_catalog: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    slug: String(r?.slug),
    dimension: String(r?.dimension) as DimensionKey,
    label: String(r?.label),
    formula: String(r?.formula),
    unit: (String(r?.unit) as KpiUnit) ?? 'number',
    is_leading: Boolean(r?.is_leading),
    tier_required: (String(r?.tier_required) as KpiTier) ?? 'BASIC',
    data_status: (String(r?.data_status) as KpiDataStatus) ?? 'live',
    rpc_column: r?.rpc_column == null ? null : String(r.rpc_column),
    description: r?.description == null ? null : String(r.description),
    references_url: r?.references_url == null ? null : String(r.references_url),
    sort_order: num(r?.sort_order),
    is_enabled: Boolean(r?.is_enabled),
  }))
}

export const setClientDimensionKpis = async (
  dimension: DimensionKey,
  slugs: string[],
): Promise<Array<{ dimension: DimensionKey; slot_index: number; kpi_slug: string }>> => {
  const { data, error } = await supabase.rpc('set_client_dimension_kpis', {
    p_dimension: dimension,
    p_slugs: slugs,
  })
  if (error) throw new Error(`set_client_dimension_kpis: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    dimension: String(r?.dimension) as DimensionKey,
    slot_index: num(r?.slot_index),
    kpi_slug: String(r?.kpi_slug),
  }))
}

export const getMyDashboardKpis = async (): Promise<DashboardKpiSlot[]> => {
  const { data, error } = await supabase.rpc('get_my_dashboard_kpis')
  if (error) throw new Error(`get_my_dashboard_kpis: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    dimension: String(r?.dimension) as DimensionKey,
    slot_index: num(r?.slot_index),
    slug: String(r?.slug),
    label: String(r?.label),
    unit: (String(r?.unit) as KpiUnit) ?? 'number',
    formula: String(r?.formula),
    data_status: (String(r?.data_status) as KpiDataStatus) ?? 'live',
    tier_required: (String(r?.tier_required) as KpiTier) ?? 'BASIC',
    is_enabled: Boolean(r?.is_enabled),
  }))
}

// --- Annual Metrics ---

export interface AnnualMetricRow {
  period: string
  value: number
}

export const getAnnualMetrics = async (metric: string): Promise<AnnualMetricRow[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('periodo,total')
    .eq('tipo_grafico', metric)
    .order('data_periodo', { ascending: true })
  if (error) throw new Error(`getAnnualMetrics(${metric}): ${error.message}`)
  return ((data ?? []) as Array<{ periodo: string; total: unknown }>).map((r) => ({
    period: r.periodo,
    value: num(r.total),
  }))
}

// --- Context Metrics (values for all client-configured KPIs) ---

export interface ContextMetricRow {
  dimension: string
  kpi: string
  label: string
  unit: string
  current_value: number | null
  mom_pct: number | null
  streak_months: number
}

/** Fetches actual current values + MoM delta for all KPIs configured for this client. */
export const getContextMetrics = async (period: string = '30d'): Promise<ContextMetricRow[]> => {
  const { data, error } = await supabase.rpc('get_my_context_metrics', { p_period: period })
  if (error) throw new Error(`get_my_context_metrics: ${error.message}`)
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    dimension: String(r?.dimension ?? ''),
    kpi: String(r?.kpi ?? ''),
    label: String(r?.label ?? ''),
    unit: String(r?.unit ?? ''),
    current_value: r?.current_value != null ? Number(r.current_value) : null,
    mom_pct: r?.mom_pct != null ? Number(r.mom_pct) : null,
    streak_months: Number(r?.streak_months ?? 0),
  }))
}
