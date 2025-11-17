import { Box, Flex, Text, Spacer } from '@chakra-ui/react';

interface StatCardProps {
  title: string;
  percentage: string;
  total: string;
  totalLabel: string;
  frequency: string;
  frequencyLabel: string;
  color: string;
}

export const StatCard = ({ 
  title, 
  percentage, 
  total, 
  totalLabel, 
  frequency, 
  frequencyLabel, 
  color 
}: StatCardProps) => {
  return (
    <Box
      bg={color}
      p={6}
      borderRadius="22px"
      color="black"
      width={{ base: '100%', md: '300px', lg: '390px' }}
      height={{ base: 'auto', md: '350px', lg: '524px' }}
      minHeight={{ base: '250px' }}
    >
      <Flex direction="column" height="100%">
        {/* Top Section (left-aligned by default) */}
        <Box>
          <Text as="h3" textStyle="homeCardTitle">{title}</Text>
          <Text textStyle="homeCardPercentage" mt="4px">{percentage}</Text>
        </Box>

        <Spacer />

        {/* Bottom Section (right-aligned) */}
        <Flex direction="column" align="flex-end">
          <Box>
            <Text textStyle="homeCardStatLabel" textAlign="right">{totalLabel}</Text>
            <Text textStyle="homeCardStatNumber" textAlign="right">{total}</Text>
          </Box>
          <Box mt={4}>
            <Text textStyle="homeCardStatLabel" textAlign="right">{frequencyLabel}</Text>
            <Text textStyle="homeCardStatNumber" textAlign="right">{frequency}</Text>
          </Box>
        </Flex>
      </Flex>
    </Box>
  );
};
