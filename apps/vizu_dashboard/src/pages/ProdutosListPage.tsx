import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState } from 'react';
import { ProdutoDetailsModal } from '../components/ProdutoDetailsModal'; // Import ProdutoDetailsModal

function ProdutosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedProduto, setSelectedProduto] = useState<any>(null);

  const handleProductRowClick = (produto: any) => {
    setSelectedProduto(produto);
    onOpen();
  };

  const produtos = [
    {
      id: "001",
      titulo: "Monitor Gamer Odyssey G9",
      precoUnitario: "R$ 6.500,00",
      estoque: 50,
      categoria: "Eletrônicos",
      fornecedor: "Samsung Brasil",
      status: "Disponível",
      clientName: "Samsung Brasil", // Using clientName for supplier name in modal
      vendasMes: "25",
      avaliacaoMedia: "4.8",
      descricaoDetalhada: "Monitor curvo ultrawide para jogos, 49 polegadas, 240Hz, 1ms."
    },
    {
      id: "002",
      titulo: "Cafeteira Expresso Automática",
      precoUnitario: "R$ 1.200,00",
      estoque: 120,
      categoria: "Eletrodomésticos",
      fornecedor: "Latte Mania S.A.",
      status: "Disponível",
      clientName: "Latte Mania S.A.",
      vendasMes: "80",
      avaliacaoMedia: "4.5",
      descricaoDetalhada: "Cafeteira automática com moedor integrado e diversas opções de bebida."
    },
    {
      id: "003",
      titulo: "Kit Teclado e Mouse Sem Fio",
      precoUnitario: "R$ 250,00",
      estoque: 0,
      categoria: "Acessórios de Informática",
      fornecedor: "Tech Acessórios",
      status: "Esgotado",
      clientName: "Tech Acessórios",
      vendasMes: "150",
      avaliacaoMedia: "4.2",
      descricaoDetalhada: "Conjunto de teclado e mouse ergonômicos e sem fio, ideal para o dia a dia."
    }
  ];

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
      </Flex>

      {/* Reusable ProdutoDetailsModal */}
      <ProdutoDetailsModal isOpen={isOpen} onClose={onClose} produto={selectedProduto} />
    </MainLayout>
  );
}

export default ProdutosListPage;
