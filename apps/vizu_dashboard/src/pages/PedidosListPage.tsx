import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { PedidoDetailsModal } from '../components/PedidoDetailsModal';
import { getPedidos } from '../services/analyticsService';
import type { Pedido } from '../services/analyticsService';

function PedidosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedPedido, setSelectedPedido] = useState<any>(null);
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

  const handleRowClick = (pedido: any) => {
    setSelectedPedido(pedido);
    onOpen();
  };

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
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Pedidos</Text> {/* Increased mt for spacing */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Criar Novo Pedido
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
          <Table variant="unstyled"> {/* Removed size="md" */}
            <Thead>
              <Tr borderBottom="3px solid black"> {/* Thick black line below headers */}
                <Th py={4}>Número do Pedido</Th>
                <Th py={4}>Valor Total</Th>
                <Th py={4}>Status</Th>
                <Th py={4}>Descrição</Th>
                <Th py={4}>Valor do Frete</Th>
                <Th py={4}>Quantidade de Itens</Th>
              </Tr>
            </Thead>
            <Tbody>
              {pedidos.map((pedido, index) => (
                <Tr
                  key={pedido.id}
                  borderBottom={index < pedidos.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleRowClick(pedido)}
                >
                  <Td py={5}>{pedido.id}</Td> {/* Increased py */}
                  <Td py={5}>{pedido.valorTotal}</Td>
                  <Td py={5}>{pedido.status}</Td>
                  <Td py={5}>{pedido.descricao}</Td>
                  <Td py={5}>{pedido.frete}</Td>
                  <Td py={5}>{pedido.quantidadeItens}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Flex>

      {/* Reusable PedidoDetailsModal */}
      <PedidoDetailsModal isOpen={isOpen} onClose={onClose} pedido={selectedPedido} />
    </MainLayout>
  );
}

export default PedidosListPage;