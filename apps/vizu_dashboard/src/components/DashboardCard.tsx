import { Box, Text, useDisclosure, Modal, ModalOverlay, ModalContent, ModalBody, Flex, IconButton, ModalCloseButton } from '@chakra-ui/react';
import { InfoOutlineIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import React from 'react';
import { GraphComponent } from './GraphComponent';
import { BarChartComponent } from './BarChartComponent';
import { MapComponent } from './MapComponent';
import { ModalContentLayout } from './ModalContentLayout';
import { AccordionComponent } from './AccordionComponent';
import { GraphCarousel } from './GraphCarousel';

interface DashboardCardProps {
  title: string;
  size?: "small" | "large";
  bgColor?: string;
  bgImage?: string;
  bgGradient?: string; // Add bgGradient prop
  // Content props
  graphData?: any;
  barChartData?: { name: string; value: number; color?: string }[]; // Bar chart data
  scorecardValue?: string;
  scorecardLabel?: string;
  mainText?: string;
  mapData?: any;
  // Modal content
  modalContent?: React.ReactNode;
  kpiItems?: { label: string; content: React.ReactNode }[]; // Dynamic KPI items
  // Text color for content overlay
  textColor?: string;
  // Modal background colors
  modalLeftBgColor?: string;
  modalRightBgColor?: string;
  // Graph modal labels
  graphTitle?: string;
  graphDescription?: string;
  // Custom expand click handler (overrides default modal)
  onExpandClick?: () => void;
  // Carousel graphs for modal (multiple graphs)
  carouselGraphs?: {
    data: any[];
    dataKey: string;
    lineColor?: string;
    title: string;
    description?: string;
    chartType?: 'line' | 'bar';
    barColors?: string[];
  }[];
}

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
  modalContent,
  kpiItems, // Destructure new prop
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
          <Flex justify="space-between" align="center"> {/* Changed align to center again */}
            <Text textStyle="cardHeaderTitle">{title}</Text> {/* Removed mb={2} */}
            <Flex> {/* Group icons together */}
              <IconButton
                aria-label="Show info"
                icon={<InfoOutlineIcon />} // Tooltip icon
                size="sm"
                variant="ghost"
                color={textColor}
                _hover={{ color: "gray.200" }}
                pointerEvents="auto"
                mr={2} // Margin right for spacing
              />
              <IconButton
                aria-label="Expand card"
                icon={<ExternalLinkIcon />} // Modal expand icon
                size="sm"
                onClick={onExpandClick || onOpen} // Use custom handler if provided, otherwise open internal modal
                variant="ghost"
                color={textColor}
                _hover={{ color: "gray.200" }}
                pointerEvents="auto"
              />
            </Flex>
          </Flex>

          {/* Conditional rendering of content */}
          {graphData && !barChartData && (
            <Box flex="1" minH="200px">
              <GraphComponent data={graphData.values} dataKey="value" lineColor="#FFA500" axisColor={textColor === "white" ? "#ffffff" : "#333333"} />
            </Box>
          )}
          {barChartData && (
            <Box flex="1" minH="200px">
              <BarChartComponent data={barChartData} axisColor={textColor === "white" ? "#ffffff" : "#333333"} />
            </Box>
          )}
          {mainText && <Text fontSize="md" mb={2}>{mainText}</Text>}

          {(scorecardValue || scorecardLabel) && (
            <Box mt="auto" textAlign="right"> {/* Added textAlign="right" */}
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
              leftBgColor={!!mapData ? "transparent" : modalLeftBgColor} // Conditionally set leftBgColor
              rightBgColor={modalRightBgColor} // Use prop
              isMapModal={!!mapData} // Pass if it's a map modal
              mapData={mapData} // Pass mapData
              leftContent={
                <Flex direction="column" height="100%" color={textColor}>
                  <Flex justify="space-between" align="center" mb={4}>
                    <Text textStyle="modalTitle" color={textColor}>{title}</Text>
                    <ModalCloseButton position="static" color={textColor} /> {/* Close button here */}
                  </Flex>
                  <Text textStyle="modalTextInfo" mb={8} color={textColor}>
                    {mainText || "Informações descritivas sobre o card."}
                  </Text>
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
                </Flex>
              }
              rightContent={
                mapData ? (
                  <MapComponent {...mapData} height="100%" /> // Map fills right half
                ) : carouselGraphs && carouselGraphs.length === 0 ? (
                  // Explicitly empty carousel - show nothing or placeholder
                  <Flex direction="column" height="100%" p={8} align="center" justify="center">
                    <Text color="gray.500" fontSize="lg">Análise detalhada em breve</Text>
                  </Flex>
                ) : (
                  <Flex direction="column" height="100%" p={8}>
                    <GraphCarousel
                      graphs={carouselGraphs || [
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
