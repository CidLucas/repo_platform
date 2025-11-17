import { Box, Text, Flex } from '@chakra-ui/react';
import React from 'react';

interface MiniCardProps {
  title: string;
  description: string;
  status?: string; // e.g., "Concluído", "Pendente"
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
      _hover={{ boxShadow: "lg" }}
    >
      <Flex justify="space-between" align="center" mb={1}>
        <Text fontWeight="semibold" fontSize="md">{title}</Text>
        {status && (
          <Text fontSize="sm" color="gray.500">{status}</Text>
        )}
      </Flex>
      <Text fontSize="sm" color="gray.600" noOfLines={2}>{description}</Text>
    </Box>
  );
};
