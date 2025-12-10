import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor } from '../services/analyticsService';
import type { FornecedoresOverviewResponse, FornecedorDetailResponse } from '../services/analyticsService';

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<FornecedorDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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

  // Map the data for the ListCard
  const listCardItems = overviewData.ranking_por_receita.map(item => ({
    id: item.nome, // Use 'nome' as a unique ID for the card
    title: item.nome,
    description: `Receita: R$ ${item.receita_total.toLocaleString('pt-BR')}`,
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
          <Text as="h1" textStyle="pageSubtitle">Fábio, você aumentou<br />sua base de fornecedores em <Text as="span" fontWeight="bold">+0.85%</Text></Text>
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
            graphData={{ values: [10, 20, 15, 25, 22] }}
            scorecardValue="R$ 1.5M"
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
            mainText="Aumentamos nossa base em 15% no último mês."
            scorecardValue="120"
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
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }}
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