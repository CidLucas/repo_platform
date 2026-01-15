import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import React, { useState, useEffect } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutosOverview, getProdutoDetails, getProductIndicators } from '../services/analyticsService';
import type { ProdutosOverviewResponse, ProdutoDetailResponse, ProdutoRankingReceita, ProductMetricsResponse } from '../services/analyticsService';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';

function ProdutosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedProduto, setSelectedProduto] = useState<ProdutoDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<ProdutosOverviewResponse | null>(null);
  const [productMetrics, setProductMetrics] = useState<ProductMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchProdutosData = async () => {
    try {
      setLoading(true);

      // Fetch both overview data and product indicators in parallel
      const [overviewResponse, metricsResponse] = await Promise.all([
        getProdutosOverview(),
        getProductIndicators(selectedPeriod)
      ]);

      console.log('Produtos overview received:', overviewResponse);
      console.log('Product metrics received:', metricsResponse);

      setOverviewData(overviewResponse);
      setProductMetrics(metricsResponse);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      console.error('Error fetching produtos:', err);
      setError(err.message || 'Erro ao carregar produtos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProdutosData();
  }, [selectedPeriod]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleProductRowClick = async (produtoItem: ProdutoRankingReceita) => {
    // When a product row is clicked, fetch the detailed data for that specific product
    try {
      setSelectedProduto(null); // Clear previous selection while loading
      const details = await getProdutoDetails(produtoItem.nome); // 'nome' is the product identifier
      setSelectedProduto(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do produto:", err);
      setError(err.message || 'Erro ao carregar detalhes do produto.');
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
                onClick={fetchProdutosData}
                isLoading={loading}
              />
            </Flex>
            <Text as="h1" textStyle="pageTitle">Produtos por Receita</Text> {/* Adjusted title */}
          </Box>
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Produto
          </Button>
        </Flex>

        {/* Dashboard Cards Section */}
        <Flex wrap="wrap" justify="center" gap="16px" mb="36px">
          <DashboardCard
            title="Métricas de Produtos"
            size="large"
            bgColor="#C7E7FF"
            graphData={{
              values: productMetrics
                ? [
                  { name: 'Total Vendido', value: productMetrics.total_sold },
                  { name: 'Produtos Únicos', value: productMetrics.unique_products },
                  { name: 'Preço Médio', value: Math.round(productMetrics.avg_price) },
                  { name: 'Alertas Estoque', value: productMetrics.low_stock_alerts }
                ]
                : []
            }}
            scorecardValue={`${overviewData?.scorecard_total_itens_unicos || 0}`}
            scorecardLabel="Produtos Únicos"
            kpiItems={
              productMetrics
                ? [
                  {
                    label: `Total Vendido: ${productMetrics.total_sold.toLocaleString('pt-BR')} unidades`,
                    content: (
                      <Box>
                        <Text>Quantidade total de produtos vendidos no período de {productMetrics.period}</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>total_sold</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Produtos Únicos: ${productMetrics.unique_products.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Número de produtos diferentes vendidos no período</Text>
                        {productMetrics.top_sellers && productMetrics.top_sellers.length > 0 && (
                          <Text mt={2} fontSize="sm">Top Sellers: {productMetrics.top_sellers.length} produtos em destaque</Text>
                        )}
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>unique_products</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Preço Médio: R$ ${productMetrics.avg_price.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    content: (
                      <Box>
                        <Text>Valor médio de venda por produto no período</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>avg_price</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Alertas de Estoque: ${productMetrics.low_stock_alerts}`,
                    content: (
                      <Box>
                        <Text>Produtos com estoque baixo que precisam de reposição</Text>
                        {productMetrics.low_stock_alerts > 0 && (
                          <Text mt={2} color="orange.600" fontWeight="bold">⚠️ Atenção necessária!</Text>
                        )}
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>low_stock_alerts</strong></Text>
                      </Box>
                    )
                  }
                ]
                : undefined
            }
            modalLeftBgColor="#C7E7FF"
            modalRightBgColor="#A0D7FF"
            modalContent={<Text>Métricas detalhadas de produtos no período de {productMetrics?.period || 'mês'}</Text>}
          />

          <DashboardCard
            title="Crescimento do Catálogo"
            size="large"
            bgColor="#E0F7FF"
            graphData={{
              values: overviewData?.chart_produtos_no_tempo
                ? overviewData.chart_produtos_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total_cumulativo || 0
                }))
                : []
            }}
            scorecardValue={`${overviewData?.scorecard_total_itens_unicos || 0}`}
            scorecardLabel="Total de Produtos"
            kpiItems={
              overviewData
                ? [
                  {
                    label: `Total de Produtos Únicos: ${overviewData.scorecard_total_itens_unicos || 0}`,
                    content: <Text>Número total de produtos diferentes no catálogo</Text>
                  },
                  {
                    label: 'Evolução do Catálogo',
                    content: <Text>Acompanhe o crescimento do seu catálogo de produtos ao longo do tempo. Cada ponto representa o total cumulativo de produtos únicos.</Text>
                  }
                ]
                : undefined
            }
            modalLeftBgColor="#E0F7FF"
            modalRightBgColor="#B8ECFF"
            modalContent={<Text>Evolução do catálogo de produtos ao longo do tempo</Text>}
          />
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
        ) : (
          <Table variant="unstyled"> {/* Removed size="md" */}
            <Thead>
              <Tr borderBottom="3px solid black"> {/* Thick black line below headers */}
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita Total</Th>
                <Th py={4}>Valor Unitário Médio</Th>
                {/* Add other relevant columns from RankingItem if needed */}
              </Tr>
            </Thead>
            <Tbody>
              {produtosList.map((produtoItem, index) => (
                <Tr
                  key={produtoItem.nome} // Use nome as key
                  borderBottom={index < produtosList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleProductRowClick(produtoItem)}
                >
                  <Td py={5}>{produtoItem.nome}</Td> {/* Increased py */}
                  <Td py={5}>{`R$ ${(produtoItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(produtoItem.valor_unitario_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                  {/* Add other relevant columns from RankingItem if needed */}
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Flex>

      {/* Reusable ProdutoDetailsModal */}
      <ProdutoDetailsModal isOpen={isOpen} onClose={onClose} produto={selectedProduto} />
    </MainLayout>
  );
}

export default ProdutosListPage;