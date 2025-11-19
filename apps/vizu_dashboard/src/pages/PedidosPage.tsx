import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react'; // Added useEffect
import { PedidoDetailsModal } from '../components/PedidoDetailsModal';
import { getPedidos } from '../services/analyticsService';
import type { Pedido } from '../services/analyticsService';

function PedidosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [pedidos, setPedidos] = useState<Pedido[]>([]); // State for fetched pedidos
  const [loading, setLoading] = useState<boolean>(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state

  useEffect(() => {
    const fetchPedidosData = async () => {
      try {
        setLoading(true);
        const data = await getPedidos();
        setPedidos(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar pedidos.');
      } finally {
        setLoading(false);
      }
    };
    fetchPedidosData();
  }, []); // Empty dependency array means this runs once on mount

  const handleMiniCardClick = (item: any) => {
    setSelectedItem(item);
    onOpen();
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

  if (error) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error">
            <AlertIcon />
            {error}
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
        bg="#F9BBCB" // Page background color for Pedidos
        color="gray.800" // Text color for visibility
      >
        {/* New Header Content for Pedidos Page */}
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Big numbers and selectors */}
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">TOTAL DE PEDIDOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">250</Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">PEDIDOS CONCLUÍDOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">200</Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">PEDIDOS PENDENTES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">50</Text>
          </Box>
          <HStack spacing="4" position="relative"> {/* HStack for multiple Selects */}
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
        {/* Grid of DashboardCards */}
        <Flex wrap="wrap" justify="center" gap="16px">
          {/* Card Type 1: Performance de Pedidos */}
          <DashboardCard
            title="Performance de Pedidos"
            size="large"
            bgColor="#FFD3E1" // Specific color for Pedidos module
            graphData={{ values: [10, 20, 15, 25, 22] }}
            scorecardValue="R$ 50K"
            scorecardLabel="Total Vendido"
            modalLeftBgColor="#FFD3E1" // Modal left background
            modalRightBgColor="#F9BBCB" // Modal right background
            modalContent={<Text>Detalhes do gráfico de pedidos</Text>}
          />

          {/* Card Type 2: List of Pedidos */}
          <ListCard
            title="Últimos Pedidos"
            items={pedidos} // Use fetched data
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/pedidos/lista" // Link to the full list page
          />

          {/* Card Type 3: Histórico de Pedidos */}
          <DashboardCard
            title="Histórico de Pedidos"
            size="small"
            bgColor="#FFD3E1" // Specific color for Pedidos module
            mainText="Histórico completo de todos os pedidos."
            modalLeftBgColor="#FFD3E1" // Modal left background
            modalRightBgColor="#F9BBCB" // Modal right background
            modalContent={<Text>Detalhes do histórico de pedidos</Text>}
          />

          {/* Card Type 4: Distribuição Geográfica (Unchanged) */}
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white" // Unchanged
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }}
            mainText="Principais regiões de entrega de pedidos."
            modalLeftBgColor="#FFD3E1" // Modal left background
            modalRightBgColor="#F9BBCB" // Modal right background
            modalContent={<Text>Detalhes do mapa de distribuição de pedidos</Text>}
          />
        </Flex>
      </Flex>

      {/* Reusable PedidoDetailsModal */}
      <PedidoDetailsModal isOpen={isOpen} onClose={onClose} pedido={selectedItem} />
    </MainLayout>
  );
}

export default PedidosPage;