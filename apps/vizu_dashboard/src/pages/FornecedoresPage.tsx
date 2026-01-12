import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor } from '../services/analyticsService';
import type { FornecedoresOverviewResponse, FornecedorDetailResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { getRegionCoordinates } from '../utils/regionCoordinates';

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<FornecedorDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  useEffect(() => {
    const fetchFornecedoresData = async () => {
      try {
        setLoading(true);
        const data = await getFornecedores();
        setOverviewData(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar dados dos fornecedores.');
      } finally {
        setLoading(false);
      }
    };
    fetchFornecedoresData();
  }, []);

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

  // Map the data for the ListCard
  const listCardItems = (overviewData.ranking_por_receita || []).map(item => ({
    id: item.nome, // Use 'nome' as a unique ID for the card
    title: item.nome,
    description: `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`,
    status: item.cluster_tier,
  }));

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
        </Flex>
        
        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE FORNECEDORES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_fornecedores}</Text>
          </Box>
          <HStack spacing="4" position="relative">
            <Select placeholder="Período" width="150px" bg="white" color="gray.800">
              <option value="semana">Última semana</option>
              <option value="mes">Último mês</option>
              <option value="tri">Último tri</option>
              <option value="total">Total</option>
            </Select>
            <Select placeholder="Métricas" width="150px" bg="white" color="gray.800">
              <option value="receita">Receita</option>
              <option value="quantidade">Quantidade</option>
              <option value="ticket_medio">Ticket Médio</option>
            </Select>
          </HStack>
        </Flex>
        
        <Flex wrap="wrap" justify="center" gap="16px">
          <DashboardCard
            title="Performance de Vendas"
            size="large"
            bgColor="#B2E7FF"
            graphData={{
              values: overviewData.chart_fornecedores_no_tempo
                ? overviewData.chart_fornecedores_no_tempo.map((d: any) => d.total_cumulativo || 0)
                : []
            }}
            scorecardValue={new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalRevenue)}
            scorecardLabel="Total Vendido"
            modalLeftBgColor="#B2E7FF"
            modalRightBgColor="#92DAFF"
            modalContent={<Text>Detalhes do gráfico de vendas</Text>}
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
            title="Últimos Fornecedores"
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
      <FornecedorDetailsModal isOpen={isOpen} onClose={onClose} fornecedor={selectedItem} />
    </MainLayout>
  );
}

export default FornecedoresPage;