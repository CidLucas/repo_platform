import { Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon, Box, Text } from '@chakra-ui/react';
import React from 'react';

interface AccordionItemData {
  label: string;
  content: React.ReactNode;
}

interface AccordionComponentProps {
  items: AccordionItemData[];
  width?: string;
  height?: string;
}

export const AccordionComponent: React.FC<AccordionComponentProps> = ({
  items,
  width = "610px",
  height = "297px",
}) => {
  return (
    <Accordion allowMultiple width={width} height={height} overflowY="auto">
      {items.map((item, index) => (
        <AccordionItem key={index} borderTop="1px solid black" borderBottom="1px solid black">
          <h2>
            <AccordionButton _expanded={{ bg: 'gray.100' }}>
              <Box as="span" flex='1' textAlign='left' textStyle="modalAccordionLabel">
                {item.label}
              </Box>
              <AccordionIcon />
            </AccordionButton>
          </h2>
          <AccordionPanel pb={4}>
            {item.content}
          </AccordionPanel>
        </AccordionItem>
      ))}
    </Accordion>
  );
};
