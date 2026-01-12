import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure, Spinner, Alert, AlertIcon } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState, useEffect } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal';
import { getProdutosOverview, getProdutoDetails } from '../services/analyticsService';
import type { ProdutosOverviewResponse, ProdutoDetailResponse } from '../services/analyticsService';

function ProdutosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedProduto, setSelectedProduto] = useState<ProdutoDetailResponse | null>(null);
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
        setError(err.message || 'Erro ao carregar produtos.');
      } finally {
        setLoading(false);
      }
    };
    fetchProdutosData();
  }, []);

  const handleProductRowClick = async (produtoItem: { nome: string }) => {
    // When a product row is clicked, fetch the detailed data for that specific product
    try {
      setSelectedProduto(null); // Clear previous selection while loading
      const details = await getProdutoDetails(produtoItem.nome); // 'nome' is the product identifier
      setSelectedProduto(details);
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

  // Use ranking_por_receita for the table
  const produtosList = overviewData.ranking_por_receita || []; // Ensure it's an array

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
          <Text as="h1" textStyle="pageTitle" mt="32px">Produtos por Receita</Text> {/* Adjusted title */}
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
                <Th py={4}>Nome</Th>
                <Th py={4}>Receita Total</Th>
                <Th py={4}>Valor Unitário Médio</Th>
                {/* Add other relevant columns from RankingItem if needed */}
              </Tr>
            </Thead>
            <Tbody>
              {produtosList.map((produtoItem, index) => (
                <Tr
                  key={produtoItem.nome} // Use nome as key
                  borderBottom={index < produtosList.length - 1 ? "1px solid black" : "none"}
                  cursor="pointer" // Make row clickable
                  _hover={{ bg: "gray.50" }} // Hover effect
                  onClick={() => handleProductRowClick(produtoItem)}
                >
                  <Td py={5}>{produtoItem.nome}</Td> {/* Increased py */}
                  <Td py={5}>{`R$ ${(produtoItem.receita_total ?? 0).toLocaleString('pt-BR')}`}</Td>
                  <Td py={5}>{`R$ ${(produtoItem.valor_unitario_medio ?? 0).toLocaleString('pt-BR')}`}</Td>
                  {/* Add other relevant columns from RankingItem if needed */}
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