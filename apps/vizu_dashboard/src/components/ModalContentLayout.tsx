import { Box, Flex } from '@chakra-ui/react';
import React from 'react';
import { MapComponent } from './MapComponent'; // Import MapComponent

interface ModalContentLayoutProps {
  leftContent: React.ReactNode;
  rightContent: React.ReactNode;
  leftBgColor?: string;
  rightBgColor?: string;
  isMapModal?: boolean; // Special prop for map modal
  mapData?: any; // Pass mapData for the background map
}

export const ModalContentLayout: React.FC<ModalContentLayoutProps> = ({
  leftContent,
  rightContent,
  leftBgColor = 'white',
  rightBgColor = 'white',
  isMapModal = false,
  mapData, // Destructure mapData
}) => {
  if (isMapModal && mapData) {
    return (
      <Box height="100%" width="100%" position="relative">
        {/* Full-screen Map Background */}
        <Box position="absolute" top="0" left="0" right="0" bottom="0" zIndex="-1"> {/* Map with zIndex="-1" */}
          <MapComponent {...mapData} height="100%" />
        </Box>

        {/* Overlays for Left and Right Content */}
        <Flex height="100%" width="100%" position="relative" zIndex="1">
          {/* Left Half Overlay with Blur */}
          <Box
            flex="1"
            bg={leftBgColor} // This should be transparent from DashboardCard
            position="relative"
          >
            <Box
              position="absolute"
              top="0"
              left="0"
              right="0"
              bottom="0"
              style={{ backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)', backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
              zIndex="1"
              border="1px solid transparent"
              borderImage="linear-gradient(156.52deg, rgba(255, 255, 255, 0.4) 2.12%, rgba(255, 255, 255, 0.0001) 39%, rgba(255, 255, 255, 0.0001) 54.33%, rgba(255, 255, 255, 0.1) 93.02%) 1"
            />
            <Flex direction="column" p={8} height="100%" position="relative" zIndex="2">
              {leftContent}
            </Flex>
          </Box>

          {/* Right Half Overlay (empty or other content) */}
          <Box flex="1" bg="transparent"> {/* Right half is transparent */}
            {rightContent}
          </Box>
        </Flex>
      </Box>
    );
  }

  // Original two-column layout for non-map modals
  return (
    <Flex height="100%" width="100%">
      {/* Left Half */}
      <Box
        flex="1"
        bg={leftBgColor}
        position="relative"
      >
        <Flex direction="column" p={8} height="100%" position="relative" zIndex="2">
          {leftContent}
        </Flex>
      </Box>

      {/* Right Half */}
      <Box flex="1" bg={rightBgColor}>
        {rightContent}
      </Box>
    </Flex>
  );
};
