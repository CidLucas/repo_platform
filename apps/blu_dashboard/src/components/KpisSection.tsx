import { Box, Flex, Text, VStack, SimpleGrid, Skeleton } from '@chakra-ui/react';
import { useMemo } from 'react';
import { FiBarChart2 } from 'react-icons/fi';
import { Icon } from '@chakra-ui/react';
import { DashboardKpiSlot } from '../hooks/useDashboardKpis';
import { SampleBadge } from './SampleBadge';

interface KpisSectionProps {
  kpis: DashboardKpiSlot[] | null;
  loading: boolean;
  isSampleData: boolean;
  demoStateShowsOnlyPrimary?: boolean;
}

const dimensionLabels: Record<string, string> = {
  finance: 'Financeiro',
  commercial: 'Comercial',
  inventory: 'Estoque',
  supply: 'Compras',
  marketing: 'Marketing',
  admin: 'Administrativo',
};

const dimensionColors: Record<string, string> = {
  finance: '#10b981',
  commercial: '#3b82f6',
  inventory: '#f97316',
  supply: '#a855f7',
  marketing: '#ec4899',
  admin: '#6366f1',
};

const dimensionOrder = ['finance', 'commercial', 'inventory', 'supply', 'marketing'];

export const KpisSection = ({
  kpis,
  loading,
  isSampleData,
  demoStateShowsOnlyPrimary = true,
}: KpisSectionProps) => {
  // Group KPIs by dimension
  const kpisByDimension = useMemo(() => {
    if (!kpis) return {};

    const grouped: Record<string, DashboardKpiSlot[]> = {};
    kpis.forEach((kpi) => {
      if (!grouped[kpi.dimension]) {
        grouped[kpi.dimension] = [];
      }
      grouped[kpi.dimension].push(kpi);
    });

    // Sort by dimension order and within by slot_index
    const sorted: Record<string, DashboardKpiSlot[]> = {};
    dimensionOrder.forEach((dim) => {
      if (grouped[dim]) {
        sorted[dim] = grouped[dim].sort((a, b) => a.slot_index - b.slot_index);
      }
    });

    return sorted;
  }, [kpis]);

  const renderKpiCard = (kpi: DashboardKpiSlot) => {
    const color = dimensionColors[kpi.dimension] || '#94a3b8';
    const isPrimary = kpi.slot_index < 3;

    return (
      <Box
        key={`${kpi.dimension}-${kpi.slug}`}
        bg="#1a1b2e"
        borderRadius="0.625rem"
        border="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        boxShadow="0 4px 24px rgba(0,0,0,0.4)"
        p={isPrimary ? 5 : 4}
        position="relative"
        overflow="hidden"
        transition="all 0.2s"
        _hover={{
          borderColor: 'rgba(255,255,255,0.12)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      >
        <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={color} />

        <VStack spacing={isPrimary ? 3 : 2} align="start" w="100%">
          <Flex justify="space-between" align="start" w="100%">
            <VStack spacing={1} align="start">
              <Text
                fontSize={isPrimary ? 'xs' : '2xs'}
                color="whiteAlpha.500"
                fontWeight="semibold"
                textTransform="uppercase"
                letterSpacing="wider"
              >
                {kpi.label}
              </Text>
              <Text
                fontSize={isPrimary ? '2xl' : 'lg'}
                fontWeight="bold"
                color={kpi.is_enabled ? 'white' : 'whiteAlpha.500'}
              >
                {kpi.is_enabled ? '—' : 'N/A'}
              </Text>
            </VStack>

            {isSampleData && isPrimary && (
              <SampleBadge />
            )}
          </Flex>

          {isPrimary && (
            <Text fontSize="xs" color="whiteAlpha.600" noOfLines={2}>
              {kpi.formula}
            </Text>
          )}

          {kpi.data_status === 'pending_data' && (
            <Text fontSize="2xs" color="#fbbf24">
              Dados não disponíveis
            </Text>
          )}
        </VStack>
      </Box>
    );
  };

  if (loading) {
    return (
      <Box
        bg="#1a1b2e"
        borderRadius="0.625rem"
        border="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        boxShadow="0 4px 24px rgba(0,0,0,0.4)"
        p={6}
      >
        <Flex align="center" gap={3} mb={4}>
          <Icon as={FiBarChart2} boxSize={5} color="#a855f7" />
          <Text fontSize="1.5rem" fontWeight="normal" fontFamily="'Playfair Display', serif" color="white">
            KPIs por Dimensão
          </Text>
        </Flex>
        <SimpleGrid columns={{ base: 1, md: 5 }} spacing={4}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} h="120px" borderRadius="md" />
          ))}
        </SimpleGrid>
      </Box>
    );
  }

  if (!kpis || Object.keys(kpisByDimension).length === 0) {
    return (
      <Box
        bg="#1a1b2e"
        borderRadius="0.625rem"
        border="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        boxShadow="0 4px 24px rgba(0,0,0,0.4)"
        p={6}
      >
        <Flex align="center" gap={3} mb={4}>
          <Icon as={FiBarChart2} boxSize={5} color="#a855f7" />
          <Text fontSize="1.5rem" fontWeight="normal" fontFamily="'Playfair Display', serif" color="white">
            KPIs por Dimensão
          </Text>
        </Flex>
        <Text fontSize="sm" color="whiteAlpha.600">
          Nenhum KPI configurado. Configure seus KPIs em Configurar → KPIs do painel.
        </Text>
      </Box>
    );
  }

  return (
    <Box
      bg="#1a1b2e"
      borderRadius="0.625rem"
      border="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      boxShadow="0 4px 24px rgba(0,0,0,0.4)"
      p={6}
    >
      <Flex align="center" gap={3} mb={6}>
        <Icon as={FiBarChart2} boxSize={5} color="#a855f7" />
        <Text fontSize="1.5rem" fontWeight="normal" fontFamily="'Playfair Display', serif" color="white">
          KPIs por Dimensão
        </Text>
      </Flex>

      <VStack spacing={8} align="stretch">
        {Object.entries(kpisByDimension).map(([dimension, dimKpis]) => {
          // In demo state, only show primary KPIs (0-2); otherwise show all 5
          const displayKpis = demoStateShowsOnlyPrimary && isSampleData
            ? dimKpis.filter((k) => k.slot_index < 3)
            : dimKpis;

          if (displayKpis.length === 0) return null;

          return (
            <Box key={dimension}>
              <Text
                fontSize="sm"
                fontWeight="semibold"
                color={dimensionColors[dimension]}
                textTransform="uppercase"
                letterSpacing="wider"
                mb={4}
              >
                {dimensionLabels[dimension] || dimension}
              </Text>

              {/* 5 slots per dimension - can be 3 primary + 2 secondary, or all 5 in a row */}
              <SimpleGrid columns={{ base: 1, md: 5 }} spacing={4}>
                {displayKpis.map((kpi) => renderKpiCard(kpi))}
              </SimpleGrid>
            </Box>
          );
        })}
      </VStack>
    </Box>
  );
};
