import { Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td, Button, useDisclosure } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';
import React, { useState } from 'react';
import { FornecedorDetailsModal } from '../components/FornecedorDetailsModal'; // Import FornecedorDetailsModal

function FornecedoresListPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedFornecedor, setSelectedFornecedor] = useState<any>(null);

  const handleFornecedorRowClick = (fornecedor: any) => {
    setSelectedFornecedor(fornecedor);
    onOpen();
  };

  const fornecedores = [
    {
      id: "001",
      nome: "Fornecedor Alpha Ltda.",
      tipo: "Matéria-prima",
      contatoPrincipal: "João Silva",
      totalFornecido: "R$ 500.000,00",
      pedidosAtivos: 15,
      status: "Ativo",
      avaliacaoMedia: "4.7",
      tempoResposta: "2h",
      endereco: "Rua das Flores, 123 - SP"
    },
    {
      id: "002",
      nome: "Beta Componentes S.A.",
      tipo: "Componentes Eletrônicos",
      contatoPrincipal: "Maria Souza",
      totalFornecido: "R$ 300.000,00",
      pedidosAtivos: 8,
      status: "Ativo",
      avaliacaoMedia: "4.2",
      tempoResposta: "4h",
      endereco: "Av. Central, 456 - RJ"
    },
    {
      id: "003",
      nome: "Gama Serviços Ltda.",
      tipo: "Serviços de TI",
      contatoPrincipal: "Pedro Santos",
      totalFornecido: "R$ 100.000,00",
      pedidosAtivos: 0,
      status: "Inativo",
      avaliacaoMedia: "3.5",
      tempoResposta: "12h",
      endereco: "Praça da Sé, 789 - MG"
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
        bg="#92DAFF" // Page background color for Fornecedores
        color="gray.800" // Text color for visibility
      >
        <Flex justify="space-between" align="flex-end" mb="36px"> {/* Container for title and CTA */}
          <Text as="h1" textStyle="pageTitle" mt="32px">Fornecedores</Text> {/* Increased mt for spacing */}
          <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: "gray.100" }}>
            Cadastrar Novo Fornecedor
          </Button>
        </Flex>
        
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
      </Flex>

      {/* Reusable FornecedorDetailsModal */}
      <FornecedorDetailsModal isOpen={isOpen} onClose={onClose} fornecedor={selectedFornecedor} />
    </MainLayout>
  );
}

export default FornecedoresListPage;
