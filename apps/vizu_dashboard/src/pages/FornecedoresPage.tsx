import { Box, Flex, Text, Heading, Select, HStack, useDisclosure } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { ListCard } from '../components/ListCard'; // Import ListCard
import React, { useState } from 'react'; // Import useState
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal'; // Import FornecedorDetailsModal

function FornecedoresPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedItem, setSelectedItem] = useState<any>(null);

  const handleMiniCardClick = (item: any) => {
    setSelectedItem(item);
    onOpen();
  };

  const sampleFornecedores = [
    {
      id: "1",
      title: "Fornecedor Alpha",
      description: "Tipo: Matéria-prima",
      status: "Ativo",
      nome: "Fornecedor Alpha Ltda.",
      totalFornecido: "R$ 500K",
      pedidosAtivos: 15,
      avaliacaoMedia: "4.7",
      tempoResposta: "2h",
      tipo: "Matéria-prima",
      contatoPrincipal: "João Silva",
      endereco: "Rua das Flores, 123 - SP"
    },
    {
      id: "2",
      title: "Fornecedor Beta",
      description: "Tipo: Componentes",
      status: "Ativo",
      nome: "Beta Componentes S.A.",
      totalFornecido: "R$ 300K",
      pedidosAtivos: 8,
      avaliacaoMedia: "4.2",
      tempoResposta: "4h",
      tipo: "Componentes Eletrônicos",
      contatoPrincipal: "Maria Souza",
      endereco: "Av. Central, 456 - RJ"
    },
    {
      id: "3",
      title: "Fornecedor Gama",
      description: "Tipo: Serviços",
      status: "Inativo",
      nome: "Gama Serviços Ltda.",
      totalFornecido: "R$ 100K",
      pedidosAtivos: 0,
      avaliacaoMedia: "3.5",
      tempoResposta: "12h",
      tipo: "Serviços de TI",
      contatoPrincipal: "Pedro Santos",
      endereco: "Praça da Sé, 789 - MG"
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
          {/* Card Type 1: Title, Graph, Scorecard (Large) */}
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
            items={sampleFornecedores}
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
