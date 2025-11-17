import { Box, Text } from '@chakra-ui/react';
import React from 'react';

interface GraphPlaceholderProps {
  data?: any;
  height?: string;
}

export const GraphPlaceholder = ({ height = "150px" }: GraphPlaceholderProps) => {
  return (
    <Box
      bg="gray.200"
      height={height}
      display="flex"
      alignItems="center"
      justifyContent="center"
      borderRadius="md"
      color="gray.600"
      fontSize="sm"
    >
      <Text>Gráfico Placeholder</Text>
    </Box>
  );
};
