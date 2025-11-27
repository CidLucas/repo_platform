import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { MapComponent } from './MapComponent'; // Assuming map component is generic
import { ProdutoDetailResponse } from '../services/analyticsService'; // Import the new type

interface ProdutoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  produto: ProdutoDetailResponse | null; // The detailed product data
}

export const ProdutoDetailsModal: React.FC<ProdutoDetailsModalProps> = ({ isOpen, onClose, produto }) => {
  if (!produto) return null; // Don't render if no produto is selected

  const { nome_produto, scorecards, charts, rankings_internos } = produto;

  // Note: old fields like 'clientName', 'id', 'status', 'precoUnitario', 'estoque',
  // 'vendasMes', 'avaliacaoMedia', 'categoria', 'fornecedor', 'descricaoDetalhada'
  // are NOT directly available in ProdutoDetailResponse.
  // We will display what is available.

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor={"#FFFB97"}
            rightBgColor={"#FFF856"}
            isMapModal={false} // Product details modal is not a map modal
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{nome_produto || "N/A"}</Text> {/* Product Name */}
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Produto: {nome_produto || "N/A"}</Text> {/* Display name as title */}
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center"> {/* Wrapper to center financial list */}
                  {/* Displaying scorecard if available */}
                  {scorecards && (
                    <Flex direction="column" width="100%">
                      <Flex justify="space-between" align="center" py={3}>
                        <Text textStyle="modalFinancialInfo" fontWeight="semibold">RECEITA TOTAL</Text>
                        <Text textStyle="modalFinancialInfo">{scorecards.receita_total.toLocaleString('pt-BR')}</Text>
                      </Flex>
                      <Box borderBottom="1px solid black" width="100%" />

                      <Flex justify="space-between" align="center" py={3}>
                        <Text textStyle="modalFinancialInfo" fontWeight="semibold">QTD. VENDIDA</Text>
                        <Text textStyle="modalFinancialInfo">{scorecards.quantidade_total.toLocaleString('pt-BR')}</Text>
                      </Flex>
                      <Box borderBottom="1px solid black" width="100%" />

                      <Flex justify="space-between" align="center" py={3}>
                        <Text textStyle="modalFinancialInfo" fontWeight="semibold">TICKET MÉDIO</Text>
                        <Text textStyle="modalFinancialInfo">{scorecards.ticket_medio.toLocaleString('pt-BR')}</Text>
                      </Flex>
                      <Box borderBottom="1px solid black" width="100%" />
                    </Flex>
                  )}
                </Flex>
              </Flex>
            }
            rightContent={
              <Flex direction="column" height="100%" p={8}>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">DETALHE DO PRODUTO</Text>
                  <ModalCloseButton position="static" onClick={onClose} />
                </Flex>
                <Flex direction="column" gap={4}>
                  {/* Chart for segmentos de clientes */}
                  {charts?.segmentos_de_clientes && charts.segmentos_de_clientes.length > 0 && (
                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFFB97"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Segmentos de Clientes</Text>
                      {/* You'd typically render a chart component here */}
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>
                        {charts.segmentos_de_clientes.map(s => `${s.name}: ${s.percentual}%`).join(', ')}
                      </Text>
                    </Box>
                  )}

                  {/* Example of displaying internal rankings if available */}
                  {rankings_internos?.clientes_por_receita && rankings_internos.clientes_por_receita.length > 0 && (
                    <Box
                      width="100%"
                      height="140px"
                      borderRadius="24px"
                      bg="#FFFB97"
                      p={4}
                      boxShadow="md"
                    >
                      <Text textTransform="uppercase" fontSize="md">Clientes por Receita</Text>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>
                        {rankings_internos.clientes_por_receita[0].nome} (R$ {rankings_internos.clientes_por_receita[0].receita_total.toLocaleString('pt-BR')})
                      </Text>
                    </Box>
                  )}
                </Flex>
              </Flex>
            }
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};