import { Box, Flex, IconButton, Text } from '@chakra-ui/react';
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
}

export const GraphCarousel: React.FC<GraphCarouselProps> = ({ graphs }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentGraph = graphs[currentIndex];

  const handlePrev = () => {
    setCurrentIndex((prevIndex) => (prevIndex === 0 ? graphs.length - 1 : prevIndex - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prevIndex) => (prevIndex === graphs.length - 1 ? 0 : prevIndex + 1));
  };

  if (!graphs || graphs.length === 0) {
    return <Text>No graphs to display.</Text>;
  }

  return (
    <Flex direction="column" align="center" justify="center" height="100%" width="100%">
      <Text textStyle="modalTitle" mb={4}>{currentGraph.title}</Text> {/* Graph title */}
      <Box flex="1" width="100%">
        <GraphComponent
          data={currentGraph.data}
          dataKey={currentGraph.dataKey}
          lineColor={currentGraph.lineColor}
        />
      </Box>
      <Flex mt={4}>
        <IconButton
          aria-label="Previous graph"
          icon={<ChevronLeftIcon />}
          onClick={handlePrev}
          variant="ghost"
        />
        <Text mx={2}>{currentIndex + 1} / {graphs.length}</Text>
        <IconButton
          aria-label="Next graph"
          icon={<ChevronRightIcon />}
          onClick={handleNext}
          variant="ghost"
        />
      </Flex>
      {currentGraph.description && (
        <Text textStyle="modalTextInfo" mt={4} textAlign="center">
          {currentGraph.description}
        </Text>
      )}
    </Flex>
  );
};
