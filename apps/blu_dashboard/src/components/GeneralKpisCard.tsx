import { Box, Flex, Text, VStack, HStack, Icon, Skeleton } from '@chakra-ui/react';
import { FiTrendingUp } from 'react-icons/fi';

interface GeneralKpi {
  label: string;
  value: string | number;
  unit?: string;
  color: string;
  subtitle?: string;
}

interface GeneralKpisCardProps {
  kpis: GeneralKpi[];
  loading?: boolean;
}

export const GeneralKpisCard = ({ kpis, loading = false }: GeneralKpisCardProps) => {
  if (loading) {
    return (
      <Box
        bg="#1a1b2e"
        borderRadius="0.625rem"
        border="1px solid"
        borderColor="rgba(255,255,255,0.08)"
        boxShadow="0 4px 24px rgba(0,0,0,0.4)"
        p={5}
      >
        <Flex justify="space-between" align="center" mb={4}>
          <HStack spacing={2}>
            <Icon as={FiTrendingUp} boxSize={4} color="#10b981" />
            <Text fontSize="sm" fontWeight="semibold" color="white">
              KPIs Gerais
            </Text>
          </HStack>
        </Flex>
        <VStack spacing={3} align="stretch">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} h="40px" borderRadius="md" />
          ))}
        </VStack>
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
      p={5}
    >
      <Flex justify="space-between" align="center" mb={4}>
        <HStack spacing={2}>
          <Icon as={FiTrendingUp} boxSize={4} color="#10b981" />
          <Text fontSize="sm" fontWeight="semibold" color="white">
            KPIs Gerais
          </Text>
        </HStack>
      </Flex>

      <VStack spacing={3} align="stretch">
        {kpis.length === 0 ? (
          <Text fontSize="xs" color="whiteAlpha.500">
            Nenhum KPI geral configurado.
          </Text>
        ) : (
          kpis.map((kpi) => (
            <Flex
              key={kpi.label}
              justify="space-between"
              align="center"
              py={2}
              borderBottom="1px solid"
              borderColor="whiteAlpha.100"
            >
              <Box>
                <Text fontSize="xs" color="whiteAlpha.600" fontWeight="medium">
                  {kpi.label}
                </Text>
                {kpi.subtitle && (
                  <Text fontSize="2xs" color="whiteAlpha.400">
                    {kpi.subtitle}
                  </Text>
                )}
              </Box>
              <Text fontSize="sm" fontWeight="bold" color={kpi.color}>
                {kpi.value}
                {kpi.unit && ` ${kpi.unit}`}
              </Text>
            </Flex>
          ))
        )}
      </VStack>
    </Box>
  );
};
