import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal';
import { getClientes, getCliente } from '../services/analyticsService';
import type { ClientesOverviewResponse, ClienteDetailResponse } from '../services/analyticsService';
import { useUserProfile } from '../hooks/useUserProfile';
import { getRegionCoordinates } from '../utils/regionCoordinates';

function ClientesPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ClienteDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<ClientesOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const profile = useUserProfile();
  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

  useEffect(() => {
    const fetchClientesData = async () => {
      try {
        setLoading(true);
        const data = await getClientes();
        console.log('Clientes data received:', data);

        // Check if data is in expected format
        if (Array.isArray(data)) {
          console.error('API returned array instead of ClientesOverviewResponse object');
          setError('Formato de dados inválido retornado pela API');
          return;
        }

        setOverviewData(data);
      } catch (err: any) {
        console.error('Error fetching clientes:', err);
        setError(err.message || 'Erro ao carregar dados dos clientes.');
      } finally {
        setLoading(false);
      }
    };
    fetchClientesData();
  }, []);

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

  // Transform regional chart data for map
  const mapMarkers = (overviewData.chart_clientes_por_regiao || []).map((region: any) => {
    const coords = getRegionCoordinates(region.name);
    return {
      position: [coords.lat, coords.lng] as [number, number],
      popupText: `${region.name}: ${region.percentual || 0}% dos clientes`
    };
  });

  // Use first marker for center, or default to São Paulo
  const mapCenter = mapMarkers.length > 0
    ? mapMarkers[0].position
    : [-23.55052, -46.633308] as [number, number];

  // Map the data for the ListCard - using ranking_por_receita for clients
  const listCardItems = (overviewData.ranking_por_receita || []).map(item => ({
    id: item.nome, // Use 'nome' as a unique ID for the card
    title: item.nome,
    description: `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`,
    status: item.cluster_tier, // Using cluster_tier as status
  }));

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
        </Flex>

        <Flex justify="space-between" align="flex-end" mb="36px">
          <Box>
            <Text textStyle="homeCardStatLabel">TOTAL DE CLIENTES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_clientes}</Text>
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
          {/* Example Dashboard Cards - these would need to be adapted for client specific data */}
          <DashboardCard
            title="Performance de Clientes"
            size="large"
            bgColor="#FFD1DC" // Lighter pink
            graphData={{
              values: overviewData.chart_cohort_clientes
                ? overviewData.chart_cohort_clientes.map((d: any) => d.contagem || 0)
                : []
            }}
            scorecardValue={`R$ ${(overviewData.scorecard_ticket_medio_geral ?? 0).toLocaleString('pt-BR')}`}
            scorecardLabel="Ticket Médio Geral"
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1" // Pink
            modalContent={<Text>Detalhes do gráfico de clientes</Text>}
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
            modalRightBgColor="#FFB6C1" // Pink
            modalContent={<Text>Detalhes dos novos clientes</Text>}
          />

          <ListCard
            title="Clientes com Maior Receita"
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
              center: mapCenter,
              zoom: mapMarkers.length > 1 ? 4 : 10,
              markers: mapMarkers.length > 0 ? mapMarkers : [{ position: [-23.55052, -46.633308] as [number, number], popupText: 'São Paulo' }]
            }}
            mainText="Principais regiões de atuação dos clientes."
            modalLeftBgColor="#FFD1DC"
            modalRightBgColor="#FFB6C1" // Pink
            modalContent={<Text>Detalhes do mapa de distribuição de clientes</Text>}
          />
        </Flex>
      </Flex>

      {/* Reusable ClienteDetailsModal */}
      <ClienteDetailsModal isOpen={isOpen} onClose={onClose} cliente={selectedItem} />
    </MainLayout>
  );
}

export default ClientesPage;