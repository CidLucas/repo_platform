import axios from 'axios';

const API_BASE_URL = 'http://localhost:8005/api'; // Assuming this is the base URL for your Analytics API

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

export interface Fornecedor {
  id: string;
  nome: string;
  tipo: string;
  contatoPrincipal: string;
  totalFornecido: string;
  pedidosAtivos: number;
  status: string;
  avaliacaoMedia: string;
  tempoResposta: string;
  endereco: string;
  // Add other fields as per your API response for Fornecedores
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

// Fornecedores API calls
export const getFornecedores = async (): Promise<Fornecedor[]> => {
  const response = await axiosInstance.get<Fornecedor[]>('/fornecedores');
  return response.data;
};

export const getFornecedor = async (id: string): Promise<Fornecedor> => {
  const response = await axiosInstance.get<Fornecedor>(`/fornecedores/${id}`);
  return response.data;
};
