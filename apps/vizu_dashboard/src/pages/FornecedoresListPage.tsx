import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal';
import { getFornecedores } from '../services/analyticsService';
import type { Fornecedor } from '../services/analyticsService';

function FornecedoresListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedFornecedor, setSelectedFornecedor] = useState<any>(null);
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

  const handleFornecedorRowClick = (fornecedor: any) => {
    setSelectedFornecedor(fornecedor);
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
        bg="#92DAFF" // Page background color for Fornecedores
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Fornecedores</Text> {/* Increased mt for spacing */}
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
          <Table variant="unstyled"> {/* Removed size="md" */}
            <Thead>
              <Tr borderBottom="3px solid black"> {/* Thick black line below headers */}
                <Th py={4}>ID</Th>
                <Th py={4}>Nome</Th>
                <Th py={4}>Tipo</Th>
                <Th py={4}>Contato Principal</Th>
                <Th py={4}>Total Fornecido</Th>
                <Th py={4}>Status</Th>
              </Tr>
            </Thead>
            <Tbody>
              {fornecedores.map((fornecedor, index) => (
                <Tr
                  key={fornecedor.id}
                  borderBottom={index < fornecedores.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleFornecedorRowClick(fornecedor)}
                >
                  <Td py={5}>{fornecedor.id}</Td> {/* Increased py */}
                  <Td py={5}>{fornecedor.nome}</Td>
                  <Td py={5}>{fornecedor.tipo}</Td>
                  <Td py={5}>{fornecedor.contatoPrincipal}</Td>
                  <Td py={5}>{fornecedor.totalFornecido}</Td>
                  <Td py={5}>{fornecedor.status}</Td>
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