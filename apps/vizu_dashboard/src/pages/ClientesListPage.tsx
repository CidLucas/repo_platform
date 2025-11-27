import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { ClienteDetailsModal } from '../components/ClienteDetailsModal'; // Use ClienteDetailsModal
import { getClientes, getCliente } from '../services/analyticsService'; // Use getClientes and getCliente
import type { ClientesOverviewResponse, ClienteDetailResponse } from '../services/analyticsService'; // Use client types

function ClientesListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedCliente, setSelectedCliente] = useState<ClienteDetailResponse | null>(null); // Use ClienteDetailResponse
  const [overviewData, setOverviewData] = useState<ClientesOverviewResponse | null>(null); // Use ClientesOverviewResponse
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchClientesData = async () => {
      try {
        setLoading(true);
        const data = await getClientes(); // Call getClientes
        setOverviewData(data);
      } catch (err: any) {
        setError(err.message || 'Erro ao carregar clientes.');
      } finally {
        setLoading(false);
      }
    };
    fetchClientesData();
  }, []);

  const handleClientRowClick = async (clienteItem: { nome: string }) => {
    // When a client row is clicked, fetch the detailed data for that specific client
    try {
      setSelectedCliente(null); // Clear previous selection while loading
      const details = await getCliente(clienteItem.nome); // 'nome' is the client identifier
      setSelectedCliente(details);
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

  // Use ranking_por_receita for the table, or another ranking from ClientesOverviewResponse
  const clientesList = overviewData.ranking_por_receita || []; // Ensure it's an array

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
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Clientes por Receita</Text> {/* Adjusted title */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Cliente
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
              {clientesList.map((clienteItem, index) => (
                <Tr
                  key={clienteItem.nome} // Use nome as key
                  borderBottom={index < clientesList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer"
                  _hover={{ bg: "gray.50" }}
                  onClick={() => handleClientRowClick(clienteItem)}
                >
                  <Td py={5}>{clienteItem.nome}</Td>
                  <Td py={5}>{`R$ ${clienteItem.receita_total.toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${clienteItem.ticket_medio.toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`${clienteItem.frequencia_pedidos_mes.toFixed(2)} / mês`}</Td>
                  <Td py={5}>{clienteItem.cluster_tier}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Flex>

      {/* Reusable ClienteDetailsModal */}
      <ClienteDetailsModal isOpen={isOpen} onClose={onClose} cliente={selectedCliente} />
    </MainLayout>
  );
}

export default ClientesListPage;