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

export interface Produto {
  id: string;
  titulo: string;
  precoUnitario: string;
  estoque: number;
  categoria: string;
  fornecedor: string;
  status: string;
  clientName: string; // Supplier name
  vendasMes: string;
  avaliacaoMedia: string;
  descricaoDetalhada: string;
  // Add other fields as per your API response for Produtos
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
  ranking_produtos_mais_vendidos: any[]; // Define more strictly if needed
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

// Produtos API calls
export const getProdutos = async (): Promise<Produto[]> => {
  const response = await axiosInstance.get<Produto[]>('/produtos');
  return response.data;
};

export const getProduto = async (id: string): Promise<Produto> => {
  const response = await axiosInstance.get<Produto>(`/produtos/${id}`);
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
