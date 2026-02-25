import { Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton, Flex, Text, Box } from '@chakra-ui/react';
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ModalContentLayout } from './ModalContentLayout';
import { ScorecardCard } from './ScorecardCard';
import { ExpandableScorecardCard } from './ExpandableScorecardCard';
import { TierBadge } from './TierBadge';
import { ClienteDetailResponse, getCustomerMonthlyOrders, MonthlyOrderData, ClientesOverviewResponse } from '../services/analyticsService';

interface ClienteDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  cliente: ClienteDetailResponse | null;
  overviewData?: ClientesOverviewResponse;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- overviewData kept for API compatibility
export const ClienteDetailsModal: React.FC<ClienteDetailsModalProps> = ({ isOpen, onClose, cliente, overviewData: _overviewData }) => {
  const navigate = useNavigate();
  const [monthlyOrders, setMonthlyOrders] = useState<MonthlyOrderData[]>([]);
  const [loadingGraph, setLoadingGraph] = useState<boolean>(false);

  // Fetch monthly orders data when cliente changes
  useEffect(() => {
    const fetchMonthlyOrders = async () => {
      if (cliente?.dados_cadastrais?.receiver_cnpj) {
        try {
          setLoadingGraph(true);
          const data = await getCustomerMonthlyOrders(cliente.dados_cadastrais.receiver_cnpj);
          setMonthlyOrders(data);
        } catch (error) {
          console.error('Error fetching monthly orders:', error);
          setMonthlyOrders([]);
        } finally {
          setLoadingGraph(false);
        }
      }
    };

    if (isOpen && cliente) {
      fetchMonthlyOrders();
    }
  }, [cliente, isOpen]);

  if (!cliente) {
    return (
      <Modal isOpen={isOpen} onClose={onClose} size="full">
        <ModalOverlay />
        <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
          <ModalBody p={0}>
            <Flex justify="center" align="center" height="100%" bg="white">
              <Text>Carregando dados do cliente...</Text>
              <ModalCloseButton />
            </Flex>
          </ModalBody>
        </ModalContent>
      </Modal>
    );
  }

  const { dados_cadastrais, scorecards, rankings_internos } = cliente;

  const clientName = dados_cadastrais?.receiver_nome || 'N/A';
  const cnpj = dados_cadastrais?.receiver_cnpj || 'N/A';
  const contact = dados_cadastrais?.receiver_telefone || 'N/A';
  const address = `${dados_cadastrais?.receiver_cidade || ''}${dados_cadastrais?.receiver_estado ? `, ${dados_cadastrais.receiver_estado}` : ''}`.trim() || 'N/A';
  const tier = scorecards?.cluster_tier || 'N/A';
  const totalRevenue = scorecards?.receita_total
    ? `R$ ${scorecards.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
    : 'N/A';
  const frequency = scorecards?.frequencia_pedidos_mes
    ? `${scorecards.frequencia_pedidos_mes.toFixed(1)} pedidos/mês`
    : 'N/A';

  const topProduct = rankings_internos?.mix_de_produtos_por_receita?.[0];
  const topProductDisplay = topProduct
    ? `${topProduct.nome.substring(0, 30)}${topProduct.nome.length > 30 ? '...' : ''}`
    : 'N/A';
  const topProductRevenue = topProduct
    ? `R$ ${topProduct.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}${topProduct.quantidade_total ? ` | ${topProduct.quantidade_total.toLocaleString('pt-BR')} kg` : ''}`
    : '';

  // Navigation handlers
  const handleProductClick = () => {
    console.log('Product click handler called', { topProduct, clientName, cnpj });
    // Navigate to PRODUCTS page (yellow) showing products bought by this customer
    if (cnpj && clientName) {
      console.log('Navigating to products bought by customer:', clientName);
      onClose();
      navigate(`/dashboard/produtos/lista?view=by-customer&customer=${encodeURIComponent(cnpj)}&customerName=${encodeURIComponent(clientName)}`);
    }
  };

  const handleRevenueClick = () => {
    console.log('Revenue click handler called', { clientName });
    if (clientName) {
      console.log('Navigating to customer products view:', clientName);
      onClose();
      navigate(`/dashboard/clientes/lista?view=customer&client=${encodeURIComponent(clientName)}`);
    }
  };

  // Transform monthly orders data for graph
  const graphData = monthlyOrders.map(item => ({
    name: item.month.substring(5), // Get MM from YYYY-MM
    pedidos: item.num_pedidos,
  }));

  console.log('Monthly orders data:', { monthlyOrders, graphData, loadingGraph });

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="full">
      <ModalOverlay />
      <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
        <ModalBody p={0}>
          <ModalContentLayout
            leftBgColor="#FFD1DC"
            rightBgColor="#FFB6C1"
            isMapModal={false}
            mapData={undefined}
            leftContent={
              <Flex direction="column" height="100%">
                <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>{clientName}</Text>
                <Flex justify="space-between" align="center" mb={4}>
                  <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">Cliente: {clientName}</Text>
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

                    <Flex justify="space-between" align="center" py={3}>
                      <Text textStyle="modalFinancialInfo" fontWeight="semibold">TIER</Text>
                      <TierBadge tier={tier} />
                    </Flex>
                    <Box borderBottom="1px solid black" width="100%" />
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
                    title="Produto Mais Comprado"
                    value={topProductDisplay}
                    subtitle={topProductRevenue}
                    bgColor="#FFD1DC"
                    onClick={topProduct ? handleProductClick : undefined}
                  />
                  <ScorecardCard
                    title="Total de Receita"
                    value={totalRevenue}
                    subtitle="Lifetime Value"
                    bgColor="#FFD1DC"
                    onClick={handleRevenueClick}
                  />
                  <ExpandableScorecardCard
                    title="Frequência de Compra"
                    value={frequency}
                    subtitle={address}
                    bgColor="#FFD1DC"
                    graphData={graphData}
                    graphDataKey="pedidos"
                    graphLineColor="#FF69B4"
                    isLoading={loadingGraph}
                  />
                </Flex>


              </Flex>
            }
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};