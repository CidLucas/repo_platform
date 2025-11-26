import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent';
import { FornecedorDetailResponse } from '../services/analyticsService'; // Import the new type

interface FornecedorDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  fornecedor: FornecedorDetailResponse | null; // The detailed supplier data
}

export const FornecedorDetailsModal: React.FC<FornecedorDetailsModalProps> = ({ isOpen, onClose, fornecedor }) => {
  if (!fornecedor) return null; // Don't render if no fornecedor is selected

  const { dados_cadastrais, rankings_internos } = fornecedor;
  const supplierName = dados_cadastrais.emitter_nome || "N/A";
  const contact = dados_cadastrais.emitter_telefone || "N/A";
  const address = `${dados_cadastrais.emitter_cidade || ''}${dados_cadastrais.emitter_estado ? `, ${dados_cadastrais.emitter_estado}` : ''}`.trim();
  const cnpj = dados_cadastrais.emitter_cnpj || "N/A";

  // Note: 'status', 'totalFornecido', 'pedidosAtivos', 'avaliacaoMedia', 'tempoResposta', 'tipo', 'id'
  // are NOT directly available in FornecedorDetailResponse.
  // We will only display what is available in dados_cadastrais for now.

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            // Assuming mapData might come from somewhere else or is not used for this modal type
            leftBgColor={"#B2E7FF"}
            rightBgColor={"#92DAFF"}
            isMapModal={false}
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{supplierName}</Text> {/* Supplier Name */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Fornecedor: {supplierName}</Text> {/* Display name as title */}
                  {/* Status removed as it's not in FornecedorDetailResponse */}
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

                    {/* Displaying internal rankings examples */}
                    {rankings_internos?.clientes_por_receita && rankings_internos.clientes_por_receita.length > 0 && (
                      <>
                        <Flex justify="space-between" align="center" py={3}>
                          <Text textStyle="modalFinancialInfo" fontWeight="semibold">TOP CLIENTE (Receita)</Text>
                          <Text textStyle="modalFinancialInfo">{rankings_internos.clientes_por_receita[0].nome} (R$ {rankings_internos.clientes_por_receita[0].receita_total.toLocaleString('pt-BR')})</Text>
                        </Flex>
                        <Box borderBottom="1px solid black" width="100%" /> {/* Separator */}
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
                  <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO FORNECEDOR</Text>
                  <ModalCloseButton position="static" onClick={onClose} />
                </Flex>
                <Flex direction="column" gap={4}>
                  {/* Example of displaying a product ranking if available */}
                  {rankings_internos?.produtos_por_receita && rankings_internos.produtos_por_receita.length > 0 && (
                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#B2E7FF"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Produto Mais Vendido</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>
                        {rankings_internos.produtos_por_receita[0].nome} (R$ {rankings_internos.produtos_por_receita[0].receita_total.toLocaleString('pt-BR')})
                      </Text>
                    </Box>
                  )}

                  <Box
                    width="100%"
                    height="140px"
                    borderRadius="24px"
                    bg="#B2E7FF"
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