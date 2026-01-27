import { Box, Flex, IconButton, Text, Spinner } from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';
import React, { useState } from 'react';
import { GraphComponent } from './GraphComponent';

interface GraphCarouselProps {
  graphs: {
    data: any[];
    dataKey: string;
    lineColor?: string;
    title: string;
    description?: string;
  }[];
  loading?: boolean;
  height?: number | string;
}

export const GraphCarousel: React.FC<GraphCarouselProps> = ({ graphs, loading = false, height = 300 }) => {
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

  // Validate current graph has data
  const hasData = currentGraph.data && currentGraph.data.length > 0;

  return (
    <Flex direction="column" align="center" justify="space-between" height="100%" width="100%">
      <Text textStyle="modalTitle" mb={2}>{currentGraph.title}</Text>
      <Box flex="1" width="100%" minHeight={typeof height === 'number' ? height - 100 : 200}>
        <GraphComponent
          data={currentGraph.data}
          dataKey={currentGraph.dataKey}
          lineColor={currentGraph.lineColor}
          height="100%"
          showGrid={true}
        />
      </Box>
      <Flex mt={2} align="center">
        <IconButton
          aria-label="Gráfico anterior"
          icon={<ChevronLeftIcon boxSize={5} />}
          onClick={handlePrev}
          variant="ghost"
          size="sm"
          isDisabled={graphs.length <= 1}
        />
        <Text mx={3} fontSize="sm" color="gray.600">{currentIndex + 1} / {graphs.length}</Text>
        <IconButton
          aria-label="Próximo gráfico"
          icon={<ChevronRightIcon boxSize={5} />}
          onClick={handleNext}
          variant="ghost"
          size="sm"
          isDisabled={graphs.length <= 1}
        />
      </Flex>
      {currentGraph.description && (
        <Text fontSize="sm" color="gray.600" mt={2} textAlign="center" px={4}>
          {currentGraph.description}
        </Text>
      )}
    </Flex>
  );
};
