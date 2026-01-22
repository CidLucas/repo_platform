import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton, Badge } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal';
import { getClientes, getCliente, getCustomerIndicators } from '../services/analyticsService';
import type { ClientesOverviewResponse, ClienteDetailResponse, CustomerMetricsResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { useGeoClusters } from '../hooks/useGeoClusters';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';
type MetricType = 'receita' | 'ticket_medio' | 'qtd_pedidos';

function ClientesPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ClienteDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<ClientesOverviewResponse | null>(null);
  const [customerMetrics, setCustomerMetrics] = useState<CustomerMetricsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  // Fetch geographic clusters for map visualization
  const { data: geoClusters, loading: loadingGeoClusters } = useGeoClusters('state');

  const fetchClientesData = async () => {
    try {
      setLoading(true);

      // Fetch both overview data and customer indicators in parallel
      const [overviewResponse, metricsResponse] = await Promise.all([
        getClientes(),
        getCustomerIndicators(selectedPeriod)
      ]);

      // Check if data is in expected format
      if (Array.isArray(overviewResponse)) {
        console.error('API returned array instead of ClientesOverviewResponse object');
        setError('Formato de dados inválido retornado pela API');
        return;
      }

      setOverviewData(overviewResponse);
      setCustomerMetrics(metricsResponse);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      console.error('Error fetching clientes:', err);
      setError(err.message || 'Erro ao carregar dados dos clientes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClientesData();
  }, [selectedPeriod]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(e.target.value as MetricType);
  };

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    // When a mini-card is clicked, fetch the detailed data for that specific client
    try {
      setSelectedItem(null); // Clear previous selection while loading
      const details = await getCliente(clickedItem.id); // 'id' is 'nome'
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do cliente:", err);
      setError(err.message || 'Erro ao carregar detalhes do cliente.');
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

  // Calculate new customers (first purchase in last 30 days)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const newCustomersCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
    const firstSaleDate = new Date(item.primeira_venda);
    return firstSaleDate >= thirtyDaysAgo;
  }).length;

  // Calculate growth percentage
  const totalCustomers = overviewData.scorecard_total_clientes || 0;
  const growthPercentage = totalCustomers > 0
    ? ((newCustomersCount / (totalCustomers - newCustomersCount)) * 100).toFixed(1)
    : '0.0';

  // Map the data for the ListCard - dynamic based on selected metric
  const getCurrentRanking = () => {
    switch (selectedMetric) {
      case 'receita':
        return overviewData.ranking_por_receita || [];
      case 'ticket_medio':
        return overviewData.ranking_por_ticket_medio || [];
      case 'qtd_pedidos':
        return overviewData.ranking_por_qtd_pedidos || [];
      default:
        return overviewData.ranking_por_receita || [];
    }
  };

  const listCardItems = getCurrentRanking().map((item: any) => {
    let description = '';
    if (selectedMetric === 'receita') {
      description = `Receita: R$ ${(item.receita_total ?? item.lifetime_value ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'ticket_medio') {
      description = `Ticket Médio: R$ ${(item.ticket_medio ?? item.avg_order_value ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'qtd_pedidos') {
      description = `Qtd Pedidos: ${(item.num_pedidos_unicos ?? item.total_orders ?? 0).toLocaleString('pt-BR')}`;
    }
    return {
      id: item.nome,
      title: item.nome,
      description,
      status: item.cluster_tier,
    };
  });

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#FFB6C1" // Page background color
        color="gray.800" // Text color for visibility
      >
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

        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE CLIENTES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_clientes}</Text>
          </Box>
          <HStack spacing="4" position="relative">
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
            <Select
              value={selectedMetric}
              onChange={handleMetricChange}
              width="150px"
              bg="white"
              color="gray.800"
            >
              <option value="receita">Receita</option>
              <option value="ticket_medio">Ticket Médio</option>
              <option value="qtd_pedidos">Quantidade de Pedidos</option>
            </Select>
          </HStack>
        </Flex>

        <Flex wrap="wrap" justify="center" gap="16px">
          {/* Example Dashboard Cards - these would need to be adapted for client specific data */}
          <DashboardCard
            key={`performance-chart-${selectedMetric}`}
            title="Performance de Clientes"
            size="large"
            bgColor="#FFD1DC" // Lighter pink
            graphData={{
              values: (() => {
                // Use time-series data based on selected metric
                // CGC1: Receita, CGC2: Ticket Médio, CGC3: Quantidade
                let chartData: any[] = [];
                if (selectedMetric === 'receita') {
                  chartData = overviewData.chart_receita_no_tempo || [];
                } else if (selectedMetric === 'ticket_medio') {
                  chartData = overviewData.chart_ticketmedio_no_tempo || [];
                } else {
                  chartData = overviewData.chart_quantidade_no_tempo || [];
                }
                return chartData.map((d: any) => ({
                  name: d.name,
                  value: d.total ?? d.value ?? d.receita ?? d.ticket_medio ?? d.quantidade ?? 0
                }));
              })()
            }}
            scorecardValue={`R$ ${(overviewData.scorecard_ticket_medio_geral ?? 0).toLocaleString('pt-BR')}`}
            scorecardLabel="Ticket Médio Geral"
            graphTitle={(() => {
              if (selectedMetric === 'receita') return 'Receita Mensal dos Clientes';
              if (selectedMetric === 'ticket_medio') return 'Ticket Médio Mensal';
              return 'Volume Comprado Mensal';
            })()}
            graphDescription={(() => {
              if (selectedMetric === 'receita') return 'Mês a mês da flutuação de receita geral comprada por todos os clientes.';
              if (selectedMetric === 'ticket_medio') return 'Mês a mês da flutuação do ticket médio geral dos clientes.';
              return 'Mês a mês da flutuação do volume comprado por clientes.';
            })()}
            carouselGraphs={[
              {
                data: (overviewData.chart_receita_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#82ca9d",
                title: "Receita Mensal dos Clientes",
                description: "Receita média gerada por cada cliente da base ao longo do tempo."
              },
              {
                data: (overviewData.chart_clientes_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#8884d8",
                title: "Frequência de Pedidos no Tempo",
                description: "Frequência média de compras por cliente por mês."
              },
              {
                data: (overviewData.chart_ticketmedio_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#ffc658",
                title: "Ticket Médio no Tempo",
                description: "Valor médio gasto por pedido por cliente ao longo dos meses."
              },
              {
                data: (overviewData.chart_quantidade_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#ff7300",
                title: "Média de Pedidos por Cliente",
                description: "Número médio de pedidos realizados por cliente ao longo do tempo."
              }
            ]}
            kpiItems={(() => {
              // Calculate averages from ranking data
              const clientes = overviewData.ranking_por_receita || [];
              const totalClientes = clientes.length || 1;

              const mediaReceitaPorCliente = clientes.reduce((sum, c) => sum + (c.receita_total || 0), 0) / totalClientes;
              const mediaFrequenciaPorCliente = clientes.reduce((sum, c) => sum + (c.frequencia_pedidos_mes || 0), 0) / totalClientes;
              const mediaTicketMedioPorCliente = clientes.reduce((sum, c) => sum + (c.ticket_medio || 0), 0) / totalClientes;
              const mediaPedidosPorCliente = clientes.reduce((sum, c) => sum + (c.num_pedidos_unicos || 0), 0) / totalClientes;

              return [
                {
                  label: `Média de Receita por Cliente: R$ ${mediaReceitaPorCliente.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  content: (
                    <Box>
                      <Text>Receita média gerada por cada cliente da base</Text>
                      <Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de clientes ({totalClientes})</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>receita_total / total_clientes</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Frequência Média de Pedidos: ${mediaFrequenciaPorCliente.toFixed(2)} pedidos/mês`,
                  content: (
                    <Box>
                      <Text>Frequência média de compras por cliente por mês</Text>
                      <Text mt={2} fontSize="sm">Indica a regularidade de compras dos clientes</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>frequencia_pedidos_mes</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Ticket Médio por Cliente: R$ ${mediaTicketMedioPorCliente.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  content: (
                    <Box>
                      <Text>Valor médio gasto por pedido por cliente</Text>
                      <Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>ticket_medio</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Média de Pedidos por Cliente: ${mediaPedidosPorCliente.toFixed(1)} pedidos`,
                  content: (
                    <Box>
                      <Text>Número médio de pedidos realizados por cliente</Text>
                      <Text mt={2} fontSize="sm">Total de pedidos únicos dividido pelo número de clientes</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>num_pedidos_unicos</strong></Text>
                    </Box>
                  )
                }
              ];
            })()}
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1" // Pink
            modalContent={<Text>Métricas detalhadas de clientes no período de {customerMetrics?.period || 'mês'}</Text>}
          />

          <DashboardCard
            title="Novos Clientes"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText={`Aumentamos nossa base em +${growthPercentage}% no último mês.`}
            scorecardValue={newCustomersCount.toString()}
            scorecardLabel="Novos Cadastros"
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1"
            graphData={{
              values: (overviewData.chart_clientes_no_tempo || []).map((d: any) => ({
                name: d.name,
                value: d.total ?? d.value ?? 0
              }))
            }}
            graphTitle="Evolução de Clientes"
            graphDescription="Evolução mensal da base de clientes."
            carouselGraphs={[
              {
                data: (overviewData.chart_clientes_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#82ca9d",
                title: "Clientes Ativos no Tempo",
                description: "Evolução mensal do número total de clientes ativos na base."
              },
              {
                data: (overviewData.chart_receita_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#8884d8",
                title: "Receita por Cliente no Tempo",
                description: "Flutuação mensal da receita gerada pelos clientes."
              },
              {
                data: (overviewData.chart_ticketmedio_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#ffc658",
                title: "Ticket Médio no Tempo",
                description: "Valor médio gasto por pedido ao longo dos meses."
              },
              {
                data: (overviewData.chart_quantidade_no_tempo || []).map((d: any) => ({ name: d.name, value: d.total ?? d.value ?? 0 })),
                dataKey: "value",
                lineColor: "#ff7300",
                title: "Volume Comprado no Tempo",
                description: "Quantidade total comprada pelos clientes mês a mês."
              }
            ]}
            kpiItems={
              customerMetrics
                ? [
                  {
                    label: `Clientes Ativos: ${customerMetrics.total_active.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Total de clientes ativos no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Clientes que realizaram pelo menos uma compra no período</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>total_active</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Novos Clientes: ${customerMetrics.new_customers.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Clientes que fizeram sua primeira compra no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Representa a expansão da base de clientes</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>new_customers</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Clientes Recorrentes: ${customerMetrics.returning_customers.toLocaleString('pt-BR')}`,
                    content: (
                      <Box>
                        <Text>Clientes que retornaram para fazer novas compras no período de {customerMetrics.period}</Text>
                        <Text mt={2} fontSize="sm">Indica a fidelização e satisfação dos clientes</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>returning_customers</strong></Text>
                      </Box>
                    )
                  },
                  {
                    label: `Valor Médio de Vida (LTV): R$ ${customerMetrics.avg_lifetime_value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                    content: (
                      <Box>
                        <Text>Valor médio total que um cliente gasta durante todo o seu relacionamento com a empresa</Text>
                        <Text mt={2} fontSize="sm">Métrica crucial para avaliar o valor de longo prazo de cada cliente</Text>
                        <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>avg_lifetime_value</strong></Text>
                      </Box>
                    )
                  }
                ]
                : undefined
            }
          />

          <ListCard
            title={(() => {
              if (selectedMetric === 'receita') return 'Clientes com Maior Receita';
              if (selectedMetric === 'ticket_medio') return 'Clientes com Maior Ticket Médio';
              return 'Clientes com Mais Pedidos';
            })()}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/clientes/lista" // Link to the full list page
            cardBgColor="#FFD1DC" // Lighter pink
          />

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
            modalRightBgColor="#FFB6C1" // Pink
            modalContent={<Text>Detalhes do mapa de distribuição de clientes</Text>}
          />
        </Flex>
      </Flex>

      {/* Reusable ClienteDetailsModal for list item clicks */}
      <ClienteDetailsModal isOpen={isOpen} onClose={onClose} cliente={selectedItem} overviewData={overviewData} />
    </MainLayout>
  );
}

export default ClientesPage;