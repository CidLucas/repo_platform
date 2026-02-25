import { Box, Text, useDisclosure, Modal, ModalOverlay, ModalContent, ModalBody, Flex, IconButton, ModalCloseButton, HStack, VStack } from '@chakra-ui/react';
import { InfoOutlineIcon } from '@chakra-ui/icons';
import React from 'react';
import { GraphComponent } from './GraphComponent';
import { BarChartComponent } from './BarChartComponent';
import { MapComponent } from './MapComponent';
import { ModalContentLayout } from './ModalContentLayout';
import { AccordionComponent } from './AccordionComponent';
import { GraphCarousel } from './GraphCarousel';

// Interface for insight bullets
export interface InsightBullet {
  text: string;
  type: 'positive' | 'negative' | 'neutral' | 'warning' | 'star';
  detail?: string; // Optional detail text shown below the main text
}

interface ChartDataPoint {
  name?: string;
  value?: number;
  data?: string;
  [key: string]: string | number | undefined;
}

interface MapMarker {
  position: [number, number];
  popupText: string;
}

interface MapDataConfig {
  center: [number, number];
  zoom: number;
  markers: MapMarker[];
}

interface DashboardCardProps {
  title: string;
  size?: "small" | "large";
  bgColor?: string;
  bgImage?: string;
  bgGradient?: string;
  graphData?: ChartDataPoint[];
  barChartData?: { name: string; value: number; color?: string }[];
  scorecardValue?: string;
  scorecardLabel?: string;
  mainText?: string;
  mapData?: MapDataConfig;
  kpiItems?: { label: string; content: React.ReactNode }[];
  insightBullets?: InsightBullet[];
  textColor?: string;
  modalLeftBgColor?: string;
  modalRightBgColor?: string;
  graphTitle?: string;
  graphDescription?: string;
  onExpandClick?: () => void;
  carouselGraphs?: {
    data: ChartDataPoint[];
    dataKey: string;
    lineColor?: string;
    title: string;
    description?: string;
    chartType?: 'line' | 'bar';
    barColors?: string[];
  }[];
}

// Helper component to render insight bullets (card version - compact)
const InsightBulletItemCompact = ({ bullet }: { bullet: InsightBullet }) => {
  const getIcon = () => {
    switch (bullet.type) {
      case 'positive':
        return <Box as="span" color="green.300" fontSize="xs">▲</Box>;
      case 'negative':
        return <Box as="span" color="red.300" fontSize="xs">▼</Box>;
      case 'warning':
        return <Box as="span" color="yellow.300" fontSize="xs">⚠</Box>;
      case 'star':
        return <Box as="span" color="yellow.200" fontSize="xs">★</Box>;
      default:
        return <Box as="span" color="blue.200" fontSize="xs">●</Box>;
    }
  };

  return (
    <HStack spacing={2} align="flex-start">
      <Box mt="2px">{getIcon()}</Box>
      <Text fontSize="xs" color="whiteAlpha.900" lineHeight="1.4">
        {bullet.text}
      </Text>
    </HStack>
  );
};

export const DashboardCard = ({
  title,
  size = "small",
  bgColor = "white",
  bgImage,
  bgGradient, // Destructure new prop
  graphData,
  barChartData,
  scorecardValue,
  scorecardLabel,
  mainText,
  mapData,
  kpiItems, // Destructure new prop
  insightBullets, // Destructure insight bullets prop
  textColor = "gray.800", // Default text color
  modalLeftBgColor = "#C9EDFF", // Default for Fornecedores
  modalRightBgColor = "#92DAFF", // Default for Fornecedores
  graphTitle,
  graphDescription,
  onExpandClick,
  carouselGraphs, // Destructure carousel graphs prop
}: DashboardCardProps) => {

  const { isOpen, onOpen, onClose } = useDisclosure();

  const cardWidth = size === "large" ? "824px" : "422px";
  const cardHeight = "524px";
  const cardPadding = { base: "24px 40px 28px 40px", md: "24px 40px 28px 40px" };
  const cardBorderRadius = "22px";

  return (
    <>
      <Flex
        direction="column"
        position="relative"
        bg={bgImage ? `url(${bgImage})` : bgColor}
        bgGradient={bgGradient}
        backgroundSize="cover"
        backgroundPosition="center"
        borderRadius={cardBorderRadius}
        boxShadow="md"
        width={cardWidth}
        height={cardHeight}
        _hover={{ boxShadow: "lg" }}
      >
        {/* Map Component - positioned absolutely to fill the card */}
        {mapData && (
          <Box position="absolute" top="0" left="0" right="0" bottom="0" borderRadius={cardBorderRadius} overflow="hidden">
            <MapComponent {...mapData} />
          </Box>
        )}

        {/* Content Overlay - positioned absolutely on top of the map/background */}
        <Flex
          direction="column"
          position="absolute"
          top="0"
          left="0"
          right="0"
          bottom="0"
          p={cardPadding}
          zIndex="1000" // Increased z-index
          pointerEvents="none" // Allow events to pass through to the map
          color={textColor} // Apply text color
          bg="transparent" // Explicitly set background to transparent
        >
          <Flex justify="space-between" align="center" flexShrink={0}>
            <Text textStyle="cardHeaderTitle">{title}</Text>
            <IconButton
              aria-label="Expand card"
              icon={<InfoOutlineIcon />}
              size="sm"
              onClick={onExpandClick || onOpen}
              variant="ghost"
              color={textColor}
              _hover={{ color: "gray.200" }}
              pointerEvents="auto"
            />
          </Flex>

          {/* Insight Bullets content - replaces graph/bar chart when present */}
          {insightBullets && insightBullets.length > 0 && !mapData ? (
            <VStack spacing={3} align="stretch" flex="1" mt={4} mb={2}>
              {insightBullets.slice(0, 4).map((bullet, index) => (
                <InsightBulletItemCompact key={index} bullet={bullet} />
              ))}
            </VStack>
          ) : (
            <>
              {/* Graph content - centralized vertically */}
              {graphData && !barChartData && (
                <Flex flex="1" align="center" justify="center" minH="200px" py={4}>
                  <Box width="100%" height="280px">
                    <GraphComponent data={graphData.values} dataKey="value" lineColor="#FFA500" axisColor={textColor === "white" ? "#ffffff" : "#333333"} height="100%" />
                  </Box>
                </Flex>
              )}
              
              {/* Bar chart content - centralized vertically */}
              {barChartData && !insightBullets && (
                <Flex flex="1" align="center" justify="center" minH="200px" py={4}>
                  <Box width="100%" height="240px">
                    <BarChartComponent data={barChartData} axisColor={textColor === "white" ? "#ffffff" : "#333333"} height="100%" />
                  </Box>
                </Flex>
              )}
            </>
          )}
          
          {/* Main text - only show if no insight bullets */}
          {(!insightBullets || insightBullets.length === 0) && mainText && <Text fontSize="md" mb={2}>{mainText}</Text>}

          {/* Scorecard - footer */}
          {(scorecardValue || scorecardLabel) && (
            <Box mt="auto" textAlign="right" flexShrink={0}>
              {scorecardLabel && <Text textStyle="homeCardStatLabel">{scorecardLabel}</Text>}
              {scorecardValue && <Text textStyle="homeCardStatNumber">{scorecardValue}</Text>}
            </Box>
          )}
        </Flex>
      </Flex>

      <Modal isOpen={isOpen} onClose={onClose} size="full">
        <ModalOverlay />
        <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh"> {/* Transparent background for custom layout */}
          <ModalBody p={0}> {/* No padding on ModalBody */}
            <ModalContentLayout
              leftBgColor={mapData ? "transparent" : modalLeftBgColor}
              rightBgColor={modalRightBgColor}
              isMapModal={Boolean(mapData)}
              mapData={mapData}
              leftContent={
                <Flex direction="column" height="100%" color={textColor}>
                  <Flex justify="space-between" align="center" mb={4} flexShrink={0}>
                    <Text textStyle="modalTitle" color={textColor}>{title}</Text>
                    <ModalCloseButton position="static" color={textColor} /> {/* Close button here */}
                  </Flex>
                  <Text textStyle="modalTextInfo" mb={4} color={textColor} flexShrink={0}>
                    {mainText || "Informações descritivas sobre o card."}
                  </Text>
                  <Box flex="1" />
                  <Box flexShrink={0} mt="auto">
                    <AccordionComponent
                      items={kpiItems || [
                        { label: "KPI 1", content: <Text>Detalhes do KPI 1</Text> },
                        { label: "KPI 2", content: <Text>Detalhes do KPI 2</Text> },
                        { label: "KPI 3", content: <Text>Detalhes do KPI 3</Text> },
                        { label: "KPI 4", content: <Text>Detalhes do KPI 4</Text> },
                        { label: "KPI 5", content: <Text>Detalhes do KPI 5</Text> },
                      ]}
                      width="100%" // Accordion fills available width
                      height="auto" // Accordion height adjusts to content
                      textColor={textColor}
                    />
                  </Box>
                </Flex>
              }
              rightContent={
                mapData ? (
                  <MapComponent {...mapData} height="100%" /> // Map fills right half
                ) : carouselGraphs && carouselGraphs.length > 0 ? (
                  <Flex direction="column" height="100%" p={8}>
                    <GraphCarousel
                      graphs={carouselGraphs}
                      textColor={textColor}
                    />
                  </Flex>
                ) : carouselGraphs && carouselGraphs.length === 0 ? (
                  // Explicitly empty carousel - show nothing or placeholder
                  <Flex direction="column" height="100%" p={8} align="center" justify="center">
                    <Text color="gray.500" fontSize="lg">Análise detalhada em breve</Text>
                  </Flex>
                ) : (
                  <Flex direction="column" height="100%" p={8}>
                    <GraphCarousel
                      graphs={[
                        {
                          data: graphData?.values || [],
                          dataKey: "value",
                          lineColor: "white",
                          title: graphTitle || title,
                          description: graphDescription || "Visualização dos dados ao longo do tempo.",
                        },
                      ]}
                      textColor={textColor}
                    />
                  </Flex>
                )
              }
            />
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
