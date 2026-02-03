import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ModalContentLayout } from './ModalContentLayout';
import { GraphCarousel } from './GraphCarousel';
import { ScorecardCard } from './ScorecardCard';
import { FornecedorDetailResponse } from '../services/analyticsService';

interface FornecedorDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  fornecedor: FornecedorDetailResponse | null;
}

export const FornecedorDetailsModal: React.FC<FornecedorDetailsModalProps> = ({ isOpen, onClose, fornecedor }) => {
  const navigate = useNavigate();
  
  if (!fornecedor) return null;

  const { dados_cadastrais, rankings_internos } = fornecedor;
  const supplierName = dados_cadastrais.emitter_nome || "N/A";
  const contact = dados_cadastrais.emitter_telefone || "N/A";
  const address = `${dados_cadastrais.emitter_cidade || ''}${dados_cadastrais.emitter_estado ? `, ${dados_cadastrais.emitter_estado}` : ''}`.trim();
  const cnpj = dados_cadastrais.emitter_cnpj || "N/A";

  const topProduct = rankings_internos?.produtos_por_receita?.[0];
  const topProductDisplay = topProduct
    ? `${topProduct.nome.substring(0, 30)}${topProduct.nome.length > 30 ? '...' : ''}`
    : 'N/A';
  const topProductRevenue = topProduct
    ? `R$ ${topProduct.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : '';

  const topClient = rankings_internos?.clientes_por_receita?.[0];
  const topClientDisplay = topClient
    ? `${topClient.nome.substring(0, 30)}${topClient.nome.length > 30 ? '...' : ''}`
    : 'N/A';
  const topClientRevenue = topClient
    ? `R$ ${topClient.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : '';

  const topRegion = dados_cadastrais.emitter_estado || 'N/A';

  // Navigation handlers - navigate to filtered lists
  const handleProductClick = () => {
    console.log('Fornecedor Product click handler called', { topProduct, supplierName, cnpj });
    // Navigate to PRODUCTS page (yellow) filtered by this supplier
    if (cnpj && supplierName && cnpj !== 'N/A') {
      console.log('Navigating to products sold by supplier:', supplierName);
      onClose();
      navigate(`/dashboard/produtos/lista?view=by-supplier&supplier=${encodeURIComponent(cnpj)}&supplierName=${encodeURIComponent(supplierName)}`);
    }
  };

  const handleClientClick = () => {
    console.log('Fornecedor Client click handler called', { topClient, supplierName, cnpj });
    // Navigate to CLIENTS page (pink) filtered by this supplier
    if (cnpj && supplierName && cnpj !== 'N/A') {
      console.log('Navigating to clients of supplier:', supplierName);
      onClose();
      navigate(`/dashboard/clientes/lista?view=by-supplier&supplier=${encodeURIComponent(cnpj)}&supplierName=${encodeURIComponent(supplierName)}`);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor="#B2E7FF"
            rightBgColor="#92DAFF"
            isMapModal={false}
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{supplierName}</Text>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Fornecedor: {supplierName}</Text>
                </Flex>
                <Flex flex="1" alignItems="center" justifyContent="center">
                  <Flex direction="column" width="100%">
                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">CNPJ</Text>
                      <Text textStyle="modalFinancialInfo">{cnpj}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">TELEFONE</Text>
                      <Text textStyle="modalFinancialInfo">{contact}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">ENDEREÇO</Text>
                      <Text textStyle="modalFinancialInfo">{address || "N/A"}</Text>
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />

                    {rankings_internos?.clientes_por_receita && rankings_internos.clientes_por_receita.length > 0 && (
                      <>
                        <Flex justify="space-between" align="center" py={3}>
                          <Text textStyle="modalFinancialInfo" fontWeight="semibold">TOP CLIENTE (Receita)</Text>
                          <Text textStyle="modalFinancialInfo">{rankings_internos.clientes_por_receita[0].nome} (R$ {rankings_internos.clientes_por_receita[0].receita_total.toLocaleString('pt-BR')})</Text>
                        </Flex>
                        <Box borderBottom="1px solid black" width="100%" />
                      </>
                    )}
                  </Flex>
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
                    title="Produto Mais Vendido"
                    value={topProductDisplay}
                    subtitle={topProductRevenue}
                    bgColor="#B2E7FF"
                    onClick={topProduct ? handleProductClick : undefined}
                  />
                  <ScorecardCard
                    title="Cliente Principal"
                    value={topClientDisplay}
                    subtitle={topClientRevenue}
                    bgColor="#B2E7FF"
                    onClick={topClient ? handleClientClick : undefined}
                  />
                  <ScorecardCard
                    title="Região de Atuação"
                    value={topRegion}
                    subtitle={address}
                    bgColor="#B2E7FF"
                  />
                </Flex>

                {fornecedor.charts?.receita_no_tempo && fornecedor.charts.receita_no_tempo.length > 0 && (
                  <Box flex="1">
                    <Text textStyle="modalTitle" mb={4}>Análise de Performance no Tempo</Text>
                    <GraphCarousel
                      graphs={[
                        {
                          data: fornecedor.charts.receita_no_tempo.map((d) => ({
                            name: d.name,
                            receita: d.total || d.receita || 0
                          })),
                          dataKey: "receita",
                          lineColor: "#353A5A",
                          title: "Receita Mensal do Fornecedor",
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