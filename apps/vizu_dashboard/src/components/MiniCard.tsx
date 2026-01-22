import { Box, Text, Flex } from '@chakra-ui/react';
import React from 'react';
import { TierBadge } from './TierBadge';

interface MiniCardProps {
  title: string;
  description: string;
  status?: string; // e.g., "A", "B", "C", "D" for tier
  onClick: () => void;
  bgColor?: string; // New prop for background color
}

export const MiniCard: React.FC<MiniCardProps> = ({ title, description, status, onClick, bgColor }) => {
  return (
    <Box
      width="390px"
      height="114px"
      borderRadius="24px"
      bg={bgColor || "#FFD3E1"} // Use bgColor prop or fallback to default
      p={4}
      boxShadow="md"
      cursor="pointer"
      onClick={onClick}
      _hover={{ boxShadow: "lg", transform: 'translateY(-2px)' }}
      transition="all 0.2s"
    >
      <Flex justify="space-between" align="center" mb={1}>
        <Text fontWeight="semibold" fontSize="md">{title}</Text>
        {status && <TierBadge tier={status} size="sm" />}
      </Flex>
      <Text fontSize="sm" color="gray.600" noOfLines={2}>{description}</Text>
    </Box>
  );
};
