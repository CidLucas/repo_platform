import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent';

interface PedidoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  pedido: any; // The selected order data
}

export const PedidoDetailsModal: React.FC<PedidoDetailsModalProps> = ({ isOpen, onClose, pedido }) => {
  if (!pedido) return null; // Don't render if no pedido is selected

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={!!pedido.mapData ? "transparent" : "#FFD3E1"} // Conditionally set leftBgColor
            rightBgColor={!!pedido.mapData ? "#F9BBCB" : "#F9BBCB"} // Use prop
            isMapModal={!!pedido.mapData} // Pass if it's a map modal
            mapData={pedido.mapData} // Pass mapData
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{pedido.clientName || "N/A"}</Text> {/* Client Name - mb reduced */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Pedido #{pedido.id}</Text> {/* Adjusted font size and semibold */}
                  <Box
                    bg={pedido.status === "Concluído" ? "green.500" : pedido.status === "Pendente" ? "orange.500" : "gray.500"}
                    color="white"
                    width="69px"
                    height="20px"
                    px="0"
                    py="0"
                    borderRadius="md"
                    textTransform="uppercase"
                    fontSize="10px" // Custom font size
                    fontWeight="semibold"
                    display="flex"
                    justifyContent="center"
                    alignItems="center"
                  >
                    {pedido.status || "N/A"}
                  </Box>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center"> {/* Wrapper to center financial list */}
                  {/* Financial Information List */}
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">QUANTIDADE</Text>
                      <Text textStyle="modalFinancialInfo">{pedido.quantidadeItens || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">VALOR UNITÁRIO</Text>
                      <Text textStyle="modalFinancialInfo">{pedido.valorUnitario || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">FRETE</Text>
                      <Text textStyle="modalFinancialInfo">{pedido.frete || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">VALOR TOTAL</Text>
                      <Text textStyle="modalFinancialInfo">{pedido.valorTotal || "N/A"}</Text>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            }
            rightContent={
              pedido.mapData ? (
                <MapComponent {...pedido.mapData} height="100%" />
              ) : (
                <Flex direction="column" height="100%" p={8}>
                  <Flex justify="space-between" align="center" mb={4}> {/* New Flex for right half header */}
                    <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO PEDIDO</Text> {/* New title */}
                    <ModalCloseButton position="static" onClick={onClose} /> {/* Close button here */}
                  </Flex>
                  <Flex direction="column" gap={4}> {/* Container for descriptive cards */}
                    {/* Endereço da Entrega Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1" // Lighter pink background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Endereço da Entrega</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{pedido.enderecoEntrega || "N/A"}</Text>
                    </Box>

                    {/* CNPJ de Faturamento Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1" // Lighter pink background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">CNPJ de Faturamento</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{pedido.cnpjFaturamento || "N/A"}</Text>
                    </Box>

                    {/* Descrição dos Produtos Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD3E1" // Lighter pink background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Descrição dos Produtos</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{pedido.descricaoProdutos || "N/A"}</Text>
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