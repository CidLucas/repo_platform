import { Box, Flex } from '@chakra-ui/react';
import { Header } from '../Header';
import { FloatingMenu } from '../FloatingMenu';
import React from 'react';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <Flex direction="column" minHeight="100vh">
      <Header />
      <Box as="main" flex="1">
        {children}
      </Box>
      <FloatingMenu />
    </Flex>
  );
};
