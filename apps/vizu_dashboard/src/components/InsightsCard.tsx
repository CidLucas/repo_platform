import { Box, Flex, HStack, Icon, Text, Badge, IconButton, VStack, Button, Tooltip, Spinner } from '@chakra-ui/react';
import { FiZap, FiX, FiMessageCircle, FiTrendingUp, FiAlertTriangle } from 'react-icons/fi';
import { useInsights } from '../hooks/useInsights';
import { useChat } from '../contexts/ChatContext';
import type { InsightItem } from '../services/analyticsService';

const severityToken = (severity: string) => {
  if (severity === 'error') return { bg: '#ef444420', color: '#ef4444', label: 'Crítico' };
  if (severity === 'warning') return { bg: '#f9731620', color: '#f97316', label: 'Atenção' };
  return { bg: '#3b82f620', color: '#3b82f6', label: 'Info' };
};

const dimensionLabel: Record<string, string> = {
  finance: 'Financeiro',
  commercial: 'Comercial',
  inventory: 'Estoque',
  supply: 'Supply',
  marketing: 'Marketing',
  operations: 'Operações',
};

/**
 * Phase 2 (I2.2): HomePage insights feed. Reads from `public.get_my_insights`,
 * renders top-N active insights ordered by severity, exposes a "Explicar"
 * deep-link into `atendente_core` and a dismiss action.
 */
export const InsightsCard = ({ limit = 5 }: { limit?: number }) => {
  const { data, loading, error, dismiss } = useInsights(limit);
  const { openChat } = useChat();

  const handleExplain = (insight: InsightItem) => {
    const dim = dimensionLabel[insight.dimension] ?? insight.dimension;
    const prompt = [
      `Explique este insight em detalhe e sugira próximos passos:`,
      ``,
      `• Dimensão: ${dim}`,
      `• KPI: ${insight.kpi}`,
      `• Observação: ${insight.observation}`,
      insight.recommendation ? `• Recomendação atual: ${insight.recommendation}` : null,
      insight.metricValue !== null && insight.baselineValue !== null
        ? `• Valor atual: ${insight.metricValue} (baseline: ${insight.baselineValue}${
            insight.variancePct !== null ? `, Δ ${insight.variancePct}%` : ''
          })`
        : null,
    ]
      .filter(Boolean)
      .join('\n');
    openChat(prompt);
  };

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
          <Icon as={FiZap} boxSize={4} color="#a855f7" />
          <Text fontSize="sm" fontWeight="semibold" color="white">Insights do dia</Text>
        </HStack>
        {data && data.length > 0 && (
          <Badge bg="#a855f720" color="#a855f7" fontSize="2xs" borderRadius="full" px={2}>
            {data.length}
          </Badge>
        )}
      </Flex>

      {loading && (
        <Flex justify="center" py={4}>
          <Spinner size="sm" color="whiteAlpha.500" />
        </Flex>
      )}

      {!loading && error && (
        <Text fontSize="xs" color="#ef4444">Não foi possível carregar os insights.</Text>
      )}

      {!loading && !error && (data?.length ?? 0) === 0 && (
        <VStack align="start" spacing={1} py={2}>
          <Text fontSize="xs" color="whiteAlpha.600">
            Sem novidades por hoje.
          </Text>
          <Text fontSize="2xs" color="whiteAlpha.400">
            A análise diária roda toda noite e aparece aqui pela manhã.
          </Text>
        </VStack>
      )}

      {!loading && !error && data && data.length > 0 && (
        <VStack spacing={3} align="stretch">
          {data.map((insight, idx) => {
            const sev = severityToken(insight.severity);
            const SevIcon = insight.severity === 'error' ? FiAlertTriangle : FiTrendingUp;
            return (
              <Box
                key={insight.id}
                pb={3}
                borderBottom={idx < data.length - 1 ? '1px solid' : 'none'}
                borderColor="rgba(255,255,255,0.06)"
              >
                <Flex align="flex-start" gap={3}>
                  <Flex
                    w={8} h={8}
                    flexShrink={0}
                    borderRadius="lg"
                    align="center" justify="center"
                    bg={sev.bg}
                  >
                    <Icon as={SevIcon} boxSize={3.5} color={sev.color} />
                  </Flex>
                  <Box flex={1} minW={0}>
                    <Flex align="center" gap={2} mb={1}>
                      <Text fontSize="xs" fontWeight="semibold" color="white" noOfLines={2}>
                        {insight.title}
                      </Text>
                      <Badge fontSize="2xs" borderRadius="full" px={1.5} bg={sev.bg} color={sev.color}>
                        {sev.label}
                      </Badge>
                    </Flex>
                    <Text fontSize="2xs" color="whiteAlpha.700" noOfLines={3} mb={2}>
                      {insight.observation}
                    </Text>
                    <HStack spacing={2}>
                      <Button
                        size="xs"
                        variant="ghost"
                        color="#a855f7"
                        leftIcon={<Icon as={FiMessageCircle} boxSize={3} />}
                        onClick={() => handleExplain(insight)}
                        _hover={{ bg: '#a855f715' }}
                      >
                        Explicar
                      </Button>
                      <Tooltip label="Dispensar" placement="top">
                        <IconButton
                          size="xs"
                          variant="ghost"
                          aria-label="Dispensar insight"
                          icon={<Icon as={FiX} boxSize={3} />}
                          color="whiteAlpha.500"
                          onClick={() => { void dismiss(insight.id); }}
                          _hover={{ bg: 'whiteAlpha.100', color: 'white' }}
                        />
                      </Tooltip>
                      <Text fontSize="2xs" color="whiteAlpha.400" ml="auto">
                        {dimensionLabel[insight.dimension] ?? insight.dimension}
                      </Text>
                    </HStack>
                  </Box>
                </Flex>
              </Box>
            );
          })}
        </VStack>
      )}
    </Box>
  );
};

export default InsightsCard;
