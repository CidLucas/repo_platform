import { Box, Flex, Text, Heading, Select, HStack, useDisclosure } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard';
import React, { useState } from 'react';
import { PedidoDetailsModal } from '../components/PedidoDetailsModal';

function PedidosPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);

  const handleMiniCardClick = (item: any) => {
    setSelectedItem(item);
    onOpen();
  };

  const samplePedidos = [
    {
      id: "1",
      title: "Pedido #001",
      description: "Cliente: João Silva",
      status: "Concluído",
      clientName: "João Silva", // Added clientName
      valorUnitario: "R$ 50,00",
      enderecoEntrega: "Rua A, 123 - Cidade X",
      cnpjFaturamento: "11.222.333/0001-44",
      descricaoProdutos: "3x Garrafa de Prata, 1x Copo de Vidro",
      modalContent: <Text>Detalhes do Pedido #001</Text>
    },
    {
      id: "2",
      title: "Pedido #002",
      description: "Cliente: Maria Souza",
      status: "Pendente",
      clientName: "Maria Souza", // Added clientName
      valorUnitario: "R$ 46,10",
      enderecoEntrega: "Av. B, 456 - Cidade Y",
      cnpjFaturamento: "55.666.777/0001-88",
      descricaoProdutos: "2x Camiseta, 1x Calça Jeans",
      modalContent: <Text>Detalhes do Pedido #002</Text>
    },
    {
      id: "3",
      title: "Pedido #003",
      description: "Cliente: Pedro Santos",
      status: "Concluído",
      clientName: "Pedro Santos", // Added clientName
      valorUnitario: "R$ 40,00",
      enderecoEntrega: "Travessa C, 789 - Cidade Z",
      cnpjFaturamento: "99.888.777/0001-22",
      descricaoProdutos: "1x Livro de Receitas, 1x Caneta",
      modalContent: <Text>Detalhes do Pedido #003</Text>
    },
    {
      id: "4",
      title: "Pedido #004",
      description: "Cliente: Ana Costa",
      status: "Em Andamento",
      clientName: "Ana Costa", // Added clientName
      valorUnitario: "R$ 50,00",
      enderecoEntrega: "Rua D, 101 - Cidade W",
      cnpjFaturamento: "12.345.678/0001-90",
      descricaoProdutos: "5x Caderno, 5x Caneta",
      modalContent: <Text>Detalhes do Pedido #004</Text>
    },
    {
      id: "5",
      title: "Pedido #005",
      description: "Cliente: Carlos Lima",
      status: "Pendente",
      clientName: "Carlos Lima", // Added clientName
      valorUnitario: "R$ 30,00",
      enderecoEntrega: "Av. E, 202 - Cidade V",
      cnpjFaturamento: "87.654.321/0001-09",
      descricaoProdutos: "2x Pão, 1x Leite",
      modalContent: <Text>Detalhes do Pedido #005</Text>
    },
  ];

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
            items={samplePedidos}
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