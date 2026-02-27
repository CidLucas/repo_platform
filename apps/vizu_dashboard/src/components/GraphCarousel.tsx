import { Box, Flex, IconButton, Text, Spinner } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';
import React, { useState } from 'react';
import { GraphComponent } from './GraphComponent';
import { BarChartComponent } from './BarChartComponent';
import type { ChartDataPoint, ChartType } from '../types';

interface GraphCarouselProps {
  graphs: {
    data: ChartDataPoint[];
    dataKey: string;
    lineColor?: string;
    title: string;
    description?: string;
    chartType?: ChartType;
    barColors?: string[];
  }[];
  loading?: boolean;
  height?: number | string;
  textColor?: string;
}

export const GraphCarousel: React.FC<GraphCarouselProps> = ({
  graphs,
  loading = false,
  height = 300,
  textColor = 'gray.800',
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const handlePrev = () => {
    setCurrentIndex((prevIndex) => (prevIndex === 0 ? graphs.length - 1 : prevIndex - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prevIndex) => (prevIndex === graphs.length - 1 ? 0 : prevIndex + 1));
  };

  if (loading) {
    return (
      <Flex direction="column" align="center" justify="center" height={height} width="100%">
        <Spinner size="lg" color="gray.500" />
        <Text mt={4} color="gray.500">Carregando gráfico...</Text>
      </Flex>
    );
  }

  if (!graphs || graphs.length === 0) {
    return (
      <Flex direction="column" align="center" justify="center" height={height} width="100%">
        <Text color="gray.500">Nenhum gráfico disponível</Text>
      </Flex>
    );
  }

  const currentGraph = graphs[currentIndex];

  // Render appropriate chart type
  const renderChart = () => {
    const chartHeight = typeof height === 'number' ? height - 100 : 200;
    const axisColor = textColor === 'white' ? '#ffffff' : '#333333';

    if (currentGraph.chartType === 'bar') {
      return (
        <BarChartComponent
          data={currentGraph.data}
          dataKey={currentGraph.dataKey}
          height={chartHeight}
          axisColor={axisColor}
          colors={currentGraph.barColors}
        />
      );
    }

    // Default: line chart
    return (
      <GraphComponent
        data={currentGraph.data}
        dataKey={currentGraph.dataKey}
        lineColor={currentGraph.lineColor}
        height="100%"
        showGrid={true}
        axisColor={axisColor}
      />
    );
  };

  return (
    <Flex direction="column" align="center" justify="space-between" height="100%" width="100%">
      <Text textStyle="modalTitle" mb={2} color={textColor}>{currentGraph.title}</Text>
      <Box flex="1" width="100%" minHeight={typeof height === 'number' ? height - 100 : 200}>
        {renderChart()}
      </Box>
      <Flex mt={2} align="center">
        <IconButton
          aria-label="Gráfico anterior"
          icon={<ChevronLeftIcon boxSize={5} />}
          onClick={handlePrev}
          variant="ghost"
          size="sm"
          color={textColor}
          isDisabled={graphs.length <= 1}
        />
        <Text mx={3} fontSize="sm" color={textColor === 'white' ? 'gray.300' : 'gray.600'}>
          {currentIndex + 1} / {graphs.length}
        </Text>
        <IconButton
          aria-label="Próximo gráfico"
          icon={<ChevronRightIcon boxSize={5} />}
          onClick={handleNext}
          variant="ghost"
          size="sm"
          color={textColor}
          isDisabled={graphs.length <= 1}
        />
      </Flex>
      {currentGraph.description && (
        <Text fontSize="sm" color={textColor === 'white' ? 'gray.300' : 'gray.600'} mt={2} textAlign="center" px={4}>
          {currentGraph.description}
        </Text>
      )}
    </Flex>
  );
};
