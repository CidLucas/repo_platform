import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores, getFornecedor } from '../services/analyticsService'; // Import getFornecedor for details
import type { FornecedoresOverviewResponse, FornecedorDetailResponse, RankingItem } from '../services/analyticsService'; // Import necessary types

function FornecedoresListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedFornecedor, setSelectedFornecedor] = useState<FornecedorDetailResponse | null>(null); // Use FornecedorDetailResponse
  const [overviewData, setOverviewData] = useState<FornecedoresOverviewResponse | null>(null); // Use FornecedoresOverviewResponse
  const [loading, setLoading] = useState<boolean>(true); // Loading state
  const [error, setError] = useState<string | null>(null); // Error state

  useEffect(() => {
    const fetchFornecedoresData = async () => {
      try {
        setLoading(true);
        const data = await getFornecedores(); // Call getFornecedores
        setOverviewData(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar fornecedores.');
      } finally {
        setLoading(false);
      }
    };
    fetchFornecedoresData();
  }, []); // Empty dependency array means this runs once on mount

  const handleFornecedorRowClick = async (fornecedorItem: RankingItem) => {
    // When a row is clicked, fetch the detailed data for that specific supplier
    try {
      setSelectedFornecedor(null); // Clear previous selection while loading
      const details = await getFornecedor(fornecedorItem.nome); // 'nome' is the identifier for details
      setSelectedFornecedor(details);
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

  // Use ranking_por_receita for the table
  const fornecedoresList = overviewData.ranking_por_receita || []; // Ensure it's an array

  return (
    <MainLayout>
      <Flex
        direction="column"
        flex="1"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }}
        bg="#92DAFF" // Page background color for Fornecedores (Light Blue)
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Fornecedores por Receita</Text> {/* Adjusted title */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Fornecedor
          </Button>
        </Flex>
        
        {loading ? (
          <Flex justify="center" align="center" height="200px">
            <Spinner size="xl" />
          </Flex>
        ) : error ? (
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        ) : (
          <Table variant="unstyled">
            <Thead>
              <Tr borderBottom="3px solid black">
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita Total</Th>
                <Th py={4}>Ticket Médio</Th>
                <Th py={4}>Frequência de Pedidos</Th>
                <Th py={4}>Tier</Th>
              </Tr>
            </Thead>
            <Tbody>
              {fornecedoresList.map((fornecedorItem, index) => (
                <Tr
                  key={fornecedorItem.nome} // Use nome as key
                  borderBottom={index < fornecedoresList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleFornecedorRowClick(fornecedorItem)}
                >
                  <Td py={5}>{fornecedorItem.nome}</Td>
                  <Td py={5}>{`R$ ${(fornecedorItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(fornecedorItem.ticket_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`${(fornecedorItem.frequencia_pedidos_mes ?? 0).toFixed(2)} / mês`}</Td>
                  <Td py={5}>{fornecedorItem.cluster_tier}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Flex>

      {/* Reusable FornecedorDetailsModal */}
      <FornecedorDetailsModal isOpen={isOpen} onClose={onClose} fornecedor={selectedFornecedor} />
    </MainLayout>
  );
}

export default FornecedoresListPage;