import { Box, Flex, Text, Heading, Select, HStack, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState, useEffect } from 'react'; // Added useEffect
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutos } from '../services/analyticsService';
import type { Produto } from '../services/analyticsService';

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [produtos, setProdutos] = useState<Produto[]>([]); // State for fetched produtos
  const [loading, setLoading] = useState<boolean>(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state

  useEffect(() => {
    const fetchProdutosData = async () => {
      try {
        setLoading(true);
        const data = await getProdutos();
        setProdutos(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar produtos.');
      } finally {
        setLoading(false);
      }
    };
    fetchProdutosData();
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
              bg="#FFF856" // Page background color for Produtos
              color="gray.800" // Text color for visibility
            >        
        {/* New Header Content for Produtos Page */}
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Big numbers and selectors */}
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">TOTAL DE PRODUTOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">1500</Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">PRODUTOS ATIVOS</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">1200</Text>
          </Box>
          <Box> {/* Wrapper for big number title and number */}
            <Text textStyle="homeCardStatLabel">ESTOQUE TOTAL</Text>
            <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">5000</Text>
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
            graphData={{ values: [10, 20, 15, 25, 22] }}
            scorecardValue="R$ 2.5M"
            scorecardLabel="Total Vendido"
            modalLeftBgColor="#FFFB97" // Modal left background
            modalRightBgColor="#FFF856" // Modal right background
            modalContent={<Text>Detalhes do gráfico de produtos</Text>}
          />

          {/* Card Type 2: Categorias de Produtos */}
          <DashboardCard
            title="Categorias de Produtos" // Added missing title
            size="small" // Added missing size
            bgGradient="linear-gradient(to-br, #353A5A, #1F2138)" // Dark blue gradient
            textColor="white" // White text for contrast
            mainText="Análise das categorias de produtos mais vendidas."
            scorecardValue="15"
            scorecardLabel="Categorias Ativas"
            modalLeftBgColor="#FFFB97" // Modal left background
            modalRightBgColor="#FFF856" // Modal right background
            modalContent={<Text>Detalhes das categorias de produtos</Text>}
          />

          {/* Card Type 3: Últimos Produtos (ListCard) */}
          <ListCard
            title="Últimos Produtos"
            items={produtos} // Use fetched data
            onMiniCardClick={handleMiniCardClick}
            viewAllLink="/produtos/lista" // Link to the full list page
            cardBgColor="#FFFB97" // Pass the specific background color for products
          />

          {/* Card Type 4: Distribuição Geográfica (Unchanged) */}
          <DashboardCard
            title="Distribuição Geográfica"
            size="large"
            bgColor="white" // Unchanged
            mapData={{ center: [-23.55052, -46.633308], zoom: 10, markers: [{ position: [-23.55052, -46.633308], popupText: 'São Paulo' }] }}
            mainText="Principais regiões de venda de produtos."
            modalLeftBgColor="#FFFB97" // Modal left background
            modalRightBgColor="#FFF856" // Modal right background
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