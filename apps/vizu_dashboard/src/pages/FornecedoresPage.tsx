import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react'; // Added useEffect
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, Fornecedor } from '../services/analyticsService'; // Import getFornecedores and Fornecedor interface

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]); // State for fetched fornecedores
  const [loading, setLoading] = useState<boolean>(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state

  useEffect(() => {
    const fetchFornecedoresData = async () => {
      try {
        setLoading(true);
        const data = await getFornecedores();
        setFornecedores(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar fornecedores.');
      } finally {
        setLoading(false);
      }
    };
    fetchFornecedoresData();
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
              flex="1" // Added flex="1"
              px={{ base: '20px', md: '40px', lg: '80px' }}
              pt={{ base: '20px', md: '40px', lg: '20px' }}
              pb={{ base: '80px', md: '40px', lg: '20px' }}
              bg="#92DAFF" // Page background color
              color="gray.800" // Text color for visibility
            >        <Flex justify="space-between" align="flex-start" mb="8px"> {/* Title only */}
          <Text as="h1" textStyle="pageSubtitle">Fábio, você aumentou<br />sua base de fornecedores em <Text as="span" fontWeight="bold">+0.85%</Text></Text>
        </Flex>
        
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Big number and selectors */}
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">TOTAL DE FORNECEDORES</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">800</Text>
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
          {/* Card Type 1: Performance de Vendas */}
          <DashboardCard
            title="Performance de Vendas"
            size="large"
            bgColor="#B2E7FF" // Lighter blue
            graphData={{ values: [10, 20, 15, 25, 22] }}
            scorecardValue="R$ 1.5M"
            scorecardLabel="Total Vendido"
            modalLeftBgColor="#B2E7FF" // Modal left background
            modalRightBgColor="#92DAFF" // Modal right background
            modalContent={<Text>Detalhes do gráfico de vendas</Text>}
          />

          {/* Card Type 2: Novos Fornecedores */}
          <DashboardCard
            title="Novos Fornecedores"
            size="small"
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
            textColor="white"
            mainText="Aumentamos nossa base em 15% no último mês."
            scorecardValue="120"
            scorecardLabel="Novos Cadastros"
            modalLeftBgColor="#B2E7FF" // Modal left background
            modalRightBgColor="#92DAFF" // Modal right background
            modalContent={<Text>Detalhes dos novos fornecedores</Text>}
          />

          {/* Card Type 3: Últimos Fornecedores (ListCard) */}
          <ListCard
            title="Últimos Fornecedores"
            items={fornecedores} // Use fetched data
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/fornecedores/lista" // Link to the full list page
            cardBgColor="#B2E7FF" // Pass the specific background color for suppliers
          />

          {/* Card Type 4: Distribuição Geográfica (Unchanged) */}
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white"
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }}
            mainText="Principais regiões de atuação dos fornecedores."
            modalLeftBgColor="#B2E7FF" // Modal left background
            modalRightBgColor="#92DAFF" // Modal right background
            modalContent={<Text>Detalhes do mapa de distribuição</Text>}
          />
        </Flex>
      </Flex>

      {/* Reusable FornecedorDetailsModal */}
      <FornecedorDetailsModal isOpen={isOpen} onClose={onClose} fornecedor={selectedItem} />
    </MainLayout>
  );
}

export default FornecedoresPage;