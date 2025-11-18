import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutos, Produto } from '../services/analyticsService'; // Import getProdutos and Produto interface

function ProdutosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedProduto, setSelectedProduto] = useState<any>(null);
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

  const handleProductRowClick = (produto: any) => {
    setSelectedProduto(produto);
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
        bg="#FFF856" // Page background color for Produtos
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Produtos</Text> {/* Increased mt for spacing */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Produto
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
                <Th py={4}>Título</Th>
                <Th py={4}>Preço Unitário</Th>
                <Th py={4}>Estoque</Th>
                <Th py={4}>Status</Th>
                <Th py={4}>Categoria</Th>
                <Th py={4}>Fornecedor</Th>
              </Tr>
            </Thead>
            <Tbody>
              {produtos.map((produto, index) => (
                <Tr
                  key={produto.id}
                  borderBottom={index < produtos.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleProductRowClick(produto)}
                >
                  <Td py={5}>{produto.id}</Td> {/* Increased py */}
                  <Td py={5}>{produto.titulo}</Td>
                  <Td py={5}>{produto.precoUnitario}</Td>
                  <Td py={5}>{produto.estoque}</Td>
                  <Td py={5}>{produto.status}</Td>
                  <Td py={5}>{produto.categoria}</Td>
                  <Td py={5}>{produto.fornecedor}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Flex>

      {/* Reusable ProdutoDetailsModal */}
      <ProdutoDetailsModal isOpen={isOpen} onClose={onClose} produto={selectedProduto} />
    </MainLayout>
  );
}

export default ProdutosListPage;