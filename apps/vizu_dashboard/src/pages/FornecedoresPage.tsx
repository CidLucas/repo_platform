import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor } from '../services/analyticsService';
import type { FornecedoresOverviewResponse, FornecedorDetailResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { getRegionCoordinates } from '../utils/regionCoordinates';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';
type MetricType = 'receita' | 'qtd_media' | 'ticket_medio' | 'frequencia';

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<FornecedorDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  const fetchFornecedoresData = async () => {
    try {
      setLoading(true);
      const data = await getFornecedores(selectedPeriod);
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
  }, [selectedPeriod, selectedMetric]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(e.target.value as MetricType);
  };

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    // When a mini-card is clicked, fetch the detailed data for that specific supplier
    try {
      setSelectedItem(null); // Clear previous selection while loading
      const details = await getFornecedor(clickedItem.id); // 'id' is 'nome_fornecedor'
      setSelectedItem(details);
      onOpen();
    } catch (err: any) {
      console.error("Erro ao carregar detalhes do fornecedor:", err);
      setError(err.message || 'Erro ao carregar detalhes do fornecedor.');
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

  // Calculate total revenue from all suppliers
  const totalRevenue = (overviewData.ranking_por_receita || []).reduce(
    (sum: number, item: any) => sum + item.receita_total,
    0
  );

  // Calculate new suppliers (first purchase in last 30 days)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  const newSuppliersCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
    const firstSaleDate = new Date(item.primeira_venda);
    return firstSaleDate >= thirtyDaysAgo;
  }).length;

  // Transform regional chart data for map
  const mapMarkers = (overviewData.chart_fornecedores_por_regiao || []).map((region: any) => {
    const coords = getRegionCoordinates(region.name);
    return {
      position: [coords.lat, coords.lng] as [number, number],
      popupText: `${region.name}: ${region.total || 0} fornecedores`
    };
  });

  // Use first marker for center, or default to São Paulo
  const mapCenter = mapMarkers.length > 0
    ? mapMarkers[0].position
    : [-23.55052, -46.633308] as [number, number];

  // Map the data for the ListCard - dynamic based on selected metric
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
    let description = '';
    if (selectedMetric === 'receita') {
      description = `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'qtd_media') {
      description = `Qtd Média: ${(item.qtd_media_por_pedido ?? item.qtd_media ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'ticket_medio') {
      description = `Ticket Médio: R$ ${(item.ticket_medio ?? item.avg_order_value ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'frequencia') {
      description = `Frequência: ${(item.frequencia_pedidos_mes ?? item.frequencia ?? 0).toFixed(1)} pedidos/mês`;
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
        bg="#92DAFF"
        color="gray.800"
      >
        <Flex justify="space-between" align="flex-start" mb="8px">
          <Text as="h1" textStyle="pageSubtitle">
            {userName}, você {overviewData.scorecard_crescimento_percentual !== null && overviewData.scorecard_crescimento_percentual !== undefined
              ? `aumentou sua base de fornecedores em ${overviewData.scorecard_crescimento_percentual >= 0 ? '+' : ''}${overviewData.scorecard_crescimento_percentual.toFixed(2)}%`
              : 'está expandindo sua rede de fornecedores'}
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

        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE FORNECEDORES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_fornecedores}</Text>
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

        <Flex wrap="wrap" justify="center" gap="16px">
          <DashboardCard
            title="Crescimento de Fornecedores no Tempo"
            size="small"
            bgColor="#B2E7FF"
            graphData={{
              values: overviewData.chart_fornecedores_no_tempo
                ? overviewData.chart_fornecedores_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total || 0
                }))
                : []
            }}
            scorecardValue={overviewData.scorecard_total_fornecedores.toString()}
            scorecardLabel="Total de Fornecedores"
            kpiItems={[
              {
                label: `Total de Fornecedores: ${overviewData.scorecard_total_fornecedores}`,
                content: <Text>Número total de fornecedores ativos na base</Text>
              },
              {
                label: 'Evolução no Tempo',
                content: <Text>Acompanhe o crescimento do número de fornecedores ao longo do tempo.</Text>
              }
            ]}
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
          />

          <DashboardCard
            title="Receita Mensal dos Fornecedores"
            size="small"
            bgColor="#B2E7FF"
            graphData={{
              values: overviewData.chart_receita_no_tempo
                ? overviewData.chart_receita_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total || 0
                }))
                : []
            }}
            scorecardValue={new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalRevenue)}
            scorecardLabel="Receita Total"
            kpiItems={[
              {
                label: `Receita Total: ${new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalRevenue)}`,
                content: <Text>Valor total de receita gerada através de todos os fornecedores</Text>
              },
              {
                label: 'Flutuação Mensal',
                content: <Text>Acompanhe mês a mês da flutuação de receita geral comercializada por todos os fornecedores.</Text>
              }
            ]}
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
          />

          <DashboardCard
            title="Ticket Médio dos Fornecedores"
            size="small"
            bgColor="#B2E7FF"
            graphData={{
              values: overviewData.chart_ticketmedio_no_tempo
                ? overviewData.chart_ticketmedio_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total || 0
                }))
                : []
            }}
            scorecardValue={overviewData.chart_ticketmedio_no_tempo && overviewData.chart_ticketmedio_no_tempo.length > 0
              ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
                overviewData.chart_ticketmedio_no_tempo[overviewData.chart_ticketmedio_no_tempo.length - 1].total || 0
              )
              : 'N/A'
            }
            scorecardLabel="Ticket Médio Atual"
            kpiItems={[
              {
                label: 'Ticket Médio',
                content: <Text>Quantidade total comercializada dividida pela quantidade de orders.</Text>
              },
              {
                label: 'Evolução Mensal',
                content: <Text>Mês a mês da flutuação do ticket médio geral dos fornecedores.</Text>
              }
            ]}
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
          />

          <DashboardCard
            title="Volume Comercializado (Quantidade)"
            size="small"
            bgColor="#B2E7FF"
            graphData={{
              values: overviewData.chart_quantidade_no_tempo
                ? overviewData.chart_quantidade_no_tempo.map((d: any) => ({
                  name: d.name,
                  value: d.total || 0
                }))
                : []
            }}
            scorecardValue={overviewData.chart_quantidade_no_tempo && overviewData.chart_quantidade_no_tempo.length > 0
              ? overviewData.chart_quantidade_no_tempo[overviewData.chart_quantidade_no_tempo.length - 1].total?.toLocaleString('pt-BR') || 'N/A'
              : 'N/A'
            }
            scorecardLabel="Volume Atual"
            kpiItems={[
              {
                label: 'Volume Total',
                content: <Text>Quantidade total (toneladas ou kgs) comercializada pelos fornecedores.</Text>
              },
              {
                label: 'Flutuação Mensal',
                content: <Text>Mês a mês da flutuação do volume comercializado.</Text>
              }
            ]}
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
          />

          <DashboardCard
            title="Novos Fornecedores"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText={`Aumentamos nossa base com ${newSuppliersCount} novos fornecedores no último mês.`}
            scorecardValue={newSuppliersCount.toString()}
            scorecardLabel="Novos Cadastros"
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
            modalContent={<Text>Detalhes dos novos fornecedores</Text>}
          />
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
            cardBgColor="#B2E7FF"
          />
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white"
            mapData={{
              center: mapCenter,
              zoom: mapMarkers.length > 1 ? 4 : 10,
              markers: mapMarkers.length > 0 ? mapMarkers : [{ position: [-23.55052, -46.633308] as [number, number], popupText: 'São Paulo' }]
            }}
            mainText="Principais regiões de atuação dos fornecedores."
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
            modalContent={<Text>Detalhes do mapa de distribuição</Text>}
          />
        </Flex>
      </Flex>
      <FornecedorDetailsModal
        isOpen={isOpen}
        onClose={onClose}
        fornecedor={selectedItem}
        overviewData={overviewData}
      />
    </MainLayout>
  );
}

export default FornecedoresPage;