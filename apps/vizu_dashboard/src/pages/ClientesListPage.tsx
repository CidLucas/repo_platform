import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon, Select, Badge } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal';
import { useClientesPageData } from '../hooks/useListData';
import {
  getCliente,
  getCustomersByProduct,
  getProductsByCustomer,
  getCustomersBySupplier
} from '../services/analyticsService';
import type {
  ClienteDetailResponse,
  CustomerByProduct,
  ProductByCustomer,
  CustomerBySupplier
} from '../services/analyticsService';

type ViewMode = 'all' | 'by-product' | 'by-customer' | 'by-supplier';

function ClientesListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [searchParams, setSearchParams] = useSearchParams();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const location = useLocation();
  const [selectedCliente, setSelectedCliente] = useState<ClienteDetailResponse | null>(null);

  // Use React Query hook for initial data (cached, parallel fetching)
  const { clientes: overviewData, productsFilter: productsList, loading, error: queryError } = useClientesPageData();

  // Local error state for user-triggered actions (clicking rows, etc.)
  const [localError, setLocalError] = useState<string | null>(null);
  const setError = (msg: string) => setLocalError(msg);
  const error = queryError || localError;

  // Filter state - initialize from URL params
  const viewParam = searchParams.get('view');
  const productParam = searchParams.get('product');
  const clientParam = searchParams.get('client');
  const supplierParam = searchParams.get('supplier');
  const supplierNameParam = searchParams.get('supplierName');

  const [viewMode, setViewMode] = useState<ViewMode>(
    viewParam === 'product' ? 'by-product' :
      viewParam === 'customer' ? 'by-customer' :
        viewParam === 'by-supplier' ? 'by-supplier' : 'all'
  );
  const [selectedProduct, setSelectedProduct] = useState<string>(productParam || '');
  const [selectedCustomer, setSelectedCustomer] = useState<string>(clientParam || '');
  const [customersByProduct, setCustomersByProduct] = useState<CustomerByProduct[]>([]);
  const [productsByCustomer, setProductsByCustomer] = useState<ProductByCustomer[]>([]);
  const [customersBySupplier, setCustomersBySupplier] = useState<CustomerBySupplier[]>([]);
  const [loadingProducts, setLoadingProducts] = useState<boolean>(false);

  // Handle URL parameters for filtering and modal opening (after data is loaded)
  useEffect(() => {
    // Only process URL params after overview data is loaded
    if (loading || !overviewData) return;

    const handleUrlParams = async () => {
      if (viewParam === 'product' && productParam) {
        setViewMode('by-product');
        setSelectedProduct(productParam);
      } else if (viewParam === 'customer' && clientParam) {
        // Show products bought by this customer
        setViewMode('by-customer');
        setSelectedCustomer(clientParam);
      } else if (viewParam === 'by-supplier' && supplierParam) {
        // Show customers who bought from this supplier
        setViewMode('by-supplier');
        await fetchCustomersBySupplierFilter(supplierParam);
      }
    };

    handleUrlParams();
  }, [loading, overviewData, viewParam, productParam, clientParam, supplierParam, onOpen]);

  // Fetch customers by supplier
  const fetchCustomersBySupplierFilter = async (cnpj: string) => {
    try {
      setLoadingProducts(true);
      const data = await getCustomersBySupplier(cnpj);
      setCustomersBySupplier(data);
    } catch (err: unknown) {
      console.error('Erro ao carregar clientes por fornecedor:', err);
      setCustomersBySupplier([]);
    } finally {
      setLoadingProducts(false);
    }
  };

  // Load customers when product filter changes
  useEffect(() => {
    const fetchCustomersByProduct = async () => {
      if (!selectedProduct) {
        setCustomersByProduct([]);
        return;
      }
      try {
        setLoadingProducts(true);
        const data = await getCustomersByProduct(selectedProduct);
        setCustomersByProduct(data);
      } catch (err: unknown) {
        console.error('Erro ao carregar clientes por produto:', err);
        setCustomersByProduct([]);
      } finally {
        setLoadingProducts(false);
      }
    };

    if (viewMode === 'by-product' && selectedProduct) {
      fetchCustomersByProduct();
    }
  }, [selectedProduct, viewMode]);

  // Load products when customer filter changes
  useEffect(() => {
    const fetchProductsByCustomer = async () => {
      if (!selectedCustomer) {
        setProductsByCustomer([]);
        return;
      }
      try {
        setLoadingProducts(true);
        // Need to get customer CPF/CNPJ first
        const clienteDetails = await getCliente(selectedCustomer);
        const cpfCnpj = clienteDetails?.dados_cadastrais?.receiver_cnpj;
        if (cpfCnpj) {
          const data = await getProductsByCustomer(cpfCnpj);
          setProductsByCustomer(data);
        }
      } catch (err: unknown) {
        console.error('Erro ao carregar produtos por cliente:', err);
        setProductsByCustomer([]);
      } finally {
        setLoadingProducts(false);
      }
    };

    if (viewMode === 'by-customer' && selectedCustomer) {
      fetchProductsByCustomer();
    }
  }, [selectedCustomer, viewMode]);

  const handleClientRowClick = async (clienteNome: string) => {
    try {
      if (!clienteNome || clienteNome.trim() === '') {
        console.warn('handleClientRowClick called with empty clienteNome', clienteNome);
        setError('Nome de cliente inválido ao tentar carregar detalhes.');
        return;
      }
      setSelectedCliente(null);
      const details = await getCliente(clienteNome);
      setSelectedCliente(details);
      onOpen();
    } catch (err: unknown) {
      console.error("Erro ao carregar detalhes do cliente:", err);
      setError(err instanceof Error ? err.message : 'Erro ao carregar detalhes do cliente.');
    }
  };

  const handleViewModeChange = (mode: ViewMode) => {
    setViewMode(mode);
    if (mode === 'all') {
      setSelectedProduct('');
      setSelectedCustomer('');
      setCustomersByProduct([]);
      setProductsByCustomer([]);
      setCustomersBySupplier([]);
      // Clear URL params
      setSearchParams({});
    }
  };

  const handleProductChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const product = e.target.value;
    setSelectedProduct(product);
    if (product) {
      setSearchParams({ view: 'product', product });
    } else {
      setSearchParams({ view: 'product' });
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
    const errorMessage = error || 'Não foi possível carregar os dados.';
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error">
            <AlertIcon />
            {errorMessage}
          </Alert>
        </Flex>
      </MainLayout>
    );
  }

  // Determine which data to show based on view mode
  const showingCustomersByProduct = viewMode === 'by-product' && selectedProduct && customersByProduct.length > 0;
  const showingProductsByCustomer = viewMode === 'by-customer' && selectedCustomer && productsByCustomer.length > 0;
  const showingCustomersBySupplier = viewMode === 'by-supplier' && customersBySupplier.length > 0;
  const clientesList = overviewData.ranking_por_receita || [];

  // Get title based on view mode
  const getPageTitle = () => {
    if (showingCustomersByProduct) {
      return `Clientes que compraram: ${selectedProduct.substring(0, 40)}${selectedProduct.length > 40 ? '...' : ''}`;
    }
    if (showingProductsByCustomer) {
      return `Produtos comprados por: ${selectedCustomer.substring(0, 40)}${selectedCustomer.length > 40 ? '...' : ''}`;
    }
    if (showingCustomersBySupplier && supplierNameParam) {
      return `Clientes de: ${decodeURIComponent(supplierNameParam).substring(0, 40)}${supplierNameParam.length > 40 ? '...' : ''}`;
    }
    return 'Clientes por Receita';
  };

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#FFB6C1"
        color="gray.800"
      >
        {/* Header */}
        <Flex justify="space-between" align="flex-end" mb="24px">
          <Box>
            <Text as="h1" textStyle="pageTitle" mt="32px">
              {getPageTitle()}
            </Text>
            {showingCustomersByProduct && (
              <Text fontSize="sm" color="gray.600" mt={1}>
                {customersByProduct.length} clientes encontrados
              </Text>
            )}
            {showingProductsByCustomer && (
              <Text fontSize="sm" color="gray.600" mt={1}>
                {productsByCustomer.length} produtos encontrados
              </Text>
            )}
            {showingCustomersBySupplier && (
              <Text fontSize="sm" color="gray.600" mt={1}>
                {customersBySupplier.length} clientes encontrados
              </Text>
            )}
          </Box>
          {(viewMode === 'by-supplier') ? (
            <Button
              variant="outline"
              borderColor="gray.800"
              onClick={() => handleViewModeChange('all')}
            >
              Ver Todos os Clientes
            </Button>
          ) : (
            <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
              Cadastrar Novo Cliente
            </Button>
          )}
        </Flex>

        {/* Filters */}
        <Flex gap={4} mb={6} align="center" flexWrap="wrap">
          <Flex gap={2}>
            <Button
              size="sm"
              variant={viewMode === 'all' ? 'solid' : 'outline'}
              bg={viewMode === 'all' ? 'white' : 'transparent'}
              borderColor="gray.800"
              onClick={() => handleViewModeChange('all')}
            >
              Todos os Clientes
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'by-product' ? 'solid' : 'outline'}
              bg={viewMode === 'by-product' ? 'white' : 'transparent'}
              borderColor="gray.800"
              onClick={() => handleViewModeChange('by-product')}
            >
              Filtrar por Produto
            </Button>
          </Flex>

          {viewMode === 'by-product' && (
            <Select
              placeholder="Selecione um produto..."
              bg="white"
              maxW="400px"
              value={selectedProduct}
              onChange={handleProductChange}
            >
              {productsList.map((product) => (
                <option key={product.nome} value={product.nome}>
                  {product.nome.substring(0, 50)}{product.nome.length > 50 ? '...' : ''}
                  {' '}({product.total_clientes} clientes)
                </option>
              ))}
            </Select>
          )}
        </Flex>

        {/* Table */}
        {loadingProducts ? (
          <Flex justify="center" align="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        ) : showingCustomersByProduct ? (
          /* Filtered by Product View - Shows Customers */
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Cliente</Th>
                <Th py={4} isNumeric>Gasto no Produto</Th>
                <Th py={4} isNumeric>Quantidade</Th>
                <Th py={4} isNumeric>Pedidos</Th>
                <Th py={4} isNumeric>Total Gasto (Geral)</Th>
                <Th py={4} isNumeric>% do Total</Th>
              </Tr>
            </Thead>
            <Tbody>
              {customersByProduct.map((customer, index) => (
                <Tr
                  key={customer.customer_cpf_cnpj}
                  borderBottom={index < customersByProduct.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleClientRowClick(customer.nome)}
                >
                  <Td py={5}>{customer.nome}</Td>
                  <Td py={5} isNumeric fontWeight="bold" color="green.700">
                    R$ {customer.produto_receita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                  <Td py={5} isNumeric>
                    {customer.produto_quantidade.toLocaleString('pt-BR')} kg
                  </Td>
                  <Td py={5} isNumeric>{customer.produto_pedidos}</Td>
                  <Td py={5} isNumeric>
                    R$ {customer.cliente_receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                  <Td py={5} isNumeric>
                    <Badge
                      colorScheme={Number(customer.percentual_do_total) > 50 ? 'green' : Number(customer.percentual_do_total) > 20 ? 'yellow' : 'gray'}
                      fontSize="sm"
                      px={2}
                    >
                      {Number(customer.percentual_do_total).toFixed(1)}%
                    </Badge>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        ) : showingProductsByCustomer ? (
          /* Filtered by Customer View - Shows Products */
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
              {productsByCustomer.map((product, index) => (
                <Tr
                  key={product.nome}
                  borderBottom={index < productsByCustomer.length - 1 ? "1px solid black" : "none"}
                  _hover={{ bg: "gray.50" }}
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
        ) : showingCustomersBySupplier ? (
          /* Filtered by Supplier View - Shows Customers */
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Cliente</Th>
                <Th py={4} isNumeric>Receita Total</Th>
                <Th py={4} isNumeric>Quantidade</Th>
                <Th py={4} isNumeric>Pedidos</Th>
                <Th py={4} isNumeric>Ticket Médio</Th>
              </Tr>
            </Thead>
            <Tbody>
              {customersBySupplier.map((customer, index) => (
                <Tr
                  key={customer.customer_cpf_cnpj}
                  borderBottom={index < customersBySupplier.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "pink.100" }}
                  onClick={() => handleClientRowClick(customer.nome)}
                >
                  <Td py={5}>{customer.nome}</Td>
                  <Td py={5} isNumeric fontWeight="bold" color="green.700">
                    R$ {customer.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                  <Td py={5} isNumeric>
                    {customer.quantidade_total.toLocaleString('pt-BR')} kg
                  </Td>
                  <Td py={5} isNumeric>{customer.num_pedidos}</Td>
                  <Td py={5} isNumeric>
                    R$ {customer.ticket_medio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        ) : (
          /* Default All Customers View */
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
              {clientesList.map((clienteItem, index) => (
                <Tr
                  key={clienteItem.nome}
                  borderBottom={index < clientesList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleClientRowClick(clienteItem.nome)}
                >
                  <Td py={5}>{clienteItem.nome}</Td>
                  <Td py={5}>{`R$ ${(clienteItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(clienteItem.ticket_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`${(clienteItem.frequencia_pedidos_mes ?? 0).toFixed(2)} / mês`}</Td>
                  <Td py={5}>{clienteItem.cluster_tier}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}

        {/* Empty state for filtered views */}
        {viewMode === 'by-product' && selectedProduct && !loadingProducts && customersByProduct.length === 0 && (
          <Flex justify="center" align="center" height="200px">
            <Text color="gray.600">Nenhum cliente encontrado para este produto.</Text>
          </Flex>
        )}

        {viewMode === 'by-customer' && selectedCustomer && !loadingProducts && productsByCustomer.length === 0 && (
          <Flex justify="center" align="center" height="200px">
            <Text color="gray.600">Nenhum produto encontrado para este cliente.</Text>
          </Flex>
        )}

        {/* Prompt to select product */}
        {viewMode === 'by-product' && !selectedProduct && (
          <Flex justify="center" align="center" height="200px">
            <Text color="gray.600">Selecione um produto para ver os clientes que o compraram.</Text>
          </Flex>
        )}
      </Flex>

      {/* Reusable ClienteDetailsModal */}
      <ClienteDetailsModal isOpen={isOpen} onClose={onClose} cliente={selectedCliente} />
    </MainLayout>
  );
}

export default ClientesListPage;
