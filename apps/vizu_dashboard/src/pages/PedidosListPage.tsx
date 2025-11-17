import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure } from '@chakra-ui/react'; // Removed Modal imports
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState } from 'react'; // Added useState
import { PedidoDetailsModal } from '../components/PedidoDetailsModal'; // Import PedidoDetailsModal

function PedidosListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedPedido, setSelectedPedido] = useState<any>(null);

  const handleRowClick = (pedido: any) => {
    setSelectedPedido(pedido);
    onOpen();
  };

  const pedidos = [
    {
      id: "001",
      valorTotal: "R$ 150,00",
      status: "Concluído",
      descricao: "Compra de eletrônicos",
      frete: "R$ 15,00",
      quantidadeItens: 3,
      valorUnitario: "R$ 50,00",
      enderecoEntrega: "Rua A, 123 - Cidade X",
      cnpjFaturamento: "11.222.333/0001-44",
      descricaoProdutos: "3x Garrafa de Prata, 1x Copo de Vidro",
      clientName: "João Silva" // Added clientName
    },
    {
      id: "002",
      valorTotal: "R$ 230,50",
      status: "Pendente",
      descricao: "Pedido de roupas",
      frete: "R$ 20,00",
      quantidadeItens: 5,
      valorUnitario: "R$ 46,10",
      enderecoEntrega: "Av. B, 456 - Cidade Y",
      cnpjFaturamento: "55.666.777/0001-88",
      descricaoProdutos: "2x Camiseta, 1x Calça Jeans",
      clientName: "Maria Souza" // Added clientName
    },
    {
      id: "003",
      valorTotal: "R$ 80,00",
      status: "Concluído",
      descricao: "Livros e papelaria",
      frete: "R$ 10,00",
      quantidadeItens: 2,
      valorUnitario: "R$ 40,00",
      enderecoEntrega: "Travessa C, 789 - Cidade Z",
      cnpjFaturamento: "99.888.777/0001-22",
      descricaoProdutos: "1x Livro de Receitas, 1x Caneta",
      clientName: "Pedro Santos" // Added clientName
    },
    {
      id: "004",
      valorTotal: "R$ 500,00",
      status: "Em Andamento",
      descricao: "Material de escritório",
      frete: "R$ 25,00",
      quantidadeItens: 10,
      valorUnitario: "R$ 50,00",
      enderecoEntrega: "Rua D, 101 - Cidade W",
      cnpjFaturamento: "12.345.678/0001-90",
      descricaoProdutos: "5x Caderno, 5x Caneta",
      clientName: "Ana Costa" // Added clientName
    },
    {
      id: "005",
      valorTotal: "R$ 120,00",
      status: "Concluído",
      descricao: "Alimentos e bebidas",
      frete: "R$ 12,00",
      quantidadeItens: 4,
      valorUnitario: "R$ 30,00",
      enderecoEntrega: "Av. E, 202 - Cidade V",
      cnpjFaturamento: "87.654.321/0001-09",
      descricaoProdutos: "2x Pão, 1x Leite",
      clientName: "Carlos Lima" // Added clientName
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
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Pedidos</Text> {/* Increased mt for spacing */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Criar Novo Pedido
          </Button>
        </Flex>
        
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
      </Flex>

      {/* Reusable PedidoDetailsModal */}
      <PedidoDetailsModal isOpen={isOpen} onClose={onClose} pedido={selectedPedido} />
    </MainLayout>
  );
}

export default PedidosListPage;
