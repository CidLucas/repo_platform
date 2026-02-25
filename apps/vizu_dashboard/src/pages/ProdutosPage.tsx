// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/ProdutosPage.tsx
import { Box, Flex, Text, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard, InsightBullet } from '../components/DashboardCard';
import { PerformanceCard, MetricSlide } from '../components/PerformanceCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useMemo, useCallback } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { useProdutos } from '../hooks/useListData';
import { getProdutoDetails } from '../services/analyticsService';
import type { ProdutoDetailResponse } from '../services/analyticsService';
import { DEFAULT_BRAZIL_CENTER } from '../utils/regionCoordinates';
import { useUserProfile } from '../hooks/useUserProfile';

type MetricType = 'quantidade' | 'ticket_medio' | 'receita' | 'produtos';

// Helper function to calculate tier metrics (outside component to avoid useMemo dependency issues)
const calcTierMetrics = (tier: { quantidade_total?: number; valor_unitario_medio?: number; receita_total?: number }[]) => {
  if (tier.length === 0) return { qtdTotal: 0, ticketMedio: 0, receita: 0, count: 0 };
  return {
    count: tier.length,
    qtdTotal: tier.reduce((sum: number, p) => sum + (p.quantidade_total || 0), 0),
    ticketMedio: tier.reduce((sum: number, p) => sum + (p.valor_unitario_medio || 0), 0) / tier.length,
    receita: tier.reduce((sum: number, p) => sum + (p.receita_total || 0), 0),
  };
};

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ProdutoDetailResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('quantidade');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  // Use React Query hook for main data (cached, automatic background refresh)
  const { data: overviewData, isLoading: loading, error: queryError, refetch } = useProdutos({ period: 'month' });
  const error = queryError?.message || localError;

  // Handle manual refresh (uses React Query refetch)
  const handleRefresh = useCallback(async () => {
    await refetch();
    setLastUpdate(new Date());
  }, [refetch]);

  const handleSlideChange = useCallback((_index: number, slideId: string) => {
    setSelectedMetric(slideId as MetricType);
  }, []);

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    try {
      setSelectedItem(null);
      const details = await getProdutoDetails(clickedItem.id);
      setSelectedItem(details);
      onOpen();
    } catch (err: unknown) {
      console.error("Erro ao carregar detalhes do produto:", err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar detalhes do produto.';
      setLocalError(errorMessage);
    }
  };

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

  // Calculate totals and tier distribution
  const allProducts = useMemo(() => overviewData?.ranking_por_receita || [], [overviewData]);

  const { totalReceita, totalQuantidade, avgTicket } = useMemo(() => {
    const receita = allProducts.reduce((sum: number, p) => sum + (p.receita_total || 0), 0);
    const quantidade = allProducts.reduce((sum: number, p) => sum + (p.quantidade_total || 0), 0);
    const ticketMedio = quantidade > 0 ? receita / quantidade : 0;
    return { totalReceita: receita, totalQuantidade: quantidade, avgTicket: ticketMedio };
  }, [allProducts]);

  const { tierA, tierB, tierC, tierD } = useMemo(() => ({
    tierA: allProducts.filter((p) => p.cluster_tier === 'A'),
    tierB: allProducts.filter((p) => p.cluster_tier === 'B'),
    tierC: allProducts.filter((p) => p.cluster_tier === 'C'),
    tierD: allProducts.filter((p) => p.cluster_tier === 'D' || !['A', 'B', 'C'].includes(p.cluster_tier || '')),
  }), [allProducts]);

  // Calculate Pareto metrics
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- paretoCount may be used in future Pareto chart
  const { paretoPercentage, paretoCount: _paretoCount } = useMemo(() => {
    const sortedByReceita = [...allProducts].sort((a, b) => (b.receita_total || 0) - (a.receita_total || 0));

    let cumulativeReceita = 0;
    let count = 0;
    for (const p of sortedByReceita) {
      cumulativeReceita += p.receita_total || 0;
      count++;
      if (cumulativeReceita >= totalReceita * 0.8) break;
    }
    const percentage = allProducts.length > 0 ? ((count / allProducts.length) * 100).toFixed(1) : '0';
    return { paretoPercentage: percentage, paretoCount: count };
  }, [allProducts, totalReceita]);

  // Calculate tier metrics
  const metricsA = useMemo(() => calcTierMetrics(tierA), [tierA]);
  const metricsB = useMemo(() => calcTierMetrics(tierB), [tierB]);
  const metricsC = useMemo(() => calcTierMetrics(tierC), [tierC]);
  const metricsD = useMemo(() => calcTierMetrics(tierD), [tierD]);

  // Insight bullets for the Insights card (4 bullets compactos para o card)
  const insightBullets: InsightBullet[] = useMemo(() => {
    if (!overviewData || allProducts.length === 0) return [];

    const totalProdutos = allProducts.length;
    const tierACount = tierA.length;
    const tierAPercent = ((tierACount / totalProdutos) * 100).toFixed(1);
    const tierAReceitaPercent = totalReceita > 0 ? ((metricsA.receita / totalReceita) * 100).toFixed(1) : '0';

    // Top produto
    const topProduto = allProducts[0];
    const topNome = topProduto?.nome
      ? (topProduto.nome.length > 18 ? topProduto.nome.substring(0, 18) + '...' : topProduto.nome)
      : 'N/A';

    // Ticket médio formatado
    const ticketFormatado = new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0
    }).format(avgTicket);

    return [
      {
        text: `${tierACount} produtos Tier A (${tierAPercent}%) geram ${tierAReceitaPercent}% da receita`,
        type: 'star' as const
      },
      {
        text: `${paretoPercentage}% dos produtos geram 80% da receita (Pareto)`,
        type: 'positive' as const
      },
      {
        text: `Top produto: ${topNome}`,
        type: 'star' as const
      },
      {
        text: `Ticket médio: ${ticketFormatado}`,
        type: 'neutral' as const
      }
    ];
  }, [overviewData, allProducts, tierA, totalReceita, metricsA.receita, avgTicket, paretoPercentage]);

  // Performance card slides
  const performanceSlides: MetricSlide[] = useMemo(() => {
    if (!overviewData) return [];

    const formatCurrency = (value: number) =>
      new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

    const formatNumber = (value: number) =>
      new Intl.NumberFormat('pt-BR').format(value);

    return [
      {
        id: 'quantidade',
        title: 'Quantidade no Tempo',
        data: chartQuantidadeData,
        dataKey: 'value',
        lineColor: '#82ca9d',
        metricLabel: 'QUANTIDADE TOTAL',
        metricValue: formatNumber(totalQuantidade),
        rankingKey: 'ranking_por_volume',
      },
      {
        id: 'ticket_medio',
        title: 'Ticket Médio no Tempo',
        data: chartTicketMedioData,
        dataKey: 'value',
        lineColor: '#8884d8',
        metricLabel: 'TICKET MÉDIO',
        metricValue: formatCurrency(avgTicket),
        rankingKey: 'ranking_por_ticket_medio',
      },
      {
        id: 'receita',
        title: 'Receita no Tempo',
        data: chartReceitaData,
        dataKey: 'value',
        lineColor: '#ffc658',
        metricLabel: 'RECEITA TOTAL',
        metricValue: formatCurrency(totalReceita),
        rankingKey: 'ranking_por_receita',
      },
      {
        id: 'produtos',
        title: 'Produtos Únicos no Tempo',
        data: chartProdutosData,
        dataKey: 'value',
        lineColor: '#ff7300',
        metricLabel: 'TOTAL DE PRODUTOS',
        metricValue: formatNumber(overviewData.scorecard_total_itens_unicos || 0),
        rankingKey: 'ranking_por_receita',
      },
    ];
  }, [overviewData, chartQuantidadeData, chartTicketMedioData, chartReceitaData, chartProdutosData, totalQuantidade, avgTicket, totalReceita]);

  // List card items based on selected metric
  const listCardItems = useMemo(() => {
    if (!overviewData) return [];

    const getRankingData = () => {
      switch (selectedMetric) {
        case 'receita':
          return overviewData?.ranking_por_receita || [];
        case 'quantidade':
          return overviewData?.ranking_por_volume || [];
        case 'ticket_medio':
          return overviewData?.ranking_por_ticket_medio || [];
        case 'produtos':
          return overviewData?.ranking_por_receita || [];
        default:
          return overviewData?.ranking_por_receita || [];
      }
    };

    return getRankingData().map((item) => {
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
      } else if (selectedMetric === 'produtos') {
        primaryMetric = `Receita: R$ ${('receita_total' in item ? item.receita_total : 0).toLocaleString('pt-BR')}`;
      }

      const description = `${primaryMetric} | Qtd: ${qtd.toLocaleString('pt-BR')} | Unit: R$ ${valorUnit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

      return {
        id: item.nome,
        title: item.nome,
        description,
        status: item.cluster_tier || '',
      };
    });
  }, [overviewData, selectedMetric]);

  // List card title based on selected metric
  const listCardTitle = useMemo(() => {
    switch (selectedMetric) {
      case 'receita':
        return 'Produtos com Maior Receita';
      case 'quantidade':
        return 'Produtos com Maior Volume';
      case 'ticket_medio':
        return 'Produtos com Maior Ticket Médio';
      case 'produtos':
        return 'Produtos com Maior Receita';
      default:
        return 'Produtos com Maior Receita';
    }
  }, [selectedMetric]);

  // KPI Items for modal
  const kpiItems = useMemo(() => {
    return [
      {
        label: `Total Vendido: ${totalQuantidade.toLocaleString('pt-BR')} unidades`,
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
        label: `Ticket Médio Geral: R$ ${avgTicket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Valor médio por unidade vendida</Text>
            <Text mt={2} fontSize="sm">Receita total dividida pela quantidade total vendida</Text>
          </Box>
        )
      }
    ];
  }, [totalQuantidade, totalReceita, allProducts.length, avgTicket]);

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
        bg="#FFF856"
        color="gray.800"
      >
        {/* ===== HEADER ===== */}
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
              onClick={handleRefresh}
              isLoading={loading}
            />
          </HStack>
        </Flex>

        {/* ===== STATS ===== */}
        <Box mb="36px">
          <Text textStyle="homeCardStatLabel">TOTAL DE PRODUTOS</Text>
          <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
            {overviewData.scorecard_total_itens_unicos}
          </Text>
        </Box>

        {/* ===== 4 CARDS ===== */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* CARD 1: LARGE - Performance de Produtos (com carrossel interno) */}
          <PerformanceCard
            title="Performance de Produtos"
            bgColor="#FFFB97"
            slides={performanceSlides}
            onSlideChange={handleSlideChange}
            modalLeftBgColor="#FFFB97"
            modalRightBgColor="#FFF856"
            mainText="Análise de performance dos seus produtos ao longo do tempo."
            kpiItems={kpiItems}
          />

          {/* CARD 2: SMALL - Insights de Produtos */}
          <DashboardCard
            title="Insights de Produtos"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            scorecardValue={allProducts.length.toString()}
            scorecardLabel="Produtos Classificados"
            insightBullets={insightBullets}
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
            kpiItems={kpiItems}
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
          />

          {/* CARD 3: ListCard - Rankings Dinâmicos */}
          <ListCard
            title={listCardTitle}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/produtos/lista"
            cardBgColor="#FFFB97"
          />

          {/* CARD 4: LARGE - Distribuição Geográfica */}
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