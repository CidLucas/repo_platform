import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { ModalContentLayout } from './ModalContentLayout';
import { GraphCarousel } from './GraphCarousel';
import { ScorecardCard } from './ScorecardCard';
import { ProdutoDetailResponse, ProdutosOverviewResponse } from '../services/analyticsService';

interface ProdutoDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  produto: ProdutoDetailResponse | null;
  overviewData?: ProdutosOverviewResponse | null;
}

export const ProdutoDetailsModal: React.FC<ProdutoDetailsModalProps> = ({ isOpen, onClose, produto, overviewData }) => {
  if (!produto) return null;

  const { nome_produto, scorecards, rankings_internos } = produto;

  const topClient = rankings_internos?.clientes_por_receita?.[0];
  const topClientDisplay = topClient
    ? `${topClient.nome.substring(0, 30)}${topClient.nome.length > 30 ? '...' : ''}`
    : 'N/A';
  const topClientRevenue = topClient
    ? `R$ ${topClient.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : '';

  const totalRevenue = scorecards?.receita_total
    ? `R$ ${scorecards.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : 'N/A';
  const totalQuantity = scorecards?.quantidade_total?.toLocaleString('pt-BR') || 'N/A';
  const avgPrice = scorecards?.valor_unitario_medio
    ? `R$ ${scorecards.valor_unitario_medio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : 'N/A';

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor="#FFFB97"
            rightBgColor="#FFF856"
            isMapModal={false}
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{nome_produto || "N/A"}</Text>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Produto: {nome_produto || "N/A"}</Text>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center">
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
                <Flex justify="space-between" align="center" mb={6}>
                  <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">INSIGHTS</Text>
                  <ModalCloseButton position="static" onClick={onClose} />
                </Flex>

                <Flex direction="column" gap={4} mb={6}>
                  <ScorecardCard
                    title="Top Cliente Comprador"
                    value={topClientDisplay}
                    subtitle={topClientRevenue}
                    bgColor="#FFFB97"
                  />
                  <ScorecardCard
                    title="Receita Total"
                    value={totalRevenue}
                    subtitle={`Quantidade: ${totalQuantity}`}
                    bgColor="#FFFB97"
                  />
                  <ScorecardCard
                    title="Preço Médio"
                    value={avgPrice}
                    subtitle="Valor unitário médio"
                    bgColor="#FFFB97"
                  />
                </Flex>

                {overviewData && (
                  <Box flex="1">
                    <Text textStyle="modalTitle" mb={4}>Análise de Performance no Tempo</Text>
                    <GraphCarousel
                      graphs={[
                        {
                          data: overviewData.chart_receita_no_tempo?.map((d: any) => ({
                            name: d.name,
                            receita: d.total || d.receita || 0
                          })) || [],
                          dataKey: "receita",
                          lineColor: "#FFF856",
                          title: "Receita Mensal dos Produtos",
                        },
                        {
                          data: overviewData.chart_quantidade_no_tempo?.map((d: any) => ({
                            name: d.name,
                            quantidade: d.total || d.quantidade || 0
                          })) || [],
                          dataKey: "quantidade",
                          lineColor: "#FFD700",
                          title: "Volume Mensal (kg/ton)",
                        },
                      ]}
                    />
                  </Box>
                )}
              </Flex>
            }
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};