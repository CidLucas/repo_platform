import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutosOverview, getProdutoDetails } from '../services/analyticsService';
import type { ProdutosOverviewResponse, ProdutoDetailResponse } from '../services/analyticsService';
import { DEFAULT_BRAZIL_CENTER } from '../utils/regionCoordinates';

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<ProdutoDetailResponse | null>(null); // This will hold the detailed data for the modal
  const [overviewData, setOverviewData] = useState<ProdutosOverviewResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProdutosData = async () => {
      try {
        setLoading(true);
        const data = await getProdutosOverview();
        setOverviewData(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar dados dos produtos.');
      } finally {
        setLoading(false);
      }
    };
    fetchProdutosData();
  }, []);

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

  // Map the data for the ListCard - using ranking_por_receita for products
  const listCardItems = overviewData?.ranking_por_receita?.map(item => ({
    id: item.nome, // Use 'nome' as a unique ID for the card
    title: item.nome,
    description: `Receita: R$ ${(item.receita_total ?? 0).toLocaleString('pt-BR')}`,
    // status: item.cluster_tier, // cluster_tier is not available in product ranking item
  })) || [];

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
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">TOTAL DE PRODUTOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">{overviewData.scorecard_total_itens_unicos}</Text>
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
          {/* Card Type 1: Performance de Produtos */}
          <DashboardCard
            title="Performance de Produtos"
            size="large"
            bgColor="#FFFB97" // Specific color for Produtos module
            graphData={{
              values: overviewData.ranking_por_receita && overviewData.ranking_por_receita.length > 0
                ? overviewData.ranking_por_receita.slice(0, 10).map((p: any) => p.receita_total || 0)
                : []
            }}
            scorecardValue={`R$ ${(overviewData.ranking_por_receita || []).reduce((acc: number, curr: any) => acc + curr.receita_total, 0).toLocaleString('pt-BR')}`}
            scorecardLabel="Total Vendido (Top 10)"
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
            title="Produtos com Maior Receita"
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
      <ProdutoDetailsModal isOpen={isOpen} onClose={onClose} produto={selectedItem} />
    </MainLayout>
  );
}

export default ProdutosPage;