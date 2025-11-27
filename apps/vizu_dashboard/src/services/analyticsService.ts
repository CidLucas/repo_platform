import axios from 'axios';

const API_BASE_URL = 'http://localhost:8009/api'; // Assuming this is the base URL for your Analytics API

// --- Type Definitions ---
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
  // Add other fields as per your API response for Pedidos
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

// Corresponds to the Pydantic 'FornecedoresOverviewResponse'
export interface FornecedoresOverviewResponse {
  scorecard_total_fornecedores: number;
  chart_fornecedores_no_tempo: ChartDataPoint[];
  chart_fornecedores_por_regiao: ChartDataPoint[];
  chart_cohort_fornecedores: ChartDataPoint[];
  ranking_por_receita: RankingItem[];
  ranking_por_qtd_media: RankingItem[];
  ranking_por_ticket_medio: RankingItem[];
  ranking_por_frequencia: RankingItem[];
  ranking_produtos_mais_vendidos: { nome: string; receita_total: number; valor_unitario_medio: number; }[]; // Corrected type based on backend
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
  scorecards: RankingItem | null; // Optional because it can be {}
  rankings_internos: {
    mix_de_produtos_por_receita: RankingItem[];
    // ultimos_pedidos: any[]; // Removed from rankings_internos in backend
  };
}

// Corresponds to the Pydantic 'ProdutosOverviewResponse'
export interface ProdutosOverviewResponse {
  scorecard_total_itens_unicos: number;
  ranking_por_receita: { nome: string; receita_total: number; valor_unitario_medio: number; }[]; // Matching backend's simplified return
  ranking_por_volume: { nome: string; quantidade_total: number; valor_unitario_medio: number; }[]; // Matching backend's simplified return
  ranking_por_ticket_medio: { nome: string; ticket_medio: number; valor_unitario_medio: number; }[]; // Matching backend's simplified return
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

// Placeholder for authentication token (replace with actual token retrieval logic)
const getAuthToken = (): string | null => {
  // In a real app, you'd get this from localStorage, a Redux store, Context API, etc.
  return localStorage.getItem('authToken'); // Example
};

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the auth token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Pedidos API calls
export const getPedidos = async (): Promise<Pedido[]> => {
  const response = await axiosInstance.get<Pedido[]>('/pedidos');
  return response.data;
};

export const getPedido = async (id: string): Promise<Pedido> => {
  const response = await axiosInstance.get<Pedido>(`/pedidos/${id}`);
  return response.data;
};

// Fornecedores API calls (overview)
export const getFornecedores = async (): Promise<FornecedoresOverviewResponse> => {
  const response = await axiosInstance.get<FornecedoresOverviewResponse>('/fornecedores');
  return response.data;
};

// Fornecedor API call (details)
export const getFornecedor = async (nome_fornecedor: string): Promise<FornecedorDetailResponse> => {
  const response = await axiosInstance.get<FornecedorDetailResponse>(`/fornecedor/${nome_fornecedor}`);
  return response.data;
};

// Clientes API calls (overview)
export const getClientes = async (): Promise<ClientesOverviewResponse> => {
  const response = await axiosInstance.get<ClientesOverviewResponse>('/clientes');
  return response.data;
};

// Cliente API call (details)
export const getCliente = async (nome_cliente: string): Promise<ClienteDetailResponse> => {
  const response = await axiosInstance.get<ClienteDetailResponse>(`/cliente/${nome_cliente}`);
  return response.data;
};

// Produtos API calls (overview)
export const getProdutosOverview = async (): Promise<ProdutosOverviewResponse> => {
  const response = await axiosInstance.get<ProdutosOverviewResponse>('/produtos');
  return response.data;
};

// Produto API call (details)
export const getProdutoDetails = async (nome_produto: string): Promise<ProdutoDetailResponse> => {
  const response = await axiosInstance.get<ProdutoDetailResponse>(`/produto/${nome_produto}`);
  return response.data;
};
