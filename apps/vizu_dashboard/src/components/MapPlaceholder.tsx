import { Box, Text } from '@chakra-ui/react';
import React from 'react';

interface MapPlaceholderProps {
  height?: string;
  data?: any;
  height?: string;
}

export const MapPlaceholder = ({ height = "150px" }: MapPlaceholderProps) => {
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
      <Text>Mapa Placeholder</Text>
    </Box>
  );
};
