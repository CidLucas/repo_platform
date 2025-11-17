import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent';

interface FornecedorDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  fornecedor: any; // The selected supplier data
}

export const FornecedorDetailsModal: React.FC<FornecedorDetailsModalProps> = ({ isOpen, onClose, fornecedor }) => {
  if (!fornecedor) return null; // Don't render if no fornecedor is selected

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={!!fornecedor.mapData ? "transparent" : "#B2E7FF"} // Conditionally set leftBgColor
            rightBgColor={!!fornecedor.mapData ? "#92DAFF" : "#92DAFF"} // Use prop
            isMapModal={!!fornecedor.mapData} // Pass if it's a map modal
            mapData={fornecedor.mapData} // Pass mapData
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{fornecedor.nome || "N/A"}</Text> {/* Supplier Name */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Fornecedor #{fornecedor.id}</Text> {/* Adjusted font size and semibold */}
                  <Box
                    bg={fornecedor.status === "Ativo" ? "green.500" : fornecedor.status === "Inativo" ? "red.500" : "gray.500"} // Adapted status colors
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
                    {fornecedor.status || "N/A"}
                  </Box>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center"> {/* Wrapper to center financial list */}
                  {/* Financial Information List */}
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">TOTAL FORNECIDO</Text>
                      <Text textStyle="modalFinancialInfo">{fornecedor.totalFornecido || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">PEDIDOS ATIVOS</Text>
                      <Text textStyle="modalFinancialInfo">{fornecedor.pedidosAtivos || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">AVALIAÇÃO MÉDIA</Text>
                      <Text textStyle="modalFinancialInfo">{fornecedor.avaliacaoMedia || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">TEMPO DE RESPOSTA</Text>
                      <Text textStyle="modalFinancialInfo">{fornecedor.tempoResposta || "N/A"}</Text>
                    </Flex>
                  </Flex>
                </Flex>
              </Flex>
            }
            rightContent={
              fornecedor.mapData ? (
                <MapComponent {...fornecedor.mapData} height="100%" />
              ) : (
                <Flex direction="column" height="100%" p={8}>
                  <Flex justify="space-between" align="center" mb={4}> {/* New Flex for right half header */}
                    <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO FORNECEDOR</Text> {/* New title */}
                    <ModalCloseButton position="static" onClick={onClose} /> {/* Close button here */}
                  </Flex>
                  <Flex direction="column" gap={4}> {/* Container for descriptive cards */}
                    {/* Tipo de Fornecedor Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#B2E7FF" // Lighter blue background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Tipo de Fornecedor</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{fornecedor.tipo || "N/A"}</Text>
                    </Box>

                    {/* Contato Principal Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#B2E7FF" // Lighter blue background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Contato Principal</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{fornecedor.contatoPrincipal || "N/A"}</Text>
                    </Box>

                    {/* Endereço Card */}
                    <Box
                      width="100%" // Fill available width
                      height="140px"
                      borderRadius="24px"
                      bg="#B2E7FF" // Lighter blue background
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Endereço</Text> {/* Uppercase, not bold */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>{fornecedor.endereco || "N/A"}</Text>
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
