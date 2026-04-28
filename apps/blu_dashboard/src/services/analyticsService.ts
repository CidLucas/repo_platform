/**
 * Analytics Service — Supabase-native API calls
 *
 * Queries analytics_v2 schema directly via Supabase PostgREST.
 * RLS policies filter by client_id automatically from JWT.
 * No client_id header needed - authentication is JWT-based.
 */

import { supabase } from '../lib/supabase';

const ANALYTICS_SCHEMA = 'analytics_v2';

// --- Type Definitions ---

// Period filter shared across analytics RPCs.
// Legacy values (week|month|quarter|year) are kept for backwards compatibility
// with existing hooks and analytics surfaces. New dimension
// pages should prefer the standardized vocabulary from `StandardPeriod`.
export type PeriodType = 'week' | 'month' | 'quarter' | 'year';

// Standardized period vocabulary introduced in Phase 1 (K1.4).
// Backed by analytics_v2._resolve_period() which also accepts the legacy
// PeriodType aliases above.
export type StandardPeriod = '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'custom';

// Recent activity feed item (public.get_recent_activity)
export interface RecentActivityItem {
  kind: 'ingestion' | 'agent_session' | 'rfq' | 'upload' | string;
  title: string;
  subtitle: string | null;
  occurredAt: string; // ISO timestamp
  severity: 'info' | 'warning' | 'error' | string;
}

// Pendência item (public.get_pendencias)
export interface PendenciaItem {
  kind: 'rfq_pending' | 'connector_error' | 'data_source_issue' | string;
  title: string;
  severity: 'info' | 'warning' | 'error' | string;
  occurredAt: string | null;
  targetRoute: string;
}

// Insight item (public.get_my_insights — Phase 2 / I2.2)
export interface InsightItem {
  id: string;
  runDate: string;
  dimension: 'finance' | 'commercial' | 'inventory' | 'supply' | 'marketing' | 'operations' | string;
  kpi: string;
  severity: 'info' | 'warning' | 'error' | string;
  title: string;
  observation: string;
  recommendation: string | null;
  metricValue: number | null;
  baselineValue: number | null;
  variancePct: number | null;
  status: 'active' | 'dismissed' | 'expired' | string;
  createdAt: string;
}

// Agent runs today (public.get_agent_runs_today)
export interface AgentRunsTodayResponse {
  total: number;
  byAgent: Record<string, number>;
}

// NPS score (public.get_nps_score)
export interface NpsScoreResponse {
  score: number;
  totalResponses: number;
  promoters: number;
  passives: number;
  detractors: number;
}

// Agenda event (Google Calendar via google-calendar-events Edge Function)
export interface AgendaEvent {
  id: string;
  title: string;
  startsAt: string; // ISO timestamp
  endsAt: string; // ISO timestamp
  type: 'meeting' | 'call' | 'deadline';
  location: string | null;
  attendeesCount: number;
  hangoutLink: string | null;
}

export interface AgendaResponse {
  events: AgendaEvent[];
  disabled: boolean;
  reason?: string;
  fetchedAt: string | null;
  rangeDays: number;
}

// Corresponds to the Pydantic 'ChartDataPoint'
export interface ChartDataPoint {
  name: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any; // Dynamic chart properties like 'total', 'percentual', 'value', etc.
}

// Corresponds to the Pydantic 'ChartData'
export interface ChartData {
  id: string;
  title: string;
  data: ChartDataPoint[];
}

// Corresponds to the Pydantic 'HomeScorecards'
export interface HomeScorecards {
  receita_total: number;
  receita_mes_atual: number;  // Receita apenas do mês corrente
  total_fornecedores: number;
  total_produtos: number;
  total_regioes: number;
  total_clientes: number;
  total_pedidos: number;
  pedidos_mes_atual?: number;  // Pedidos count for current calendar month
  ticket_medio?: number;
  crescimento_receita?: number;  // Variação % receita (último mês vs penúltimo)
  crescimento_pedidos?: number;  // Variação % pedidos (último mês vs penúltimo)
  crescimento_clientes?: number;  // Variação % clientes (último mês vs penúltimo)
  crescimento_produtos?: number;  // Variação % produtos (último mês vs penúltimo)
  frequencia_media_fornecedores?: number;  // Média de pedidos por fornecedor por mês
  ultimo_mes?: string;  // Nome do último mês com dados (ex: "2026-01")
  // Consolidated from v_resumo_dashboard (replaces useIndicators)
  clientes_ativos?: number;  // Customers with recency <= 90 days
  clientes_novos?: number;   // Customers with single order
  quantidade_total_vendida?: number;  // Total quantity sold across all products
}

// Corresponds to the Pydantic 'HomeMetricsResponse'
export interface HomeMetricsResponse {
  scorecards: HomeScorecards;
  charts: ChartData[];
}

// --- Supabase Query Helpers ---

/**
 * Helper to throw on Supabase errors
 */
function throwIfError<T>(data: T | null, error: { message: string } | null): T {
  if (error) throw new Error(error.message);
  if (!data) throw new Error('No data returned');
  return data;
}

// --- API Client Functions ---

// Home metrics API call (dashboard overview)
export const getHomeMetrics = async (): Promise<HomeMetricsResponse> => {
  // Get dashboard summary
  const { data: resumo, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .limit(1)
    .maybeSingle();

  if (error) console.error('[Dashboard] v_resumo_dashboard FAILED:', error.code, error.message, error.details, error.hint);

  // Get series temporal for charts
  const { data: series, error: seriesError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .order('data_periodo', { ascending: true });

  if (seriesError) console.error('[Dashboard] v_series_temporal FAILED:', seriesError.code, seriesError.message, seriesError.details, seriesError.hint);

  const dashboard = resumo || {};

  const scorecards: HomeScorecards = {
    receita_total: Number(dashboard.receita_total) || 0,
    receita_mes_atual: Number(dashboard.receita_mes_atual) || 0,
    total_fornecedores: Number(dashboard.total_fornecedores) || 0,
    total_produtos: Number(dashboard.total_produtos) || 0,
    total_regioes: Number(dashboard.total_regioes) || 0,
    total_clientes: Number(dashboard.total_clientes) || 0,
    total_pedidos: Number(dashboard.total_pedidos) || 0,
    pedidos_mes_atual: Number(dashboard.pedidos_mes_atual) || 0,
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
  };

  // Group series by tipo_grafico for charts
  const receitaNoTempo = (series || []).filter(s => s.tipo_grafico === 'receita').map(s => ({
    name: s.periodo,
    total: Number(s.total) || 0,
  }));

  const charts: ChartData[] = [
    { id: 'receita_no_tempo', title: 'Receita no Tempo', data: receitaNoTempo },
  ];

  return { scorecards, charts };
};

// Recent activity feed (public.get_recent_activity)
export const getRecentActivity = async (
  limit: number = 10,
): Promise<RecentActivityItem[]> => {
  const { data, error } = await supabase.rpc('get_recent_activity', { p_limit: limit });

  if (error) throw new Error(error.message);

  return (data || []).map(
    (row: {
      kind: string;
      title: string;
      subtitle: string | null;
      occurred_at: string;
      severity: string;
    }) => ({
      kind: row.kind,
      title: row.title,
      subtitle: row.subtitle,
      occurredAt: row.occurred_at,
      severity: row.severity,
    }),
  );
};

// Pendências feed (public.get_pendencias)
export const getPendencias = async (): Promise<PendenciaItem[]> => {
  const { data, error } = await supabase.rpc('get_pendencias');

  if (error) throw new Error(error.message);

  return (data || []).map(
    (row: {
      kind: string;
      title: string;
      severity: string;
      occurred_at: string | null;
      target_route: string;
    }) => ({
      kind: row.kind,
      title: row.title,
      severity: row.severity,
      occurredAt: row.occurred_at,
      targetRoute: row.target_route,
    }),
  );
};

// Insights feed (public.get_my_insights — Phase 2 / I2.2)
export const getInsights = async (limit: number = 5): Promise<InsightItem[]> => {
  const { data, error } = await supabase.rpc('get_my_insights', {
    p_limit: limit,
    p_status: 'active',
  });

  if (error) throw new Error(error.message);

  return (data || []).map(
    (row: {
      id: string;
      run_date: string;
      dimension: string;
      kpi: string;
      severity: string;
      title: string;
      observation: string;
      recommendation: string | null;
      metric_value: number | string | null;
      baseline_value: number | string | null;
      variance_pct: number | string | null;
      status: string;
      created_at: string;
    }) => ({
      id: row.id,
      runDate: row.run_date,
      dimension: row.dimension,
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
  );
};

// Dismiss an insight (public.dismiss_insight — Phase 2 / I2.2)
export const dismissInsight = async (insightId: string): Promise<void> => {
  const { error } = await supabase.rpc('dismiss_insight', { p_insight_id: insightId });
  if (error) throw new Error(error.message);
};

// Agent runs today (public.get_agent_runs_today)
export const getAgentRunsToday = async (): Promise<AgentRunsTodayResponse> => {
  const { data, error } = await supabase.rpc('get_agent_runs_today');

  if (error) throw new Error(error.message);

  const row = (Array.isArray(data) ? data[0] : data) as
    | { total?: number | string; by_agent?: Record<string, number> | null }
    | null
    | undefined;

  return {
    total: Number(row?.total) || 0,
    byAgent: (row?.by_agent ?? {}) as Record<string, number>,
  };
};

// NPS score (public.get_nps_score)
export const getNpsScore = async (windowDays: number = 90): Promise<NpsScoreResponse> => {
  const { data, error } = await supabase.rpc('get_nps_score', {
    p_window_days: windowDays,
  });

  if (error) throw new Error(error.message);

  const row = (Array.isArray(data) ? data[0] : data) as
    | {
        score?: number | string;
        total_responses?: number | string;
        promoters?: number | string;
        passives?: number | string;
        detractors?: number | string;
      }
    | null
    | undefined;

  return {
    score: Number(row?.score) || 0,
    totalResponses: Number(row?.total_responses) || 0,
    promoters: Number(row?.promoters) || 0,
    passives: Number(row?.passives) || 0,
    detractors: Number(row?.detractors) || 0,
  };
};

// Agenda events from Google Calendar (Edge Function: google-calendar-events).
// Returns `disabled: true` with a typed `reason` when the integration is
// off, missing tokens, or refresh fails — so the UI can render an onboarding
// CTA instead of an error state.
export const getAgendaEvents = async (
  rangeDays: number = 7,
): Promise<AgendaResponse> => {
  const { data, error } = await supabase.functions.invoke(
    'google-calendar-events',
    { body: { rangeDays } },
  );

  if (error) {
    // Network / function-level error — surface as disabled so the UI degrades
    // gracefully without throwing across the React Query boundary.
    return {
      events: [],
      disabled: true,
      reason: 'function_error',
      fetchedAt: null,
      rangeDays,
    };
  }

  const payload = (data ?? {}) as {
    events?: Array<{
      id: string;
      title: string;
      starts_at: string;
      ends_at: string;
      type: string;
      location: string | null;
      attendees_count: number;
      hangout_link: string | null;
    }>;
    disabled?: boolean;
    reason?: string;
    fetched_at?: string;
    range_days?: number;
  };

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
  };
};

// Geographic clusters API call
export interface GeoCluster {
  location: string;
  count: number;
  total_revenue: number;
  coordinates: [number, number];
}

export interface GeoClustersResponse {
  clusters: GeoCluster[];
  center: [number, number];
  max_count: number;
  total_clusters: number;
}

// Brazilian state capital coordinates for geo map circles
const STATE_COORDINATES: Record<string, [number, number]> = {
  AC: [-9.0238, -70.812], AL: [-9.5713, -36.782], AM: [-3.1190, -60.022],
  AP: [0.0349, -51.066], BA: [-12.971, -38.511], CE: [-3.7172, -38.543],
  DF: [-15.780, -47.929], ES: [-20.319, -40.338], GO: [-16.686, -49.264],
  MA: [-2.5297, -44.282], MG: [-19.920, -43.938], MS: [-20.469, -54.620],
  MT: [-15.601, -56.097], PA: [-1.4558, -48.502], PB: [-7.1195, -34.845],
  PE: [-8.0476, -34.877], PI: [-5.0892, -42.802], PR: [-25.430, -49.271],
  RJ: [-22.907, -43.173], RN: [-5.7945, -35.211], RO: [-8.7612, -63.900],
  RR: [2.81950, -60.672], RS: [-30.034, -51.230], SC: [-27.594, -48.548],
  SE: [-10.909, -37.072], SP: [-23.550, -46.633], TO: [-10.186, -48.334],
};

export const getGeoClusters = async (groupBy: 'state' | 'city' = 'state'): Promise<GeoClustersResponse> => {
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('endereco_uf, endereco_cidade, receita_total');

  if (error) console.warn('Error fetching geo clusters:', error);

  // Aggregate by location (state or city only — CEP was dropped in the Apr 2026 slim)
  const grouped = (clientes || []).reduce((acc, c) => {
    const loc = groupBy === 'state'
      ? String(c.endereco_uf || 'N/A')
      : String(c.endereco_cidade || 'N/A');
    if (!acc[loc]) acc[loc] = { count: 0, total_revenue: 0 };
    acc[loc].count++;
    acc[loc].total_revenue += Number(c.receita_total) || 0;
    return acc;
  }, {} as Record<string, { count: number; total_revenue: number }>);

  const clusters: GeoCluster[] = Object.entries(grouped)
    .filter(([loc]) => loc !== 'N/A')
    .map(([location, data]) => ({
      location,
      count: data.count,
      total_revenue: data.total_revenue,
      coordinates: STATE_COORDINATES[location.toUpperCase()] || [-14.235, -51.925],
    }));

  return {
    clusters,
    center: [-14.235, -51.925], // Brazil center
    max_count: Math.max(...clusters.map(c => c.count), 1),
    total_clusters: clusters.length,
  };
};

// --- Domain Analytics (for DomainExpansionModal) ---

export interface DomainAnalytics {
  monthlyData: ChartDataPoint[];
  kpis: Record<string, number>;
}

interface DomainSeriesRow {
  periodo: string;
  total: number | string | null;
}

const toMonthlySeries = (series: DomainSeriesRow[] | null | undefined): Array<{ name: string; value: number }> => {
  const byMonth = new Map<string, number>();

  for (const row of series || []) {
    const month = row?.periodo;
    if (!month) continue;
    byMonth.set(month, (byMonth.get(month) || 0) + (Number(row.total) || 0));
  }

  return Array.from(byMonth.entries()).map(([name, value]) => ({ name, value }));
};

const fetchMonthlyDomainSeries = async (
  tipoGrafico: string,
  dimensaoPreferencial: string
): Promise<Array<{ name: string; value: number }>> => {
  const { data: primary } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('periodo,total,dimensao,data_periodo')
    .eq('tipo_grafico', tipoGrafico)
    .eq('dimensao', dimensaoPreferencial)
    .order('data_periodo', { ascending: true });

  if (primary && primary.length > 0) {
    return toMonthlySeries(primary as DomainSeriesRow[]);
  }

  const fallbackDimensions = ['contagem', 'quantidade', 'receita'].filter(
    d => d !== dimensaoPreferencial
  );

  for (const fallbackDim of fallbackDimensions) {
    const { data: fallback } = await supabase
      .schema(ANALYTICS_SCHEMA)
      .from('v_series_temporal')
      .select('periodo,total,dimensao,data_periodo')
      .eq('tipo_grafico', tipoGrafico)
      .eq('dimensao', fallbackDim)
      .order('data_periodo', { ascending: true });

    if (fallback && fallback.length > 0) {
      return toMonthlySeries(fallback as DomainSeriesRow[]);
    }
  }

  return [];
};

/**
 * Fetches analytics for a specific business domain (orders, customers, suppliers, products).
 * Uses existing v_series_temporal + dimension tables to build monthly trends and KPIs.
 */
export const getDomainAnalytics = async (
  domain: 'orders' | 'customers' | 'suppliers' | 'products'
): Promise<DomainAnalytics> => {
  // Get dashboard summary for KPIs
  const { data: resumo } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .limit(1)
    .maybeSingle();

  const dashboard = resumo || {};

  switch (domain) {
    case 'orders': {
      const series = await fetchMonthlyDomainSeries('receita', 'receita');
      const monthlyData = series.map(s => ({
        name: s.name,
        month: s.name,
        value: s.value,
        revenue: s.value,
      }));

      return {
        monthlyData,
        kpis: {
          total_orders: Number(dashboard.total_pedidos) || 0,
          avg_ticket: Number(dashboard.ticket_medio) || 0,
          growth: Number(dashboard.crescimento_receita) || 0,
          conversion_rate: 0,
          revenue_growth: Number(dashboard.crescimento_receita) || 0,
        },
      };
    }

    case 'customers': {
      const series = await fetchMonthlyDomainSeries('clientes', 'contagem');
      const monthlyData = series.map(s => ({
        name: s.name,
        month: s.name,
        value: s.value,
        new: s.value,
        returning: 0,
      }));

      return {
        monthlyData,
        kpis: {
          active_customers: Number(dashboard.clientes_ativos) || Number(dashboard.total_clientes) || 0,
          total_customers: Number(dashboard.total_clientes) || 0,
          avg_ltv: Number(dashboard.ticket_medio) || 0,
          churn_rate: 0,
          growth: Number(dashboard.crescimento_clientes) || 0,
        },
      };
    }

    case 'suppliers': {
      const series = await fetchMonthlyDomainSeries('fornecedores', 'contagem');
      const monthlyData = series.map(s => ({
        name: s.name,
        month: s.name,
        value: s.value,
        active: s.value,
        orders: 0,
      }));

      return {
        monthlyData,
        kpis: {
          total_suppliers: Number(dashboard.total_fornecedores) || 0,
          active_suppliers: Number(dashboard.total_fornecedores) || 0,
          total_revenue: Number(dashboard.receita_total) || 0,
          avg_delivery_time: 0,
          compliance_rate: 0,
        },
      };
    }

    case 'products': {
      const series = await fetchMonthlyDomainSeries('produtos', 'contagem');
      const monthlyData = series.map(s => ({
        name: s.name,
        month: s.name,
        value: s.value,
        sold: s.value,
        revenue: 0,
      }));

      return {
        monthlyData,
        kpis: {
          total_products: Number(dashboard.total_produtos) || 0,
          total_sold: Number(dashboard.quantidade_total_vendida) || 0,
          total_revenue: Number(dashboard.receita_total) || 0,
          avg_margin: 0,
          turnover_rate: 0,
        },
      };
    }
  }
};

// ─────────────────────────────────────────────────────────────────────
// Phase 1 — Per-dimension KPI RPCs (BLU-MVP-010..014)
// All RPCs are SECURITY INVOKER and accept the standardized period vocabulary
// '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'custom' as well as the legacy
// PeriodType aliases ('week' | 'month' | 'quarter' | 'year').
// ─────────────────────────────────────────────────────────────────────

export type DimensionKey = 'finance' | 'commercial' | 'inventory' | 'supply' | 'marketing' | 'admin';

export interface FinanceIndicators {
  receita_liquida: number;
  custo_total: number;
  margem_bruta_perc: number | null;
  margem_operacional_perc: number | null;
  ticket_medio: number;
  receita_yoy_perc: number | null;
  crescimento_receita_perc: number | null;
  total_pedidos: number;
  // §6.1 PRO extensions (NULL until upstream ingest lands)
  dso_dias: number | null;
  dpo_dias: number | null;
  ccc_dias: number | null;
  working_capital_ratio: number | null;
  burn_rate_mensal: number | null;
  runway_meses: number | null;
  cash_flow_30d: number | null;
  period: string;
}

export interface CommercialIndicators {
  pedidos_periodo: number;
  receita_periodo: number;
  ticket_medio: number;
  clientes_unicos: number;
  clientes_novos: number;
  clientes_recorrentes: number;
  recencia_media_dias: number;
  frequencia_media_mensal: number;
  churn_60d_perc: number | null;
  crescimento_receita_perc: number | null;
  // §6.2 PRO extensions
  win_rate_perc: number | null;
  ciclo_venda_dias: number | null;
  nrr_perc: number | null;
  clv: number | null;
  checkout_conversion_perc: number | null;
  nps: number | null;
  period: string;
}

export interface InventoryIndicators {
  skus_ativos: number;
  skus_total: number;
  quantidade_vendida_periodo: number;
  receita_skus_periodo: number;
  giro_estimado: number | null;
  ticket_medio_sku: number;
  cobertura_top20_perc: number | null;
  stockout_rate_perc: number | null;
  crescimento_quantidade_perc: number | null;
  // §6.3 PRO extensions
  dio_dias: number | null;
  cobertura_dias: number | null;
  fill_rate_perc: number | null;
  sell_through_perc: number | null;
  gmroi: number | null;
  acuracidade_perc: number | null;
  period: string;
}

export interface SupplyIndicators {
  rfqs_abertas: number;
  rfqs_enviadas: number;
  rfqs_respondidas: number;
  taxa_resposta_perc: number | null;
  tempo_resposta_medio_h: number | null;
  pos_aprovadas: number;
  pos_pendentes_aprovacao: number;
  spend_periodo: number;
  fornecedores_ativos: number;
  concentracao_top_perc: number | null;
  cycle_time_medio_h: number | null;
  // §6.4 PRO extensions
  cost_savings_perc: number | null;
  ppv: number | null;
  otif_perc: number | null;
  lead_time_medio_dias: number | null;
  maverick_spend_perc: number | null;
  spend_under_management_perc: number | null;
  period: string;
}

export interface MarketingIndicators {
  novos_clientes_periodo: number;
  receita_novos_clientes: number;
  conversao_campanha_perc: number | null;
  engajamento_whatsapp_perc: number | null;
  taxa_optout_perc: number | null;
  cac: number | null;
  ltv_cac_ratio: number | null;
  roas: number | null;
  ctr_perc: number | null;
  // §6.5 PRO extensions
  cac_payback_meses: number | null;
  share_of_voice_perc: number | null;
  period: string;
}

export interface AdminIndicators {
  aprovacoes_pendentes: number;
  lead_time_aprovacao_h: number | null;
  sla_aprovacao_perc: number | null;
  documentos_pendentes: number;
  cobertura_rotinas_perc: number | null;
  frescor_dados_h: number | null;
  audit_coverage_perc: number | null;
  period: string;
}

export interface DimensionIndicatorMap {
  finance: FinanceIndicators;
  commercial: CommercialIndicators;
  inventory: InventoryIndicators;
  supply: SupplyIndicators;
  marketing: MarketingIndicators;
  admin: AdminIndicators;
}

const num = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};
const numOrNull = (v: unknown): number | null => {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

async function callDimensionRpc<T>(rpc: string, period: PeriodType | StandardPeriod | string): Promise<T> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc(rpc, { p_period: period });
  if (error) throw new Error(`${rpc}: ${error.message}`);
  return (Array.isArray(data) ? data[0] : data) as T;
}

export const getFinanceIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<FinanceIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_finance_indicators', period);
  return {
    receita_liquida:           num(r?.receita_liquida),
    custo_total:               num(r?.custo_total),
    margem_bruta_perc:         numOrNull(r?.margem_bruta_perc),
    margem_operacional_perc:   numOrNull(r?.margem_operacional_perc),
    ticket_medio:              num(r?.ticket_medio),
    receita_yoy_perc:          numOrNull(r?.receita_yoy_perc),
    crescimento_receita_perc:  numOrNull(r?.crescimento_receita_perc),
    total_pedidos:             num(r?.total_pedidos),
    dso_dias:                  numOrNull(r?.dso_dias),
    dpo_dias:                  numOrNull(r?.dpo_dias),
    ccc_dias:                  numOrNull(r?.ccc_dias),
    working_capital_ratio:     numOrNull(r?.working_capital_ratio),
    burn_rate_mensal:          numOrNull(r?.burn_rate_mensal),
    runway_meses:              numOrNull(r?.runway_meses),
    cash_flow_30d:             numOrNull(r?.cash_flow_30d),
    period:                    String(r?.period ?? period),
  };
};

export const getCommercialIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<CommercialIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_commercial_indicators', period);
  return {
    pedidos_periodo:          num(r?.pedidos_periodo),
    receita_periodo:          num(r?.receita_periodo),
    ticket_medio:             num(r?.ticket_medio),
    clientes_unicos:          num(r?.clientes_unicos),
    clientes_novos:           num(r?.clientes_novos),
    clientes_recorrentes:     num(r?.clientes_recorrentes),
    recencia_media_dias:      num(r?.recencia_media_dias),
    frequencia_media_mensal:  num(r?.frequencia_media_mensal),
    churn_60d_perc:           numOrNull(r?.churn_60d_perc),
    crescimento_receita_perc: numOrNull(r?.crescimento_receita_perc),
    win_rate_perc:            numOrNull(r?.win_rate_perc),
    ciclo_venda_dias:         numOrNull(r?.ciclo_venda_dias),
    nrr_perc:                 numOrNull(r?.nrr_perc),
    clv:                      numOrNull(r?.clv),
    checkout_conversion_perc: numOrNull(r?.checkout_conversion_perc),
    nps:                      numOrNull(r?.nps),
    period:                   String(r?.period ?? period),
  };
};

export const getInventoryIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<InventoryIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_inventory_indicators', period);
  return {
    skus_ativos:                  num(r?.skus_ativos),
    skus_total:                   num(r?.skus_total),
    quantidade_vendida_periodo:   num(r?.quantidade_vendida_periodo),
    receita_skus_periodo:         num(r?.receita_skus_periodo),
    giro_estimado:                numOrNull(r?.giro_estimado),
    ticket_medio_sku:             num(r?.ticket_medio_sku),
    cobertura_top20_perc:         numOrNull(r?.cobertura_top20_perc),
    stockout_rate_perc:           numOrNull(r?.stockout_rate_perc),
    crescimento_quantidade_perc:  numOrNull(r?.crescimento_quantidade_perc),
    dio_dias:                     numOrNull(r?.dio_dias),
    cobertura_dias:               numOrNull(r?.cobertura_dias),
    fill_rate_perc:               numOrNull(r?.fill_rate_perc),
    sell_through_perc:            numOrNull(r?.sell_through_perc),
    gmroi:                        numOrNull(r?.gmroi),
    acuracidade_perc:             numOrNull(r?.acuracidade_perc),
    period:                       String(r?.period ?? period),
  };
};

export const getSupplyIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<SupplyIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_supply_indicators', period);
  return {
    rfqs_abertas:             num(r?.rfqs_abertas),
    rfqs_enviadas:            num(r?.rfqs_enviadas),
    rfqs_respondidas:         num(r?.rfqs_respondidas),
    taxa_resposta_perc:       numOrNull(r?.taxa_resposta_perc),
    tempo_resposta_medio_h:   numOrNull(r?.tempo_resposta_medio_h),
    pos_aprovadas:            num(r?.pos_aprovadas),
    pos_pendentes_aprovacao:  num(r?.pos_pendentes_aprovacao),
    spend_periodo:            num(r?.spend_periodo),
    fornecedores_ativos:      num(r?.fornecedores_ativos),
    concentracao_top_perc:    numOrNull(r?.concentracao_top_perc),
    cycle_time_medio_h:       numOrNull(r?.cycle_time_medio_h),
    cost_savings_perc:        numOrNull(r?.cost_savings_perc),
    ppv:                      numOrNull(r?.ppv),
    otif_perc:                numOrNull(r?.otif_perc),
    lead_time_medio_dias:     numOrNull(r?.lead_time_medio_dias),
    maverick_spend_perc:      numOrNull(r?.maverick_spend_perc),
    spend_under_management_perc: numOrNull(r?.spend_under_management_perc),
    period:                   String(r?.period ?? period),
  };
};

export const getMarketingIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<MarketingIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_marketing_indicators', period);
  return {
    novos_clientes_periodo:    num(r?.novos_clientes_periodo),
    receita_novos_clientes:    num(r?.receita_novos_clientes),
    conversao_campanha_perc:   numOrNull(r?.conversao_campanha_perc),
    engajamento_whatsapp_perc: numOrNull(r?.engajamento_whatsapp_perc),
    taxa_optout_perc:          numOrNull(r?.taxa_optout_perc),
    cac:                       numOrNull(r?.cac),
    ltv_cac_ratio:             numOrNull(r?.ltv_cac_ratio),
    roas:                      numOrNull(r?.roas),
    ctr_perc:                  numOrNull(r?.ctr_perc),
    cac_payback_meses:         numOrNull(r?.cac_payback_meses),
    share_of_voice_perc:       numOrNull(r?.share_of_voice_perc),
    period:                    String(r?.period ?? period),
  };
};

export const getAdminIndicators = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<AdminIndicators> => {
  const r = await callDimensionRpc<Record<string, unknown>>('get_admin_indicators', period);
  return {
    aprovacoes_pendentes:    num(r?.aprovacoes_pendentes),
    lead_time_aprovacao_h:   numOrNull(r?.lead_time_aprovacao_h),
    sla_aprovacao_perc:      numOrNull(r?.sla_aprovacao_perc),
    documentos_pendentes:    num(r?.documentos_pendentes),
    cobertura_rotinas_perc:  numOrNull(r?.cobertura_rotinas_perc),
    frescor_dados_h:         numOrNull(r?.frescor_dados_h),
    audit_coverage_perc:     numOrNull(r?.audit_coverage_perc),
    period:                  String(r?.period ?? period),
  };
};

export const DIMENSION_RPC: Record<DimensionKey, (period: PeriodType | StandardPeriod | string) => Promise<unknown>> = {
  finance:    getFinanceIndicators,
  commercial: getCommercialIndicators,
  inventory:  getInventoryIndicators,
  supply:     getSupplyIndicators,
  marketing:  getMarketingIndicators,
  admin:      getAdminIndicators,
};

// ──────────────────────────────────────────────────────────────────────────
// §6.2 Commercial — list/groupby KPIs
// ──────────────────────────────────────────────────────────────────────────

export interface RevenueByChannelRow {
  channel: string;
  receita: number;
  pedidos: number;
  share_perc: number | null;
  period: string;
}

export const getCommercialRevenueByChannel = async (
  period: PeriodType | StandardPeriod | string = '30d',
): Promise<RevenueByChannelRow[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_commercial_revenue_by_channel', { p_period: period });
  if (error) throw new Error(`get_commercial_revenue_by_channel: ${error.message}`);
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    channel:    String(r?.channel ?? 'sem_canal'),
    receita:    num(r?.receita),
    pedidos:    num(r?.pedidos),
    share_perc: numOrNull(r?.share_perc),
    period:     String(r?.period ?? period),
  }));
};

export interface TopClientRow {
  cliente_id: number;
  nome: string | null;
  receita: number;
  pedidos: number;
  share_perc: number | null;
  period: string;
}

export const getCommercialTopClients = async (
  period: PeriodType | StandardPeriod | string = '30d',
  limit = 10,
): Promise<TopClientRow[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_commercial_top_clients', { p_period: period, p_limit: limit });
  if (error) throw new Error(`get_commercial_top_clients: ${error.message}`);
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    cliente_id: num(r?.cliente_id),
    nome:       r?.nome == null ? null : String(r.nome),
    receita:    num(r?.receita),
    pedidos:    num(r?.pedidos),
    share_perc: numOrNull(r?.share_perc),
    period:     String(r?.period ?? period),
  }));
};

// ──────────────────────────────────────────────────────────────────────────
// §6 KPI Catalog (public.list_kpi_catalog) — single source of truth for the
// labels, formulas, tier-gates and data_status displayed on the dashboard.
// ──────────────────────────────────────────────────────────────────────────

export type KpiUnit = 'number' | 'currency' | 'percent' | 'days' | 'hours' | 'ratio' | 'count';
export type KpiDataStatus = 'live' | 'proxy' | 'external' | 'pending_data';
export type KpiTier = 'BASIC' | 'SME' | 'PRO' | 'PREMIUM' | 'ENTERPRISE' | 'ADMIN';

export interface KpiCatalogEntry {
  slug: string;
  dimension: DimensionKey;
  label: string;
  formula: string;
  unit: KpiUnit;
  is_leading: boolean;
  tier_required: KpiTier;
  data_status: KpiDataStatus;
  rpc_column: string | null;
  description: string | null;
  references_url: string | null;
  sort_order: number;
  is_enabled: boolean;
}

export interface DashboardKpiSlot {
  dimension: DimensionKey;
  slot_index: number;
  slug: string;
  label: string;
  unit: KpiUnit;
  formula: string;
  data_status: KpiDataStatus;
  tier_required: KpiTier;
  is_enabled: boolean;
}

export const listKpiCatalog = async (
  dimension: DimensionKey | null = null,
  onlyEnabled = true,
): Promise<KpiCatalogEntry[]> => {
  const { data, error } = await supabase.rpc('list_kpi_catalog', {
    p_dimension:    dimension,
    p_only_enabled: onlyEnabled,
  });
  if (error) throw new Error(`list_kpi_catalog: ${error.message}`);
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    slug:           String(r?.slug),
    dimension:      String(r?.dimension) as DimensionKey,
    label:          String(r?.label),
    formula:        String(r?.formula),
    unit:           (String(r?.unit) as KpiUnit) ?? 'number',
    is_leading:     Boolean(r?.is_leading),
    tier_required:  (String(r?.tier_required) as KpiTier) ?? 'BASIC',
    data_status:    (String(r?.data_status) as KpiDataStatus) ?? 'live',
    rpc_column:     r?.rpc_column == null ? null : String(r.rpc_column),
    description:    r?.description == null ? null : String(r.description),
    references_url: r?.references_url == null ? null : String(r.references_url),
    sort_order:     num(r?.sort_order),
    is_enabled:     Boolean(r?.is_enabled),
  }));
};

export const setClientDimensionKpis = async (
  dimension: DimensionKey,
  slugs: string[],
): Promise<Array<{ dimension: DimensionKey; slot_index: number; kpi_slug: string }>> => {
  const { data, error } = await supabase.rpc('set_client_dimension_kpis', {
    p_dimension: dimension,
    p_slugs: slugs,
  });
  if (error) throw new Error(`set_client_dimension_kpis: ${error.message}`);
  return ((data ?? []) as Array<Record<string, unknown>>).map((r) => ({
    dimension: String(r?.dimension) as DimensionKey,
    slot_index: num(r?.slot_index),
    kpi_slug: String(r?.kpi_slug),
  }));
};

export const getMyDashboardKpis = async (): Promise<DashboardKpiSlot[]> => {
  const { data, error } = await supabase.rpc('get_my_dashboard_kpis');
  if (error) throw new Error(`get_my_dashboard_kpis: ${error.message}`);
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
  }));
};

// ──────────────────────────────────────────────────────────────────────────
// Phase 3B (C3.1, C3.2) — Inbox helpers
// ─────────────────────────────────────────────────────────────────────────

export interface InboxThread {
  contact_id: string;
  channel: 'whatsapp' | 'gmail';
  external_id: string;
  display_name: string | null;
  last_message_preview: string | null;
  last_direction: 'inbound' | 'outbound' | null;
  last_status: string | null;
  last_message_at: string | null;
  unread_count: number;
  message_count: number;
}

export interface InboxMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  status: string;
  body: string;
  sent_at: string | null;
  created_at: string;
  metadata: Record<string, unknown> | null;
}

const _inboxBase = (): string => {
  const baseUrl =
    (import.meta as { env?: Record<string, string | undefined> }).env
      ?.VITE_TOOL_POOL_API_URL ?? '';
  if (!baseUrl) throw new Error('VITE_TOOL_POOL_API_URL não configurada.');
  return baseUrl.replace(/\/$/, '');
};

const _inboxFetch = async <T>(
  path: string,
  init: RequestInit = {},
): Promise<T> => {
  const { data: sessionData } = await supabase.auth.getSession();
  const token = sessionData?.session?.access_token;
  if (!token) throw new Error('Sessão expirada — faça login novamente.');

  const resp = await fetch(`${_inboxBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Inbox API ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
};

export const listInboxThreads = async (limit = 50): Promise<InboxThread[]> => {
  const data = await _inboxFetch<{ threads: InboxThread[] }>(
    `/integrations/inbox/threads?limit=${limit}`,
  );
  return data.threads ?? [];
};

export const listThreadMessages = async (
  contactId: string,
  limit = 100,
): Promise<InboxMessage[]> => {
  const data = await _inboxFetch<{ messages: InboxMessage[] }>(
    `/integrations/inbox/threads/${contactId}/messages?limit=${limit}`,
  );
  return data.messages ?? [];
};

export interface DraftReplyResponse {
  message_id: string;
  draft_text: string;
  channel: string;
}

export const draftInboxReply = async (
  contactId: string,
  hint?: string,
): Promise<DraftReplyResponse> =>
  _inboxFetch<DraftReplyResponse>('/integrations/inbox/threads/draft', {
    method: 'POST',
    body: JSON.stringify({ contact_id: contactId, hint }),
  });

export interface SendReplyResponse {
  status: 'pending_approval' | 'sent';
  approval_id?: string;
  external_id?: string;
}

export const sendInboxReply = async (
  messageId: string,
  editedBody?: string,
): Promise<SendReplyResponse> =>
  _inboxFetch<SendReplyResponse>('/integrations/inbox/threads/send', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, edited_body: editedBody }),
  });

// ─────────────────────────────────────────────────────────────────────────
// Phase 4 (R4.3) — Reports helpers
// ─────────────────────────────────────────────────────────────────────────

export type ReportFormat = 'markdown' | 'pdf' | 'xlsx' | 'gdoc' | 'gsheet';
export type ReportCadence = 'daily' | 'weekly' | 'monthly';
export type ReportStatus = 'pending' | 'running' | 'success' | 'failed';

export interface ReportTemplate {
  id: string;
  title: string;
  description: string;
  domain: string;
  default_period: string;
  default_format: ReportFormat;
  tier_required: string;
  sections: string[];
}

export interface ReportRun {
  id: string;
  template_id: string;
  period: string;
  format: ReportFormat;
  status: ReportStatus;
  output_url: string | null;
  output_metadata: Record<string, unknown> | null;
  error_message: string | null;
  schedule_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface ReportSchedule {
  id: string;
  template_id: string;
  period: string;
  format: ReportFormat;
  cadence: ReportCadence;
  enabled: boolean;
  notify_channel: 'app' | 'email' | 'whatsapp';
  last_run_at: string | null;
  next_run_at: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface GenerateReportResponse {
  run_id: string;
  status: ReportStatus;
  template_id: string;
  format: ReportFormat;
  period: string;
  output_url: string | null;
  output_metadata: Record<string, unknown> | null;
}

export interface ReportPayload {
  run_id: string;
  format: ReportFormat;
  mime_type: string;
  filename: string;
  size_bytes: number;
  payload_b64: string;
}

const _reportsBase = (): string => {
  const baseUrl =
    (import.meta as { env?: Record<string, string | undefined> }).env
      ?.VITE_TOOL_POOL_API_URL ?? '';
  if (!baseUrl) throw new Error('VITE_TOOL_POOL_API_URL não configurada.');
  return baseUrl.replace(/\/$/, '');
};

const _reportsFetch = async <T>(
  path: string,
  init: RequestInit = {},
): Promise<T> => {
  const { data: sessionData } = await supabase.auth.getSession();
  const token = sessionData?.session?.access_token;
  if (!token) throw new Error('Sessão expirada — faça login novamente.');

  const resp = await fetch(`${_reportsBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Reports API ${resp.status}: ${text}`);
  }
  return (await resp.json()) as T;
};

export const listReportTemplates = async (): Promise<ReportTemplate[]> => {
  const data = await _reportsFetch<{ templates: ReportTemplate[] }>(
    '/integrations/reports/templates',
  );
  return data.templates ?? [];
};

export const listReportRuns = async (limit = 50): Promise<ReportRun[]> => {
  const data = await _reportsFetch<{ runs: ReportRun[] }>(
    `/integrations/reports/runs?limit=${limit}`,
  );
  return data.runs ?? [];
};

export const fetchReportPayload = async (
  runId: string,
): Promise<ReportPayload> =>
  _reportsFetch<ReportPayload>(`/integrations/reports/runs/${runId}/payload`);

export const generateReport = async (
  templateId: string,
  options: { period?: string; format?: ReportFormat } = {},
): Promise<GenerateReportResponse> =>
  _reportsFetch<GenerateReportResponse>('/integrations/reports/generate', {
    method: 'POST',
    body: JSON.stringify({
      template_id: templateId,
      period: options.period,
      format: options.format,
    }),
  });

export const listReportSchedules = async (): Promise<ReportSchedule[]> => {
  const data = await _reportsFetch<{ schedules: ReportSchedule[] }>(
    '/integrations/reports/schedules',
  );
  return data.schedules ?? [];
};

export interface UpsertScheduleInput {
  template_id: string;
  period?: string;
  format?: ReportFormat;
  cadence?: ReportCadence;
  notify_channel?: 'app' | 'email' | 'whatsapp';
  enabled?: boolean;
  config?: Record<string, unknown>;
}

export const upsertReportSchedule = async (
  input: UpsertScheduleInput,
): Promise<ReportSchedule> =>
  _reportsFetch<ReportSchedule>('/integrations/reports/schedules', {
    method: 'POST',
    body: JSON.stringify({
      template_id: input.template_id,
      period: input.period ?? '30d',
      format: input.format ?? 'pdf',
      cadence: input.cadence ?? 'monthly',
      notify_channel: input.notify_channel ?? 'app',
      enabled: input.enabled ?? true,
      config: input.config ?? {},
    }),
  });

export const disableReportSchedule = async (
  scheduleId: string,
): Promise<ReportSchedule> =>
  _reportsFetch<ReportSchedule>(
    `/integrations/reports/schedules/${scheduleId}/disable`,
    { method: 'POST' },
  );

/**
 * Convenience helper: triggers a download in the browser for runs whose
 * payload is stored inline (markdown/pdf/xlsx). Google Doc/Sheet runs
 * should redirect to `output_url` instead.
 */
export const downloadReportRun = async (run: ReportRun): Promise<void> => {
  if (run.output_url && (run.format === 'gdoc' || run.format === 'gsheet')) {
    window.open(run.output_url, '_blank');
    return;
  }
  const payload = await fetchReportPayload(run.id);
  const binary = atob(payload.payload_b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: payload.mime_type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = payload.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

export interface ActivationStatusSnapshot {
  client_id: string;
  has_synced_connector: boolean;
  pending_approvals: number;
}

/**
 * Small activation snapshot for celebratory/coach-mark UX.
 */
export const getActivationStatusSnapshot = async (): Promise<ActivationStatusSnapshot> => {
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError || !user) {
    throw new Error('Usuário não autenticado');
  }

  let clientId = user.app_metadata?.client_id as string | undefined;
  if (!clientId) {
    const { data: tenant, error: tenantError } = await supabase
      .from('clientes_blu')
      .select('client_id')
      .eq('external_user_id', user.id)
      .maybeSingle();
    if (tenantError) {
      throw new Error(`Falha ao resolver tenant: ${tenantError.message}`);
    }
    clientId = (tenant?.client_id as string | undefined) ?? undefined;
  }

  if (!clientId) {
    throw new Error('Tenant não encontrado para usuário atual');
  }

  const [connectorRes, approvalsRes] = await Promise.all([
    supabase
      .from('client_data_sources')
      .select('id')
      .eq('client_id', clientId)
      .not('last_synced_at', 'is', null)
      .limit(1),
    supabase
      .from('approval_requests')
      .select('id')
      .eq('client_id', clientId)
      .eq('status', 'pending'),
  ]);

  if (connectorRes.error) {
    throw new Error(`Falha ao carregar conectores: ${connectorRes.error.message}`);
  }
  if (approvalsRes.error) {
    throw new Error(`Falha ao carregar aprovações: ${approvalsRes.error.message}`);
  }

  return {
    client_id: clientId,
    has_synced_connector: Boolean((connectorRes.data ?? []).length > 0),
    pending_approvals: (approvalsRes.data ?? []).length,
  };
};
