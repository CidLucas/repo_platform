/**
 * React Query hooks for list pages (Clientes, Fornecedores, Produtos).
 * Provides automatic caching, background refetching, and deduplication.
 */
import { useQuery } from '@tanstack/react-query';
import {
  getClientes,
  getFornecedores,
  getProdutosOverview,
  getProductsForFilter,
} from '../services/analyticsService';

// ================== CLIENTES ==================

interface UseClientesOptions {
  period?: string;
  enabled?: boolean;
}

export const useClientes = ({ period = 'all', enabled = true }: UseClientesOptions = {}) => {
  return useQuery({
    queryKey: ['clientes', period],
    queryFn: () => getClientes(period),
    enabled,
    staleTime: 5 * 60 * 1000,  // 5 minutes
  });
};

// ================== FORNECEDORES ==================

interface UseFornecedoresOptions {
  period?: string;
  enabled?: boolean;
}

export const useFornecedores = ({ period = 'all', enabled = true }: UseFornecedoresOptions = {}) => {
  return useQuery({
    queryKey: ['fornecedores', period],
    queryFn: () => getFornecedores(period),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
};

// ================== PRODUTOS ==================

interface UseProdutosOptions {
  period?: string;
  enabled?: boolean;
}

export const useProdutos = ({ period = 'all', enabled = true }: UseProdutosOptions = {}) => {
  return useQuery({
    queryKey: ['produtos', period],
    queryFn: () => getProdutosOverview(period),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
};

// ================== FILTERS ==================

export const useProductsFilter = () => {
  return useQuery({
    queryKey: ['productsFilter'],
    queryFn: getProductsForFilter,
    staleTime: 10 * 60 * 1000,  // 10 minutes - filter options change rarely
  });
};

// ================== COMBINED HOOKS FOR LIST PAGES ==================

/**
 * Combined hook for ClientesListPage - fetches both clientes and products filter in parallel.
 * React Query automatically deduplicates and caches the requests.
 */
export const useClientesPageData = (period: string = 'all') => {
  const clientesQuery = useClientes({ period });
  const productsFilterQuery = useProductsFilter();

  return {
    clientes: clientesQuery.data ?? null,
    productsFilter: productsFilterQuery.data ?? [],
    loading: clientesQuery.isLoading || productsFilterQuery.isLoading,
    error: clientesQuery.error?.message || productsFilterQuery.error?.message || null,
    refetch: async () => {
      await Promise.all([clientesQuery.refetch(), productsFilterQuery.refetch()]);
    },
  };
};

/**
 * Combined hook for FornecedoresListPage.
 * Uses React Query for caching and automatic background refetching.
 */
export const useFornecedoresPageData = (period: string = 'all') => {
  const fornecedoresQuery = useFornecedores({ period });

  return {
    fornecedores: fornecedoresQuery.data ?? null,
    loading: fornecedoresQuery.isLoading,
    error: fornecedoresQuery.error?.message || null,
    refetch: fornecedoresQuery.refetch,
  };
};

/**
 * Combined hook for ProdutosListPage.
 * Uses React Query for caching and automatic background refetching.
 */
export const useProdutosPageData = (period: string = 'all') => {
  const produtosQuery = useProdutos({ period });

  return {
    produtos: produtosQuery.data ?? null,
    loading: produtosQuery.isLoading,
    error: produtosQuery.error?.message || null,
    refetch: produtosQuery.refetch,
  };
};
