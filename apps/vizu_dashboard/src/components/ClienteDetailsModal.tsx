import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent'; // Assuming map component is generic
import { ClienteDetailResponse } from '../services/analyticsService'; // Import the new type

interface ClienteDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  cliente: ClienteDetailResponse | null; // The detailed client data
}

export const ClienteDetailsModal: React.FC<ClienteDetailsModalProps> = ({ isOpen, onClose, cliente }) => {
  if (!cliente) return null; // Don't render if no cliente is selected

  const { dados_cadastrais, scorecards, rankings_internos } = cliente;
  const clientName = dados_cadastrais.receiver_nome || "N/A";
  const contact = dados_cadastrais.receiver_telefone || "N/A";
  const address = `${dados_cadastrais.receiver_cidade || ''}${dados_cadastrais.receiver_estado ? `, ${dados_cadastrais.receiver_estado}` : ''}`.trim();
  const cnpj = dados_cadastrais.receiver_cnpj || "N/A";

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={"#FFD1DC"} // Lighter pink
            rightBgColor={"#FFB6C1"} // Pink
            isMapModal={false}
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{clientName}</Text> {/* Client Name */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Cliente: {clientName}</Text> {/* Display name as title */}
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center"> {/* Wrapper to center financial list */}
                  {/* Displaying relevant information from dados_cadastrais */}
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">CNPJ</Text>
                      <Text textStyle="modalFinancialInfo">{cnpj}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">TELEFONE</Text>
                      <Text textStyle="modalFinancialInfo">{contact}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}
                    
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">ENDEREÇO</Text>
                      <Text textStyle="modalFinancialInfo">{address || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}

                    {/* Displaying scorecard if available */}
                    {scorecards && (
                      <>
                        <Flex justify="space-between" align="center" py={3}>
                          <Text textStyle="modalFinancialInfo" fontWeight="semibold">TIER</Text>
                          <Text textStyle="modalFinancialInfo">{scorecards.cluster_tier || "N/A"}</Text>
                        </Flex>
                        <Box borderBottom="1px solid black" width="100%" />
                      </>
                    )}
                  </Flex>
                </Flex>
              </Flex>
            }
            rightContent={
              // Removed mapData conditional as it's not part of this specific modal logic now
              <Flex direction="column" height="100%" p={8}>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO CLIENTE</Text>
                  <ModalCloseButton position="static" onClick={onClose} />
                </Flex>
                <Flex direction="column" gap={4}>
                  {/* Example of displaying a product ranking if available */}
                  {rankings_internos?.mix_de_produtos_por_receita && rankings_internos.mix_de_produtos_por_receita.length > 0 && (
                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFD1DC" // Lighter pink
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Produto de Maior Receita</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>
                        {rankings_internos.mix_de_produtos_por_receita[0].nome} (R$ {rankings_internos.mix_de_produtos_por_receita[0].receita_total.toLocaleString('pt-BR')})
                      </Text>
                    </Box>
                  )}

                  <Box
                    width="100%"
                    height="140px"
                    borderRadius="24px"
                    bg="#FFD1DC" // Lighter pink
                    p={4}
                    boxShadow="md"
                  >
                    <Text textTransform="uppercase" fontSize="md">Localização</Text>
                    <Text fontSize="sm" color="gray.600" noOfLines={2}>{address || "N/A"}</Text>
                  </Box>
                  {/* Placeholder for other internal rankings or data if needed */}
                </Flex>
              </Flex>
            }
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};