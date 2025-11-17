import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent';

interface ProdutoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  produto: any; // The selected product data
}

export const ProdutoDetailsModal: React.FC<ProdutoDetailsModalProps> = ({ isOpen, onClose, produto }) => {
  if (!produto) return null; // Don't render if no produto is selected

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={!!produto.mapData ? "transparent" : "#FFFB97"} // Conditionally set leftBgColor
            rightBgColor={!!produto.mapData ? "#FFF856" : "#FFF856"} // Use prop
            isMapModal={!!produto.mapData} // Pass if it's a map modal
            mapData={produto.mapData} // Pass mapData
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{produto.clientName || "N/A"}</Text> {/* Client Name - mb reduced */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Produto #{produto.id}</Text> {/* Adjusted font size and semibold */}
                  <Box
                    bg={produto.status === "Disponível" ? "green.500" : produto.status === "Esgotado" ? "red.500" : "gray.500"} // Adapted status colors
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
                    {produto.status || "N/A"}
                  </Box>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center"> {/* Wrapper to center financial list */}
                  {/* Financial Information List */}
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">PREÇO UNITÁRIO</Text>
                      <Text textStyle="modalFinancialInfo">{produto.precoUnitario || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">ESTOQUE</Text>
                      <Text textStyle="modalFinancialInfo">{produto.estoque || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">VENDAS (MÊS)</Text>
                      <Text textStyle="modalFinancialInfo">{produto.vendasMes || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">AVALIAÇÃO MÉDIA</Text>
                      <Text textStyle="modalFinancialInfo">{produto.avaliacaoMedia || "N/A"}</Text>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            }
            rightContent={
              produto.mapData ? (
                <MapComponent {...produto.mapData} height="100%" />
              ) : (
                <Flex direction="column" height="100%" p={8}>
                  <Flex justify="space-between" align="center" mb={4}> {/* New Flex for right half header */}
                    <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO PRODUTO</Text> {/* New title */}
                    <ModalCloseButton position="static" onClick={onClose} /> {/* Close button here */}
                  </Flex>
                  <Flex direction="column" gap={4}> {/* Container for descriptive cards */}
                    {/* Categoria Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFFB97" // Lighter yellow background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Categoria</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{produto.categoria || "N/A"}</Text>
                    </Box>

                    {/* Fornecedor Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFFB97" // Lighter yellow background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Fornecedor</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{produto.fornecedor || "N/A"}</Text>
                    </Box>

                    {/* Descrição Detalhada Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#FFFB97" // Lighter yellow background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Descrição Detalhada</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{produto.descricaoDetalhada || "N/A"}</Text>
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
