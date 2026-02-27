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

// Note: This Pedido interface appears to be for a different use case (possibly OLTP/UI-specific)
// and does not match the backend's PedidoItem or PedidoDetailResponse from the analytics API.
// Consider renaming this to avoid confusion or document its specific purpose.
export interface Pedido {
  id: string;
  title: string;
  description: string;
  status: string;
  clientName: string;
  valorUnitario: string;
  enderecoEntrega: string;
  cnpjFaturamento: string;
  descricaoProdutos: string;
  // Campos adicionais usados na listagem
  valorTotal?: string;
  descricao?: string;
  frete?: string;
  quantidadeItens?: number;
  // Add other fields as per your API response for Pedidos
}

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

// Corresponds to the Pydantic 'CustomerMetricsResponse' from indicators endpoint
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

// Corresponds to the Pydantic 'ProductMetricsResponse' from indicators endpoint
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

// Corresponds to the Pydantic 'OrderMetricsResponse' from indicators endpoint
export interface OrderMetricsResponse {
  total: number;
  revenue: number;
  avg_order_value: number;
  growth_rate: number | null;
  by_status: Record<string, number>;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
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
  cluster_tier: string;
}

// Corresponds to the Pydantic 'ProdutoRankingVolume'
export interface ProdutoRankingVolume {
  nome: string;
  quantidade_total: number;
  valor_unitario_medio: number;
  receita_total: number;
  cluster_tier: string;
}

// Corresponds to the Pydantic 'ProdutoRankingTicket'
export interface ProdutoRankingTicket {
  nome: string;
  ticket_medio: number;
  valor_unitario_medio: number;
  quantidade_total: number;
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
  ticket_medio?: number;
  crescimento_receita?: number;  // Variação % receita (último mês vs penúltimo)
  crescimento_clientes?: number;  // Variação % clientes (último mês vs penúltimo)
  crescimento_produtos?: number;  // Variação % produtos (último mês vs penúltimo)
  frequencia_media_fornecedores?: number;  // Média de pedidos por fornecedor por mês
  ultimo_mes?: string;  // Nome do último mês com dados (ex: "2026-01")
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { data: resumo, error: resumoError } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .single();

  const dashboard = resumo || { total_pedidos: 0, receita_total: 0, ticket_medio: 0 };

  // Calculate scorecards
  const totalPedidos = dashboard.total_pedidos || 0;
  const receitaTotal = Number(dashboard.receita_total) || 0;
  const ticketMedio = totalPedidos > 0 ? receitaTotal / totalPedidos : 0;

  return {
    scorecard_ticket_medio_por_pedido: ticketMedio,
    scorecard_qtd_media_produtos_por_pedido: 0, // Would need aggregation from fato_transacoes
    scorecard_taxa_recorrencia_clientes_perc: 0, // Would need calculation
    scorecard_recencia_media_entre_pedidos_dias: 0, // Would need calculation
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
      dim_clientes(nome, cpf_cnpj, telefone, endereco_uf, endereco_cidade),
      dim_inventory!inventory_id(nome),
      dim_datas!data_competencia_id(data)
    `)
    .eq('documento', order_id);

  throwIfError(transacoes, error);

  const firstItem = transacoes?.[0];
  const cliente = firstItem?.dim_clientes as unknown as Record<string, string> | null;

  return {
    order_id,
    status_pedido: 'completed',
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
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getFornecedores = async (_period: string = 'all'): Promise<FornecedoresOverviewResponse> => {
  // Get fornecedores from dim_fornecedores
  const { data: fornecedores, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_fornecedores')
    .select('*')
    .order('receita_total', { ascending: false });

  throwIfError(fornecedores, error);

  // Get series temporal for charts
  const { data: seriesReceita } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .eq('tipo_grafico', 'fornecedores')
    .eq('dimensao', 'receita')
    .order('data_periodo', { ascending: true });

  // Get regional distribution
  const { data: regional } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_distribuicao_regional')
    .select('*')
    .eq('tipo_grafico', 'fornecedores')
    .order('total', { ascending: false });

  const totalFornecedores = fornecedores?.length || 0;

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
    scorecard_crescimento_percentual: null,
    chart_fornecedores_no_tempo: [],
    chart_receita_no_tempo: (seriesReceita || []).map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_ticketmedio_no_tempo: [],
    chart_quantidade_no_tempo: [],
    chart_fornecedores_por_regiao: (regional || []).map(r => ({ name: r.estado || r.regiao, total: Number(r.total) })),
    chart_cohort_fornecedores: [],
    ranking_por_receita: (fornecedores || []).slice(0, 20).map(toRankingItem),
    ranking_por_qtd_media: (fornecedores || []).slice(0, 20).map(toRankingItem),
    ranking_por_ticket_medio: [...(fornecedores || [])].sort((a, b) => Number(b.ticket_medio) - Number(a.ticket_medio)).slice(0, 20).map(toRankingItem),
    ranking_por_frequencia: [...(fornecedores || [])].sort((a, b) => Number(b.frequencia_mensal) - Number(a.frequencia_mensal)).slice(0, 20).map(toRankingItem),
    ranking_produtos_mais_vendidos: [],
  };
};

// Fornecedor API call (details)
export const getFornecedor = async (nome_fornecedor: string): Promise<FornecedorDetailResponse> => {
  const { data: fornecedor, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_fornecedores')
    .select('*')
    .eq('nome', nome_fornecedor)
    .single();

  throwIfError(fornecedor, error);

  return {
    dados_cadastrais: {
      emitter_nome: fornecedor?.nome,
      emitter_cnpj: fornecedor?.cnpj,
      emitter_telefone: fornecedor?.telefone,
      emitter_estado: fornecedor?.endereco_uf,
      emitter_cidade: fornecedor?.endereco_cidade,
    },
    rankings_internos: {
      clientes_por_receita: [],
      produtos_por_receita: [],
      regioes_por_receita: [],
    },
    charts: {
      receita_no_tempo: [],
    },
  };
};

// Clientes API calls (overview)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getClientes = async (_period: string = 'all'): Promise<ClientesOverviewResponse> => {
  // Get clientes from dim_clientes
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('*')
    .order('receita_total', { ascending: false });

  throwIfError(clientes, error);

  // Get series temporal for charts
  const { data: seriesReceita } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .eq('tipo_grafico', 'clientes')
    .eq('dimensao', 'receita')
    .order('data_periodo', { ascending: true });

  // Get regional distribution
  const { data: regional } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_distribuicao_regional')
    .select('*')
    .eq('tipo_grafico', 'clientes')
    .order('total', { ascending: false });

  const totalClientes = clientes?.length || 0;
  const receitaTotal = clientes?.reduce((sum, c) => sum + Number(c.receita_total || 0), 0) || 0;
  const ticketMedio = totalClientes > 0 ? receitaTotal / totalClientes : 0;
  const frequenciaMedia = clientes?.reduce((sum, c) => sum + Number(c.frequencia_mensal || 0), 0) / totalClientes || 0;

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
    scorecard_crescimento_percentual: null,
    chart_clientes_no_tempo: [],
    chart_receita_no_tempo: (seriesReceita || []).map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_ticketmedio_no_tempo: [],
    chart_quantidade_no_tempo: [],
    chart_clientes_por_regiao: (regional || []).map(r => ({ name: r.estado || r.regiao, total: Number(r.total) })),
    chart_cohort_clientes: [],
    ranking_por_receita: (clientes || []).slice(0, 20).map(toRankingItem),
    ranking_por_ticket_medio: [...(clientes || [])].sort((a, b) => Number(b.ticket_medio) - Number(a.ticket_medio)).slice(0, 20).map(toRankingItem),
    ranking_por_qtd_pedidos: [...(clientes || [])].sort((a, b) => Number(b.total_pedidos) - Number(a.total_pedidos)).slice(0, 20).map(toRankingItem),
    ranking_por_cluster_vizu: [...(clientes || [])].sort((a, b) => Number(b.pontuacao_cluster) - Number(a.pontuacao_cluster)).slice(0, 20).map(toRankingItem),
  };
};

// Cliente API call (details)
export const getCliente = async (nome_cliente: string): Promise<ClienteDetailResponse> => {
  const { data: cliente, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('*')
    .eq('nome', nome_cliente)
    .single();

  throwIfError(cliente, error);

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
      mix_de_produtos_por_receita: [],
    },
  };
};

// Produtos API calls (overview)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getProdutosOverview = async (_period: string = 'all'): Promise<ProdutosOverviewResponse> => {
  const { data: produtos, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_inventory')
    .select('*')
    .order('receita_total', { ascending: false });

  throwIfError(produtos, error);

  // Get series temporal
  const { data: seriesReceita } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .eq('tipo_grafico', 'produtos')
    .order('data_periodo', { ascending: true });

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
    scorecard_total_itens_unicos: produtos?.length || 0,
    chart_produtos_no_tempo: [],
    chart_receita_no_tempo: (seriesReceita || []).map(s => ({ name: s.periodo, total: Number(s.total) })),
    chart_quantidade_no_tempo: [],
    ranking_por_receita: (produtos || []).slice(0, 20).map(toProdutoReceita),
    ranking_por_volume: [...(produtos || [])].sort((a, b) => Number(b.quantidade_total_vendida) - Number(a.quantidade_total_vendida)).slice(0, 20).map(toProdutoVolume),
    ranking_por_ticket_medio: [...(produtos || [])].sort((a, b) => (Number(b.receita_total) / Number(b.total_pedidos || 1)) - (Number(a.receita_total) / Number(a.total_pedidos || 1))).slice(0, 20).map(toProdutoTicket),
  };
};

// Produto API call (details)
export const getProdutoDetails = async (nome_produto: string): Promise<ProdutoDetailResponse> => {
  const { data: produto, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_inventory')
    .select('*')
    .eq('nome', nome_produto)
    .single();

  throwIfError(produto, error);

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

  return {
    nome_produto,
    scorecards,
    charts: {
      segmentos_de_clientes: [],
    },
    rankings_internos: {
      clientes_por_receita: [],
      regioes_por_receita: [],
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
    .single();

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
    receita_mes_atual: Number(dashboard.receita_total) || 0, // Would need monthly filter
    total_fornecedores: Number(dashboard.total_fornecedores) || 0,
    total_produtos: Number(dashboard.total_produtos) || 0,
    total_regioes: 0, // Would need aggregation
    total_clientes: Number(dashboard.total_clientes) || 0,
    total_pedidos: Number(dashboard.total_pedidos) || 0,
    ticket_medio: Number(dashboard.ticket_medio) || 0,
  };

  // Group series by tipo_grafico for charts
  const receitaNoTempo = (series || []).filter(s => s.dimensao === 'receita').map(s => ({
    name: s.periodo,
    total: Number(s.total) || 0,
  }));

  const charts: ChartData[] = [
    { id: 'receita_no_tempo', title: 'Receita no Tempo', data: receitaNoTempo },
  ];

  return { scorecards, charts };
};

// Customer Indicators (from IndicatorService)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getCustomerIndicators = async (period: string = 'month', _includeComparisons: boolean = false): Promise<CustomerMetricsResponse> => {
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('total_pedidos, receita_total, dias_recencia');

  if (error) console.warn('Error fetching customer indicators:', error);

  const clientesData = clientes || [];
  const totalActive = clientesData.filter(c => Number(c.dias_recencia) <= 90).length;
  const newCustomers = clientesData.filter(c => Number(c.total_pedidos) === 1).length;
  const returningCustomers = totalActive - newCustomers;
  const avgLifetimeValue = clientesData.length > 0
    ? clientesData.reduce((sum, c) => sum + Number(c.receita_total || 0), 0) / clientesData.length
    : 0;

  return {
    total_active: totalActive,
    new_customers: newCustomers,
    returning_customers: returningCustomers,
    avg_lifetime_value: avgLifetimeValue,
    period,
  };
};

// Product Indicators (from IndicatorService)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getProductIndicators = async (period: string = 'month', _includeComparisons: boolean = false): Promise<ProductMetricsResponse> => {
  const { data: produtos, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_inventory')
    .select('quantidade_total_vendida, total_pedidos, preco_medio');

  if (error) console.warn('Error fetching product indicators:', error);

  const produtosData = produtos || [];
  const totalSold = produtosData.reduce((sum, p) => sum + Number(p.quantidade_total_vendida || 0), 0);
  const avgPrice = produtosData.length > 0
    ? produtosData.reduce((sum, p) => sum + Number(p.preco_medio || 0), 0) / produtosData.length
    : 0;

  return {
    total_sold: totalSold,
    unique_products: produtosData.length,
    top_sellers: [],
    low_stock_alerts: 0,
    avg_price: avgPrice,
    period,
  };
};

// Order Indicators (from IndicatorService)
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getOrderIndicators = async (period: string = 'month', _includeComparisons: boolean = false): Promise<OrderMetricsResponse> => {
  const { data: resumo, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_resumo_dashboard')
    .select('*')
    .single();

  if (error) console.warn('Error fetching order indicators:', error);

  const dashboard = resumo || {};

  return {
    total: Number(dashboard.total_pedidos) || 0,
    revenue: Number(dashboard.receita_total) || 0,
    avg_order_value: Number(dashboard.ticket_medio) || 0,
    growth_rate: null,
    by_status: { completed: Number(dashboard.total_pedidos) || 0 },
    period,
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

export const getGeoClusters = async (groupBy: 'state' | 'city' | 'cep' = 'state'): Promise<GeoClustersResponse> => {
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('endereco_uf, endereco_cidade, endereco_cep, receita_total');

  if (error) console.warn('Error fetching geo clusters:', error);

  // Aggregate by location
  const grouped = (clientes || []).reduce((acc, c) => {
    const loc = groupBy === 'state'
      ? String(c.endereco_uf || 'N/A')
      : groupBy === 'city'
        ? String(c.endereco_cidade || 'N/A')
        : String(c.endereco_cep || 'N/A');
    if (!acc[loc]) acc[loc] = { count: 0, total_revenue: 0 };
    acc[loc].count++;
    acc[loc].total_revenue += Number(c.receita_total) || 0;
    return acc;
  }, {} as Record<string, { count: number; total_revenue: number }>);

  const clusters: GeoCluster[] = Object.entries(grouped).map(([location, data]) => ({
    location,
    count: data.count,
    total_revenue: data.total_revenue,
    coordinates: [0, 0], // Would need geocoding
  }));

  return {
    clusters,
    center: [-23.55, -46.63], // São Paulo default
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
    .single();

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
    .single();

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
    .single();

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
    .single();

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
export interface MeResponse {
  client_id: string;
}

// Get client_id from the authenticated user's custom claims or clientes_vizu table
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const getMe = async (_token: string): Promise<MeResponse> => {
  // Get current user from Supabase auth
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error || !user) {
    throw new Error('User not authenticated');
  }

  // The client_id should be in app_metadata or we need to look it up
  const clientId = user.app_metadata?.client_id;

  if (clientId) {
    return { client_id: clientId };
  }

  // Fallback: look up in clientes_vizu table by user email
  const { data: cliente, error: clienteError } = await supabase
    .from('clientes_vizu')
    .select('client_id')
    .eq('email', user.email)
    .single();

  if (clienteError || !cliente) {
    throw new Error('Client not found for user');
  }

  return { client_id: cliente.client_id };
};

// --- MATERIALIZED VIEW ENDPOINTS (Fast pre-computed data) ---

// MV Customer Summary
export interface MVCustomerSummary {
  customer_id: string;
  name: string;
  cpf_cnpj: string;
  estado: string | null;
  total_orders: number;
  lifetime_value: number;
  avg_order_value: number;
  total_quantity: number;
  last_order_date: string | null;
  first_order_date: string | null;
  days_since_last_order: number;
}

export interface MVCustomersResponse {
  customers: MVCustomerSummary[];
  total: number;
}

// MV Product Summary
export interface MVProductSummary {
  product_id: string;
  product_name: string;
  times_sold: number;
  total_quantity_sold: number;
  total_revenue: number;
  avg_order_value: number;
  avg_price: number;
  min_price: number;
  max_price: number;
  last_sold_date: string | null;
  unique_customers: number;
}

export interface MVProductsResponse {
  products: MVProductSummary[];
  total: number;
}

// MV Monthly Sales Trend
export interface MVMonthlySales {
  month: string;  // YYYY-MM format
  name: string;   // Same as month, for chart compatibility
  orders: number;
  unique_customers: number;
  revenue: number;
  total: number;  // Same as revenue, for chart compatibility
  avg_order_value: number;
}

export interface MVMonthlySalesResponse {
  monthly_sales: MVMonthlySales[];
  total_months: number;
}

// MV Dashboard Summary (combined)
export interface MVDashboardSummary {
  total_customers: number;
  total_products: number;
  total_orders: number;
  total_revenue: number;
  avg_order_value: number;
  monthly_trend: MVMonthlySales[];
  top_customers: MVCustomerSummary[];
  top_products: MVProductSummary[];
}

// Get customer summary from dim_clientes
export const getMVCustomers = async (): Promise<MVCustomersResponse> => {
  const { data: clientes, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_clientes')
    .select('*')
    .order('receita_total', { ascending: false })
    .limit(100);

  if (error) console.warn('Error fetching MV customers:', error);

  const customers: MVCustomerSummary[] = (clientes || []).map(c => ({
    customer_id: c.cliente_id,
    name: c.nome,
    cpf_cnpj: c.cpf_cnpj,
    estado: c.endereco_uf,
    total_orders: c.total_pedidos || 0,
    lifetime_value: Number(c.receita_total) || 0,
    avg_order_value: Number(c.ticket_medio) || 0,
    total_quantity: Number(c.quantidade_total) || 0,
    last_order_date: c.data_ultima_compra,
    first_order_date: c.data_primeira_compra,
    days_since_last_order: c.dias_recencia || 0,
  }));

  return { customers, total: customers.length };
};

// Get product summary from dim_inventory
export const getMVProducts = async (): Promise<MVProductsResponse> => {
  const { data: produtos, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('dim_inventory')
    .select('*')
    .order('receita_total', { ascending: false })
    .limit(100);

  if (error) console.warn('Error fetching MV products:', error);

  const products: MVProductSummary[] = (produtos || []).map(p => ({
    product_id: p.inventory_id,
    product_name: p.nome,
    times_sold: p.total_pedidos || 0,
    total_quantity_sold: Number(p.quantidade_total_vendida) || 0,
    total_revenue: Number(p.receita_total) || 0,
    avg_order_value: Number(p.receita_total) / (p.total_pedidos || 1),
    avg_price: Number(p.preco_medio) || 0,
    min_price: Number(p.preco_medio) || 0,
    max_price: Number(p.preco_medio) || 0,
    last_sold_date: p.data_ultima_venda,
    unique_customers: 0, // Would need join to calculate
  }));

  return { products, total: products.length };
};

// Get monthly sales trend from v_series_temporal
export const getMVMonthlySales = async (): Promise<MVMonthlySalesResponse> => {
  const { data: series, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from('v_series_temporal')
    .select('*')
    .eq('tipo_grafico', 'vendas')
    .eq('dimensao', 'receita')
    .order('data_periodo', { ascending: true });

  if (error) console.warn('Error fetching MV monthly sales:', error);

  const monthly_sales: MVMonthlySales[] = (series || []).map(s => ({
    month: s.periodo,
    name: s.periodo,
    orders: 0, // Would need different query
    unique_customers: 0,
    revenue: Number(s.total) || 0,
    total: Number(s.total) || 0,
    avg_order_value: 0,
  }));

  return { monthly_sales, total_months: monthly_sales.length };
};

// Get complete dashboard summary
export const getMVDashboardSummary = async (): Promise<MVDashboardSummary> => {
  const [resumoRes, customersRes, productsRes, salesRes] = await Promise.all([
    supabase.schema(ANALYTICS_SCHEMA).from('v_resumo_dashboard').select('*').single(),
    getMVCustomers(),
    getMVProducts(),
    getMVMonthlySales(),
  ]);

  const resumo = resumoRes.data || {};

  return {
    total_customers: Number(resumo.total_clientes) || 0,
    total_products: Number(resumo.total_produtos) || 0,
    total_orders: Number(resumo.total_pedidos) || 0,
    total_revenue: Number(resumo.receita_total) || 0,
    avg_order_value: Number(resumo.ticket_medio) || 0,
    monthly_trend: salesRes.monthly_sales,
    top_customers: customersRes.customers.slice(0, 10),
    top_products: productsRes.products.slice(0, 10),
  };
};
