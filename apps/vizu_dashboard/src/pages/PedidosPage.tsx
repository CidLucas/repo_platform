import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react'; // Added useEffect
import { PedidoDetailsModal } from '../components/PedidoDetailsModal';
import { getPedidosOverview, getPedidoDetails, getOrderIndicators } from '../services/analyticsService';
import type { PedidosOverviewResponse, PedidoDetailResponse, PedidoItem, OrderMetricsResponse } from '../services/analyticsService';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';

function PedidosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<PedidoDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<PedidosOverviewResponse | null>(null);
  const [orderMetrics, setOrderMetrics] = useState<OrderMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchPedidosData = async () => {
    try {
      setLoading(true);

      // Fetch both overview data and order indicators in parallel
      const [overviewResponse, metricsResponse] = await Promise.all([
        getPedidosOverview(),
        getOrderIndicators(selectedPeriod)
      ]);

      console.log('Pedidos overview received:', overviewResponse);
      console.log('Order metrics received:', metricsResponse);

      setOverviewData(overviewResponse);
      setOrderMetrics(metricsResponse);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      console.error('Error fetching pedidos:', err);
      setError(err.message || 'Erro ao carregar pedidos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPedidosData();
  }, [selectedPeriod]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMiniCardClick = async (item: PedidoItem) => {
    // When a mini-card is clicked, fetch the detailed data for that specific pedido
    try {
      setSelectedItem(null); // Clear previous selection while loading
      const details = await getPedidoDetails(item.order_id);
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do pedido:", err);
      setError(err.message || 'Erro ao carregar detalhes do pedido.');
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

  // Map PedidoItem to the format expected by ListCard
  const listCardItems = (overviewData.ultimos_pedidos || []).map((item: PedidoItem) => ({
    id: item.order_id,
    title: `Pedido ${item.order_id}`,
    description: `Cliente: ${item.id_cliente} | Total: R$ ${item.ticket_pedido.toLocaleString('pt-BR')}`,
    status: `${item.qtd_produtos} itens`,
  }));

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#F9BBCB" // Page background color for Pedidos
        color="gray.800" // Text color for visibility
      >
        {/* Refresh section */}
        <Flex justify="flex-end" mb={2}>
          <HStack spacing={2}>
            <Text fontSize="sm" color="gray.600">
              Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </Text>
            <IconButton
              icon={<RepeatIcon />}
              aria-label="Atualizar dados"
              size="sm"
              onClick={fetchPedidosData}
              isLoading={loading}
            />
          </HStack>
        </Flex>
        {/* New Header Content for Pedidos Page */}
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Big numbers and selectors */}
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">TOTAL DE PEDIDOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
              {orderMetrics?.total || 0}
            </Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">PEDIDOS CONCLUÍDOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
              {orderMetrics?.by_status?.completed || orderMetrics?.by_status?.Completed || 0}
            </Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">PEDIDOS PENDENTES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
              {orderMetrics?.by_status?.pending || orderMetrics?.by_status?.Pending || 0}
            </Text>
          </Box>
          <HStack spacing="4" position="relative"> {/* HStack for multiple Selects */}
            <Select
              value={selectedPeriod}
              onChange={handlePeriodChange}
              width="150px"
              bg="white"
              color="gray.800"
            >
              <option value="week">Última semana</option>
              <option value="month">Último mês</option>
              <option value="quarter">Último trimestre</option>
              <option value="year">Último ano</option>
            </Select>
            <Select placeholder="Métricas" width="150px" bg="white" color="gray.800">
              <option value="receita">Receita</option>
              <option value="quantidade">Quantidade</option>
              <option value="ticket_medio">Ticket Médio</option>
            </Select>
          </HStack>
        </Flex>
        {/* Grid of DashboardCards */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* Card Type 1: Métricas de Pedidos */}
          <DashboardCard
            title="Métricas de Pedidos"
            size="large"
            bgColor="#FFD3E1"
            graphData={{
              values: orderMetrics
                ? [
                  { name: 'Total Pedidos', value: orderMetrics.total },
                  { name: 'Receita', value: Math.round(orderMetrics.revenue / 1000) }, // Convert to thousands for readability
                  { name: 'Ticket Médio', value: Math.round(orderMetrics.avg_order_value) },
                  { name: 'Crescimento %', value: Math.round(orderMetrics.growth_rate || 0) }
                ]
                : []
            }}
            scorecardValue={orderMetrics ? `R$ ${(orderMetrics.revenue / 1000).toFixed(1)}K` : 'R$ 0'}
            scorecardLabel="Total Vendido"
            kpiItems={
              orderMetrics
                ? [
                  {
                    label: `Total de Pedidos: ${orderMetrics.total.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Número total de pedidos no período de {orderMetrics.period}</Text>
                        {orderMetrics.by_status && Object.keys(orderMetrics.by_status).length > 0 && (
                          <Box mt={2}>
                            <Text fontSize="sm" fontWeight="bold">Por Status:</Text>
                            {Object.entries(orderMetrics.by_status).map(([status, count]) => (
                              <Text key={status} fontSize="sm">• {status}: {count}</Text>
                            ))}
                          </Box>
                        )}
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>total</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Receita Total: R$ ${orderMetrics.revenue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    content: (
                      <Box>
                        <Text>Valor total de receita gerada pelos pedidos no período</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>revenue</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Ticket Médio: R$ ${orderMetrics.avg_order_value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    content: (
                      <Box>
                        <Text>Valor médio por pedido (receita total ÷ número de pedidos)</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>avg_order_value</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Taxa de Crescimento: ${orderMetrics.growth_rate !== null ? (orderMetrics.growth_rate >= 0 ? '+' : '') + orderMetrics.growth_rate.toFixed(1) : 'N/A'}%`,
                    content: (
                      <Box>
                        <Text>Crescimento percentual em relação ao período anterior</Text>
                        {orderMetrics.growth_rate !== null && (
                          <Text mt={2} color={orderMetrics.growth_rate >= 0 ? 'green.600' : 'red.600'} fontWeight="bold">
                            {orderMetrics.growth_rate >= 0 ? '📈 Crescimento positivo' : '📉 Requer atenção'}
                          </Text>
                        )}
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>growth_rate</strong></Text>
                      </Box>
                    )
                  }
                ]
                : undefined
            }
            modalLeftBgColor="#FFD3E1"
            modalRightBgColor="#F9BBCB"
            modalContent={<Text>Métricas detalhadas de pedidos no período de {orderMetrics?.period || 'mês'}</Text>}
          />

          {/* Card Type 1.5: Volume de Pedidos ao Longo do Tempo */}
          <DashboardCard
            title="Volume de Pedidos"
            size="large"
            bgColor="#FFF4C7"
            graphData={{
              values: overviewData?.chart_pedidos_no_tempo
                ? overviewData.chart_pedidos_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total_cumulativo || 0
                }))
                : []
            }}
            scorecardValue={orderMetrics ? `${orderMetrics.total}` : '0'}
            scorecardLabel="Total de Pedidos"
            kpiItems={
              orderMetrics && overviewData
                ? [
                  {
                    label: `Total de Pedidos: ${orderMetrics.total}`,
                    content: <Text>Número total de pedidos processados no período</Text>
                  },
                  {
                    label: 'Tendência de Crescimento',
                    content: <Text>Acompanhe a evolução do volume de pedidos ao longo do tempo. O gráfico mostra o total cumulativo de pedidos.</Text>
                  }
                ]
                : undefined
            }
            modalLeftBgColor="#FFF4C7"
            modalRightBgColor="#FFE9A0"
            modalContent={<Text>Evolução do volume de pedidos ao longo do tempo</Text>}
          />

          {/* Card Type 2: List of Pedidos */}
          <ListCard
            title="Últimos Pedidos"
            items={listCardItems} // Use mapped data from analytics API
            onMiniCardClick={(item: { id: string }) => {
              const pedidoItem = overviewData.ultimos_pedidos.find((p: PedidoItem) => p.order_id === item.id);
              if (pedidoItem) handleMiniCardClick(pedidoItem);
            }}
            viewAllLink="/dashboard/pedidos/lista" // Link to the full list page
          />

          {/* Card Type 3: Histórico de Pedidos */}
          <DashboardCard
            title="Histórico de Pedidos"
            size="small"
            bgColor="#FFD3E1" // Specific color for Pedidos module
            mainText="Histórico completo de todos os pedidos."
            modalLeftBgColor="#FFD3E1" // Modal left background
            modalRightBgColor="#F9BBCB" // Modal right background
            modalContent={<Text>Detalhes do histórico de pedidos</Text>}
          />

          {/* Card Type 4: Distribuição Geográfica (Unchanged) */}
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white" // Unchanged
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }}
            mainText="Principais regiões de entrega de pedidos."
            modalLeftBgColor="#FFD3E1" // Modal left background
            modalRightBgColor="#F9BBCB" // Modal right background
            modalContent={<Text>Detalhes do mapa de distribuição de pedidos</Text>}
          />
        </Flex>
      </Flex>

      {/* Reusable PedidoDetailsModal */}
      <PedidoDetailsModal isOpen={isOpen} onClose={onClose} pedido={selectedItem} />
    </MainLayout>
  );
}

export default PedidosPage;