import { Accordion, AccordionItem, AccordionButton, AccordionPanel, AccordionIcon, Box } from '@chakra-ui/react';
import React from 'react';

interface AccordionItemData {
  label: string;
  content: React.ReactNode;
}

interface AccordionComponentProps {
  items: AccordionItemData[];
  width?: string;
  height?: string;
  textColor?: string;
}

export const AccordionComponent: React.FC<AccordionComponentProps> = ({
  items,
  width = "610px",
  height = "297px",
  textColor = "gray.800",
}) => {
  const isDark = textColor === 'white';
  
  return (
    <Accordion allowMultiple width={width} height={height} overflowY="auto">
      {items.map((item, index) => (
        <AccordionItem key={index} borderTop={`1px solid ${isDark ? 'rgba(255,255,255,0.3)' : 'black'}`} borderBottom={`1px solid ${isDark ? 'rgba(255,255,255,0.3)' : 'black'}`}>
          <h2>
            <AccordionButton _expanded={{ bg: isDark ? 'rgba(255,255,255,0.1)' : 'gray.100' }}>
              <Box as="span" flex='1' textAlign='left' textStyle="modalAccordionLabel" color={textColor}>
                {item.label}
              </Box>
              <AccordionIcon color={textColor} />
            </AccordionButton>
          </h2>
          <AccordionPanel pb={4} color={textColor}>
            {item.content}
          </AccordionPanel>
        </AccordionItem>
      ))}
    </Accordion>
  );
};
