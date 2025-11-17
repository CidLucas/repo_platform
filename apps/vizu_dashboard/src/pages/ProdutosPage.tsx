import { Box, Flex, Text, Heading, Select, HStack, useDisclosure } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard'; // Import ListCard
import React, { useState } from 'react'; // Import useState
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal'; // Import ProdutoDetailsModal

function ProdutosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);

  const handleMiniCardClick = (item: any) => {
    setSelectedItem(item);
    onOpen();
  };

  const sampleProdutos = [
    {
      id: "1",
      title: "Produto A",
      description: "Categoria: Eletrônicos",
      status: "Disponível",
      clientName: "Fornecedor X", // Using clientName for supplier name
      precoUnitario: "R$ 150,00",
      estoque: 100,
      vendasMes: 50,
      avaliacaoMedia: "4.5",
      categoria: "Eletrônicos",
      fornecedor: "Fornecedor X",
      descricaoDetalhada: "Smartphone de última geração com câmera de alta resolução e bateria de longa duração."
    },
    {
      id: "2",
      title: "Produto B",
      description: "Categoria: Vestuário",
      status: "Esgotado",
      clientName: "Fornecedor Y",
      precoUnitario: "R$ 80,00",
      estoque: 0,
      vendasMes: 20,
      avaliacaoMedia: "3.8",
      categoria: "Vestuário",
      fornecedor: "Fornecedor Y",
      descricaoDetalhada: "Camiseta de algodão orgânico, confortável e durável."
    },
    {
      id: "3",
      title: "Produto C",
      description: "Categoria: Alimentos",
      status: "Disponível",
      clientName: "Fornecedor Z",
      precoUnitario: "R$ 10,00",
      estoque: 500,
      vendasMes: 200,
      avaliacaoMedia: "4.9",
      categoria: "Alimentos",
      fornecedor: "Fornecedor Z",
      descricaoDetalhada: "Café gourmet moído na hora, com grãos selecionados."
    },
  ];

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
            items={sampleProdutos}
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