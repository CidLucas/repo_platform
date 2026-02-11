import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { useProdutosPageData } from '../hooks/useListData';
import { getProdutoDetails, getProductsByCustomer, getProductsBySupplier } from '../services/analyticsService';
import type { ProdutoDetailResponse, ProdutoRankingReceita, ProductByCustomer } from '../services/analyticsService';

type ViewMode = 'all' | 'by-customer' | 'by-supplier';

function ProdutosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProduto, setSelectedProduto] = useState<ProdutoDetailResponse | null>(null);

  // Use React Query hook for main data (cached, automatic background refresh)
  const { produtos: overviewData, loading, error: queryError, refetch } = useProdutosPageData();

  // Local state for filtered views and user actions
  const [localError, setLocalError] = useState<string | null>(null);
  const error = queryError || localError;
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Filter state - initialize from URL params
  const viewParam = searchParams.get('view');
  const customerParam = searchParams.get('customer');
  const customerNameParam = searchParams.get('customerName');
  const supplierParam = searchParams.get('supplier');
  const supplierNameParam = searchParams.get('supplierName');

  const [viewMode, setViewMode] = useState<ViewMode>(
    viewParam === 'by-customer' ? 'by-customer' :
      viewParam === 'by-supplier' ? 'by-supplier' : 'all'
  );
  const [productsByFilter, setProductsByFilter] = useState<ProductByCustomer[]>([]);
  const [loadingFiltered, setLoadingFiltered] = useState<boolean>(false);

  // Handle manual refresh (uses React Query refetch)
  const handleRefresh = async () => {
    await refetch();
    setLastUpdate(new Date());
  };

  // Handle URL parameters for filtering
  useEffect(() => {
    if (loading) return;

    const handleUrlParams = async () => {
      if (viewParam === 'by-customer' && customerParam) {
        setViewMode('by-customer');
        await fetchProductsByCustomerFilter(customerParam);
      } else if (viewParam === 'by-supplier' && supplierParam) {
        setViewMode('by-supplier');
        await fetchProductsBySupplierFilter(supplierParam);
      }
    };

    handleUrlParams();
  }, [loading, viewParam, customerParam, supplierParam]);

  const fetchProductsByCustomerFilter = async (cpfCnpj: string) => {
    try {
      setLoadingFiltered(true);
      const data = await getProductsByCustomer(cpfCnpj);
      setProductsByFilter(data);
    } catch (err: unknown) {
      console.error('Erro ao carregar produtos por cliente:', err);
      setProductsByFilter([]);
    } finally {
      setLoadingFiltered(false);
    }
  };

  const fetchProductsBySupplierFilter = async (cnpj: string) => {
    try {
      setLoadingFiltered(true);
      const data = await getProductsBySupplier(cnpj);
      setProductsByFilter(data);
    } catch (err: unknown) {
      console.error('Erro ao carregar produtos por fornecedor:', err);
      setProductsByFilter([]);
    } finally {
      setLoadingFiltered(false);
    }
  };

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    if (mode === 'all') {
      setProductsByFilter([]);
      setSearchParams({});
    }
  };

  const handleProductRowClick = async (produtoItem: ProdutoRankingReceita) => {
    // When a product row is clicked, fetch the detailed data for that specific product
    try {
      setSelectedProduto(null); // Clear previous selection while loading
      const details = await getProdutoDetails(produtoItem.nome); // 'nome' is the product identifier
      setSelectedProduto(details);
      onOpen();
    } catch (err: unknown) {
      console.error("Erro ao carregar detalhes do produto:", err);
      setLocalError(err instanceof Error ? err.message : 'Erro ao carregar detalhes do produto.');
    }
  };

  // Conditional rendering for loading and error states
  if (loading) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Spinner size="xl" />
        </Flex>
      </MainLayout>
    );
  }

  if (error || !overviewData) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error">
            <AlertIcon />
            {error || 'Não foi possível carregar os dados.'}
          </Alert>
        </Flex>
      </MainLayout>
    );
  }

  // Use ranking_por_receita for the table
  const produtosList = overviewData.ranking_por_receita || []; // Ensure it's an array

  // Determine which data to show based on view mode
  const showingFilteredProducts = (viewMode === 'by-customer' || viewMode === 'by-supplier') && productsByFilter.length > 0;

  // Get title based on view mode
  const getPageTitle = () => {
    if (viewMode === 'by-customer' && customerNameParam) {
      return `Produtos comprados por: ${decodeURIComponent(customerNameParam).substring(0, 40)}${customerNameParam.length > 40 ? '...' : ''}`;
    }
    if (viewMode === 'by-supplier' && supplierNameParam) {
      return `Produtos vendidos por: ${decodeURIComponent(supplierNameParam).substring(0, 40)}${supplierNameParam.length > 40 ? '...' : ''}`;
    }
    return 'Produtos por Receita';
  };

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#FFF856" // Page background color for Produtos
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Box>
            <Flex align="center" gap={2} mb={2}>
              <Text fontSize="sm" color="gray.600">
                Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </Text>
              <IconButton
                icon={<RepeatIcon />}
                aria-label="Atualizar dados"
                size="xs"
                onClick={handleRefresh}
                isLoading={loading}
              />
            </Flex>
            <Text as="h1" textStyle="pageTitle">{getPageTitle()}</Text>
            {showingFilteredProducts && (
              <Text fontSize="sm" color="gray.600" mt={1}>
                {productsByFilter.length} produtos encontrados
              </Text>
            )}
          </Box>
          {(viewMode === 'by-customer' || viewMode === 'by-supplier') ? (
            <Button
              variant="outline"
              borderColor="gray.800"
              onClick={() => handleViewModeChange('all')}
            >
              Ver Todos os Produtos
            </Button>
          ) : (
            <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
              Cadastrar Novo Produto
            </Button>
          )}
        </Flex>

        {loading ? (
          <Flex justify="center" align="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        ) : error ? (
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        ) : loadingFiltered ? (
          <Flex justify="center" align="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        ) : showingFilteredProducts ? (
          /* Filtered Products View */
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Produto</Th>
                <Th py={4} isNumeric>Receita Total</Th>
                <Th py={4} isNumeric>Quantidade</Th>
                <Th py={4} isNumeric>Pedidos</Th>
                <Th py={4} isNumeric>Preço Médio</Th>
              </Tr>
            </Thead>
            <Tbody>
              {productsByFilter.map((product, index) => (
                <Tr
                  key={product.nome}
                  borderBottom={index < productsByFilter.length - 1 ? "1px solid black" : "none"}
                  _hover={{ bg: "yellow.100" }}
                >
                  <Td py={5}>{product.nome}</Td>
                  <Td py={5} isNumeric fontWeight="bold" color="green.700">
                    R$ {product.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                  <Td py={5} isNumeric>
                    {product.quantidade_total.toLocaleString('pt-BR')} kg
                  </Td>
                  <Td py={5} isNumeric>{product.num_pedidos}</Td>
                  <Td py={5} isNumeric>
                    R$ {product.valor_unitario_medio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        ) : (
          /* Default All Products View */
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita Total</Th>
                <Th py={4}>Valor Unitário Médio</Th>
              </Tr>
            </Thead>
            <Tbody>
              {produtosList.map((produtoItem, index) => (
                <Tr
                  key={produtoItem.nome}
                  borderBottom={index < produtosList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "yellow.100" }}
                  onClick={() => handleProductRowClick(produtoItem)}
                >
                  <Td py={5}>{produtoItem.nome}</Td>
                  <Td py={5}>{`R$ ${(produtoItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(produtoItem.valor_unitario_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}

        {/* Empty state for filtered views */}
        {(viewMode === 'by-customer' || viewMode === 'by-supplier') && !loadingFiltered && productsByFilter.length === 0 && (
          <Flex justify="center" align="center" height="200px">
            <Text color="gray.600">Nenhum produto encontrado para este filtro.</Text>
          </Flex>
        )}
      </Flex>

      {/* Reusable ProdutoDetailsModal */}
      <ProdutoDetailsModal isOpen={isOpen} onClose={onClose} produto={selectedProduto} />
    </MainLayout>
  );
}

export default ProdutosListPage;