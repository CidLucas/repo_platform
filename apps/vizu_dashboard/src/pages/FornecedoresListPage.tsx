import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon, Badge, HStack } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor, getSuppliersByProduct } from '../services/analyticsService';
import type { FornecedoresOverviewResponse, FornecedorDetailResponse, SupplierByProduct } from '../services/analyticsService';

type ViewMode = 'all' | 'by-product';

function FornecedoresListPage() {
  const [searchParams] = useSearchParams();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedFornecedor, setSelectedFornecedor] = useState<FornecedorDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null);
  const [suppliersByProduct, setSuppliersByProduct] = useState<SupplierByProduct[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingByProduct, setLoadingByProduct] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [selectedProduct, setSelectedProduct] = useState<string | null>(null);
  const [productDisplayName, setProductDisplayName] = useState<string | null>(null);

  // Parse URL params on mount
  useEffect(() => {
    const viewParam = searchParams.get('view');
    const productParam = searchParams.get('product');
    const productNameParam = searchParams.get('productName');

    if (viewParam === 'by-product' && productParam) {
      setViewMode('by-product');
      setSelectedProduct(decodeURIComponent(productParam));
      setProductDisplayName(productNameParam ? decodeURIComponent(productNameParam) : decodeURIComponent(productParam));
    }
  }, [searchParams]);

  // Fetch all fornecedores
  useEffect(() => {
    const fetchFornecedoresData = async () => {
      try {
        setLoading(true);
        const data = await getFornecedores();
        setOverviewData(data);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar fornecedores.';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };
    fetchFornecedoresData();
  }, []);

  // Fetch suppliers by product when in by-product mode
  useEffect(() => {
    const fetchSuppliersByProduct = async () => {
      if (viewMode === 'by-product' && selectedProduct) {
        try {
          setLoadingByProduct(true);
          const data = await getSuppliersByProduct(selectedProduct);
          setSuppliersByProduct(data);
        } catch (err: unknown) {
          console.error('Erro ao carregar fornecedores por produto:', err);
          setSuppliersByProduct([]);
        } finally {
          setLoadingByProduct(false);
        }
      }
    };
    fetchSuppliersByProduct();
  }, [viewMode, selectedProduct]);

  const handleFornecedorRowClick = async (fornecedorNome: string) => {
    try {
      setSelectedFornecedor(null);
      const details = await getFornecedor(fornecedorNome);
      setSelectedFornecedor(details);
      onOpen();
    } catch (err: unknown) {
      console.error("Erro ao carregar detalhes do fornecedor:", err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar detalhes do fornecedor.';
      setError(errorMessage);
    }
  };

  const handleClearFilter = () => {
    setViewMode('all');
    setSelectedProduct(null);
    setProductDisplayName(null);
    setSuppliersByProduct([]);
    // Clear URL params
    window.history.replaceState({}, '', '/dashboard/fornecedores/lista');
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

  // Determine which data to show
  const showingByProduct = viewMode === 'by-product' && selectedProduct && suppliersByProduct.length > 0;
  const fornecedoresList = overviewData.ranking_por_receita || [];

  // Dynamic page title
  const pageTitle = showingByProduct
    ? `Fornecedores do Produto: ${productDisplayName || selectedProduct}`
    : 'Fornecedores por Receita';

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#92DAFF"
        color="gray.800"
      >
        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text as="h1" textStyle="pageTitle" mt="32px">{pageTitle}</Text>
            {showingByProduct && (
              <HStack mt={2}>
                <Badge colorScheme="blue" fontSize="sm">
                  Filtrado por produto
                </Badge>
                <Button size="xs" variant="outline" onClick={handleClearFilter}>
                  Limpar filtro
                </Button>
              </HStack>
            )}
          </Box>
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Fornecedor
          </Button>
        </Flex>
        
        {loadingByProduct ? (
          <Flex justify="center" align="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        ) : showingByProduct ? (
          // Table for suppliers by product
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita do Produto</Th>
                <Th py={4}>Quantidade Vendida</Th>
                <Th py={4}>Nº Pedidos</Th>
                <Th py={4}>Preço Unit. Médio</Th>
                <Th py={4}>Cidade/UF</Th>
              </Tr>
            </Thead>
            <Tbody>
              {suppliersByProduct.map((supplier, index) => (
                <Tr
                  key={supplier.supplier_cnpj || index}
                  borderBottom={index < suppliersByProduct.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleFornecedorRowClick(supplier.supplier_name)}
                >
                  <Td py={5}>{supplier.supplier_name}</Td>
                  <Td py={5}>{`R$ ${(supplier.total_revenue ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{(supplier.quantity_sold ?? 0).toLocaleString('pt-BR')}</Td>
                  <Td py={5}>{supplier.order_count ?? 0}</Td>
                  <Td py={5}>{`R$ ${(supplier.avg_unit_price ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`}</Td>
                  <Td py={5}>{`${supplier.endereco_cidade || '-'} / ${supplier.endereco_uf || '-'}`}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        ) : (
          // Default table - all fornecedores
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita Total</Th>
                <Th py={4}>Ticket Médio</Th>
                <Th py={4}>Frequência de Pedidos</Th>
                <Th py={4}>Tier</Th>
              </Tr>
            </Thead>
            <Tbody>
              {fornecedoresList.map((fornecedorItem, index) => (
                <Tr
                  key={fornecedorItem.nome}
                  borderBottom={index < fornecedoresList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleFornecedorRowClick(fornecedorItem.nome)}
                >
                  <Td py={5}>{fornecedorItem.nome}</Td>
                  <Td py={5}>{`R$ ${(fornecedorItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(fornecedorItem.ticket_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`${(fornecedorItem.frequencia_pedidos_mes ?? 0).toFixed(2)} / mês`}</Td>
                  <Td py={5}>{fornecedorItem.cluster_tier}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}

        {/* Empty state for by-product view */}
        {viewMode === 'by-product' && selectedProduct && !loadingByProduct && suppliersByProduct.length === 0 && (
          <Alert status="info" mt={4}>
            <AlertIcon />
            Nenhum fornecedor encontrado para o produto "{productDisplayName || selectedProduct}".
          </Alert>
        )}
      </Flex>

      <FornecedorDetailsModal isOpen={isOpen} onClose={onClose} fornecedor={selectedFornecedor} />
    </MainLayout>
  );
}

export default FornecedoresListPage;