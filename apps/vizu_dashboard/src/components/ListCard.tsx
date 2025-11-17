import { Box, Flex, Text, Link as ChakraLink } from '@chakra-ui/react';
import React from 'react';
import { MiniCard } from './MiniCard';
import { Link as ReactRouterLink } from 'react-router-dom';

interface ListCardProps {
  title: string;
  items: {
    id: string;
    title: string;
    description: string;
    status?: string;
    modalContent: React.ReactNode; // Content for the modal when mini-card is clicked
  }[];
  onMiniCardClick: (item: any) => void; // Function to open modal with item data
  viewAllLink: string; // Link to the full list page
  cardBgColor?: string; // New prop for MiniCard background color
}

export const ListCard: React.FC<ListCardProps> = ({ title, items, onMiniCardClick, viewAllLink, cardBgColor }) => {
  const cardWidth = "422px";
  const cardHeight = "524px";
  const cardBorderRadius = "22px";

  return (
    <Flex
      direction="column"
      width={cardWidth}
      height={cardHeight}
      borderRadius={cardBorderRadius}
      bg="transparent" // Transparent background
      p={4}
    >
      <Flex justify="space-between" align="center" mb={4}>
        <Text textStyle="cardHeaderTitle" color="gray.800">{title}</Text>
        <ChakraLink as={ReactRouterLink} to={viewAllLink} fontSize="sm" color="blue.500">
          Ver Todos
        </ChakraLink>
      </Flex>

      <Flex direction="column" gap={2} overflowY="auto" flex="1">
        {items.slice(0, 4).map((item) => ( // Show up to 4 mini-cards
          <MiniCard
            key={item.id}
            title={item.title}
            description={item.description}
            status={item.status}
            onClick={() => onMiniCardClick(item)}
            bgColor={cardBgColor} // Pass the background color
          />
        ))}
      </Flex>
    </Flex>
  );
};
