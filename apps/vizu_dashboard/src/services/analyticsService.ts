import axios from 'axios';
import { supabase } from '../lib/supabase';

const API_BASE_URL = import.meta.env.VITE_API_URL_ANALYTICS || 'http://localhost:8004';

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
  top_sellers: any[];
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
  by_status: Record<string, any>;
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
  [key: string]: any; // Allows for other properties like 'total', 'percentual', etc.
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
}

// Corresponds to the Pydantic 'ProdutoRankingVolume'
export interface ProdutoRankingVolume {
  nome: string;
  quantidade_total: number;
  valor_unitario_medio: number;
}

// Corresponds to the Pydantic 'ProdutoRankingTicket'
export interface ProdutoRankingTicket {
  nome: string;
  ticket_medio: number;
  valor_unitario_medio: number;
}

// Corresponds to the Pydantic 'HomeScorecards'
export interface HomeScorecards {
  receita_total: number;
  total_fornecedores: number;
  total_produtos: number;
  total_regioes: number;
  total_clientes: number;
  total_pedidos: number;
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

// Corresponds to the Pydantic 'CadastralData'
export interface CadastralData {
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


// --- API Client Functions ---

const getAuthToken = async (): Promise<string | null> => {
  try {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.access_token) return data.session.access_token;
  } catch (err) {
    console.warn('Failed to read Supabase session token, falling back to localStorage', err);
  }

  return localStorage.getItem('authToken');
};

// Get client ID from localStorage (stored by AuthContext from /me endpoint)
// This is the real client_id from clientes_vizu table, NOT the Supabase user.id
const getClientId = (): string | null => {
  return localStorage.getItem('vizu_client_id');
};

const axiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the auth token and client ID
axiosInstance.interceptors.request.use(
  async (config) => {
    config.headers = config.headers ?? {};

    // Add Authorization header with JWT token
    const token = await getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add X-Client-ID header with the real client_id from clientes_vizu
    const clientId = getClientId();
    if (clientId) {
      config.headers['X-Client-ID'] = clientId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Pedidos API calls (overview)
export const getPedidosOverview = async (): Promise<PedidosOverviewResponse> => {
  const response = await axiosInstance.get<PedidosOverviewResponse>('/pedidos');
  return response.data;
};

// Pedido API call (details)
export const getPedidoDetails = async (order_id: string): Promise<PedidoDetailResponse> => {
  const response = await axiosInstance.get<PedidoDetailResponse>(`/pedido/${order_id}`);
  return response.data;
};

// Fornecedores API calls (overview)
export const getFornecedores = async (period: string = 'all'): Promise<FornecedoresOverviewResponse> => {
  const response = await axiosInstance.get<FornecedoresOverviewResponse>('/fornecedores', {
    params: { period }
  });
  return response.data;
};

// Fornecedor API call (details) - Uses GOLD table for fast reads
export const getFornecedor = async (nome_fornecedor: string): Promise<FornecedorDetailResponse> => {
  const response = await axiosInstance.get<FornecedorDetailResponse>(`/fornecedor/${nome_fornecedor}/gold`);
  return response.data;
};

// Clientes API calls (overview)
export const getClientes = async (period: string = 'all'): Promise<ClientesOverviewResponse> => {
  const response = await axiosInstance.get<ClientesOverviewResponse>('/clientes', {
    params: { period }
  });
  return response.data;
};

// Cliente API call (details) - Uses GOLD table for fast reads
export const getCliente = async (nome_cliente: string): Promise<ClienteDetailResponse> => {
  const encoded = encodeURIComponent(nome_cliente || '');
  const response = await axiosInstance.get<ClienteDetailResponse>(`/cliente/${encoded}/gold`);
  return response.data;
};

// Produtos API calls (overview)
export const getProdutosOverview = async (period: string = 'all'): Promise<ProdutosOverviewResponse> => {
  const response = await axiosInstance.get<ProdutosOverviewResponse>('/produtos', {
    params: { period }
  });
  return response.data;
};

// Produto API call (details) - Uses GOLD table for fast reads
export const getProdutoDetails = async (nome_produto: string): Promise<ProdutoDetailResponse> => {
  const response = await axiosInstance.get<ProdutoDetailResponse>(`/produto/${nome_produto}/gold`);
  return response.data;
};

// Home metrics API call (dashboard overview)
export const getHomeMetrics = async (): Promise<HomeMetricsResponse> => {
  const response = await axiosInstance.get<HomeMetricsResponse>('/dashboard/home_gold');
  return response.data;
};

// Customer Indicators (from IndicatorService)
export const getCustomerIndicators = async (period: string = 'month', includeComparisons: boolean = false): Promise<CustomerMetricsResponse> => {
  const response = await axiosInstance.get<CustomerMetricsResponse>(`/indicators/customers`, {
    params: { period, include_comparisons: includeComparisons }
  });
  return response.data;
};

// Product Indicators (from IndicatorService)
export const getProductIndicators = async (period: string = 'month', includeComparisons: boolean = false): Promise<ProductMetricsResponse> => {
  const response = await axiosInstance.get<ProductMetricsResponse>(`/indicators/products`, {
    params: { period, include_comparisons: includeComparisons }
  });
  return response.data;
};

// Order Indicators (from IndicatorService)
export const getOrderIndicators = async (period: string = 'month', includeComparisons: boolean = false): Promise<OrderMetricsResponse> => {
  const response = await axiosInstance.get<OrderMetricsResponse>(`/indicators/orders`, {
    params: { period, include_comparisons: includeComparisons }
  });
  return response.data;
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
  const response = await axiosInstance.get<GeoClustersResponse>(`/dashboard/clientes/geo-clusters`, {
    params: { group_by: groupBy }
  });
  return response.data;
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
  const response = await axiosInstance.get<ProductFilterItem[]>('/filters/products');
  return response.data;
};

// Get customers list for filter dropdown
export const getCustomersForFilter = async (): Promise<CustomerFilterItem[]> => {
  const response = await axiosInstance.get<CustomerFilterItem[]>('/filters/customers');
  return response.data;
};

// Get customers who bought a specific product
export const getCustomersByProduct = async (productName: string, limit: number = 100): Promise<CustomerByProduct[]> => {
  const response = await axiosInstance.get<CustomerByProduct[]>(`/customers-by-product/${encodeURIComponent(productName)}`, {
    params: { limit }
  });
  return response.data;
};

// Get products bought by a specific customer
export const getProductsByCustomer = async (customerCpfCnpj: string, limit: number = 100): Promise<ProductByCustomer[]> => {
  const response = await axiosInstance.get<ProductByCustomer[]>(`/products-by-customer/${encodeURIComponent(customerCpfCnpj)}`, {
    params: { limit }
  });
  return response.data;
};

// Get monthly orders for a specific customer (time series)
export const getCustomerMonthlyOrders = async (customerCpfCnpj: string): Promise<MonthlyOrderData[]> => {
  const response = await axiosInstance.get<MonthlyOrderData[]>(`/customer-monthly-orders/${encodeURIComponent(customerCpfCnpj)}`);
  return response.data;
};

// User profile API call - creates client_id if doesn't exist
export interface MeResponse {
  client_id: string;
}

export const getMe = async (token: string): Promise<MeResponse> => {
  const response = await axios.get<MeResponse>(`${API_BASE_URL}/api/dashboard/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};
