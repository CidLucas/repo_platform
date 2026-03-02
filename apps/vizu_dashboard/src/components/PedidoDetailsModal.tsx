import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent';
import type { PedidoDetailResponse } from '../services/analyticsService';
import type { MapData } from '../types';

interface PedidoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  pedido: PedidoDetailResponse | null;
  mapData?: MapData;
}

/** Format currency in BRL */
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value);
};

export const PedidoDetailsModal: React.FC<PedidoDetailsModalProps> = ({ isOpen, onClose, pedido, mapData }) => {
  if (!pedido) return null;

  // Derive display values from PedidoDetailResponse
  const clientName = pedido.dados_cliente?.name || pedido.dados_cliente?.cnpj || 'N/A';
  const quantidadeItens = pedido.itens_pedido?.reduce((acc, item) => acc + item.quantidade, 0) || 0;
  const valorTotal = formatCurrency(pedido.total_pedido || 0);
  // Calculate average unit price from items
  const valorUnitarioMedio = pedido.itens_pedido?.length > 0
    ? formatCurrency(pedido.total_pedido / quantidadeItens)
    : 'N/A';
  const enderecoEntrega = pedido.dados_cliente?.endereco || 'N/A';
  const cnpjFaturamento = pedido.dados_cliente?.cnpj || 'N/A';
  const descricaoProdutos =
    pedido.itens_pedido
      ?.map(item => item.descricao_produto || item.raw_product_description)
      .join(', ') ||
    'N/A';

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={mapData ? "transparent" : "#FFD3E1"}
            rightBgColor="#F9BBCB"
            isMapModal={Boolean(mapData)}
            mapData={mapData}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{clientName}</Text>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Pedido #{pedido.order_id}</Text>
                  <Box
                    bg={pedido.status_pedido === "Concluído" ? "green.500" : pedido.status_pedido === "Pendente" ? "orange.500" : "gray.500"}
                    color="white"
                    width="69px"
                    height="20px"
                    px="0"
                    py="0"
                    borderRadius="md"
                    textTransform="uppercase"
                    fontSize="10px"
                    fontWeight="semibold"
                    display="flex"
                    justifyContent="center"
                    alignItems="center"
                  >
                    {pedido.status_pedido || "N/A"}
                  </Box>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center">
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">QUANTIDADE</Text>
                      <Text textStyle="modalFinancialInfo">{quantidadeItens}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">VALOR UNITÁRIO</Text>
                      <Text textStyle="modalFinancialInfo">{valorUnitarioMedio}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">FRETE</Text>
                      <Text textStyle="modalFinancialInfo">N/A</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">VALOR TOTAL</Text>
                      <Text textStyle="modalFinancialInfo">{valorTotal}</Text>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            }
            rightContent={
              mapData ? (
                <MapComponent {...mapData} height="100%" />
              ) : (
                <Flex direction="column" height="100%" p={8}>
                  <Flex justify="space-between" align="center" mb={4}>
                    <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO PEDIDO</Text>
                    <ModalCloseButton position="static" onClick={onClose} />
                  </Flex>
                  <Flex direction="column" gap={4}>
                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Endereço da Entrega</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{enderecoEntrega}</Text>
                    </Box>

                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">CNPJ de Faturamento</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{cnpjFaturamento}</Text>
                    </Box>

                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Descrição dos Produtos</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{descricaoProdutos}</Text>
                    </Box>
                  </Flex>
                </Flex>
              )
            }
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};