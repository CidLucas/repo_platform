import { Box, Flex, Text, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard, InsightBullet } from '../components/DashboardCard';
import { PerformanceCard, MetricSlide } from '../components/PerformanceCard';
import { ListCard } from '../components/ListCard';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { useFornecedores } from '../hooks/useListData';
import { getFornecedor } from '../services/analyticsService';
import type { FornecedorDetailResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { useGeoClusters } from '../hooks/useGeoClusters';
import React, { useState, useMemo, useCallback } from 'react';

type MetricType = 'receita' | 'quantidade' | 'ticket_medio' | 'fornecedores';

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<FornecedorDetailResponse | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  // Use React Query hook for main data (cached, automatic background refresh)
  const { data: overviewData, isLoading: loading, error: queryError, refetch } = useFornecedores({ period: 'month' });
  const error = queryError?.message || localError;

  // Hooks para dados
  const { data: geoClusters } = useGeoClusters('state');

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
      const details = await getFornecedor(clickedItem.id);
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do fornecedor:", err);
      setLocalError(err.message || 'Erro ao carregar detalhes do fornecedor.');
    }
  };

  // Memoized calculations
  const { newSuppliersCount } = useMemo(() => {
    if (!overviewData) return { newSuppliersCount: 0 };
    
    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    const newCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
      const firstSaleDate = new Date(item.primeira_venda);
      return firstSaleDate >= thirtyDaysAgo;
    }).length;

    return { newSuppliersCount: newCount };
  }, [overviewData]);

  // Performance card slides
  const performanceSlides: MetricSlide[] = useMemo(() => {
    if (!overviewData) return [];

    const formatCurrency = (value: number) => 
      new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    
    const formatNumber = (value: number) => 
      new Intl.NumberFormat('pt-BR').format(value);

    // Calculate totals
    const totalReceita = (overviewData.ranking_por_receita || []).reduce(
      (sum, item: any) => sum + (item.receita_total || 0), 0
    );
    const totalQuantidade = (overviewData.ranking_por_receita || []).reduce(
      (sum, item: any) => sum + (item.quantidade_total || 0), 0
    );
    const totalPedidos = (overviewData.ranking_por_receita || []).reduce(
      (sum, item: any) => sum + (item.total_pedidos || item.num_pedidos_unicos || 0), 0
    );
    // Ticket Médio = receita_total / total_pedidos (valor médio por pedido)
    const avgTicket = totalPedidos > 0 ? totalReceita / totalPedidos : 0;

    return [
      {
        id: 'receita',
        title: 'Receita no Tempo',
        data: (overviewData.chart_receita_no_tempo || []).map((d: any) => ({
          name: d.name,
          value: d.total ?? d.value ?? 0
        })),
        dataKey: 'value',
        lineColor: '#82ca9d',
        metricLabel: 'RECEITA TOTAL',
        metricValue: formatCurrency(totalReceita),
        rankingKey: 'ranking_por_receita',
      },
      {
        id: 'ticket_medio',
        title: 'Ticket Médio no Tempo',
        data: (overviewData.chart_ticketmedio_no_tempo || []).map((d: any) => ({
          name: d.name,
          value: d.total ?? d.value ?? 0
        })),
        dataKey: 'value',
        lineColor: '#ffc658',
        metricLabel: 'TICKET MÉDIO',
        metricValue: formatCurrency(avgTicket),
        rankingKey: 'ranking_por_ticket_medio',
      },
      {
        id: 'quantidade',
        title: 'Quantidade no Tempo',
        data: (overviewData.chart_quantidade_no_tempo || []).map((d: any) => ({
          name: d.name,
          value: d.total ?? d.value ?? 0
        })),
        dataKey: 'value',
        lineColor: '#8884d8',
        metricLabel: 'QUANTIDADE TOTAL',
        metricValue: formatNumber(totalQuantidade),
        rankingKey: 'ranking_por_qtd_media',
      },
      {
        id: 'fornecedores',
        title: 'Fornecedores Únicos no Tempo',
        data: (overviewData.chart_fornecedores_no_tempo || []).map((d: any) => ({
          name: d.name,
          value: d.total ?? d.value ?? 0
        })),
        dataKey: 'value',
        lineColor: '#ff7300',
        metricLabel: 'TOTAL DE FORNECEDORES',
        metricValue: formatNumber(overviewData.scorecard_total_fornecedores || 0),
        rankingKey: 'ranking_por_receita',
      },
    ];
  }, [overviewData]);

  // List card items based on selected metric
  const listCardItems = useMemo(() => {
    if (!overviewData) return [];

    const getRankingData = () => {
      switch (selectedMetric) {
        case 'receita':
          return overviewData.ranking_por_receita || [];
        case 'quantidade':
          return overviewData.ranking_por_qtd_media || [];
        case 'ticket_medio':
          return overviewData.ranking_por_ticket_medio || [];
        case 'fornecedores':
          return overviewData.ranking_por_frequencia || [];
        default:
          return overviewData.ranking_por_receita || [];
      }
    };

    return getRankingData().map((item: any) => {
      let description = '';
      if (selectedMetric === 'receita') {
        description = `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'quantidade') {
        description = `Qtd Média: ${(item.qtd_media_por_pedido ?? item.qtd_media ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'ticket_medio') {
        description = `Ticket Médio: R$ ${(item.ticket_medio ?? item.avg_order_value ?? 0).toLocaleString('pt-BR')}`;
      } else if (selectedMetric === 'fornecedores') {
        description = `Frequência: ${(item.frequencia_pedidos_mes ?? item.frequencia ?? 0).toFixed(1)} vendas/mês`;
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
        return 'Fornecedores com Maior Receita';
      case 'quantidade':
        return 'Fornecedores com Maior Qtd Média';
      case 'ticket_medio':
        return 'Fornecedores com Maior Ticket Médio';
      case 'fornecedores':
        return 'Fornecedores com Maior Frequência';
      default:
        return 'Fornecedores com Maior Receita';
    }
  }, [selectedMetric]);

  // Insight bullets for the Insights card (4 bullets compactos para o card)
  const insightBullets: InsightBullet[] = useMemo(() => {
    if (!overviewData) return [];

    const fornecedores = overviewData.ranking_por_receita || [];
    const totalFornecedores = fornecedores.length || 1;

    // Cálculos dos tiers
    const tierA = fornecedores.filter((f: any) => f.cluster_tier === 'A');
    const tierACount = tierA.length;
    const tierAPercent = ((tierACount / totalFornecedores) * 100).toFixed(1);
    const receitaTierA = tierA.reduce((sum: number, f: any) => sum + (f.receita_total || 0), 0);
    const receitaTotal = fornecedores.reduce((sum: number, f: any) => sum + (f.receita_total || 0), 0);
    const tierAReceitaPercent = receitaTotal > 0 ? ((receitaTierA / receitaTotal) * 100).toFixed(1) : '0';

    // Frequência média
    const freqMedia = fornecedores.reduce((sum: number, f: any) => sum + (f.frequencia_pedidos_mes || 0), 0) / totalFornecedores;

    // Ticket médio = receita_total / total_pedidos
    const receitaTotalGeral = fornecedores.reduce((sum: number, f: any) => sum + (f.receita_total || f.total_revenue || 0), 0);
    const totalPedidosGeral = fornecedores.reduce((sum: number, f: any) => sum + (f.total_pedidos || f.total_orders || 0), 0);
    const ticketMedio = totalPedidosGeral > 0 ? receitaTotalGeral / totalPedidosGeral : 0;
    const ticketFormatado = new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
      maximumFractionDigits: 0
    }).format(ticketMedio);

    // Top fornecedor
    const topFornecedor = fornecedores[0];
    const topNome = topFornecedor?.nome 
      ? (topFornecedor.nome.length > 18 ? topFornecedor.nome.substring(0, 18) + '...' : topFornecedor.nome)
      : 'N/A';

    return [
      {
        text: `${tierACount} fornecedores Tier A (${tierAPercent}%) geram ${tierAReceitaPercent}% da receita`,
        type: 'star' as const
      },
      {
        text: `${freqMedia >= 10 ? 'Alta' : freqMedia >= 4 ? 'Média' : 'Baixa'} frequência: ${freqMedia.toFixed(1)} vendas/mês`,
        type: freqMedia >= 4 ? 'positive' as const : 'warning' as const
      },
      {
        text: `Top fornecedor: ${topNome}`,
        type: 'star' as const
      },
      {
        text: `Ticket médio: ${ticketFormatado}`,
        type: 'neutral' as const
      }
    ];
  }, [overviewData]);

  // KPI Items for modal
  const kpiItems = useMemo(() => {
    if (!overviewData) return [];

    const fornecedores = overviewData.ranking_por_receita || [];
    const totalFornecedores = fornecedores.length || 1;

    const mediaReceitaPorFornecedor = fornecedores.reduce((sum, f: any) => sum + (f.receita_total || 0), 0) / totalFornecedores;
    const mediaFrequenciaPorFornecedor = fornecedores.reduce((sum, f: any) => sum + (f.frequencia_pedidos_mes || 0), 0) / totalFornecedores;
    const mediaTicketMedioPorFornecedor = fornecedores.reduce((sum, f: any) => sum + (f.ticket_medio || 0), 0) / totalFornecedores;
    const mediaQtdPorFornecedor = fornecedores.reduce((sum, f: any) => sum + (f.qtd_media_por_pedido || 0), 0) / totalFornecedores;

    return [
      {
        label: `Média de Receita por Fornecedor: R$ ${mediaReceitaPorFornecedor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Receita média gerada por cada fornecedor da base</Text>
            <Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de fornecedores ({totalFornecedores})</Text>
          </Box>
        )
      },
      {
        label: `Frequência Média de Vendas: ${mediaFrequenciaPorFornecedor.toFixed(2)} vendas/mês`,
        content: (
          <Box>
            <Text>Frequência média de vendas por fornecedor por mês</Text>
            <Text mt={2} fontSize="sm">Indica a regularidade de vendas dos fornecedores</Text>
          </Box>
        )
      },
      {
        label: `Ticket Médio por Fornecedor: R$ ${mediaTicketMedioPorFornecedor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        content: (
          <Box>
            <Text>Valor médio gerado por pedido de cada fornecedor</Text>
            <Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text>
          </Box>
        )
      },
      {
        label: `Quantidade Média por Pedido: ${mediaQtdPorFornecedor.toFixed(1)} unidades`,
        content: (
          <Box>
            <Text>Quantidade média comercializada por pedido</Text>
            <Text mt={2} fontSize="sm">Total de quantidade dividido pelo número de pedidos</Text>
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
        bg="#92DAFF"
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
              onClick={handleRefresh}
              isLoading={loading}
            />
          </HStack>
        </Flex>

        {/* ===== STATS ===== */}
        <Box mb="36px">
          <Text textStyle="homeCardStatLabel">TOTAL DE FORNECEDORES</Text>
          <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
            {overviewData.scorecard_total_fornecedores}
          </Text>
        </Box>

        {/* ===== 4 CARDS ===== */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* CARD 1: LARGE - Performance de Fornecedores (com carrossel interno) */}
          <PerformanceCard
            title="Performance de Fornecedores"
            bgColor="#D4F1F4"
            slides={performanceSlides}
            onSlideChange={handleSlideChange}
            modalLeftBgColor="#D4F1F4"
            modalRightBgColor="#B2E7FF"
            mainText="Análise de performance dos seus fornecedores ao longo do tempo."
            kpiItems={kpiItems}
          />

          {/* CARD 2: SMALL - Insights de Fornecedores */}
          <DashboardCard
            title="Insights de Fornecedores"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            scorecardValue={newSuppliersCount.toString()}
            scorecardLabel="Novos Cadastros"
            modalLeftBgColor="#353A5A"
            modalRightBgColor="#1F2138"
            insightBullets={insightBullets}
          />

          {/* CARD 3: ListCard - Rankings Dinâmicos */}
          <ListCard
            title={listCardTitle}
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