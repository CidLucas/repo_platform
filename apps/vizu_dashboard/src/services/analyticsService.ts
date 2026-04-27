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

// Corresponds to the Pydantic 'PedidoItem' (used in PedidosOverviewResponse)
export interface PedidoItem {
  order_id: string;
  data_transacao: string; // ISO date string
  id_cliente: string;
  ticket_pedido: number;
  qtd_produtos: number;
}

// Corresponds to the Pydantic 'PedidoItemDetalhe' (used in PedidoDetailResponse)
export interface PedidoItemDetalhe {
  raw_product_description: string;
  descricao_produto?: string; // some responses use this key instead
  quantidade: number;
  valor_unitario: number;
  valor_total_emitter: number;
}

// Corresponds to the Pydantic 'PedidosOverviewResponse'
export interface PedidosOverviewResponse {
  scorecard_ticket_medio_por_pedido: number;
  scorecard_qtd_media_produtos_por_pedido: number;
  scorecard_taxa_recorrencia_clientes_perc: number;
  scorecard_recencia_media_entre_pedidos_dias: number;
  chart_pedidos_no_tempo: ChartDataPoint[];
  ranking_pedidos_por_regiao: ChartDataPoint[];
  ultimos_pedidos: PedidoItem[];
}

// Customer metrics payload shape (used by useIndicators / HomePage)
export interface CustomerMetricsResponse {
  total_active: number;
  new_customers: number;
  returning_customers: number;
  avg_lifetime_value: number;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}

// Product metrics payload shape (used by useIndicators / HomePage)
export interface ProductMetricsResponse {
  total_sold: number;
  unique_products: number;
  top_sellers: { name: string; quantity: number; revenue: number }[];
  low_stock_alerts: number;
  avg_price: number;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}

// Order metrics payload shape (used by PedidosPage)
export interface OrderMetricsResponse {
  total: number;
  revenue: number;
  avg_order_value: number;
  growth_rate: number | null;
  /**
   * Sourced from `analytics_v2.get_order_status_breakdown` →
   * `fato_transacoes.status` (real values like `valid`, `review`, `invalid`).
   */
  by_status: Record<string, number>;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}

// Period filter shared across pedidos RPCs.
// Legacy values (week|month|quarter|year) are kept for backwards compatibility
// with existing pages (PedidosPage, useDashboardIndicators). New dimension
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

// Pedidos overview scorecards (analytics_v2.get_pedidos_overview_scorecards)
export interface PedidosOverviewScorecards {
  qtdMediaProdutos: number;
  taxaRecorrencia: number;
  recenciaMediaDias: number;
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

// Corresponds to the Pydantic 'PedidoDetailResponse'
export interface PedidoDetailResponse {
  order_id: string;
  status_pedido: string;
  total_pedido: number;
  dados_cliente: CadastralData;
  itens_pedido: PedidoItemDetalhe[];
}

// Corresponds to the Pydantic 'RankingItem'
export interface RankingItem {
  nome: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos_unicos: number;
  primeira_venda: string; // ISO date string
  ultima_venda: string; // ISO date string
  ticket_medio: number;
  qtd_media_por_pedido: number;
  frequencia_pedidos_mes: number;
  recencia_dias: number;
  valor_unitario_medio: number;
  cluster_score: number;
  cluster_tier: string;
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

// Corresponds to the Pydantic 'ProdutoRankingReceita'
export interface ProdutoRankingReceita {
  nome: string;
  receita_total: number;
  valor_unitario_medio: number;
  quantidade_total: number;
  num_pedidos?: number;
  cluster_tier: string;
}

// Corresponds to the Pydantic 'ProdutoRankingVolume'
export interface ProdutoRankingVolume {
  nome: string;
  quantidade_total: number;
  valor_unitario_medio: number;
  receita_total: number;
  num_pedidos?: number;
  cluster_tier: string;
}

// Corresponds to the Pydantic 'ProdutoRankingTicket'
export interface ProdutoRankingTicket {
  nome: string;
  ticket_medio: number;
  valor_unitario_medio: number;
  quantidade_total: number;
  num_pedidos?: number;
  cluster_tier: string;
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

// Corresponds to the Pydantic 'FornecedoresOverviewResponse'
export interface FornecedoresOverviewResponse {
  scorecard_total_fornecedores: number;
  scorecard_crescimento_percentual?: number | null;
  // Tier breakdowns
  scorecard_tier_a_count?: number;
  scorecard_tier_b_count?: number;
  scorecard_tier_c_count?: number;
  scorecard_tier_d_count?: number;
  scorecard_tier_a_receita?: number;
  scorecard_tier_b_receita?: number;
  scorecard_tier_c_receita?: number;
  scorecard_tier_d_receita?: number;
  scorecard_tier_a_ticket_medio?: number;
  scorecard_tier_b_ticket_medio?: number;
  scorecard_tier_c_ticket_medio?: number;
  scorecard_tier_d_ticket_medio?: number;
  chart_fornecedores_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[]; // Monthly revenue fluctuation
  chart_ticketmedio_no_tempo: ChartDataPoint[]; // Monthly avg ticket fluctuation
  chart_quantidade_no_tempo: ChartDataPoint[]; // Monthly volume (kg/tons) fluctuation
  chart_fornecedores_por_regiao: ChartDataPoint[];
  chart_cohort_fornecedores: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  ranking_por_qtd_media: RankingItem[];
  ranking_por_ticket_medio: RankingItem[];
  ranking_por_frequencia: RankingItem[];
  ranking_produtos_mais_vendidos: ProdutoRankingReceita[];
}

// Corresponds to the Pydantic 'CadastralData'.  In practice the
// object can carry a variety of attributes depending on the endpoint –
// clients use the same type for orders, suppliers, etc.  We therefore
// include the fields our UI actually reads (name/cnpj/endereco) as
// optional in addition to the generic emitter/receiver properties.
export interface CadastralData {
  name?: string;
  cnpj?: string;
  endereco?: string;
  emitter_nome?: string;
  emitter_cnpj?: string;
  emitter_telefone?: string;
  emitter_estado?: string;
  emitter_cidade?: string;
  receiver_nome?: string;
  receiver_cnpj?: string;
  receiver_telefone?: string;
  receiver_estado?: string;
  receiver_cidade?: string;
}

// Corresponds to the Pydantic 'FornecedorDetailResponse'
export interface FornecedorDetailResponse {
  dados_cadastrais: CadastralData;
  rankings_internos: {
    clientes_por_receita: RankingItem[];
    produtos_por_receita: RankingItem[];
    regioes_por_receita: RankingItem[];
  };
  charts: {
    receita_no_tempo: ChartDataPoint[];
  };
}

// Corresponds to the Pydantic 'ClientesOverviewResponse'
export interface ClientesOverviewResponse {
  scorecard_total_clientes: number;
  scorecard_ticket_medio_geral: number;
  scorecard_frequencia_media_geral: number;
  scorecard_crescimento_percentual?: number | null;
  // Tier breakdowns
  scorecard_tier_a_count?: number;
  scorecard_tier_b_count?: number;
  scorecard_tier_c_count?: number;
  scorecard_tier_d_count?: number;
  scorecard_tier_a_receita?: number;
  scorecard_tier_b_receita?: number;
  scorecard_tier_c_receita?: number;
  scorecard_tier_d_receita?: number;
  scorecard_tier_a_ticket_medio?: number;
  scorecard_tier_b_ticket_medio?: number;
  scorecard_tier_c_ticket_medio?: number;
  scorecard_tier_d_ticket_medio?: number;
  chart_clientes_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[]; // Monthly revenue from customers
  chart_ticketmedio_no_tempo: ChartDataPoint[]; // Monthly average ticket from customers
  chart_quantidade_no_tempo: ChartDataPoint[]; // Monthly volume purchased by customers
  chart_clientes_por_regiao: ChartDataPoint[];
  chart_cohort_clientes: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  ranking_por_ticket_medio: RankingItem[];
  ranking_por_qtd_pedidos: RankingItem[];
  ranking_por_cluster_vizu: RankingItem[];
}

// Corresponds to the Pydantic 'ClienteDetailResponse'
export interface ClienteDetailResponse {
  dados_cadastrais: CadastralData;
  scorecards: RankingItem | null;
  rankings_internos: {
    mix_de_produtos_por_receita: RankingItem[];
  };
}

// Corresponds to the Pydantic 'ProdutosOverviewResponse'
export interface ProdutosOverviewResponse {
  scorecard_total_itens_unicos: number;
  scorecard_receita_total?: number;  // Total revenue from ALL products
  scorecard_quantidade_total?: number;  // Total quantity from ALL products
  scorecard_ticket_medio?: number;  // Avg ticket (receita/quantidade)
  scorecard_crescimento_percentual?: number;  // Growth % vs previous month
  // Tier counts (from ALL products)
  scorecard_tier_a_count?: number;
  scorecard_tier_b_count?: number;
  scorecard_tier_c_count?: number;
  scorecard_tier_d_count?: number;
  // Tier receita (from ALL products)
  scorecard_tier_a_receita?: number;
  scorecard_tier_b_receita?: number;
  scorecard_tier_c_receita?: number;
  scorecard_tier_d_receita?: number;
  // Tier quantidade (from ALL products)
  scorecard_tier_a_quantidade?: number;
  scorecard_tier_b_quantidade?: number;
  scorecard_tier_c_quantidade?: number;
  scorecard_tier_d_quantidade?: number;
  // Tier ticket médio (from ALL products)
  scorecard_tier_a_ticket_medio?: number;
  scorecard_tier_b_ticket_medio?: number;
  scorecard_tier_c_ticket_medio?: number;
  scorecard_tier_d_ticket_medio?: number;
  // Price variation
  scorecard_variacao_preco_percentual?: number;  // Avg unit price change vs previous month
  // Top price variation product
  top_variacao_produto_nome?: string | null;  // Product with highest price variation
  top_variacao_produto_percentual?: number;  // Variation % of that product
  top_variacao_produto_direcao?: string;  // 'up', 'down', or 'stable'
  // Charts
  chart_produtos_no_tempo: ChartDataPoint[];
  chart_receita_no_tempo: ChartDataPoint[]; // Monthly revenue from products
  chart_quantidade_no_tempo: ChartDataPoint[]; // Monthly volume of products sold
  ranking_por_receita: ProdutoRankingReceita[];
  ranking_por_volume: ProdutoRankingVolume[];
  ranking_por_ticket_medio: ProdutoRankingTicket[];
}

// Corresponds to the Pydantic 'ProdutoDetailResponse'
export interface ProdutoDetailResponse {
  nome_produto: string;
  scorecards: RankingItem | null;
  charts: {
    segmentos_de_clientes: ChartDataPoint[];
  };
  rankings_internos: {
    clientes_por_receita: RankingItem[];
    regioes_por_receita: RankingItem[];
  };
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

// Pedidos API calls (overview)
export const getPedidosOverview = async (): Promise<PedidosOverviewResponse> => {
  // Get ultimos_pedidos from view
  const { data: pedidos, error: pedidosError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_ultimos_pedidos')
    .select('*')
    .order('ordem', { ascending: true })
    .limit(50);

  throwIfError(pedidos, pedidosError);

  // Get series temporal for chart_pedidos_no_tempo
  const { data: series, error: seriesError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .eq('tipo_grafico', 'pedidos')
    .eq('dimensao', 'total')
    .order('data_periodo', { ascending: true });

  throwIfError(series, seriesError);

  // Get regional distribution for ranking
  const { data: regional, error: regionalError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_distribuicao_regional')
    .select('*')
    .eq('tipo_grafico', 'pedidos')
    .eq('dimensao', 'regiao')
    .order('total', { ascending: false });

  throwIfError(regional, regionalError);

  // Get scorecards from dim_clientes aggregations
  const { data: resumo, error: resumoError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .limit(1)
    .maybeSingle();

  if (resumoError) console.warn('[Pedidos] v_resumo_dashboard error:', resumoError.message);
  const dashboard = resumo || { total_pedidos: 0, receita_total: 0, ticket_medio: 0 };

  // Calculate scorecards
  const totalPedidos = dashboard.total_pedidos || 0;
  const receitaTotal = Number(dashboard.receita_total) || 0;
  const ticketMedio = totalPedidos > 0 ? receitaTotal / totalPedidos : 0;

  // Real recurrence / recency / qty-per-order scorecards from RPC.
  // Soft-fail to zeros so the page still renders if the RPC errors.
  let realScorecards: PedidosOverviewScorecards = {
    qtdMediaProdutos: 0,
    taxaRecorrencia: 0,
    recenciaMediaDias: 0,
  };
  try {
    realScorecards = await getPedidosOverviewScorecards();
  } catch (err) {
    console.warn('[Pedidos] get_pedidos_overview_scorecards error:', err);
  }

  return {
    scorecard_ticket_medio_por_pedido: ticketMedio,
    scorecard_qtd_media_produtos_por_pedido: realScorecards.qtdMediaProdutos,
    scorecard_taxa_recorrencia_clientes_perc: realScorecards.taxaRecorrencia,
    scorecard_recencia_media_entre_pedidos_dias: realScorecards.recenciaMediaDias,
    chart_pedidos_no_tempo: (series || []).map(s => ({
      name: s.periodo,
      total: Number(s.total) || 0,
    })),
    ranking_pedidos_por_regiao: (regional || []).map(r => ({
      name: r.estado || r.regiao || 'N/A',
      total: Number(r.total) || 0,
      percentual: Number(r.percentual) || 0,
    })),
    ultimos_pedidos: (pedidos || []).map(p => ({
      order_id: p.pedido_id,
      data_transacao: p.data_transacao,
      id_cliente: p.cliente_cpf_cnpj || '',
      ticket_pedido: Number(p.valor_pedido) || 0,
      qtd_produtos: Number(p.qtd_produtos) || 0,
    })),
  };
};

// Pedido API call (details)
export const getPedidoDetails = async (order_id: string): Promise<PedidoDetailResponse> => {
  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      documento,
      valor,
      quantidade,
      valor_unitario,
      status,
      dim_clientes(nome, cpf_cnpj, telefone, endereco_uf, endereco_cidade),
      dim_inventory!inventory_id(nome),
      dim_datas!data_competencia_id(data)
    `)
    .eq('documento', order_id);

  throwIfError(transacoes, error);

  const firstItem = transacoes?.[0];
  const cliente = firstItem?.dim_clientes as unknown as Record<string, string> | null;

  // Pick the most-common non-null status across the order's rows; fall back to first non-null.
  const statusCounts = (transacoes || []).reduce((acc, v) => {
    const s = (v as { status?: string | null }).status;
    if (s) acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>);
  const statusPedido =
    Object.entries(statusCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'unknown';

  return {
    order_id,
    status_pedido: statusPedido,
    total_pedido: transacoes?.reduce((sum, v) => sum + Number(v.valor || 0), 0) || 0,
    dados_cliente: {
      receiver_nome: cliente?.nome,
      receiver_cnpj: cliente?.cpf_cnpj,
      receiver_telefone: cliente?.telefone,
      receiver_estado: cliente?.endereco_uf,
      receiver_cidade: cliente?.endereco_cidade,
    },
    itens_pedido: (transacoes || []).map(v => ({
      raw_product_description: (v.dim_inventory as unknown as Record<string, string> | null)?.nome || 'N/A',
      quantidade: Number(v.quantidade) || 0,
      valor_unitario: Number(v.valor_unitario) || (Number(v.valor) / Number(v.quantidade)) || 0,
      valor_total_emitter: Number(v.valor) || 0,
    })),
  };
};

// Fornecedores API calls (overview)

export const getFornecedores = async (_period: string = 'all'): Promise<FornecedoresOverviewResponse> => {
  // Fetch fornecedores, series, and regional in parallel
  const [fornecedoresRes, seriesRes, regionalRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_fornecedores').select('*').order('receita_total', { ascending: false }),
    supabase.schema(ANALYTICS_SCHEMA).from('v_series_temporal').select('*').eq('tipo_grafico', 'fornecedores').order('data_periodo', { ascending: true }),
    supabase.schema(ANALYTICS_SCHEMA).from('v_distribuicao_regional').select('*').eq('tipo_grafico', 'pedidos_por_regiao').order('total', { ascending: false }),
  ]);

  throwIfError(fornecedoresRes.data, fornecedoresRes.error);
  const fornecedores = fornecedoresRes.data || [];
  const allSeries = seriesRes.data || [];
  const regional = regionalRes.data || [];

  // Split series by dimensao
  const seriesReceita = allSeries.filter(s => s.dimensao === 'receita');
  const seriesContagem = allSeries.filter(s => s.dimensao === 'contagem');
  const seriesQuantidade = allSeries.filter(s => s.dimensao === 'quantidade');

  // Compute ticket medio time series
  const seriesTicketMedio = seriesReceita.map((r, idx) => {
    const q = seriesQuantidade[idx] ? Number(seriesQuantidade[idx].total) : 0;
    const rv = Number(r.total) || 0;
    return { periodo: r.periodo, total: q > 0 ? Math.round(rv / q) : 0 };
  });

  const totalFornecedores = fornecedores.length;

  // Growth from series
  let crescimentoPercentual: number | null = null;
  if (seriesReceita.length >= 2) {
    const last = Number(seriesReceita[seriesReceita.length - 1].total) || 0;
    const prev = Number(seriesReceita[seriesReceita.length - 2].total) || 0;
    crescimentoPercentual = prev > 0 ? ((last - prev) / prev) * 100 : null;
  }

  // Tier aggregations
  const tiers = ['A', 'B', 'C', 'D'] as const;
  const tierData = Object.fromEntries(tiers.map(t => {
    const items = fornecedores.filter(f => String(f.nivel_cluster || '').toUpperCase() === t);
    const count = items.length;
    const receita = items.reduce((s, f) => s + (Number(f.receita_total) || 0), 0);
    const ticket = count > 0 ? receita / count : 0;
    return [t, { count, receita, ticket }];
  })) as Record<string, { count: number; receita: number; ticket: number }>;

  // Map fornecedores to RankingItem format
  const toRankingItem = (f: Record<string, unknown>): RankingItem => ({
    nome: String(f.nome || ''),
    receita_total: Number(f.receita_total) || 0,
    quantidade_total: 0,
    num_pedidos_unicos: Number(f.total_pedidos_recebidos) || 0,
    primeira_venda: String(f.data_primeira_transacao || ''),
    ultima_venda: String(f.data_ultima_transacao || ''),
    ticket_medio: Number(f.ticket_medio) || 0,
    qtd_media_por_pedido: 0,
    frequencia_pedidos_mes: Number(f.frequencia_mensal) || 0,
    recencia_dias: Number(f.dias_recencia) || 0,
    valor_unitario_medio: 0,
    cluster_score: Number(f.pontuacao_cluster) || 0,
    cluster_tier: String(f.nivel_cluster || 'N/A'),
  });

  return {
    scorecard_total_fornecedores: totalFornecedores,
    scorecard_crescimento_percentual: crescimentoPercentual,
    // Tier data
    scorecard_tier_a_count: tierData.A.count,
    scorecard_tier_b_count: tierData.B.count,
    scorecard_tier_c_count: tierData.C.count,
    scorecard_tier_d_count: tierData.D.count,
    scorecard_tier_a_receita: tierData.A.receita,
    scorecard_tier_b_receita: tierData.B.receita,
    scorecard_tier_c_receita: tierData.C.receita,
    scorecard_tier_d_receita: tierData.D.receita,
    scorecard_tier_a_ticket_medio: tierData.A.ticket,
    scorecard_tier_b_ticket_medio: tierData.B.ticket,
    scorecard_tier_c_ticket_medio: tierData.C.ticket,
    scorecard_tier_d_ticket_medio: tierData.D.ticket,
    chart_fornecedores_no_tempo: seriesContagem.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_receita_no_tempo: seriesReceita.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_ticketmedio_no_tempo: seriesTicketMedio.map(s => ({ name: s.periodo, total: s.total })),
    chart_quantidade_no_tempo: seriesQuantidade.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_fornecedores_por_regiao: regional.map(r => ({ name: r.estado || r.regiao, total: Number(r.total) })),
    chart_cohort_fornecedores: [],
    ranking_por_receita: fornecedores.slice(0, 20).map(toRankingItem),
    ranking_por_qtd_media: fornecedores.slice(0, 20).map(toRankingItem),
    ranking_por_ticket_medio: [...fornecedores].sort((a, b) => Number(b.ticket_medio) - Number(a.ticket_medio)).slice(0, 20).map(toRankingItem),
    ranking_por_frequencia: [...fornecedores].sort((a, b) => Number(b.frequencia_mensal) - Number(a.frequencia_mensal)).slice(0, 20).map(toRankingItem),
    ranking_produtos_mais_vendidos: [],
  };
};

// Fornecedor API call (details)
export const getFornecedor = async (nome_fornecedor: string): Promise<FornecedorDetailResponse> => {
  // Fetch fornecedor data + cross-entity rankings + time series in parallel
  // Use .limit(1) instead of .single() because multiple fornecedores can share the same name (different CNPJs)
  const [fornecedorRes, topClientsRes, topProductsRes, topRegionsRes, revenueSeriesRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_fornecedores').select('*').eq('nome', nome_fornecedor).limit(1).maybeSingle(),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_supplier_top_clients', { p_supplier_name: nome_fornecedor }),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_supplier_top_products', { p_supplier_name: nome_fornecedor }),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_supplier_top_regions', { p_supplier_name: nome_fornecedor }),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_supplier_revenue_series', { p_supplier_name: nome_fornecedor }),
  ]);

  if (fornecedorRes.error) throw new Error(fornecedorRes.error.message);
  const fornecedor = fornecedorRes.data;

  const toSimpleRanking = (item: Record<string, unknown>) => ({
    nome: String(item.nome || item.regiao || ''),
    receita_total: Number(item.receita_total) || 0,
  });

  return {
    dados_cadastrais: {
      emitter_nome: fornecedor?.nome,
      emitter_cnpj: fornecedor?.cnpj,
      emitter_telefone: fornecedor?.telefone,
      emitter_estado: fornecedor?.endereco_uf,
      emitter_cidade: fornecedor?.endereco_cidade,
    },
    rankings_internos: {
      clientes_por_receita: (topClientsRes.data || []).map(toSimpleRanking),
      produtos_por_receita: (topProductsRes.data || []).map(toSimpleRanking),
      regioes_por_receita: (topRegionsRes.data || []).map(toSimpleRanking),
    },
    charts: {
      receita_no_tempo: (revenueSeriesRes.data || []).map((s: Record<string, unknown>) => ({ name: String(s.periodo), total: Number(s.total) })),
    },
  };
};

// Clientes API calls (overview)

export const getClientes = async (_period: string = 'all'): Promise<ClientesOverviewResponse> => {
  // Fetch dim_clientes, series, and regional in parallel
  const [clientesRes, seriesRes, regionalRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_clientes').select('*').order('receita_total', { ascending: false }),
    supabase.schema(ANALYTICS_SCHEMA).from('v_series_temporal').select('*').eq('tipo_grafico', 'clientes').order('data_periodo', { ascending: true }),
    supabase.schema(ANALYTICS_SCHEMA).from('v_distribuicao_regional').select('*').eq('tipo_grafico', 'pedidos_por_regiao').order('total', { ascending: false }),
  ]);

  throwIfError(clientesRes.data, clientesRes.error);
  const clientes = clientesRes.data || [];
  const allSeries = seriesRes.data || [];
  const regional = regionalRes.data || [];

  // Split series by dimensao
  const seriesReceita = allSeries.filter(s => s.dimensao === 'receita');
  const seriesContagem = allSeries.filter(s => s.dimensao === 'contagem');
  const seriesQuantidade = allSeries.filter(s => s.dimensao === 'quantidade');

  // Compute ticket medio time series from receita / quantidade
  const seriesTicketMedio = seriesReceita.map((r, idx) => {
    const q = seriesQuantidade[idx] ? Number(seriesQuantidade[idx].total) : 0;
    const rv = Number(r.total) || 0;
    return { periodo: r.periodo, total: q > 0 ? Math.round(rv / q) : 0 };
  });

  const totalClientes = clientes.length;
  const receitaTotal = clientes.reduce((sum, c) => sum + Number(c.receita_total || 0), 0);
  const ticketMedio = totalClientes > 0 ? receitaTotal / totalClientes : 0;
  const frequenciaMedia = clientes.reduce((sum, c) => sum + Number(c.frequencia_mensal || 0), 0) / (totalClientes || 1);

  // Growth from series
  let crescimentoPercentual: number | null = null;
  if (seriesReceita.length >= 2) {
    const last = Number(seriesReceita[seriesReceita.length - 1].total) || 0;
    const prev = Number(seriesReceita[seriesReceita.length - 2].total) || 0;
    crescimentoPercentual = prev > 0 ? ((last - prev) / prev) * 100 : null;
  }

  // Tier aggregations
  const tiers = ['A', 'B', 'C', 'D'] as const;
  const tierData = Object.fromEntries(tiers.map(t => {
    const items = clientes.filter(c => String(c.nivel_cluster || '').toUpperCase() === t);
    const count = items.length;
    const receita = items.reduce((s, c) => s + (Number(c.receita_total) || 0), 0);
    const ticket = count > 0 ? receita / count : 0;
    return [t, { count, receita, ticket }];
  })) as Record<string, { count: number; receita: number; ticket: number }>;

  // Map clientes to RankingItem format
  const toRankingItem = (c: Record<string, unknown>): RankingItem => ({
    nome: String(c.nome || ''),
    receita_total: Number(c.receita_total) || 0,
    quantidade_total: Number(c.quantidade_total) || 0,
    num_pedidos_unicos: Number(c.total_pedidos) || 0,
    primeira_venda: String(c.data_primeira_compra || ''),
    ultima_venda: String(c.data_ultima_compra || ''),
    ticket_medio: Number(c.ticket_medio) || 0,
    qtd_media_por_pedido: 0,
    frequencia_pedidos_mes: Number(c.frequencia_mensal) || 0,
    recencia_dias: Number(c.dias_recencia) || 0,
    valor_unitario_medio: 0,
    cluster_score: Number(c.pontuacao_cluster) || 0,
    cluster_tier: String(c.nivel_cluster || 'N/A'),
  });

  return {
    scorecard_total_clientes: totalClientes,
    scorecard_ticket_medio_geral: ticketMedio,
    scorecard_frequencia_media_geral: frequenciaMedia,
    scorecard_crescimento_percentual: crescimentoPercentual,
    // Tier data
    scorecard_tier_a_count: tierData.A.count,
    scorecard_tier_b_count: tierData.B.count,
    scorecard_tier_c_count: tierData.C.count,
    scorecard_tier_d_count: tierData.D.count,
    scorecard_tier_a_receita: tierData.A.receita,
    scorecard_tier_b_receita: tierData.B.receita,
    scorecard_tier_c_receita: tierData.C.receita,
    scorecard_tier_d_receita: tierData.D.receita,
    scorecard_tier_a_ticket_medio: tierData.A.ticket,
    scorecard_tier_b_ticket_medio: tierData.B.ticket,
    scorecard_tier_c_ticket_medio: tierData.C.ticket,
    scorecard_tier_d_ticket_medio: tierData.D.ticket,
    chart_clientes_no_tempo: seriesContagem.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_receita_no_tempo: seriesReceita.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_ticketmedio_no_tempo: seriesTicketMedio.map(s => ({ name: s.periodo, total: s.total })),
    chart_quantidade_no_tempo: seriesQuantidade.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_clientes_por_regiao: regional.map(r => ({ name: r.estado || r.regiao, total: Number(r.total) })),
    chart_cohort_clientes: [],
    ranking_por_receita: clientes.slice(0, 20).map(toRankingItem),
    ranking_por_ticket_medio: [...clientes].sort((a, b) => Number(b.ticket_medio) - Number(a.ticket_medio)).slice(0, 20).map(toRankingItem),
    ranking_por_qtd_pedidos: [...clientes].sort((a, b) => Number(b.total_pedidos) - Number(a.total_pedidos)).slice(0, 20).map(toRankingItem),
    ranking_por_cluster_vizu: [...clientes].sort((a, b) => Number(b.pontuacao_cluster) - Number(a.pontuacao_cluster)).slice(0, 20).map(toRankingItem),
  };
};

// Cliente API call (details)
export const getCliente = async (nome_cliente: string): Promise<ClienteDetailResponse> => {
  // Fetch cliente data + cross-entity rankings in parallel
  // Use .limit(1) instead of .single() because multiple clientes can share the same name
  const [clienteRes, topProductsRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_clientes').select('*').eq('nome', nome_cliente).limit(1).maybeSingle(),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_client_top_products', { p_client_name: nome_cliente }),
  ]);

  if (clienteRes.error) throw new Error(clienteRes.error.message);
  const cliente = clienteRes.data;

  const scorecards: RankingItem | null = cliente ? {
    nome: cliente.nome,
    receita_total: Number(cliente.receita_total) || 0,
    quantidade_total: Number(cliente.quantidade_total) || 0,
    num_pedidos_unicos: Number(cliente.total_pedidos) || 0,
    primeira_venda: cliente.data_primeira_compra || '',
    ultima_venda: cliente.data_ultima_compra || '',
    ticket_medio: Number(cliente.ticket_medio) || 0,
    qtd_media_por_pedido: 0,
    frequencia_pedidos_mes: Number(cliente.frequencia_mensal) || 0,
    recencia_dias: Number(cliente.dias_recencia) || 0,
    valor_unitario_medio: 0,
    cluster_score: Number(cliente.pontuacao_cluster) || 0,
    cluster_tier: cliente.nivel_cluster || 'N/A',
  } : null;

  return {
    dados_cadastrais: {
      receiver_nome: cliente?.nome,
      receiver_cnpj: cliente?.cpf_cnpj,
      receiver_telefone: cliente?.telefone,
      receiver_estado: cliente?.endereco_uf,
      receiver_cidade: cliente?.endereco_cidade,
    },
    scorecards,
    rankings_internos: {
      mix_de_produtos_por_receita: (topProductsRes.data || []).map((item: Record<string, unknown>) => ({
        nome: String(item.nome || ''),
        receita_total: Number(item.receita_total) || 0,
      })),
    },
  };
};

// Produtos API calls (overview)

export const getProdutosOverview = async (_period: string = 'all'): Promise<ProdutosOverviewResponse> => {
  // Fetch dim_inventory + all produtos series in parallel
  const [produtosRes, seriesRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_inventory').select('*').order('receita_total', { ascending: false }),
    supabase.schema(ANALYTICS_SCHEMA).from('v_series_temporal').select('*').eq('tipo_grafico', 'produtos').order('data_periodo', { ascending: true }),
  ]);

  throwIfError(produtosRes.data, produtosRes.error);
  const produtos = produtosRes.data || [];
  const allSeries = seriesRes.data || [];

  // Split series by dimensao
  const seriesReceita = allSeries.filter(s => s.dimensao === 'receita');
  const seriesQuantidade = allSeries.filter(s => s.dimensao === 'quantidade');
  const seriesContagem = allSeries.filter(s => s.dimensao === 'contagem');

  // --- Compute scorecard aggregations from dim_inventory rows ---
  const totalProdutos = produtos.length;
  const receitaTotal = produtos.reduce((sum, p) => sum + (Number(p.receita_total) || 0), 0);
  const quantidadeTotal = produtos.reduce((sum, p) => sum + (Number(p.quantidade_total_vendida) || 0), 0);
  const ticketMedio = quantidadeTotal > 0 ? receitaTotal / quantidadeTotal : 0;

  // Growth: compare last 2 months of receita series
  let crescimentoPercentual: number | undefined;
  if (seriesReceita.length >= 2) {
    const last = Number(seriesReceita[seriesReceita.length - 1].total) || 0;
    const prev = Number(seriesReceita[seriesReceita.length - 2].total) || 0;
    crescimentoPercentual = prev > 0 ? ((last - prev) / prev) * 100 : undefined;
  }

  // Tier aggregations
  const tiers = ['A', 'B', 'C', 'D'] as const;
  const tierData = Object.fromEntries(tiers.map(t => {
    const items = produtos.filter(p => String(p.nivel_cluster || '').toUpperCase() === t);
    const count = items.length;
    const receita = items.reduce((s, p) => s + (Number(p.receita_total) || 0), 0);
    const quantidade = items.reduce((s, p) => s + (Number(p.quantidade_total_vendida) || 0), 0);
    const ticket = quantidade > 0 ? receita / quantidade : 0;
    return [t, { count, receita, quantidade, ticket }];
  })) as Record<string, { count: number; receita: number; quantidade: number; ticket: number }>;

  // Price variation (compare the 2 most recent months of avg price from series)
  // Fallback: no data → undefined
  let variacaoPrecoPercentual: number | undefined;
  const topVariacaoNome: string | null = null;
  let topVariacaoPercentual: number | undefined;
  let topVariacaoDirecao: string | undefined;

  // Ranking mappers
  const toProdutoReceita = (p: Record<string, unknown>): ProdutoRankingReceita => ({
    nome: String(p.nome || ''),
    receita_total: Number(p.receita_total) || 0,
    valor_unitario_medio: Number(p.preco_medio) || 0,
    quantidade_total: Number(p.quantidade_total_vendida) || 0,
    cluster_tier: String(p.nivel_cluster || 'N/A'),
  });

  const toProdutoVolume = (p: Record<string, unknown>): ProdutoRankingVolume => ({
    nome: String(p.nome || ''),
    quantidade_total: Number(p.quantidade_total_vendida) || 0,
    valor_unitario_medio: Number(p.preco_medio) || 0,
    receita_total: Number(p.receita_total) || 0,
    cluster_tier: String(p.nivel_cluster || 'N/A'),
  });

  const toProdutoTicket = (p: Record<string, unknown>): ProdutoRankingTicket => ({
    nome: String(p.nome || ''),
    ticket_medio: Number(p.receita_total) / Number(p.total_pedidos || 1) || 0,
    valor_unitario_medio: Number(p.preco_medio) || 0,
    quantidade_total: Number(p.quantidade_total_vendida) || 0,
    cluster_tier: String(p.nivel_cluster || 'N/A'),
  });

  return {
    scorecard_total_itens_unicos: totalProdutos,
    scorecard_receita_total: receitaTotal,
    scorecard_quantidade_total: quantidadeTotal,
    scorecard_ticket_medio: ticketMedio,
    scorecard_crescimento_percentual: crescimentoPercentual,
    // Tier data
    scorecard_tier_a_count: tierData.A.count,
    scorecard_tier_b_count: tierData.B.count,
    scorecard_tier_c_count: tierData.C.count,
    scorecard_tier_d_count: tierData.D.count,
    scorecard_tier_a_receita: tierData.A.receita,
    scorecard_tier_b_receita: tierData.B.receita,
    scorecard_tier_c_receita: tierData.C.receita,
    scorecard_tier_d_receita: tierData.D.receita,
    scorecard_tier_a_quantidade: tierData.A.quantidade,
    scorecard_tier_b_quantidade: tierData.B.quantidade,
    scorecard_tier_c_quantidade: tierData.C.quantidade,
    scorecard_tier_d_quantidade: tierData.D.quantidade,
    scorecard_tier_a_ticket_medio: tierData.A.ticket,
    scorecard_tier_b_ticket_medio: tierData.B.ticket,
    scorecard_tier_c_ticket_medio: tierData.C.ticket,
    scorecard_tier_d_ticket_medio: tierData.D.ticket,
    // Price variation
    scorecard_variacao_preco_percentual: variacaoPrecoPercentual,
    top_variacao_produto_nome: topVariacaoNome,
    top_variacao_produto_percentual: topVariacaoPercentual,
    top_variacao_produto_direcao: topVariacaoDirecao,
    // Charts — from v_series_temporal expanded view
    chart_produtos_no_tempo: seriesContagem.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_receita_no_tempo: seriesReceita.map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_quantidade_no_tempo: seriesQuantidade.map(s => ({ name: s.periodo, total: Number(s.total) })),
    // Rankings
    ranking_por_receita: produtos.slice(0, 20).map(toProdutoReceita),
    ranking_por_volume: [...produtos].sort((a, b) => Number(b.quantidade_total_vendida) - Number(a.quantidade_total_vendida)).slice(0, 20).map(toProdutoVolume),
    ranking_por_ticket_medio: [...produtos].sort((a, b) => (Number(b.receita_total) / Number(b.total_pedidos || 1)) - (Number(a.receita_total) / Number(a.total_pedidos || 1))).slice(0, 20).map(toProdutoTicket),
  };
};

// Produto API call (details)
export const getProdutoDetails = async (nome_produto: string): Promise<ProdutoDetailResponse> => {
  // Fetch product data + cross-entity rankings + time series in parallel
  // Use .limit(1).maybeSingle() to avoid errors when name matches multiple rows
  const [produtoRes, topClientsRes, topRegionsRes, revenueSeriesRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('dim_inventory').select('*').eq('nome', nome_produto).limit(1).maybeSingle(),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_product_top_clients', { p_product_name: nome_produto }),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_product_top_regions', { p_product_name: nome_produto }),
    supabase.schema(ANALYTICS_SCHEMA).rpc('get_product_revenue_series', { p_product_name: nome_produto }),
  ]);

  if (produtoRes.error) throw new Error(produtoRes.error.message);
  const produto = produtoRes.data;

  const scorecards: RankingItem | null = produto ? {
    nome: produto.nome,
    receita_total: Number(produto.receita_total) || 0,
    quantidade_total: Number(produto.quantidade_total_vendida) || 0,
    num_pedidos_unicos: Number(produto.total_pedidos) || 0,
    primeira_venda: '',
    ultima_venda: produto.data_ultima_venda || '',
    ticket_medio: Number(produto.receita_total) / Number(produto.total_pedidos || 1) || 0,
    qtd_media_por_pedido: Number(produto.quantidade_media_por_pedido) || 0,
    frequencia_pedidos_mes: Number(produto.frequencia_mensal) || 0,
    recencia_dias: Number(produto.dias_recencia) || 0,
    valor_unitario_medio: Number(produto.preco_medio) || 0,
    cluster_score: Number(produto.pontuacao_cluster) || 0,
    cluster_tier: produto.nivel_cluster || 'N/A',
  } : null;

  const toSimpleRanking = (item: Record<string, unknown>) => ({
    nome: String(item.nome || item.regiao || ''),
    receita_total: Number(item.receita_total) || 0,
  });

  return {
    nome_produto,
    scorecards,
    charts: {
      segmentos_de_clientes: (revenueSeriesRes.data || []).map((s: Record<string, unknown>) => ({ name: String(s.periodo), total: Number(s.total) })),
    },
    rankings_internos: {
      clientes_por_receita: (topClientsRes.data || []).map(toSimpleRanking),
      regioes_por_receita: (topRegionsRes.data || []).map(toSimpleRanking),
    },
  };
};

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

// Dashboard period-toggle indicators (HomePage rolling-window KPIs).
// Backed by analytics_v2.get_dashboard_indicators(p_period) — returns
// rolling current-window aggregates plus growth vs the prior equal-length
// window. Calendar-month "mês atual" values still come from
// v_resumo_dashboard / getHomeMetrics(); this RPC powers the period select.
export interface DashboardIndicatorsResponse {
  total_pedidos: number;
  receita: number;
  ticket_medio: number;
  quantidade: number;
  clientes_unicos: number;
  produtos_unicos: number;
  fornecedores_unicos: number;
  crescimento_receita: number | null;
  crescimento_pedidos: number | null;
  crescimento_clientes: number | null;
  period: string;
}

export const getDashboardIndicators = async (
  period: PeriodType | string = 'month',
): Promise<DashboardIndicatorsResponse> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_dashboard_indicators', { p_period: period });

  if (error) throw new Error(error.message);

  const row = (Array.isArray(data) ? data[0] : data) as
    | {
        total_pedidos?: number | string;
        receita?: number | string;
        ticket_medio?: number | string;
        quantidade?: number | string;
        clientes_unicos?: number | string;
        produtos_unicos?: number | string;
        fornecedores_unicos?: number | string;
        crescimento_receita?: number | string | null;
        crescimento_pedidos?: number | string | null;
        crescimento_clientes?: number | string | null;
        period?: string;
      }
    | null
    | undefined;

  return {
    total_pedidos: Number(row?.total_pedidos) || 0,
    receita: Number(row?.receita) || 0,
    ticket_medio: Number(row?.ticket_medio) || 0,
    quantidade: Number(row?.quantidade) || 0,
    clientes_unicos: Number(row?.clientes_unicos) || 0,
    produtos_unicos: Number(row?.produtos_unicos) || 0,
    fornecedores_unicos: Number(row?.fornecedores_unicos) || 0,
    crescimento_receita: row?.crescimento_receita != null ? Number(row.crescimento_receita) : null,
    crescimento_pedidos: row?.crescimento_pedidos != null ? Number(row.crescimento_pedidos) : null,
    crescimento_clientes: row?.crescimento_clientes != null ? Number(row.crescimento_clientes) : null,
    period: row?.period || String(period),
  };
};

// Order Indicators (used by PedidosPage)
// Backed by analytics_v2.get_order_indicators(p_period) — period filters
// fato_transacoes by dim_datas.data window. Status breakdown is fetched
// separately via getOrderStatusBreakdown to keep payloads small.
export const getOrderIndicators = async (
  period: PeriodType | string = 'month',
): Promise<OrderMetricsResponse> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_order_indicators', { p_period: period });

  if (error) throw new Error(error.message);

  const row = (Array.isArray(data) ? data[0] : data) as
    | {
        total?: number | string;
        revenue?: number | string;
        avg_order_value?: number | string;
        growth_rate?: number | string | null;
        period?: string;
      }
    | null
    | undefined;

  // Pull the real status breakdown for the same period in parallel-friendly
  // sequence (RPC above is the gating call, this is a quick aggregation).
  const breakdown = await getOrderStatusBreakdown(period);
  const by_status: Record<string, number> = {};
  for (const item of breakdown) {
    by_status[item.status] = item.count;
  }

  return {
    total: Number(row?.total) || 0,
    revenue: Number(row?.revenue) || 0,
    avg_order_value: Number(row?.avg_order_value) || 0,
    growth_rate: row?.growth_rate != null ? Number(row.growth_rate) : null,
    by_status,
    period: row?.period || String(period),
  };
};

// Order status breakdown (analytics_v2.get_order_status_breakdown)
export const getOrderStatusBreakdown = async (
  period: PeriodType | string = 'month',
): Promise<{ status: string; count: number }[]> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_order_status_breakdown', { p_period: period });

  if (error) throw new Error(error.message);

  return (data || []).map((row: { status: string; count: number | string }) => ({
    status: row.status,
    count: Number(row.count) || 0,
  }));
};

// Maps real `fato_transacoes.status` values to the UI's coarse buckets used
// by PedidosPage scorecards. Defined here so the page stays presentational.
// Source values observed in production: `valid`, `review`, `invalid`.
// Anything we have not classified is bucketed as `other` so the header still
// reflects 100% of the period's pedidos.
export type OrderStatusBucket = 'completed' | 'pending' | 'other';

export const ORDER_STATUS_BUCKETS: Record<string, OrderStatusBucket> = {
  valid: 'completed',
  completed: 'completed',
  finalizado: 'completed',
  pago: 'completed',
  review: 'pending',
  pending: 'pending',
  aberto: 'pending',
  aguardando: 'pending',
};

export interface OrderStatusSummary {
  completed: number;
  pending: number;
  other: number;
  total: number;
}

export const summarizeOrderStatusBreakdown = (
  items: { status: string; count: number }[] | null | undefined,
): OrderStatusSummary => {
  const summary: OrderStatusSummary = { completed: 0, pending: 0, other: 0, total: 0 };
  for (const item of items ?? []) {
    const bucket = ORDER_STATUS_BUCKETS[String(item.status).toLowerCase()] ?? 'other';
    summary[bucket] += item.count;
    summary.total += item.count;
  }
  return summary;
};

// Pedidos time series for the "Métricas de Pedidos" chart selector.
// Reads `analytics_v2.v_series_temporal` (monthly granularity). Period
// truncates the trailing window client-side so the chart respects the
// page's period select. `metric` switches between revenue, qty and ticket.
export type PedidosMetric = 'receita' | 'quantidade' | 'ticket_medio';

const PERIOD_TO_MONTHS: Record<string, number> = {
  week: 1,
  month: 1,
  quarter: 3,
  year: 12,
};

export const getPedidosTimeSeries = async (
  period: PeriodType | string = 'month',
  metric: PedidosMetric = 'receita',
): Promise<ChartDataPoint[]> => {
  // Map UI metric → (tipo_grafico, dimensao) tuples present in v_series_temporal.
  const queries: { tipo: string; dim: string }[] =
    metric === 'ticket_medio'
      ? [
          { tipo: 'receita', dim: 'receita' },
          { tipo: 'pedidos', dim: 'total' },
        ]
      : metric === 'quantidade'
        ? [{ tipo: 'clientes', dim: 'quantidade' }]
        : [{ tipo: 'receita', dim: 'receita' }];

  const results = await Promise.all(
    queries.map(({ tipo, dim }) =>
      supabase
        .schema(ANALYTICS_SCHEMA)
        .from('v_series_temporal')
        .select('periodo, data_periodo, total')
        .eq('tipo_grafico', tipo)
        .eq('dimensao', dim)
        .order('data_periodo', { ascending: true }),
    ),
  );

  for (const r of results) {
    if (r.error) throw new Error(r.error.message);
  }

  const months = PERIOD_TO_MONTHS[String(period)] ?? 12;

  if (metric === 'ticket_medio') {
    const receita = (results[0].data ?? []) as { periodo: string; total: number | string }[];
    const totals = (results[1].data ?? []) as { periodo: string; total: number | string }[];
    const totalsByPeriod = new Map(totals.map((t) => [t.periodo, Number(t.total) || 0]));
    const merged = receita.map((r) => {
      const orders = totalsByPeriod.get(r.periodo) ?? 0;
      const value = orders > 0 ? Number(r.total) / orders : 0;
      return { name: r.periodo, value: Math.round(value) };
    });
    return merged.slice(-months);
  }

  const rows = (results[0].data ?? []) as { periodo: string; total: number | string }[];
  return rows.slice(-months).map((r) => ({
    name: r.periodo,
    value: Number(r.total) || 0,
  }));
};

// Pedidos overview scorecards (analytics_v2.get_pedidos_overview_scorecards)
export const getPedidosOverviewScorecards = async (): Promise<PedidosOverviewScorecards> => {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc('get_pedidos_overview_scorecards');

  if (error) throw new Error(error.message);

  const row = (Array.isArray(data) ? data[0] : data) as
    | {
        qtd_media_produtos_por_pedido?: number | string;
        taxa_recorrencia_clientes_perc?: number | string;
        recencia_media_entre_pedidos_dias?: number | string;
      }
    | null
    | undefined;

  return {
    qtdMediaProdutos: Number(row?.qtd_media_produtos_por_pedido) || 0,
    taxaRecorrencia: Number(row?.taxa_recorrencia_clientes_perc) || 0,
    recenciaMediaDias: Number(row?.recencia_media_entre_pedidos_dias) || 0,
  };
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

// --- FILTER ENDPOINTS: Customer-Product Cross Analysis ---

// Product filter item (for dropdown)
export interface ProductFilterItem {
  nome: string;
  receita_total: number;
  total_clientes: number;
}

// Customer filter item (for dropdown)
export interface CustomerFilterItem {
  customer_cpf_cnpj: string;
  nome: string;
  receita_total: number;
  total_produtos: number;
}

// Customer by product (cross analysis result)
export interface CustomerByProduct {
  customer_cpf_cnpj: string;
  nome: string;
  produto_receita: number;
  produto_quantidade: number;
  produto_pedidos: number;
  cliente_receita_total: number;
  percentual_do_total: number;
}

// Product by customer (cross analysis result)
export interface ProductByCustomer {
  nome: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos: number;
  valor_unitario_medio: number;
}

// Monthly orders data for customer time series
export interface MonthlyOrderData {
  month: string;  // YYYY-MM format
  num_pedidos: number;
}

// Get products list for filter dropdown
export const getProductsForFilter = async (): Promise<ProductFilterItem[]> => {
  const { data: produtos, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_inventory')
    .select('nome, receita_total, total_pedidos')
    .order('receita_total', { ascending: false });

  if (error) console.warn('Error fetching products for filter:', error);

  return (produtos || []).map(p => ({
    nome: p.nome,
    receita_total: Number(p.receita_total) || 0,
    total_clientes: Number(p.total_pedidos) || 0,
  }));
};

// Get customers list for filter dropdown
export const getCustomersForFilter = async (): Promise<CustomerFilterItem[]> => {
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('cpf_cnpj, nome, receita_total, total_pedidos')
    .order('receita_total', { ascending: false });

  if (error) console.warn('Error fetching customers for filter:', error);

  return (clientes || []).map(c => ({
    customer_cpf_cnpj: c.cpf_cnpj || '',
    nome: c.nome || '',
    receita_total: Number(c.receita_total) || 0,
    total_produtos: Number(c.total_pedidos) || 0,
  }));
};

// Get customers who bought a specific product
export const getCustomersByProduct = async (productName: string, limit: number = 100): Promise<CustomerByProduct[]> => {
  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      valor,
      quantidade,
      dim_clientes!inner(cpf_cnpj, nome, receita_total),
      dim_inventory!inner(nome)
    `)
    .eq('dim_inventory.nome', productName)
    .limit(limit * 10);

  if (error) console.warn('Error fetching customers by product:', error);

  // Aggregate by customer
  const byCustomer = (transacoes || []).reduce((acc, v) => {
    const cliente = v.dim_clientes as unknown as Record<string, unknown> | null;
    const cpf = String(cliente?.cpf_cnpj || '');
    if (!acc[cpf]) {
      acc[cpf] = {
        customer_cpf_cnpj: cpf,
        nome: String(cliente?.nome || ''),
        produto_receita: 0,
        produto_quantidade: 0,
        produto_pedidos: 0,
        cliente_receita_total: Number(cliente?.receita_total || 0),
        percentual_do_total: 0,
      };
    }
    acc[cpf].produto_receita += Number(v.valor) || 0;
    acc[cpf].produto_quantidade += Number(v.quantidade) || 0;
    acc[cpf].produto_pedidos++;
    return acc;
  }, {} as Record<string, CustomerByProduct>);

  const result = Object.values(byCustomer);
  result.forEach(c => {
    c.percentual_do_total = c.cliente_receita_total > 0
      ? (c.produto_receita / c.cliente_receita_total) * 100
      : 0;
  });

  return result.sort((a, b) => b.produto_receita - a.produto_receita).slice(0, limit);
};

// Get products bought by a specific customer
export const getProductsByCustomer = async (customerCpfCnpj: string, limit: number = 100): Promise<ProductByCustomer[]> => {
  // Resolve cpf_cnpj -> cliente_id first
  const { data: customer } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('cliente_id')
    .eq('cpf_cnpj', customerCpfCnpj)
    .maybeSingle();

  if (!customer) return [];

  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      valor,
      quantidade,
      valor_unitario,
      dim_inventory!inner(nome)
    `)
    .eq('cliente_id', customer.cliente_id)
    .limit(limit * 10);

  if (error) console.warn('Error fetching products by customer:', error);

  // Aggregate by product
  const byProduct = (transacoes || []).reduce((acc, v) => {
    const produto = v.dim_inventory as unknown as Record<string, string> | null;
    const nome = produto?.nome || '';
    if (!acc[nome]) {
      acc[nome] = {
        nome,
        receita_total: 0,
        quantidade_total: 0,
        num_pedidos: 0,
        valor_unitario_medio: 0,
      };
    }
    acc[nome].receita_total += Number(v.valor) || 0;
    acc[nome].quantidade_total += Number(v.quantidade) || 0;
    acc[nome].num_pedidos++;
    return acc;
  }, {} as Record<string, ProductByCustomer>);

  const result = Object.values(byProduct);
  result.forEach(p => {
    p.valor_unitario_medio = p.quantidade_total > 0
      ? p.receita_total / p.quantidade_total
      : 0;
  });

  return result.sort((a, b) => b.receita_total - a.receita_total).slice(0, limit);
};

// Get monthly orders for a specific customer (time series)
export const getCustomerMonthlyOrders = async (customerCpfCnpj: string): Promise<MonthlyOrderData[]> => {
  // Resolve cpf_cnpj -> cliente_id first
  const { data: customer } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('cliente_id')
    .eq('cpf_cnpj', customerCpfCnpj)
    .maybeSingle();

  if (!customer) return [];

  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      documento,
      dim_datas!data_competencia_id(data)
    `)
    .eq('cliente_id', customer.cliente_id);

  if (error) console.warn('Error fetching customer monthly orders:', error);

  // Aggregate by month
  const byMonth = (transacoes || []).reduce((acc, v) => {
    const dimData = v.dim_datas as unknown as Record<string, string> | null;
    if (!dimData?.data) return acc;
    const date = new Date(dimData.data);
    const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    if (!acc[month]) acc[month] = new Set<string>();
    acc[month].add(v.documento);
    return acc;
  }, {} as Record<string, Set<string>>);

  return Object.entries(byMonth)
    .map(([month, pedidos]) => ({ month, num_pedidos: pedidos.size }))
    .sort((a, b) => a.month.localeCompare(b.month));
};

// Interface for customers by supplier
export interface CustomerBySupplier {
  nome: string;
  customer_cpf_cnpj: string;
  receita_total: number;
  quantidade_total: number;
  num_pedidos: number;
  ticket_medio: number;
}

// Get customers who bought from a specific supplier
export const getCustomersBySupplier = async (supplierCnpj: string, limit: number = 100): Promise<CustomerBySupplier[]> => {
  // Resolve cnpj -> fornecedor_id first
  const { data: supplier } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_fornecedores')
    .select('fornecedor_id')
    .eq('cnpj', supplierCnpj)
    .maybeSingle();

  if (!supplier) return [];

  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      valor,
      quantidade,
      dim_clientes!inner(cpf_cnpj, nome)
    `)
    .eq('fornecedor_id', supplier.fornecedor_id)
    .limit(limit * 10);

  if (error) console.warn('Error fetching customers by supplier:', error);

  // Aggregate by customer
  const byCustomer = (transacoes || []).reduce((acc, v) => {
    const cliente = v.dim_clientes as unknown as Record<string, string> | null;
    const cpf = String(cliente?.cpf_cnpj || '');
    if (!acc[cpf]) {
      acc[cpf] = {
        nome: cliente?.nome || '',
        customer_cpf_cnpj: cpf,
        receita_total: 0,
        quantidade_total: 0,
        num_pedidos: 0,
        ticket_medio: 0,
      };
    }
    acc[cpf].receita_total += Number(v.valor) || 0;
    acc[cpf].quantidade_total += Number(v.quantidade) || 0;
    acc[cpf].num_pedidos++;
    return acc;
  }, {} as Record<string, CustomerBySupplier>);

  const result = Object.values(byCustomer);
  result.forEach(c => {
    c.ticket_medio = c.num_pedidos > 0 ? c.receita_total / c.num_pedidos : 0;
  });

  return result.sort((a, b) => b.receita_total - a.receita_total).slice(0, limit);
};

// Get products sold by a specific supplier
export const getProductsBySupplier = async (supplierCnpj: string, limit: number = 100): Promise<ProductByCustomer[]> => {
  // Resolve cnpj -> fornecedor_id first
  const { data: supplier } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_fornecedores')
    .select('fornecedor_id')
    .eq('cnpj', supplierCnpj)
    .maybeSingle();

  if (!supplier) return [];

  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      valor,
      quantidade,
      valor_unitario,
      dim_inventory!inner(nome)
    `)
    .eq('fornecedor_id', supplier.fornecedor_id)
    .limit(limit * 10);

  if (error) console.warn('Error fetching products by supplier:', error);

  // Aggregate by product
  const byProduct = (transacoes || []).reduce((acc, v) => {
    const produto = v.dim_inventory as unknown as Record<string, string> | null;
    const nome = produto?.nome || '';
    if (!acc[nome]) {
      acc[nome] = {
        nome,
        receita_total: 0,
        quantidade_total: 0,
        num_pedidos: 0,
        valor_unitario_medio: 0,
      };
    }
    acc[nome].receita_total += Number(v.valor) || 0;
    acc[nome].quantidade_total += Number(v.quantidade) || 0;
    acc[nome].num_pedidos++
    return acc;
  }, {} as Record<string, ProductByCustomer>);

  const result = Object.values(byProduct);
  result.forEach(p => {
    p.valor_unitario_medio = p.quantidade_total > 0
      ? p.receita_total / p.quantidade_total
      : 0;
  });

  return result.sort((a, b) => b.receita_total - a.receita_total).slice(0, limit);
};

// Interface for suppliers by product
export interface SupplierByProduct {
  supplier_id: string;
  supplier_name: string;
  supplier_cnpj: string;
  endereco_cidade: string | null;
  endereco_uf: string | null;
  quantity_sold: number;
  total_revenue: number;
  order_count: number;
  avg_unit_price: number;
  last_sale: string | null;
}

// Get suppliers who sell a specific product
export const getSuppliersByProduct = async (productName: string, limit: number = 100): Promise<SupplierByProduct[]> => {
  const { data: transacoes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('fato_transacoes')
    .select(`
      valor,
      quantidade,
      valor_unitario,
      dim_fornecedores!inner(fornecedor_id, nome, cnpj, endereco_cidade, endereco_uf),
      dim_inventory!inner(nome),
      dim_datas!data_competencia_id(data)
    `)
    .eq('dim_inventory.nome', productName)
    .limit(limit * 10);

  if (error) console.warn('Error fetching suppliers by product:', error);

  // Aggregate by supplier
  const bySupplier = (transacoes || []).reduce((acc, v) => {
    const fornecedor = v.dim_fornecedores as unknown as Record<string, unknown> | null;
    const cnpj = String(fornecedor?.cnpj || '');
    if (!acc[cnpj]) {
      acc[cnpj] = {
        supplier_id: String(fornecedor?.fornecedor_id || ''),
        supplier_name: String(fornecedor?.nome || ''),
        supplier_cnpj: cnpj,
        endereco_cidade: fornecedor?.endereco_cidade as string | null,
        endereco_uf: fornecedor?.endereco_uf as string | null,
        quantity_sold: 0,
        total_revenue: 0,
        order_count: 0,
        avg_unit_price: 0,
        last_sale: null as string | null,
      };
    }
    acc[cnpj].quantity_sold += Number(v.quantidade) || 0;
    acc[cnpj].total_revenue += Number(v.valor) || 0;
    acc[cnpj].order_count++;
    const dimData = v.dim_datas as unknown as Record<string, string> | null;
    const date = dimData?.data || null;
    if (date && (!acc[cnpj].last_sale || date > acc[cnpj].last_sale!)) {
      acc[cnpj].last_sale = date;
    }
    return acc;
  }, {} as Record<string, SupplierByProduct>);

  const result = Object.values(bySupplier);
  result.forEach(s => {
    s.avg_unit_price = s.quantity_sold > 0
      ? s.total_revenue / s.quantity_sold
      : 0;
  });

  return result.sort((a, b) => b.total_revenue - a.total_revenue).slice(0, limit);
};

// User profile API call - now reads from Supabase auth session
// (getMe helper removed — consumers import `resolveClientId()` from lib/auth directly)

// --- Domain Analytics (for DomainExpansionModal) ---

export interface DomainAnalytics {
  monthlyData: ChartDataPoint[];
  kpis: Record<string, number>;
}

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
      const { data: series } = await supabase
        .schema(ANALYTICS_SCHEMA)
        .from('v_series_temporal')
        .select('*')
        .eq('tipo_grafico', 'receita')
        .eq('dimensao', 'receita')
        .order('data_periodo', { ascending: true });

      const monthlyData = (series || []).map(s => ({
        name: s.periodo,
        month: s.periodo,
        value: Number(s.total) || 0,
        revenue: Number(s.total) || 0,
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
      const { data: series } = await supabase
        .schema(ANALYTICS_SCHEMA)
        .from('v_series_temporal')
        .select('*')
        .eq('tipo_grafico', 'clientes')
        .eq('dimensao', 'contagem')
        .order('data_periodo', { ascending: true });

      const monthlyData = (series || []).map(s => ({
        name: s.periodo,
        month: s.periodo,
        new: Number(s.total) || 0,
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
      const { data: series } = await supabase
        .schema(ANALYTICS_SCHEMA)
        .from('v_series_temporal')
        .select('*')
        .eq('tipo_grafico', 'fornecedores')
        .eq('dimensao', 'contagem')
        .order('data_periodo', { ascending: true });

      const monthlyData = (series || []).map(s => ({
        name: s.periodo,
        month: s.periodo,
        active: Number(s.total) || 0,
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
      const { data: series } = await supabase
        .schema(ANALYTICS_SCHEMA)
        .from('v_series_temporal')
        .select('*')
        .eq('tipo_grafico', 'produtos')
        .eq('dimensao', 'quantidade')
        .order('data_periodo', { ascending: true });

      const monthlyData = (series || []).map(s => ({
        name: s.periodo,
        month: s.periodo,
        sold: Number(s.total) || 0,
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

// ──────────────────────────────────────────────────────────────────────────
// Phase 3A — Procurement (P3.4) BLU-MVP-043 / BLU-MVP-044
// ──────────────────────────────────────────────────────────────────────────

export interface RfqStatusBreakdown {
  pending: number;
  sent: number;
  responded: number;
  expired: number;
  total: number;
}

export interface PurchaseOrderStatusBreakdown {
  draft: number;
  pending_approval: number;
  approved: number;
  delivered: number;
  cancelled: number;
  total: number;
}

export interface ProcurementOverview {
  rfq: RfqStatusBreakdown;
  purchase_orders: PurchaseOrderStatusBreakdown;
}

/**
 * Fetch RFQ + PO status counts for the current tenant.
 * Uses Supabase PostgREST so RLS scopes by client_id automatically.
 */
export const getProcurementOverview = async (): Promise<ProcurementOverview> => {
  const [rfqRes, poRes] = await Promise.all([
    supabase.from('rfq_requests').select('status'),
    supabase.from('purchase_orders').select('status'),
  ]);

  if (rfqRes.error) throw new Error(rfqRes.error.message);
  if (poRes.error) throw new Error(poRes.error.message);

  const rfq: RfqStatusBreakdown = { pending: 0, sent: 0, responded: 0, expired: 0, total: 0 };
  for (const row of rfqRes.data ?? []) {
    rfq.total += 1;
    const s = (row as { status?: string }).status;
    if (s === 'pending') rfq.pending += 1;
    else if (s === 'sent') rfq.sent += 1;
    else if (s === 'responded') rfq.responded += 1;
    else if (s === 'expired') rfq.expired += 1;
  }

  const po: PurchaseOrderStatusBreakdown = {
    draft: 0,
    pending_approval: 0,
    approved: 0,
    delivered: 0,
    cancelled: 0,
    total: 0,
  };
  for (const row of poRes.data ?? []) {
    po.total += 1;
    const s = (row as { status?: string }).status;
    if (s === 'draft') po.draft += 1;
    else if (s === 'pending_approval') po.pending_approval += 1;
    else if (s === 'approved') po.approved += 1;
    else if (s === 'delivered') po.delivered += 1;
    else if (s === 'cancelled') po.cancelled += 1;
  }

  return { rfq, purchase_orders: po };
};

export interface PurchaseOrderListItem {
  id: string;
  status: string;
  total_amount: number;
  supplier_id: string | null;
  created_at: string;
  approved_at: string | null;
}

/**
 * Recent purchase orders for the current tenant.
 */
export const getRecentPurchaseOrders = async (
  limit: number = 20,
): Promise<PurchaseOrderListItem[]> => {
  const { data, error } = await supabase
    .from('purchase_orders')
    .select('id,status,total_amount,supplier_id,created_at,approved_at')
    .order('created_at', { ascending: false })
    .limit(limit);
  if (error) throw new Error(error.message);
  return (data ?? []) as PurchaseOrderListItem[];
};

export interface PoExportToSheetsResponse {
  spreadsheet_url: string;
  spreadsheet_id: string;
}

/**
 * BLU-MVP-044 — call the existing `export_po_to_sheets` MCP tool through the
 * tool_pool_api integrations endpoint. The endpoint requires the user JWT for
 * RLS and forges its own service-role context server-side.
 */
export const exportPoToSheets = async (
  poId: string,
): Promise<PoExportToSheetsResponse> => {
  const { data: sessionData } = await supabase.auth.getSession();
  const token = sessionData?.session?.access_token;
  if (!token) throw new Error('Sessão expirada — faça login novamente.');

  const baseUrl =
    (import.meta as { env?: Record<string, string | undefined> }).env
      ?.VITE_TOOL_POOL_API_URL ?? '';
  if (!baseUrl) throw new Error('VITE_TOOL_POOL_API_URL não configurada.');

  const resp = await fetch(`${baseUrl.replace(/\/$/, '')}/integrations/tools/export_po_to_sheets`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ po_id: poId }),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Falha ao exportar pedido: ${text}`);
  }
  return (await resp.json()) as PoExportToSheetsResponse;
};

// ─────────────────────────────────────────────────────────────────────────
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
