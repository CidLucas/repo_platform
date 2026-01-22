import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon, IconButton } from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutosOverview, getProdutoDetails } from '../services/analyticsService';
import type { ProdutosOverviewResponse, ProdutoDetailResponse } from '../services/analyticsService';
import { DEFAULT_BRAZIL_CENTER } from '../utils/regionCoordinates';

type PeriodType = 'week' | 'month' | 'quarter' | 'year';
type MetricType = 'receita' | 'quantidade' | 'ticket_medio';

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ProdutoDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<ProdutosOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('receita');
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchProdutosData = async () => {
    try {
      setLoading(true);
      const data = await getProdutosOverview(selectedPeriod);
      setOverviewData(data);
      setLastUpdate(new Date());
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados dos produtos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProdutosData();
  }, [selectedPeriod, selectedMetric]);

  const handlePeriodChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedPeriod(e.target.value as PeriodType);
  };

  const handleMetricChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedMetric(e.target.value as MetricType);
  };

  const handleMiniCardClick = async (clickedItem: { id: string }) => {
    // When a mini-card is clicked, fetch the detailed data for that specific product
    try {
      setSelectedItem(null); // Clear previous selection while loading
      const details = await getProdutoDetails(clickedItem.id); // 'id' is 'nome_produto'
      setSelectedItem(details);
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

  // Map the data for the ListCard - dynamic based on selected metric
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

  const listCardItems = getCurrentRanking().map((item: any) => {
    let description = '';
    if (selectedMetric === 'receita') {
      description = `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'quantidade') {
      description = `Quantidade: ${(item.quantidade_total ?? 0).toLocaleString('pt-BR')}`;
    } else if (selectedMetric === 'ticket_medio') {
      description = `Ticket Médio: R$ ${(item.ticket_medio ?? 0).toLocaleString('pt-BR')}`;
    }
    return {
      id: item.nome,
      title: item.nome,
      description,
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
        bg="#FFF856" // Page background color for Produtos
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Big numbers and selectors */}
          <Box>
            <HStack spacing={2} mb={2}>
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
            </HStack>
            <Text textStyle="homeCardStatLabel">TOTAL DE PRODUTOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_itens_unicos}</Text>
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
          {/* Card Type 1: Performance de Produtos */}
          <DashboardCard
            title="Performance de Produtos"
            size="large"
            bgColor="#FFFB97" // Specific color for Produtos module
            graphData={{
              values: (() => {
                const ranking = getCurrentRanking();
                if (ranking.length === 0) return [];
                if (selectedMetric === 'receita') {
                  return ranking.slice(0, 10).map((p: any) => p.receita_total || 0);
                } else if (selectedMetric === 'quantidade') {
                  return ranking.slice(0, 10).map((p: any) => p.quantidade_total || 0);
                } else {
                  return ranking.slice(0, 10).map((p: any) => p.ticket_medio || 0);
                }
              })()
            }}
            scorecardValue={(() => {
              const ranking = getCurrentRanking();
              if (selectedMetric === 'receita') {
                const total = ranking.reduce((acc: number, curr: any) => acc + (curr.receita_total || 0), 0);
                return `R$ ${total.toLocaleString('pt-BR')}`;
              } else if (selectedMetric === 'quantidade') {
                const total = ranking.reduce((acc: number, curr: any) => acc + (curr.quantidade_total || 0), 0);
                return total.toLocaleString('pt-BR');
              } else {
                const avg = ranking.length > 0
                  ? ranking.reduce((acc: number, curr: any) => acc + (curr.ticket_medio || 0), 0) / ranking.length
                  : 0;
                return `R$ ${avg.toLocaleString('pt-BR')}`;
              }
            })()}
            scorecardLabel={(() => {
              if (selectedMetric === 'receita') return 'Total Vendido (Top 10)';
              if (selectedMetric === 'quantidade') return 'Total Quantidade (Top 10)';
              return 'Ticket Médio (Top 10)';
            })()}
            modalLeftBgColor="#FFFB97" // Modal left background
            modalRightBgColor="#FFF856" // Modal right background
            modalContent={<Text>Detalhes do gráfico de produtos</Text>}
          />

          {/* Card Type 2: Categorias de Produtos */}
          <DashboardCard
            title="Categorias de Produtos"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText="Análise das categorias de produtos mais vendidas."
            scorecardValue={overviewData.scorecard_total_itens_unicos.toString()}
            scorecardLabel="Produtos Únicos"
            modalLeftBgColor="#FFFB97"
            modalRightBgColor="#FFF856"
            modalContent={<Text>Detalhes das categorias de produtos</Text>}
          />

          {/* Card Type 3: Produtos (ListCard) */}
          <ListCard
            title={(() => {
              if (selectedMetric === 'receita') return 'Produtos com Maior Receita';
              if (selectedMetric === 'quantidade') return 'Produtos com Maior Volume';
              return 'Produtos com Maior Ticket Médio';
            })()}
            items={listCardItems}
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/dashboard/produtos/lista" // Link to the full list page
            cardBgColor="#FFFB97" // Pass the specific background color
          />

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

      {/* Reusable ProdutoDetailsModal */}
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