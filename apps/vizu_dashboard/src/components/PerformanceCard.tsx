import { Box, Text, Flex, IconButton, useDisclosure, Modal, ModalOverlay, ModalContent, ModalBody, ModalCloseButton } from '@chakra-ui/react';
import { InfoOutlineIcon, ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons';
import React, { useState, useEffect, useMemo } from 'react';
import { GraphComponent } from './GraphComponent';
import { ModalContentLayout } from './ModalContentLayout';
import { AccordionComponent } from './AccordionComponent';
import { GraphCarousel } from './GraphCarousel';

export type PeriodType = 'week' | 'month' | 'quarter' | 'year';

export interface MetricSlide {
  id: string;
  title: string;           // Título do gráfico (ex: "Receita no Tempo")
  data: any[];             // Dados do gráfico
  dataKey: string;         // Chave dos dados (ex: "value")
  lineColor?: string;      // Cor da linha do gráfico
  metricLabel: string;     // Label da métrica (ex: "RECEITA TOTAL")
  metricValue: string;     // Valor formatado da métrica (ex: "R$ 1.234.567,00")
  rankingKey?: string;     // Chave do ranking associado (ex: "ranking_por_receita")
}

interface PerformanceCardProps {
  title: string;
  bgColor?: string;
  textColor?: string;
  // Slides do carrossel
  slides: MetricSlide[];
  // Callback quando muda o slide (para filtrar ListCard)
  onSlideChange?: (slideIndex: number, slideId: string) => void;
  // Conteúdo do modal
  modalLeftBgColor?: string;
  modalRightBgColor?: string;
  mainText?: string;
  kpiItems?: { label: string; content: React.ReactNode }[];
  // Gráficos do carrossel no modal
  carouselGraphs?: {
    data: any[];
    dataKey: string;
    lineColor?: string;
    title: string;
    description?: string;
    chartType?: 'line' | 'bar';
    barColors?: string[];
  }[];
  // Number of months to show in charts (default: 12)
  chartMonths?: number;
}

export const PerformanceCard: React.FC<PerformanceCardProps> = ({
  title,
  bgColor = "#D4F1F4",
  textColor = "gray.800",
  slides,
  onSlideChange,
  modalLeftBgColor = "#D4F1F4",
  modalRightBgColor = "#92DAFF",
  mainText,
  kpiItems,
  carouselGraphs,
  chartMonths = 12,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  const cardWidth = "824px";
  const cardHeight = "524px";
  const cardPadding = { base: "24px 40px 28px 40px", md: "24px 40px 28px 40px" };
  const cardBorderRadius = "22px";

  // Helper function to filter chart data to last N months
  const filterLastNMonths = <T extends { name: string }>(data: T[], months: number): T[] => {
    if (!data || data.length === 0) return data;
    // Take only the last N entries (assuming data is ordered chronologically)
    return data.slice(-months);
  };

  // Filter slides data to last N months
  const filteredSlides = useMemo(() => {
    return slides.map(slide => ({
      ...slide,
      data: filterLastNMonths(slide.data, chartMonths),
    }));
  }, [slides, chartMonths]);

  // Filter carousel graphs data to last N months
  const filteredCarouselGraphs = useMemo(() => {
    if (!carouselGraphs) return undefined;
    return carouselGraphs.map(graph => ({
      ...graph,
      data: filterLastNMonths(graph.data, chartMonths),
    }));
  }, [carouselGraphs, chartMonths]);

  // Notifica o parent quando o slide muda
  useEffect(() => {
    if (onSlideChange && filteredSlides[currentSlideIndex]) {
      onSlideChange(currentSlideIndex, filteredSlides[currentSlideIndex].id);
    }
  }, [currentSlideIndex, filteredSlides, onSlideChange]);

  const handlePrevSlide = () => {
    setCurrentSlideIndex((prev) => (prev === 0 ? filteredSlides.length - 1 : prev - 1));
  };

  const handleNextSlide = () => {
    setCurrentSlideIndex((prev) => (prev === filteredSlides.length - 1 ? 0 : prev + 1));
  };

  const currentSlide = filteredSlides[currentSlideIndex];

  if (!currentSlide) {
    return null;
  }

  return (
    <>
      <Flex
        direction="column"
        position="relative"
        bg={bgColor}
        borderRadius={cardBorderRadius}
        boxShadow="md"
        width={cardWidth}
        height={cardHeight}
        _hover={{ boxShadow: "lg" }}
      >
        {/* Content Overlay */}
        <Flex
          direction="column"
          position="absolute"
          top="0"
          left="0"
          right="0"
          bottom="0"
          p={cardPadding}
          zIndex="1000"
          color={textColor}
        >
          {/* Header */}
          <Flex justify="space-between" align="center" flexShrink={0} mb={2}>
            <Text textStyle="cardHeaderTitle">{title}</Text>
            <IconButton
              aria-label="Open details"
              icon={<InfoOutlineIcon />}
              size="sm"
              onClick={onOpen}
              variant="ghost"
              color={textColor}
              _hover={{ color: "gray.500" }}
            />
          </Flex>

          {/* Carousel Navigation + Graph */}
          <Flex flex="1" direction="column" position="relative">
            {/* Slide Title with Navigation */}
            <Flex align="center" justify="center" mb={2}>
              <IconButton
                aria-label="Previous metric"
                icon={<ChevronLeftIcon boxSize={5} />}
                onClick={handlePrevSlide}
                variant="ghost"
                size="sm"
                color={textColor}
                isDisabled={filteredSlides.length <= 1}
                _hover={{ bg: 'rgba(0,0,0,0.05)' }}
              />
              <Text 
                fontSize="sm" 
                fontWeight="600" 
                color={textColor} 
                mx={4}
                minW="200px"
                textAlign="center"
              >
                {currentSlide.title}
              </Text>
              <IconButton
                aria-label="Next metric"
                icon={<ChevronRightIcon boxSize={5} />}
                onClick={handleNextSlide}
                variant="ghost"
                size="sm"
                color={textColor}
                isDisabled={filteredSlides.length <= 1}
                _hover={{ bg: 'rgba(0,0,0,0.05)' }}
              />
            </Flex>

            {/* Dots indicator */}
            <Flex justify="center" mb={2}>
              {filteredSlides.map((_, index) => (
                <Box
                  key={index}
                  w="8px"
                  h="8px"
                  borderRadius="full"
                  bg={index === currentSlideIndex ? textColor : 'rgba(0,0,0,0.2)'}
                  mx={1}
                  cursor="pointer"
                  onClick={() => setCurrentSlideIndex(index)}
                  transition="all 0.2s"
                />
              ))}
            </Flex>

            {/* Graph */}
            <Box flex="1" minH="200px">
              <GraphComponent
                data={currentSlide.data}
                dataKey={currentSlide.dataKey}
                lineColor={currentSlide.lineColor || '#FFA500'}
                axisColor={textColor === "white" ? "#ffffff" : "#333333"}
                height="100%"
              />
            </Box>
          </Flex>

          {/* Footer: Metric Display (right aligned) */}
          <Flex justify="flex-end" align="flex-end" mt="auto" flexShrink={0}>
            {/* Metric Display */}
            <Box textAlign="right">
              <Text textStyle="homeCardStatLabel">{currentSlide.metricLabel}</Text>
              <Text textStyle="homeCardStatNumber">{currentSlide.metricValue}</Text>
            </Box>
          </Flex>
        </Flex>
      </Flex>

      {/* Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="full">
        <ModalOverlay />
        <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
          <ModalBody p={0}>
            <ModalContentLayout
              leftBgColor={modalLeftBgColor}
              rightBgColor={modalRightBgColor}
              leftContent={
                <Flex direction="column" height="100%" color={textColor}>
                  {/* Header */}
                  <Flex justify="space-between" align="center" mb={4} flexShrink={0}>
                    <Text textStyle="modalTitle" color={textColor}>{title}</Text>
                    <ModalCloseButton position="static" color={textColor} />
                  </Flex>
                  
                  {/* Main text */}
                  <Text textStyle="modalTextInfo" mb={4} color={textColor} flexShrink={0}>
                    {mainText || "Análise detalhada de performance."}
                  </Text>
                  
                  {/* Spacer to push accordion to bottom */}
                  <Box flex="1" />
                  
                  {/* Accordion at the bottom */}
                  <Box flexShrink={0} mt="auto">
                    <AccordionComponent
                      items={kpiItems || []}
                      width="100%"
                      height="auto"
                      textColor={textColor}
                    />
                  </Box>
                </Flex>
              }
              rightContent={
                <Flex direction="column" height="100%" p={8}>
                  <GraphCarousel
                    graphs={filteredCarouselGraphs || filteredSlides.map(slide => ({
                      data: slide.data,
                      dataKey: slide.dataKey,
                      lineColor: slide.lineColor || '#FFA500',
                      title: slide.title,
                      description: `Visualização de ${slide.title.toLowerCase()} ao longo do tempo.`,
                    }))}
                    textColor={textColor}
                  />
                </Flex>
              }
            />
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
