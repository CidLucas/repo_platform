import { Box, Flex, Text, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { PerformanceCard, MetricSlide } from '../components/PerformanceCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal';
import { getClientes, getCliente, getCustomerIndicators } from '../services/analyticsService';
import type { ClientesOverviewResponse, ClienteDetailResponse, CustomerMetricsResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { useGeoClusters } from '../hooks/useGeoClusters';
import { useMVMonthlySales, useMVCustomers } from '../hooks/useMVData';

type MetricType = 'receita' | 'ticket_medio' | 'qtd_pedidos' | 'clientes';

function ClientesPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ClienteDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<ClientesOverviewResponse | null>(null);
  const [customerMetrics, setCustomerMetrics] = useState<CustomerMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  // Fetch from materialized views for faster chart data
  const { chartData: mvChartData, loading: mvLoading } = useMVMonthlySales();
  const { data: mvCustomers } = useMVCustomers();

  // Fetch geographic clusters for map visualization
  const { data: geoClusters, loading: loadingGeoClusters } = useGeoClusters('state');

  // Memoize chart data from MV (falls back to empty if MV not available)
  const chartRevenueData = useMemo(() => {
    if (mvChartData && mvChartData.length > 0) {
      return mvChartData.map(d => ({ name: d.name, value: d.revenue, total: d.revenue }));
    }
    return (overviewData?.chart_receita_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0, total: d.total ?? d.value ?? 0 }));
  }, [mvChartData, overviewData]);

  const chartOrdersData = useMemo(() => {
    if (mvChartData && mvChartData.length > 0) {
      return mvChartData.map(d => ({ name: d.name, value: d.orders, total: d.orders }));
    }
    return (overviewData?.chart_clientes_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0, total: d.total ?? d.value ?? 0 }));
  }, [mvChartData, overviewData]);

  const chartCustomersData = useMemo(() => {
    if (mvChartData && mvChartData.length > 0) {
      return mvChartData.map(d => ({ name: d.name, value: d.customers, total: d.customers }));
    }
    return (overviewData?.chart_clientes_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0, total: d.total ?? d.value ?? 0 }));
  }, [mvChartData, overviewData]);

  const chartAvgOrderData = useMemo(() => {
    if (mvChartData && mvChartData.length > 0) {
      return mvChartData.map(d => ({ name: d.name, value: d.avgOrderValue, total: d.avgOrderValue }));
    }
    return (overviewData?.chart_ticketmedio_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0, total: d.total ?? d.value ?? 0 }));
  }, [mvChartData, overviewData]);

  const fetchClientesData = useCallback(async () => {
    try {
      setLoading(true);

      const [overviewResponse, metricsResponse] = await Promise.all([
        getClientes(),
        getCustomerIndicators('month')
      ]);

      if (Array.isArray(overviewResponse)) {
        console.error('API returned array instead of ClientesOverviewResponse object');
        setError('Formato de dados inválido retornado pela API');
        return;
      }

      setOverviewData(overviewResponse);
      setCustomerMetrics(metricsResponse);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: unknown) {
      console.error('Error fetching clientes:', err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar dados dos clientes.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClientesData();
  }, [fetchClientesData]);

  const handleSlideChange = useCallback((_index: number, slideId: string) => {
    setSelectedMetric(slideId as MetricType);
  }, []);

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    try {
      if (!clickedItem?.id || clickedItem.id.trim() === '') {
        console.warn('handleMiniCardClick called with empty client id', clickedItem);
        setError('Nome de cliente inválido ao tentar carregar detalhes.');
        return;
      }
      setSelectedItem(null);
      const details = await getCliente(clickedItem.id);
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do cliente:", err);
      setError(err.message || 'Erro ao carregar detalhes do cliente.');
    }
  };

  // Performance card slides
  const performanceSlides: MetricSlide[] = useMemo(() => {
    if (!overviewData) return [];

    const formatCurrency = (value: number) => 
      new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    
    const formatNumber = (value: number) => 
      new Intl.NumberFormat('pt-BR').format(value);

    // Calculate totals
    const clientes = overviewData.ranking_por_receita || [];
    const totalReceita = clientes.reduce((sum, c: any) => sum + (c.receita_total || c.lifetime_value || 0), 0);
    const totalPedidos = clientes.reduce((sum, c: any) => sum + (c.num_pedidos_unicos || c.total_orders || 0), 0);
    const avgTicket = clientes.length > 0
      ? clientes.reduce((sum, c: any) => sum + (c.ticket_medio || c.avg_order_value || 0), 0) / clientes.length
      : 0;

    return [
      {
        id: 'receita',
        title: 'Receita no Tempo',
        data: chartRevenueData,
        dataKey: 'value',
        lineColor: '#82ca9d',
        metricLabel: 'RECEITA TOTAL',
        metricValue: formatCurrency(totalReceita),
        rankingKey: 'ranking_por_receita',
      },
      {
        id: 'ticket_medio',
        title: 'Ticket Médio no Tempo',
        data: chartAvgOrderData,
        dataKey: 'value',
        lineColor: '#ffc658',
        metricLabel: 'TICKET MÉDIO',
        metricValue: formatCurrency(avgTicket),
        rankingKey: 'ranking_por_ticket_medio',
      },
      {
        id: 'qtd_pedidos',
        title: 'Pedidos no Tempo',
        data: chartOrdersData,
        dataKey: 'value',
        lineColor: '#8884d8',
        metricLabel: 'TOTAL DE PEDIDOS',
        metricValue: formatNumber(totalPedidos),
        rankingKey: 'ranking_por_qtd_pedidos',
      },
      {
        id: 'clientes',
        title: 'Clientes Únicos no Tempo',
        data: chartCustomersData,
        dataKey: 'value',
        lineColor: '#ff7300',
        metricLabel: 'TOTAL DE CLIENTES',
        metricValue: formatNumber(overviewData.scorecard_total_clientes || 0),
        rankingKey: 'ranking_por_receita',
      },
    ];
  }, [overviewData, chartRevenueData, chartAvgOrderData, chartOrdersData, chartCustomersData]);

  // List card items based on selected metric
  const listCardItems = useMemo(() => {
    if (!overviewData) return [];

    const getRankingData = () => {
      switch (selectedMetric) {
        case 'receita':
          return overviewData.ranking_por_receita || [];
        case 'ticket_medio':
          return overviewData.ranking_por_ticket_medio || [];
        case 'qtd_pedidos':
          return overviewData.ranking_por_qtd_pedidos || [];
        case 'clientes':
          return overviewData.ranking_por_receita || [];
        default:
          return overviewData.ranking_por_receita || [];
      }
    };

    return getRankingData().map((item: any) => {
      let description = '';
      if (selectedMetric === 'receita') {
        description = `Receita: R$ ${(item.receita_total ?? item.lifetime_value ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'ticket_medio') {
        description = `Ticket Médio: R$ ${(item.ticket_medio ?? item.avg_order_value ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'qtd_pedidos') {
        description = `Qtd Pedidos: ${(item.num_pedidos_unicos ?? item.total_orders ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'clientes') {
        description = `Receita: R$ ${(item.receita_total ?? item.lifetime_value ?? 0).toLocaleString('pt-BR')}`;
      }
      return {
        id: item.nome,
        title: item.nome,
        description,
        status: item.cluster_tier,
      };
    });
  }, [overviewData, selectedMetric]);

  // List card title based on selected metric
  const listCardTitle = useMemo(() => {
    switch (selectedMetric) {
      case 'receita':
        return 'Clientes com Maior Receita';
      case 'ticket_medio':
        return 'Clientes com Maior Ticket Médio';
      case 'qtd_pedidos':
        return 'Clientes com Mais Pedidos';
      case 'clientes':
        return 'Clientes com Maior Receita';
      default:
        return 'Clientes com Maior Receita';
    }
  }, [selectedMetric]);

  // Calculate new customers metrics
  const { newCustomersCount, growthPercentage } = useMemo(() => {
    if (!overviewData) return { newCustomersCount: 0, growthPercentage: '0.0' };

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const newCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
      const firstSaleDate = new Date(item.primeira_venda);
      return firstSaleDate >= thirtyDaysAgo;
    }).length;

    const totalCustomers = overviewData.scorecard_total_clientes || 0;
    const growth = totalCustomers > 0
      ? ((newCount / (totalCustomers - newCount)) * 100).toFixed(1)
      : '0.0';

    return { newCustomersCount: newCount, growthPercentage: growth };
  }, [overviewData]);

  // KPI Items for modal
  const kpiItems = useMemo(() => {
    if (!overviewData) return [];

    const clientes = overviewData.ranking_por_receita || [];
    const totalClientes = clientes.length || 1;

    const mediaReceitaPorCliente = clientes.reduce((sum, c: any) => sum + (c.receita_total || 0), 0) / totalClientes;
    const mediaFrequenciaPorCliente = clientes.reduce((sum, c: any) => sum + (c.frequencia_pedidos_mes || 0), 0) / totalClientes;
    const mediaTicketMedioPorCliente = clientes.reduce((sum, c: any) => sum + (c.ticket_medio || 0), 0) / totalClientes;
    const mediaPedidosPorCliente = clientes.reduce((sum, c: any) => sum + (c.num_pedidos_unicos || 0), 0) / totalClientes;

    return [
      {
        label: `Média de Receita por Cliente: R$ ${mediaReceitaPorCliente.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Receita média gerada por cada cliente da base</Text>
            <Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de clientes ({totalClientes})</Text>
          </Box>
        )
      },
      {
        label: `Frequência Média de Pedidos: ${mediaFrequenciaPorCliente.toFixed(2)} pedidos/mês`,
        content: (
          <Box>
            <Text>Frequência média de compras por cliente por mês</Text>
            <Text mt={2} fontSize="sm">Indica a regularidade de compras dos clientes</Text>
          </Box>
        )
      },
      {
        label: `Ticket Médio por Cliente: R$ ${mediaTicketMedioPorCliente.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Valor médio gasto por pedido por cliente</Text>
            <Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text>
          </Box>
        )
      },
      {
        label: `Média de Pedidos por Cliente: ${mediaPedidosPorCliente.toFixed(1)} pedidos`,
        content: (
          <Box>
            <Text>Número médio de pedidos realizados por cliente</Text>
            <Text mt={2} fontSize="sm">Total de pedidos únicos dividido pelo número de clientes</Text>
          </Box>
        )
      }
    ];
  }, [overviewData]);

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
        {/* ===== HEADER ===== */}
        <Flex justify="space-between" align="flex-start" mb="8px">
          <Text as="h1" textStyle="pageSubtitle">
            {userName}, sua base de clientes {overviewData.scorecard_crescimento_percentual !== null && overviewData.scorecard_crescimento_percentual !== undefined
              ? `aumentou em ${overviewData.scorecard_crescimento_percentual >= 0 ? '+' : ''}${overviewData.scorecard_crescimento_percentual.toFixed(2)}%`
              : 'está sendo analisada'}
          </Text>
          <HStack spacing={2}>
            <Text fontSize="sm" color="gray.600">
              Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </Text>
            <IconButton
              icon={<RepeatIcon />}
              aria-label="Atualizar dados"
              size="sm"
              onClick={fetchClientesData}
              isLoading={loading}
            />
          </HStack>
        </Flex>

        {/* ===== STATS ===== */}
        <Box mb="36px">
          <Text textStyle="homeCardStatLabel">TOTAL DE CLIENTES</Text>
          <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
            {overviewData.scorecard_total_clientes}
          </Text>
        </Box>

        {/* ===== 4 CARDS ===== */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* CARD 1: LARGE - Performance de Clientes (com carrossel interno) */}
          <PerformanceCard
            title="Performance de Clientes"
            bgColor="#FFD1DC"
            slides={performanceSlides}
            onSlideChange={handleSlideChange}
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1"
            mainText="Análise de performance dos seus clientes ao longo do tempo."
            kpiItems={kpiItems}
          />

          {/* CARD 2: SMALL - Novos Clientes */}
          <DashboardCard
            title="Novos Clientes"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText={`Aumentamos nossa base em +${growthPercentage}% no último mês.`}
            scorecardValue={newCustomersCount.toString()}
            scorecardLabel="Novos Cadastros"
            barChartData={(() => {
              const clientes = overviewData.ranking_por_receita || [];
              const tierA = clientes.filter((c: any) => c.cluster_tier === 'A').length;
              const tierB = clientes.filter((c: any) => c.cluster_tier === 'B').length;
              const tierC = clientes.filter((c: any) => c.cluster_tier === 'C').length;
              const outros = clientes.length - tierA - tierB - tierC;
              
              return [
                { name: 'Tier A', value: tierA, color: '#4CAF50' },
                { name: 'Tier B', value: tierB, color: '#FFC107' },
                { name: 'Tier C', value: tierC, color: '#FF5722' },
                ...(outros > 0 ? [{ name: 'Outros', value: outros, color: '#9E9E9E' }] : []),
              ];
            })()}
            graphTitle="Distribuição por Tier"
            graphDescription="Quantidade de clientes por tier de performance."
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
            kpiItems={
              customerMetrics
                ? [
                  {
                    label: `Clientes Ativos: ${customerMetrics.total_active.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Total de clientes ativos no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Clientes que realizaram pelo menos uma compra no período</Text>
                      </Box>
                    )
                  },
                  {
                    label: `Novos Clientes: ${customerMetrics.new_customers.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Clientes que fizeram sua primeira compra no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Representa a expansão da base de clientes</Text>
                      </Box>
                    )
                  },
                  {
                    label: `Clientes Recorrentes: ${customerMetrics.returning_customers.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Clientes que retornaram para fazer novas compras no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Indica a fidelização e satisfação dos clientes</Text>
                      </Box>
                    )
                  },
                  {
                    label: `Valor Médio de Vida (LTV): R$ ${customerMetrics.avg_lifetime_value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    content: (
                      <Box>
                        <Text>Valor médio total que um cliente gasta durante todo o seu relacionamento com a empresa</Text>
                        <Text mt={2} fontSize="sm">Métrica crucial para avaliar o valor de longo prazo de cada cliente</Text>
                      </Box>
                    )
                  }
                ]
                : undefined
            }
            carouselGraphs={[
              {
                data: chartCustomersData,
                dataKey: "value",
                lineColor: "#82ca9d",
                title: "Clientes Únicos por Mês",
                description: "Evolução mensal do número de clientes únicos."
              },
              {
                data: chartRevenueData,
                dataKey: "value",
                lineColor: "#8884d8",
                title: "Receita Mensal",
                description: "Flutuação mensal da receita total."
              },
              {
                data: chartAvgOrderData,
                dataKey: "value",
                lineColor: "#ffc658",
                title: "Ticket Médio no Tempo",
                description: "Valor médio por pedido ao longo dos meses."
              },
              {
                data: chartOrdersData,
                dataKey: "value",
                lineColor: "#ff7300",
                title: "Pedidos por Mês",
                description: "Total de pedidos realizados mês a mês."
              }
            ]}
          />

          {/* CARD 3: ListCard - Rankings Dinâmicos */}
          <ListCard
            title={listCardTitle}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/clientes/lista"
            cardBgColor="#FFD1DC"
          />

          {/* CARD 4: LARGE - Distribuição Geográfica */}
          <DashboardCard
            title="Distribuição Geográfica de Clientes"
            size="large"
            bgColor="white"
            mapData={{
              center: geoClusters?.center || [-14.2350, -51.9253],
              zoom: 4.5,
              clusters: geoClusters?.clusters || [],
              maxCount: geoClusters?.max_count || 1
            }}
            mainText="Principais regiões de atuação dos clientes."
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1"
          />
        </Flex>
      </Flex>

      {/* Reusable ClienteDetailsModal for list item clicks */}
      <ClienteDetailsModal isOpen={isOpen} onClose={onClose} cliente={selectedItem} overviewData={overviewData} />
    </MainLayout>
  );
}

export default ClientesPage;