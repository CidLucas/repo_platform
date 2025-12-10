import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal';
import { getClientes, getCliente } from '../services/analyticsService';
import type { ClientesOverviewResponse, ClienteDetailResponse } from '../services/analyticsService';

function ClientesPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ClienteDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<ClientesOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchClientesData = async () => {
      try {
        setLoading(true);
        const data = await getClientes();
        setOverviewData(data);
      } catch (err: any) {
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

  // Map the data for the ListCard - using ranking_por_receita for clients
  const listCardItems = overviewData.ranking_por_receita.map(item => ({
    id: item.nome, // Use 'nome' as a unique ID for the card
    title: item.nome,
    description: `Receita: R$ ${item.receita_total.toLocaleString('pt-BR')}`,
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
          <Text as="h1" textStyle="pageSubtitle">Fábio, sua base de clientes aumentou em <Text as="span" fontWeight="bold">+X%</Text></Text> {/* Placeholder text */}
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
            graphData={{ values: [10, 20, 15, 25, 22] }} // Placeholder
            scorecardValue={`R$ ${overviewData.scorecard_ticket_medio_geral.toLocaleString('pt-BR')}`}
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
            mainText="Aumentamos nossa base em X% no último mês." // Placeholder
            scorecardValue="X" // Placeholder
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
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }} // Placeholder
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