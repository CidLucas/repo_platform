// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/ProdutosPage.tsx
import { Box, Flex, Text, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect, useMemo } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutosOverview, getProdutoDetails } from '../services/analyticsService';
import type { ProdutosOverviewResponse, ProdutoDetailResponse } from '../services/analyticsService';
import { DEFAULT_BRAZIL_CENTER } from '../utils/regionCoordinates';
import { useUserProfile } from '../hooks/useUserProfile';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';
type MetricType = 'receita' | 'quantidade' | 'ticket_medio';

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ProdutoDetailResponse | null>(null);
  const [overviewData, setOverviewData] = useState<ProdutosOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  const fetchProdutosData = async () => {
    try {
      setLoading(true);
      const data = await getProdutosOverview(selectedPeriod);
      setOverviewData(data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar dados dos produtos.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProdutosData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPeriod, selectedMetric]);

  // Memoized chart data
  const chartQuantidadeData = useMemo(() => {
    return (overviewData?.chart_quantidade_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
      name: d.name,
      value: d.total ?? d.value ?? 0
    }));
  }, [overviewData]);

  const chartReceitaData = useMemo(() => {
    return (overviewData?.chart_receita_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
      name: d.name,
      value: d.total ?? d.value ?? 0
    }));
  }, [overviewData]);

  const chartProdutosData = useMemo(() => {
    return (overviewData?.chart_produtos_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
      name: d.name,
      value: d.total ?? d.value ?? 0
    }));
  }, [overviewData]);

  // Calculate ticket médio over time
  const chartTicketMedioData = useMemo(() => {
    const quantidadeData = overviewData?.chart_quantidade_no_tempo || [];
    const receitaData = overviewData?.chart_receita_no_tempo || [];
    
    return receitaData.map((r: { name: string; total?: number; value?: number }, idx: number) => {
      const qItem = quantidadeData[idx] as { total?: number; value?: number } | undefined;
      const quantidade = qItem?.total ?? qItem?.value ?? 1;
      const receita = r.total ?? r.value ?? 0;
      return {
        name: r.name,
        value: quantidade > 0 ? receita / quantidade : 0
      };
    });
  }, [overviewData]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(e.target.value as MetricType);
  };

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    try {
      setSelectedItem(null);
      const details = await getProdutoDetails(clickedItem.id);
      setSelectedItem(details);
      onOpen();
    } catch (err: unknown) {
      console.error("Erro ao carregar detalhes do produto:", err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar detalhes do produto.';
      setError(errorMessage);
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

  // Get current ranking based on selected metric
  const getCurrentRanking = () => {
    switch (selectedMetric) {
      case 'receita':
        return overviewData?.ranking_por_receita || [];
      case 'quantidade':
        return overviewData?.ranking_por_volume || [];
      case 'ticket_medio':
        return overviewData?.ranking_por_ticket_medio || [];
      default:
        return overviewData?.ranking_por_receita || [];
    }
  };

  // Combine all rankings for tier analysis
  const allProducts = overviewData?.ranking_por_receita || [];

  // Calculate tier distribution
  const tierA = allProducts.filter((p) => p.cluster_tier === 'A');
  const tierB = allProducts.filter((p) => p.cluster_tier === 'B');
  const tierC = allProducts.filter((p) => p.cluster_tier === 'C');
  const tierD = allProducts.filter((p) => p.cluster_tier === 'D' || !['A', 'B', 'C'].includes(p.cluster_tier || ''));

  // Calculate Pareto metrics
  const totalReceita = allProducts.reduce((sum: number, p) => sum + (p.receita_total || 0), 0);
  const sortedByReceita = [...allProducts].sort((a, b) => (b.receita_total || 0) - (a.receita_total || 0));
  
  // Find how many products generate 80% of revenue (Pareto)
  let cumulativeReceita = 0;
  let paretoCount = 0;
  for (const p of sortedByReceita) {
    cumulativeReceita += p.receita_total || 0;
    paretoCount++;
    if (cumulativeReceita >= totalReceita * 0.8) break;
  }
  const paretoPercentage = allProducts.length > 0 ? ((paretoCount / allProducts.length) * 100).toFixed(1) : '0';

  // Calculate tier metrics
  const calcTierMetrics = (tier: typeof allProducts) => {
    if (tier.length === 0) return { qtdTotal: 0, ticketMedio: 0, receita: 0, count: 0 };
    return {
      count: tier.length,
      qtdTotal: tier.reduce((sum: number, p) => sum + (p.quantidade_total || 0), 0),
      ticketMedio: tier.reduce((sum: number, p) => sum + (p.valor_unitario_medio || 0), 0) / tier.length,
      receita: tier.reduce((sum: number, p) => sum + (p.receita_total || 0), 0),
    };
  };

  const metricsA = calcTierMetrics(tierA);
  const metricsB = calcTierMetrics(tierB);
  const metricsC = calcTierMetrics(tierC);
  const metricsD = calcTierMetrics(tierD);

  // ListCard items with enhanced descriptions
  const listCardItems = getCurrentRanking().map((item) => {
    const qtd = item.quantidade_total ?? 0;
    const ticketMedio = 'ticket_medio' in item ? (item.ticket_medio ?? item.valor_unitario_medio ?? 0) : (item.valor_unitario_medio ?? 0);
    const valorUnit = item.valor_unitario_medio ?? 0;
    
    let primaryMetric = '';
    if (selectedMetric === 'receita') {
      primaryMetric = `Receita: R$ ${('receita_total' in item ? item.receita_total : 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'quantidade') {
      primaryMetric = `Quantidade: ${qtd.toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'ticket_medio') {
      primaryMetric = `Ticket Médio: R$ ${ticketMedio.toLocaleString('pt-BR')}`;
    }
    
    // Enhanced description with all key metrics
    const description = `${primaryMetric} | Qtd: ${qtd.toLocaleString('pt-BR')} | Unit: R$ ${valorUnit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
    
    return {
      id: item.nome,
      title: item.nome,
      description,
      status: item.cluster_tier || '',
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
        bg="#FFF856"
        color="gray.800"
      >
        <Flex justify="space-between" align="flex-start" mb="8px">
          <Text as="h1" textStyle="pageSubtitle">
            {userName}, seus produtos geraram R$ {totalReceita.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} em receita
          </Text>
          <HStack spacing={2}>
            <Text fontSize="sm" color="gray.600">
              Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </Text>
            <IconButton
              icon={<RepeatIcon />}
              aria-label="Atualizar dados"
              size="sm"
              onClick={fetchProdutosData}
              isLoading={loading}
            />
          </HStack>
        </Flex>

        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE PRODUTOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_itens_unicos}</Text>
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
              <option value="quantidade">Quantidade</option>
              <option value="ticket_medio">Ticket Médio</option>
            </Select>
          </HStack>
        </Flex>

        {/* Grid of DashboardCards */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* Card 1: Performance de Produtos - LARGE with carousel graphs */}
          <DashboardCard
            key={`performance-chart-${selectedMetric}`}
            title="Performance de Produtos"
            size="large"
            bgColor="#FFFB97"
            graphData={{
              values: chartQuantidadeData
            }}
            scorecardValue={`R$ ${totalReceita.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`}
            scorecardLabel="Receita Total"
            graphTitle="Quantidade Vendida no Tempo"
            graphDescription="Evolução mensal da quantidade de produtos vendidos."
            carouselGraphs={[
              {
                data: chartQuantidadeData,
                dataKey: "value",
                lineColor: "#82ca9d",
                title: "Quantidade Vendida no Tempo",
                description: "Evolução mensal da quantidade de produtos vendidos."
              },
              {
                data: chartTicketMedioData,
                dataKey: "value",
                lineColor: "#8884d8",
                title: "Ticket Médio no Tempo",
                description: "Evolução mensal do valor médio por unidade vendida."
              },
              {
                data: chartReceitaData,
                dataKey: "value",
                lineColor: "#ffc658",
                title: "Receita no Tempo",
                description: "Evolução mensal da receita gerada pelos produtos."
              },
              {
                data: chartProdutosData,
                dataKey: "value",
                lineColor: "#ff7300",
                title: "Produtos Únicos no Tempo",
                description: "Número de produtos únicos vendidos por mês."
              }
            ]}
            kpiItems={[
              {
                label: `Total Vendido: ${allProducts.reduce((sum: number, p) => sum + (p.quantidade_total || 0), 0).toLocaleString('pt-BR')} unidades`,
                content: (
                  <Box>
                    <Text>Quantidade total de produtos vendidos no período</Text>
                    <Text mt={2} fontSize="sm">Soma de todas as unidades vendidas de todos os produtos</Text>
                  </Box>
                )
              },
              {
                label: `Receita Total: R$ ${totalReceita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
                content: (
                  <Box>
                    <Text>Receita total gerada por todos os produtos</Text>
                    <Text mt={2} fontSize="sm">Soma do faturamento de todos os produtos no período</Text>
                  </Box>
                )
              },
              {
                label: `Produtos Ativos: ${allProducts.length}`,
                content: (
                  <Box>
                    <Text>Número de produtos únicos com vendas no período</Text>
                    <Text mt={2} fontSize="sm">Produtos que tiveram pelo menos uma venda</Text>
                  </Box>
                )
              },
              {
                label: `Ticket Médio Geral: R$ ${(totalReceita / Math.max(allProducts.reduce((sum: number, p) => sum + (p.quantidade_total || 0), 0), 1)).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
                content: (
                  <Box>
                    <Text>Valor médio por unidade vendida</Text>
                    <Text mt={2} fontSize="sm">Receita total dividida pela quantidade total vendida</Text>
                  </Box>
                )
              }
            ]}
            modalLeftBgColor="#FFFB97"
            modalRightBgColor="#FFF856"
          />

          {/* Card 2: Insights de Produtos - SMALL with tier distribution */}
          <DashboardCard
            title="Insights de Produtos"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText={`${paretoPercentage}% dos produtos geram 80% da receita (Pareto).`}
            scorecardValue={allProducts.length.toString()}
            scorecardLabel="Produtos Classificados"
            barChartData={[
              { name: 'Tier A', value: tierA.length, color: '#4CAF50' },
              { name: 'Tier B', value: tierB.length, color: '#FFC107' },
              { name: 'Tier C', value: tierC.length, color: '#FF5722' },
              { name: 'Tier D', value: tierD.length, color: '#9E9E9E' },
            ]}
            graphTitle="Distribuição por Tier"
            graphDescription="Quantidade de produtos por tier de performance."
            kpiItems={[
              {
                label: `Tier A: ${tierA.length} produtos (${((tierA.length / Math.max(allProducts.length, 1)) * 100).toFixed(1)}%)`,
                content: (
                  <Box>
                    <Text>Produtos de alta performance</Text>
                    <Text mt={2} fontSize="sm">Quantidade Total: {metricsA.qtdTotal.toLocaleString('pt-BR')} un</Text>
                    <Text fontSize="sm">Ticket Médio: R$ {metricsA.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                    <Text fontSize="sm">Receita: R$ {metricsA.receita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                  </Box>
                )
              },
              {
                label: `Tier B: ${tierB.length} produtos (${((tierB.length / Math.max(allProducts.length, 1)) * 100).toFixed(1)}%)`,
                content: (
                  <Box>
                    <Text>Produtos de média performance</Text>
                    <Text mt={2} fontSize="sm">Quantidade Total: {metricsB.qtdTotal.toLocaleString('pt-BR')} un</Text>
                    <Text fontSize="sm">Ticket Médio: R$ {metricsB.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                    <Text fontSize="sm">Receita: R$ {metricsB.receita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                  </Box>
                )
              },
              {
                label: `Tier C: ${tierC.length} produtos (${((tierC.length / Math.max(allProducts.length, 1)) * 100).toFixed(1)}%)`,
                content: (
                  <Box>
                    <Text>Produtos em desenvolvimento</Text>
                    <Text mt={2} fontSize="sm">Quantidade Total: {metricsC.qtdTotal.toLocaleString('pt-BR')} un</Text>
                    <Text fontSize="sm">Ticket Médio: R$ {metricsC.ticketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                    <Text fontSize="sm">Receita: R$ {metricsC.receita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>
                  </Box>
                )
              },
              {
                label: `Análise de Pareto`,
                content: (
                  <Box>
                    <Text fontWeight="bold">{paretoPercentage}% dos produtos geram 80% da receita</Text>
                    <Text mt={2} fontSize="sm">Isso significa que {paretoCount} de {allProducts.length} produtos são responsáveis pela maior parte do faturamento.</Text>
                    <Text mt={2} fontSize="sm" color="gray.400">Foque nos produtos Tier A e B para maximizar resultados.</Text>
                  </Box>
                )
              }
            ]}
            carouselGraphs={[
              {
                data: [
                  { name: 'Tier A', value: tierA.length, color: '#4CAF50' },
                  { name: 'Tier B', value: tierB.length, color: '#FFC107' },
                  { name: 'Tier C', value: tierC.length, color: '#FF5722' },
                  { name: 'Tier D', value: tierD.length, color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Distribuição de Produtos por Tier',
                description: 'Quantidade de produtos em cada tier de performance.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(metricsA.ticketMedio), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(metricsB.ticketMedio), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(metricsC.ticketMedio), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(metricsD.ticketMedio), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Ticket Médio por Tier (R$)',
                description: 'Comparativo do valor médio unitário em cada tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(metricsA.receita), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(metricsB.receita), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(metricsC.receita), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(metricsD.receita), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Receita por Tier (R$)',
                description: 'Comparativo da receita gerada por cada tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(metricsA.qtdTotal), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(metricsB.qtdTotal), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(metricsC.qtdTotal), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(metricsD.qtdTotal), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Quantidade Vendida por Tier',
                description: 'Comparativo da quantidade total vendida por tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
              },
            ]}
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
          />

          {/* Card 3: ListCard - Rankings */}
          <ListCard
            title={(() => {
              if (selectedMetric === 'receita') return 'Produtos com Maior Receita';
              if (selectedMetric === 'quantidade') return 'Produtos com Maior Volume';
              return 'Produtos com Maior Ticket Médio';
            })()}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/produtos/lista"
            cardBgColor="#FFFB97"
          />

          {/* Card 4: Distribuição Geográfica */}
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white"
            mapData={{
              center: [DEFAULT_BRAZIL_CENTER.lat, DEFAULT_BRAZIL_CENTER.lng] as [number, number],
              zoom: 4,
              markers: [{ position: [DEFAULT_BRAZIL_CENTER.lat, DEFAULT_BRAZIL_CENTER.lng] as [number, number], popupText: 'Brasil' }]
            }}
            mainText="Principais regiões de venda de produtos."
            modalLeftBgColor="#FFFB97"
            modalRightBgColor="#FFF856"
            modalContent={<Text>Detalhes do mapa de distribuição de produtos</Text>}
          />
        </Flex>
      </Flex>

      <ProdutoDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        produto={selectedItem}
        overviewData={overviewData}
      />
    </MainLayout>
  );
}

export default ProdutosPage;