import React from 'react';
import { Box, Text, Button, Flex, Icon, VStack } from '@chakra-ui/react';
import { FiAlertCircle, FiInbox, FiWifiOff } from 'react-icons/fi';

/**
 * EmptyStateCard — Phase 1 / K1.5 (BLU-MVP-022)
 *
 * Standard empty / degraded state for dimension KPI cards and lists.
 * Variants follow roadmap §10 Fallbacks table:
 *   - 'empty'        — no data yet (e.g. no orders for selected period)
 *   - 'disconnected' — "Conexão indisponível" (data source disconnected)
 *   - 'error'        — RPC/network failure
 *
 * Use the `actionLabel` + `onAction` props to wire the reconnect/retry CTA.
 */

export type EmptyStateVariant = 'empty' | 'disconnected' | 'error';

export interface EmptyStateCardProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  compact?: boolean;
}

const VARIANT_DEFAULTS: Record<EmptyStateVariant, { title: string; description: string; icon: typeof FiInbox; color: string }> = {
  empty: {
    title: 'Sem dados no período',
    description: 'Tente um intervalo maior ou volte quando houver atividade.',
    icon: FiInbox,
    color: 'gray.400',
  },
  disconnected: {
    title: 'Conexão indisponível',
    description: 'A fonte de dados desta dimensão está desconectada.',
    icon: FiWifiOff,
    color: 'orange.400',
  },
  error: {
    title: 'Não foi possível carregar',
    description: 'Tente novamente em instantes.',
    icon: FiAlertCircle,
    color: 'red.400',
  },
};

export const EmptyStateCard: React.FC<EmptyStateCardProps> = ({
  variant = 'empty',
  title,
  description,
  actionLabel,
  onAction,
  compact = false,
}) => {
  const d = VARIANT_DEFAULTS[variant];
  const py = compact ? 4 : 8;
  return (
    <Box
      borderRadius="16px"
      bg="white"
      border="1px dashed"
      borderColor="gray.200"
      px={6}
      py={py}
      width="100%"
    >
      <Flex direction="column" align="center" textAlign="center" gap={2}>
        <Icon as={d.icon} boxSize={compact ? 6 : 8} color={d.color} />
        <VStack spacing={1}>
          <Text fontWeight="semibold" fontSize={compact ? 'sm' : 'md'} color="gray.700">
            {title ?? d.title}
          </Text>
          <Text fontSize="xs" color="gray.500" maxW="320px">
            {description ?? d.description}
          </Text>
        </VStack>
        {actionLabel && onAction && (
          <Button size="sm" colorScheme="blue" variant="outline" onClick={onAction} mt={1}>
            {actionLabel}
          </Button>
        )}
      </Flex>
    </Box>
  );
};
