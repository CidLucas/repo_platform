import { Box, Text, Flex } from '@chakra-ui/react';
import React from 'react';

interface ScorecardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  bgColor?: string;
  width?: string;
  height?: string;
  onClick?: () => void;
}

export const ScorecardCard: React.FC<ScorecardCardProps> = ({
  title,
  value,
  subtitle,
  bgColor = '#B2E7FF',
  width = '100%',
  height = '140px',
  onClick,
}) => {
  const handleClick = () => {
    console.log('ScorecardCard clicked:', title, 'onClick defined:', !!onClick);
    if (onClick) {
      onClick();
    }
  };

  return (
    <Box
      width={width}
      height={height}
      borderRadius="24px"
      bg={bgColor}
      p={4}
      boxShadow="md"
      cursor={onClick ? 'pointer' : 'default'}
      onClick={handleClick}
      _hover={onClick ? { boxShadow: 'lg', transform: 'translateY(-2px)' } : {}}
      transition="all 0.2s"
    >
      <Flex direction="column" height="100%" justify="space-between">
        <Text
          textTransform="uppercase"
          fontSize="sm"
          fontWeight="semibold"
          color="gray.700"
          mb={2}
        >
          {title}
        </Text>
        <Box>
          <Text
            fontSize="2xl"
            fontWeight="bold"
            color="black"
            noOfLines={2}
          >
            {value}
          </Text>
          {subtitle && (
            <Text
              fontSize="sm"
              color="gray.600"
              mt={1}
            >
              {subtitle}
            </Text>
          )}
        </Box>
      </Flex>
    </Box>
  );
};
