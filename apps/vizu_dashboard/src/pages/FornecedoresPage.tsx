import { Box, Flex, Text, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor } from '../services/analyticsService';
import type { FornecedoresOverviewResponse, FornecedorDetailResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { useGeoClusters } from '../hooks/useGeoClusters';
import React, { useState, useEffect } from 'react';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';
type MetricType = 'receita' | 'qtd_media' | 'ticket_medio' | 'frequencia';

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<FornecedorDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  // Hooks para dados
  const { data: geoClusters } = useGeoClusters('state');

  const fetchFornecedoresData = async () => {
    try {
      setLoading(true);
      const data = await getFornecedores(selectedPeriod);
      console.log('API Response Fornecedores:', data);
      console.log('First ranking item structure:', data.ranking_por_receita?.[0]);
      console.log('Keys in first item:', Object.keys(data.ranking_por_receita?.[0] || {}));
      console.log('Chart data structure:', {
        receita: data.chart_receita_no_tempo?.[0],
        fornecedores: data.chart_fornecedores_no_tempo?.[0],
        ticket: data.chart_ticketmedio_no_tempo?.[0],
      });
      // DEBUG: Log mapped graph data for "Novos Fornecedores" card
      const mappedGraphData = (data.chart_fornecedores_no_tempo || []).map((d: any) => ({
        name: d.name,
        value: d.total ?? d.value ?? 0
      }));
      console.log('📊 Mapped graphData for Novos Fornecedores:', mappedGraphData.slice(0, 3));
      console.log('📊 Total mapped items:', mappedGraphData.length);
      setOverviewData(data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados dos fornecedores.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFornecedoresData();
  }, [selectedPeriod]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(e.target.value as MetricType);
  };

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    try {
      setSelectedItem(null);
      const details = await getFornecedor(clickedItem.id);
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do fornecedor:", err);
      setError(err.message || 'Erro ao carregar detalhes do fornecedor.');
    }
  };

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

  // Cálculos derivados
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const newSuppliersCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
    const firstSaleDate = new Date(item.primeira_venda);
    return firstSaleDate >= thirtyDaysAgo;
  }).length;

  // Calcular crescimento percentual
  const growthPercentage = newSuppliersCount > 0 && overviewData.scorecard_total_fornecedores > 0
    ? ((newSuppliersCount / (overviewData.scorecard_total_fornecedores - newSuppliersCount)) * 100).toFixed(1)
    : '0.0';

  // Mapear dados para ListCard - dinâmico por métrica
  const getCurrentRanking = () => {
    switch (selectedMetric) {
      case 'receita':
        return overviewData.ranking_por_receita || [];
      case 'qtd_media':
        return overviewData.ranking_por_qtd_media || [];
      case 'ticket_medio':
        return overviewData.ranking_por_ticket_medio || [];
      case 'frequencia':
        return overviewData.ranking_por_frequencia || [];
      default:
        return overviewData.ranking_por_receita || [];
    }
  };

  const listCardItems = getCurrentRanking().map((item: any) => {
    console.log('Item:', item); // ← ADICIONE ISTO
    console.log('Item.nome:', item.nome); // ← E ISTO
    let description = '';
    if (selectedMetric === 'receita') {
      description = `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'qtd_media') {
      description = `Qtd Média: ${(item.qtd_media_por_pedido ?? item.qtd_media ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'ticket_medio') {
      description = `Ticket Médio: R$ ${(item.ticket_medio ?? item.avg_order_value ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'frequencia') {
      description = `Frequência: ${(item.frequencia_pedidos_mes ?? item.frequencia ?? 0).toFixed(1)} vendas/mês`;
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
        bg="#B2E7FF"
        color="gray.800"
      >
        {/* ===== HEADER ===== */}
        <Flex justify="space-between" align="flex-start" mb="8px">
          <Text as="h1" textStyle="pageSubtitle">
            {userName}, sua base de fornecedores {overviewData.scorecard_crescimento_percentual !== null && overviewData.scorecard_crescimento_percentual !== undefined
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
              onClick={fetchFornecedoresData}
              isLoading={loading}
            />
          </HStack>
        </Flex>

        {/* ===== STATS + FILTERS ===== */}
        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE FORNECEDORES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
              {overviewData.scorecard_total_fornecedores}
            </Text>
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
              <option value="qtd_media">Qtd Média</option>
              <option value="ticket_medio">Ticket Médio</option>
              <option value="frequencia">Frequência</option>
            </Select>
          </HStack>
        </Flex>

        {/* ===== 4 CARDS APENAS ===== */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* CARD 1: LARGE - Performance de Fornecedores */}
          <DashboardCard
            key={`performance-chart-${selectedMetric}`}
            title="Performance de Fornecedores"
            size="large"
            bgColor="#D4F1F4"
            graphData={{
              values: (() => {
                let chartData: any[] = [];
                if (selectedMetric === 'receita') {
                  chartData = overviewData.chart_receita_no_tempo || [];
                } else if (selectedMetric === 'qtd_media') {
                  chartData = overviewData.chart_quantidade_no_tempo || [];
                } else if (selectedMetric === 'ticket_medio') {
                  chartData = overviewData.chart_ticketmedio_no_tempo || [];
                } else {
                  // frequencia usa receita como fallback
                  chartData = overviewData.chart_receita_no_tempo || [];
                }
                return chartData.map((d: any) => ({
                  name: d.name,
                  value: d.total ?? d.value ?? 0
                }));
              })()
            }}
            scorecardValue={new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
              overviewData.chart_ticketmedio_no_tempo && overviewData.chart_ticketmedio_no_tempo.length > 0
                ? overviewData.chart_ticketmedio_no_tempo[overviewData.chart_ticketmedio_no_tempo.length - 1].total || 0
                : 0
            )}
            scorecardLabel="Ticket Médio Geral"
            graphTitle={(() => {
              if (selectedMetric === 'receita') return 'Receita Mensal dos Fornecedores';
              if (selectedMetric === 'qtd_media') return 'Volume Comercializado Mensal';
              if (selectedMetric === 'ticket_medio') return 'Ticket Médio Mensal';
              return 'Receita Mensal dos Fornecedores';
            })()}
            graphDescription={(() => {
              if (selectedMetric === 'receita') return 'Mês a mês da flutuação de receita geral comercializada por todos os fornecedores.';
              if (selectedMetric === 'qtd_media') return 'Mês a mês da flutuação do volume comercializado pelos fornecedores.';
              if (selectedMetric === 'ticket_medio') return 'Mês a mês da flutuação do ticket médio geral dos fornecedores.';
              return 'Mês a mês da flutuação de receita geral comercializada por todos os fornecedores.';
            })()}
            carouselGraphs={[
              {
                data: (overviewData.chart_receita_no_tempo || []).map((d: any) => ({
                  name: d.name,
                  value: d.total ?? d.value ?? 0
                })),
                dataKey: "value",
                lineColor: "#82ca9d",
                title: "Receita Mensal dos Fornecedores",
                description: "Receita total gerada por todos os fornecedores ao longo do tempo."
              },
              {
                data: (overviewData.chart_fornecedores_no_tempo || []).map((d: any) => ({
                  name: d.name,
                  value: d.total ?? d.value ?? 0
                })),
                dataKey: "value",
                lineColor: "#8884d8",
                title: "Fornecedores Únicos por Mês",
                description: "Número de fornecedores únicos que realizaram vendas em cada mês."
              },
              {
                data: (overviewData.chart_ticketmedio_no_tempo || []).map((d: any) => ({
                  name: d.name,
                  value: d.total ?? d.value ?? 0
                })),
                dataKey: "value",
                lineColor: "#ffc658",
                title: "Ticket Médio no Tempo",
                description: "Valor médio por pedido ao longo dos meses."
              }
            ]}
            kpiItems={(() => {
              const fornecedores = overviewData.ranking_por_receita || [];
              const totalFornecedores = fornecedores.length || 1;

              const mediaReceitaPorFornecedor = fornecedores.reduce((sum, f) => sum + (f.receita_total || 0), 0) / totalFornecedores;
              const mediaFrequenciaPorFornecedor = fornecedores.reduce((sum, f) => sum + (f.frequencia_pedidos_mes || 0), 0) / totalFornecedores;
              const mediaTicketMedioPorFornecedor = fornecedores.reduce((sum, f) => sum + (f.ticket_medio || 0), 0) / totalFornecedores;
              const mediaQtdPorFornecedor = fornecedores.reduce((sum, f) => sum + (f.qtd_media_por_pedido || 0), 0) / totalFornecedores;

              return [
                {
                  label: `Média de Receita por Fornecedor: R$ ${mediaReceitaPorFornecedor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  content: (
                    <Box>
                      <Text>Receita média gerada por cada fornecedor da base</Text>
                      <Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de fornecedores ({totalFornecedores})</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>receita_total / total_fornecedores</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Frequência Média de Vendas: ${mediaFrequenciaPorFornecedor.toFixed(2)} vendas/mês`,
                  content: (
                    <Box>
                      <Text>Frequência média de vendas por fornecedor por mês</Text>
                      <Text mt={2} fontSize="sm">Indica a regularidade de vendas dos fornecedores</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>frequencia_pedidos_mes</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Ticket Médio por Fornecedor: R$ ${mediaTicketMedioPorFornecedor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                  content: (
                    <Box>
                      <Text>Valor médio gerado por pedido de cada fornecedor</Text>
                      <Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>ticket_medio</strong></Text>
                    </Box>
                  )
                },
                {
                  label: `Quantidade Média por Pedido: ${mediaQtdPorFornecedor.toFixed(1)} unidades`,
                  content: (
                    <Box>
                      <Text>Quantidade média comercializada por pedido</Text>
                      <Text mt={2} fontSize="sm">Total de quantidade dividido pelo número de pedidos</Text>
                      <Text mt={2} fontSize="sm" color="gray.600">Métrica: <strong>qtd_media_por_pedido</strong></Text>
                    </Box>
                  )
                }
              ];
            })()}
            modalLeftBgColor="#D4F1F4"
            modalRightBgColor="#B2E7FF"
          />

          {/* CARD 2: SMALL - Insights de Fornecedores */}
          <DashboardCard
            title="Insights de Fornecedores"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText={`Aumentamos nossa base em +${growthPercentage}% no último mês.`}
            scorecardValue={newSuppliersCount.toString()}
            scorecardLabel="Novos Cadastros"
            barChartData={(() => {
              // Calcular dados por tier para o gráfico de barras
              const fornecedores = overviewData.ranking_por_receita || [];
              const tierA = fornecedores.filter((f: any) => f.cluster_tier === 'A').length;
              const tierB = fornecedores.filter((f: any) => f.cluster_tier === 'B').length;
              const tierC = fornecedores.filter((f: any) => f.cluster_tier === 'C').length;
              const outros = fornecedores.length - tierA - tierB - tierC;
              
              return [
                { name: 'Tier A', value: tierA, color: '#4CAF50' },
                { name: 'Tier B', value: tierB, color: '#FFC107' },
                { name: 'Tier C', value: tierC, color: '#FF5722' },
                ...(outros > 0 ? [{ name: 'Outros', value: outros, color: '#9E9E9E' }] : []),
              ];
            })()}
            graphTitle="Distribuição por Tier"
            graphDescription="Quantidade de fornecedores por tier de performance."
            kpiItems={(() => {
              // Calcular métricas por tier
              const fornecedores = overviewData.ranking_por_receita || [];
              const tierA = fornecedores.filter((f: any) => f.cluster_tier === 'A');
              const tierB = fornecedores.filter((f: any) => f.cluster_tier === 'B');
              const tierC = fornecedores.filter((f: any) => f.cluster_tier === 'C');

              const calcTierMetrics = (tier: any[]) => {
                if (tier.length === 0) return { qtdMedia: 0, ticketMedio: 0, frequencia: 0 };
                return {
                  qtdMedia: tier.reduce((sum, f) => sum + (f.qtd_media_por_pedido || 0), 0) / tier.length,
                  ticketMedio: tier.reduce((sum, f) => sum + (f.ticket_medio || 0), 0) / tier.length,
                  frequencia: tier.reduce((sum, f) => sum + (f.frequencia_pedidos_mes || 0), 0) / tier.length,
                };
              };

              const metricsA = calcTierMetrics(tierA);
              const metricsB = calcTierMetrics(tierB);
              const metricsC = calcTierMetrics(tierC);

              return [
                {
                  label: `Tier A: ${tierA.length} fornecedores`,
                  content: (
                    <Box>
                      <Text>Fornecedores de alta performance</Text>
                      <Text mt={2} fontSize="sm">Qtd Média: {metricsA.qtdMedia.toFixed(1)} un/pedido</Text>
                      <Text fontSize="sm">Ticket Médio: R$ {metricsA.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                      <Text fontSize="sm">Frequência: {metricsA.frequencia.toFixed(1)} vendas/mês</Text>
                    </Box>
                  )
                },
                {
                  label: `Tier B: ${tierB.length} fornecedores`,
                  content: (
                    <Box>
                      <Text>Fornecedores de média performance</Text>
                      <Text mt={2} fontSize="sm">Qtd Média: {metricsB.qtdMedia.toFixed(1)} un/pedido</Text>
                      <Text fontSize="sm">Ticket Médio: R$ {metricsB.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                      <Text fontSize="sm">Frequência: {metricsB.frequencia.toFixed(1)} vendas/mês</Text>
                    </Box>
                  )
                },
                {
                  label: `Tier C: ${tierC.length} fornecedores`,
                  content: (
                    <Box>
                      <Text>Fornecedores em desenvolvimento</Text>
                      <Text mt={2} fontSize="sm">Qtd Média: {metricsC.qtdMedia.toFixed(1)} un/pedido</Text>
                      <Text fontSize="sm">Ticket Médio: R$ {metricsC.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                      <Text fontSize="sm">Frequência: {metricsC.frequencia.toFixed(1)} vendas/mês</Text>
                    </Box>
                  )
                },
                {
                  label: `Novos (últimos 30 dias): ${newSuppliersCount}`,
                  content: (
                    <Box>
                      <Text>Fornecedores cadastrados recentemente</Text>
                      <Text mt={2} fontSize="sm">Crescimento: +{growthPercentage}%</Text>
                      <Text fontSize="sm" color="gray.600">Fornecedores com primeira venda nos últimos 30 dias</Text>
                    </Box>
                  )
                }
              ];
            })()}
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
            carouselGraphs={(() => {
              // Calcular métricas por tier para os gráficos
              const fornecedores = overviewData.ranking_por_receita || [];
              const tierA = fornecedores.filter((f: any) => f.cluster_tier === 'A');
              const tierB = fornecedores.filter((f: any) => f.cluster_tier === 'B');
              const tierC = fornecedores.filter((f: any) => f.cluster_tier === 'C');
              const tierD = fornecedores.filter((f: any) => f.cluster_tier === 'D' || !['A', 'B', 'C'].includes(f.cluster_tier));

              const calcTierMetrics = (tier: any[]) => {
                if (tier.length === 0) return { qtdMedia: 0, ticketMedio: 0, frequencia: 0, count: 0 };
                return {
                  count: tier.length,
                  qtdMedia: tier.reduce((sum, f) => sum + (f.qtd_media_por_pedido || 0), 0) / tier.length,
                  ticketMedio: tier.reduce((sum, f) => sum + (f.ticket_medio || 0), 0) / tier.length,
                  frequencia: tier.reduce((sum, f) => sum + (f.frequencia_pedidos_mes || 0), 0) / tier.length,
                };
              };

              const metricsA = calcTierMetrics(tierA);
              const metricsB = calcTierMetrics(tierB);
              const metricsC = calcTierMetrics(tierC);
              const metricsD = calcTierMetrics(tierD);

              return [
                // 1. Gráfico de distribuição por tier (barras)
                {
                  data: [
                    { name: 'Tier A', value: tierA.length, color: '#4CAF50' },
                    { name: 'Tier B', value: tierB.length, color: '#FFC107' },
                    { name: 'Tier C', value: tierC.length, color: '#FF5722' },
                    { name: 'Tier D', value: tierD.length, color: '#9E9E9E' },
                  ],
                  dataKey: 'value',
                  title: 'Distribuição de Fornecedores por Tier',
                  description: 'Quantidade de fornecedores em cada tier de performance.',
                  chartType: 'bar' as const,
                  barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                },
                // 2. Gráfico de ticket médio comparativo
                {
                  data: [
                    { name: 'Tier A', value: Math.round(metricsA.ticketMedio), color: '#4CAF50' },
                    { name: 'Tier B', value: Math.round(metricsB.ticketMedio), color: '#FFC107' },
                    { name: 'Tier C', value: Math.round(metricsC.ticketMedio), color: '#FF5722' },
                    { name: 'Tier D', value: Math.round(metricsD.ticketMedio), color: '#9E9E9E' },
                  ],
                  dataKey: 'value',
                  title: 'Ticket Médio por Tier (R$)',
                  description: 'Comparativo do valor médio por pedido em cada tier.',
                  chartType: 'bar' as const,
                  barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                },
                // 3. Gráfico de quantidade média comparativo
                {
                  data: [
                    { name: 'Tier A', value: Math.round(metricsA.qtdMedia * 10) / 10, color: '#4CAF50' },
                    { name: 'Tier B', value: Math.round(metricsB.qtdMedia * 10) / 10, color: '#FFC107' },
                    { name: 'Tier C', value: Math.round(metricsC.qtdMedia * 10) / 10, color: '#FF5722' },
                    { name: 'Tier D', value: Math.round(metricsD.qtdMedia * 10) / 10, color: '#9E9E9E' },
                  ],
                  dataKey: 'value',
                  title: 'Quantidade Média por Pedido',
                  description: 'Comparativo da quantidade média comercializada por tier.',
                  chartType: 'bar' as const,
                  barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                },
                // 4. Gráfico de frequência comparativo
                {
                  data: [
                    { name: 'Tier A', value: Math.round(metricsA.frequencia * 10) / 10, color: '#4CAF50' },
                    { name: 'Tier B', value: Math.round(metricsB.frequencia * 10) / 10, color: '#FFC107' },
                    { name: 'Tier C', value: Math.round(metricsC.frequencia * 10) / 10, color: '#FF5722' },
                    { name: 'Tier D', value: Math.round(metricsD.frequencia * 10) / 10, color: '#9E9E9E' },
                  ],
                  dataKey: 'value',
                  title: 'Frequência de Vendas (por mês)',
                  description: 'Comparativo da frequência média de vendas por tier.',
                  chartType: 'bar' as const,
                  barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                },
              ];
            })()}
          />

          {/* CARD 3: ListCard - Rankings Dinâmicos */}
          <ListCard
            title={(() => {
              if (selectedMetric === 'receita') return 'Fornecedores com Maior Receita';
              if (selectedMetric === 'qtd_media') return 'Fornecedores com Maior Qtd Média';
              if (selectedMetric === 'ticket_medio') return 'Fornecedores com Maior Ticket Médio';
              return 'Fornecedores com Maior Frequência';
            })()}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/fornecedores/lista"
            cardBgColor="#D4F1F4"
          />

          {/* CARD 4: LARGE - Distribuição Geográfica */}
          <DashboardCard
            title="Distribuição Geográfica de Fornecedores"
            size="large"
            bgColor="white"
            mapData={{
              center: geoClusters?.center || [-14.2350, -51.9253],
              zoom: 4.5,
              clusters: geoClusters?.clusters || [],
              maxCount: geoClusters?.max_count || 1
            }}
            mainText="Principais regiões de atuação dos fornecedores."
            modalLeftBgColor="#D4F1F4"
            modalRightBgColor="#B2E7FF"
            modalContent={<Text>Detalhes do mapa de distribuição de fornecedores</Text>}
          />
        </Flex>
      </Flex>

      {/* Modal para detalhes */}
      <FornecedorDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        fornecedor={selectedItem}
      />
    </MainLayout>
  );
}

export default FornecedoresPage;