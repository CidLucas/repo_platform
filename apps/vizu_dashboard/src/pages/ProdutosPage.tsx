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

  // Calculate growth message (same pattern as ClientesPage and FornecedoresPage)
  const growthMessage = useMemo(() => {
    const crescimento = overviewData?.scorecard_crescimento_percentual ?? 0;
    const absValue = Math.abs(crescimento).toFixed(1);
    
    if (crescimento > 0) {
      return `${userName}, você vendeu mais ${absValue}% em produtos este mês`;
    } else if (crescimento < 0) {
      return `${userName}, você vendeu menos ${absValue}% em produtos este mês`;
    } else {
      return `${userName}, suas vendas de produtos estão estáveis este mês`;
    }
  }, [overviewData?.scorecard_crescimento_percentual, userName]);

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
  
  // Use scorecards from backend (calculated from ALL products, not just top 10)
  const {
    totalProdutos,
    totalReceita,
    totalQuantidade,
    avgTicket,
    // Tier data from backend (ALL products)
    tierACount, tierBCount, tierCCount, tierDCount,
    tierAReceita, tierBReceita, tierCReceita, tierDReceita,
    tierAQuantidade, tierBQuantidade, tierCQuantidade, tierDQuantidade,
    tierATicketMedio, tierBTicketMedio, tierCTicketMedio, tierDTicketMedio
  } = useMemo(() => {
    if (!overviewData) {
      return {
        totalProdutos: 0, totalReceita: 0, totalQuantidade: 0, avgTicket: 0,
        tierACount: 0, tierBCount: 0, tierCCount: 0, tierDCount: 0,
        tierAReceita: 0, tierBReceita: 0, tierCReceita: 0, tierDReceita: 0,
        tierAQuantidade: 0, tierBQuantidade: 0, tierCQuantidade: 0, tierDQuantidade: 0,
        tierATicketMedio: 0, tierBTicketMedio: 0, tierCTicketMedio: 0, tierDTicketMedio: 0
      };
    }
    
    return {
      totalProdutos: overviewData.scorecard_total_itens_unicos || 0,
      totalReceita: overviewData.scorecard_receita_total || 0,
      totalQuantidade: overviewData.scorecard_quantidade_total || 0,
      avgTicket: overviewData.scorecard_ticket_medio || 0,
      // Tier counts (from ALL products via backend)
      tierACount: overviewData.scorecard_tier_a_count || 0,
      tierBCount: overviewData.scorecard_tier_b_count || 0,
      tierCCount: overviewData.scorecard_tier_c_count || 0,
      tierDCount: overviewData.scorecard_tier_d_count || 0,
      // Tier receita
      tierAReceita: overviewData.scorecard_tier_a_receita || 0,
      tierBReceita: overviewData.scorecard_tier_b_receita || 0,
      tierCReceita: overviewData.scorecard_tier_c_receita || 0,
      tierDReceita: overviewData.scorecard_tier_d_receita || 0,
      // Tier quantidade
      tierAQuantidade: overviewData.scorecard_tier_a_quantidade || 0,
      tierBQuantidade: overviewData.scorecard_tier_b_quantidade || 0,
      tierCQuantidade: overviewData.scorecard_tier_c_quantidade || 0,
      tierDQuantidade: overviewData.scorecard_tier_d_quantidade || 0,
      // Tier ticket médio
      tierATicketMedio: overviewData.scorecard_tier_a_ticket_medio || 0,
      tierBTicketMedio: overviewData.scorecard_tier_b_ticket_medio || 0,
      tierCTicketMedio: overviewData.scorecard_tier_c_ticket_medio || 0,
      tierDTicketMedio: overviewData.scorecard_tier_d_ticket_medio || 0,
    };
  }, [overviewData]);

  // Insight bullets for the Insights card (5 bullets relevantes)
  const insightBullets: InsightBullet[] = useMemo(() => {
    if (!overviewData || totalProdutos === 0) return [];

    const formatCurrency = (value: number) => 
      new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
    
    const formatNumber = (value: number) => 
      new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(value);

    const truncateName = (name: string, maxLen: number = 22) => 
      name.length > maxLen ? name.substring(0, maxLen) + '...' : name;

    const bullets: InsightBullet[] = [];

    // 1. Produto líder em receita
    const topReceita = allProducts[0];
    if (topReceita?.nome) {
      bullets.push({
        text: `Líder receita: ${truncateName(topReceita.nome)} (${formatCurrency(topReceita.receita_total)})`,
        type: 'star' as const
      });
    }

    // 2. Tier A gera X% da receita
    const tierAReceitaPercent = totalReceita > 0 ? ((tierAReceita / totalReceita) * 100).toFixed(1) : '0';
    bullets.push({
      text: `${tierACount} produtos Tier A geram ${tierAReceitaPercent}% da receita`,
      type: 'star' as const
    });

    // 3. Produto com maior volume vendido (do ranking_por_volume)
    const rankingVolume = overviewData.ranking_por_volume || [];
    const topVolume = rankingVolume[0];
    if (topVolume?.nome && topVolume.nome !== topReceita?.nome) {
      bullets.push({
        text: `Maior volume: ${truncateName(topVolume.nome)} (${formatNumber(topVolume.quantidade_total)} un)`,
        type: 'neutral' as const
      });
    }

    // 4. Produto com maior variação de preço (do backend)
    const topVariacaoNome = overviewData.top_variacao_produto_nome;
    const topVariacaoPercent = overviewData.top_variacao_produto_percentual || 0;
    const topVariacaoDirecao = overviewData.top_variacao_produto_direcao || 'stable';
    
    if (topVariacaoNome && Math.abs(topVariacaoPercent) > 1) {
      const variacaoTexto = topVariacaoPercent >= 0 
        ? `+${topVariacaoPercent.toFixed(1)}%` 
        : `${topVariacaoPercent.toFixed(1)}%`;
      const variacaoTipo = topVariacaoDirecao === 'up' ? 'negative' : topVariacaoDirecao === 'down' ? 'positive' : 'neutral';
      
      bullets.push({
        text: `Maior variação preço: ${truncateName(topVariacaoNome, 18)} (${variacaoTexto})`,
        type: variacaoTipo as 'positive' | 'negative' | 'neutral'
      });
    }

    // 5. Produto com maior ticket médio (do ranking_por_ticket_medio)
    const rankingTicket = overviewData.ranking_por_ticket_medio || [];
    const topTicket = rankingTicket[0];
    if (topTicket?.nome && topTicket.nome !== topReceita?.nome) {
      bullets.push({
        text: `Maior ticket: ${truncateName(topTicket.nome)} (${formatCurrency(topTicket.ticket_medio)}/un)`,
        type: 'neutral' as const
      });
    }

    // Garantir que temos pelo menos 4 bullets
    if (bullets.length < 4) {
      // Adicionar ticket médio geral se não tiver variação de preço
      bullets.push({
        text: `Ticket médio geral: ${formatCurrency(avgTicket)}/unidade`,
        type: 'neutral' as const
      });
    }

    return bullets.slice(0, 4); // Máximo 4 bullets
  }, [overviewData, allProducts, totalProdutos, totalReceita, tierACount, tierAReceita, avgTicket]);

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
        metricLabel: 'QUANTIDADE KGs MENSAL',
        metricValue: formatNumber(totalQuantidade),
        rankingKey: 'ranking_por_volume',
      },
      {
        id: 'ticket_medio',
        title: 'Ticket Médio no Tempo',
        data: chartTicketMedioData,
        dataKey: 'value',
        lineColor: '#8884d8',
        metricLabel: 'TICKET MÉDIO KGs MENSAL',
        metricValue: formatCurrency(avgTicket),
        rankingKey: 'ranking_por_ticket_medio',
      },
      {
        id: 'receita',
        title: 'Receita no Tempo',
        data: chartReceitaData,
        dataKey: 'value',
        lineColor: '#ffc658',
        metricLabel: 'RECEITA MENSAL',
        metricValue: formatCurrency(totalReceita),
        rankingKey: 'ranking_por_receita',
      },
      {
        id: 'produtos',
        title: 'Produtos Únicos no Tempo',
        data: chartProdutosData,
        dataKey: 'value',
        lineColor: '#ff7300',
        metricLabel: 'PRODUTOS ÚNICOS MENSAL',
        metricValue: formatNumber(overviewData.scorecard_total_itens_unicos || 0),
        rankingKey: 'ranking_por_receita',
      },
    ];
  }, [overviewData, chartQuantidadeData, chartTicketMedioData, chartReceitaData, chartProdutosData, totalQuantidade, avgTicket, totalReceita]);

  // List card items based on selected metric
  const listCardItems = useMemo(() => {
    if (!overviewData) return [];

    type RankingItemBase = {
      nome: string;
      quantidade_total: number;
      valor_unitario_medio: number;
      cluster_tier?: string;
      receita_total?: number;
      ticket_medio?: number;
    };

    const getRankingData = (): RankingItemBase[] => {
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

    return getRankingData().map((item: RankingItemBase) => {
      const qtd = item.quantidade_total ?? 0;
      const ticketMedio = item.ticket_medio ?? item.valor_unitario_medio ?? 0;
      const valorUnit = item.valor_unitario_medio ?? 0;
      const receita = item.receita_total ?? 0;
      
      let primaryMetric = '';
      if (selectedMetric === 'receita') {
        primaryMetric = `Receita: R$ ${receita.toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'quantidade') {
        primaryMetric = `Quantidade: ${qtd.toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'ticket_medio') {
        primaryMetric = `Ticket Médio: R$ ${ticketMedio.toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'produtos') {
        primaryMetric = `Receita: R$ ${receita.toLocaleString('pt-BR')}`;
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
        label: `Produtos Únicos Vendidos: ${totalProdutos}`,
        content: (
          <Box>
            <Text>Número de produtos únicos com vendas no período</Text>
            <Text mt={2} fontSize="sm">Produtos que tiveram pelo menos uma venda</Text>
          </Box>
        )
      },
      {
        label: `Ticket Médio KG's: R$ ${avgTicket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Valor médio por unidade vendida</Text>
            <Text mt={2} fontSize="sm">Receita total dividida pela quantidade total vendida</Text>
          </Box>
        )
      }
    ];
  }, [totalQuantidade, totalReceita, totalProdutos, avgTicket]);

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
            {growthMessage}
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
            scorecardValue={totalProdutos.toString()}
            scorecardLabel="Produtos Classificados"
            insightBullets={insightBullets}
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
            kpiItems={kpiItems}
            carouselGraphs={[
              {
                data: [
                  { name: 'Tier A', value: tierACount, color: '#4CAF50' },
                  { name: 'Tier B', value: tierBCount, color: '#FFC107' },
                  { name: 'Tier C', value: tierCCount, color: '#FF5722' },
                  { name: 'Tier D', value: tierDCount, color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Distribuição de Produtos por Tier',
                description: 'Quantidade de produtos em cada tier de performance.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                valueLabel: 'Produtos',
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(tierATicketMedio), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(tierBTicketMedio), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(tierCTicketMedio), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(tierDTicketMedio), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Ticket Médio por Tier (R$)',
                description: 'Receita total dividida pela quantidade vendida em cada tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                valueLabel: 'Ticket Médio (R$)',
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(tierAReceita), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(tierBReceita), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(tierCReceita), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(tierDReceita), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Receita por Tier (R$)',
                description: 'Comparativo da receita gerada por cada tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                valueLabel: 'Receita (R$)',
              },
              {
                data: [
                  { name: 'Tier A', value: Math.round(tierAQuantidade), color: '#4CAF50' },
                  { name: 'Tier B', value: Math.round(tierBQuantidade), color: '#FFC107' },
                  { name: 'Tier C', value: Math.round(tierCQuantidade), color: '#FF5722' },
                  { name: 'Tier D', value: Math.round(tierDQuantidade), color: '#9E9E9E' },
                ],
                dataKey: 'value',
                title: 'Quantidade Vendida por Tier',
                description: 'Comparativo da quantidade total vendida por tier.',
                chartType: 'bar' as const,
                barColors: ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'],
                valueLabel: 'Quantidade',
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