import { Box, Text, Flex, Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon } from '@chakra-ui/react';
import React from 'react';
import { GraphComponent } from './GraphComponent';
import type { ChartDataPoint } from '../types';

interface ExpandableScorecardCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  bgColor?: string;
  width?: string;
  height?: string;
  onClick?: () => void;
  graphData?: ChartDataPoint[];
  graphDataKey?: string;
  graphLineColor?: string;
  isLoading?: boolean;
}

export const ExpandableScorecardCard: React.FC<ExpandableScorecardCardProps> = ({
  title,
  value,
  subtitle,
  bgColor = '#B2E7FF',
  width = '100%',
  height = '140px',
  onClick,
  graphData,
  graphDataKey = 'value',
  graphLineColor = '#FFA500',
  isLoading = false,
}) => {
  // If graphData prop is provided (even if empty array), render as expandable
  const isExpandable = graphData !== undefined;

  // If no graph data prop at all (undefined), render as regular scorecard with optional click handler
  if (!isExpandable) {
    return (
      <Box
        width={width}
        height={height}
        borderRadius="24px"
        bg={bgColor}
        p={4}
        boxShadow="md"
        cursor={onClick ? 'pointer' : 'default'}
        onClick={onClick}
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
  }

  // Render as expandable accordion with graph
  return (
    <Accordion allowToggle width={width}>
      <AccordionItem
        border="none"
        borderRadius="24px"
        bg={bgColor}
        overflow="hidden"
        boxShadow="md"
      >
        <AccordionButton
          p={4}
          _hover={{ bg: 'rgba(0,0,0,0.05)' }}
          _expanded={{ borderBottomRadius: 0 }}
          borderRadius="24px"
          transition="all 0.2s"
        >
          <Flex
            direction="column"
            flex={1}
            align="flex-start"
            minHeight={height}
            justify="space-between"
          >
            <Text
              textTransform="uppercase"
              fontSize="sm"
              fontWeight="semibold"
              color="gray.700"
              mb={2}
            >
              {title}
            </Text>
            <Box width="100%">
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
          <AccordionIcon ml={2} />
        </AccordionButton>

        <AccordionPanel pb={4} pt={2}>
          {isLoading ? (
            <Flex justify="center" align="center" height="250px">
              <Text color="gray.600">Carregando gráfico...</Text>
            </Flex>
          ) : graphData.length === 0 ? (
            <Flex justify="center" align="center" height="250px">
              <Text color="gray.600">Nenhum dado disponível</Text>
            </Flex>
          ) : (
            <Box>
              <Text fontSize="sm" fontWeight="semibold" color="gray.700" mb={2}>
                Histórico Mensal
              </Text>
              <GraphComponent
                data={graphData}
                dataKey={graphDataKey}
                lineColor={graphLineColor}
              />
            </Box>
          )}
        </AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
};
