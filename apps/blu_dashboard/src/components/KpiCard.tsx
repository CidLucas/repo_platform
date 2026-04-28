import { Box, Flex, HStack, Icon, Text } from '@chakra-ui/react';
import { FiMinus, FiTrendingDown, FiTrendingUp } from 'react-icons/fi';
import type { IconType } from 'react-icons';
import { SampleBadge } from './SampleBadge';

type TrendDirection = 'up' | 'down' | 'flat';

interface KpiDeltaViewModel {
  label: string;
  color: string;
  icon: IconType;
  direction: TrendDirection;
}

const formatKpiDelta = (delta: number | null | undefined): KpiDeltaViewModel => {
  const safeDelta = Number.isFinite(delta) ? Number(delta) : 0;
  if (safeDelta > 0) {
    return {
      label: `+${safeDelta.toFixed(1)}%`,
      color: 'green.400',
      icon: FiTrendingUp,
      direction: 'up',
    };
  }
  if (safeDelta < 0) {
    return {
      label: `${safeDelta.toFixed(1)}%`,
      color: 'red.400',
      icon: FiTrendingDown,
      direction: 'down',
    };
  }

  return {
    label: '0,0%',
    color: 'whiteAlpha.500',
    icon: FiMinus,
    direction: 'flat',
  };
};

interface KpiCardProps {
  title: string;
  value: string;
  icon: IconType;
  accentColor: string;
  delta?: number | null;
  deltaContext?: string;
  description?: string;
  isSample?: boolean;
}

export const KpiCard = ({
  title,
  value,
  icon,
  accentColor,
  delta,
  deltaContext,
  description,
  isSample = false,
}: KpiCardProps) => {
  const trend = delta !== undefined ? formatKpiDelta(delta) : null;

  return (
    <Box
      bg="#1a1b2e"
      borderRadius="0.625rem"
      border="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      boxShadow="0 4px 24px rgba(0,0,0,0.4)"
      p={6}
      position="relative"
      overflow="hidden"
    >
      <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={accentColor} />
      <Flex justify="space-between" align="start" mb={3}>
        <Box>
          <HStack spacing={2} mb={1}>
            <Text
              color="whiteAlpha.500"
              fontSize="xs"
              fontWeight="semibold"
              textTransform="uppercase"
              letterSpacing="wider"
            >
              {title}
            </Text>
            {isSample && <SampleBadge />}
          </HStack>
          <Text fontSize="2.5rem" fontWeight="bold" color="white" lineHeight="1.05">
            {value}
          </Text>
        </Box>

        <Flex
          w={12}
          h={12}
          borderRadius="1rem"
          align="center"
          justify="center"
          bgGradient={`linear(to-br, ${accentColor}, ${accentColor}dd)`}
          boxShadow={`0 4px 12px ${accentColor}99`}
        >
          <Icon as={icon} boxSize={6} color="white" />
        </Flex>
      </Flex>

      {trend && (
        <HStack spacing={2}>
          <HStack spacing={1} color={trend.color}>
            <Icon as={trend.icon} boxSize={4} />
            <Text fontSize="sm" fontWeight="medium">
              {trend.label}
            </Text>
          </HStack>
          {deltaContext && (
            <Text fontSize="sm" color="whiteAlpha.500">
              {deltaContext}
            </Text>
          )}
        </HStack>
      )}

      {!trend && description && (
        <Text fontSize="xs" color="whiteAlpha.600">
          {description}
        </Text>
      )}
    </Box>
  );
};

export default KpiCard;
