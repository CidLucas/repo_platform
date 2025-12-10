import { Box, Flex } from '@chakra-ui/react';
import { Header } from '../Header';
import { ChatPanel } from '../ChatPanel';
import { useChat } from '../../contexts/ChatContext';
import React from 'react';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  const { isChatOpen, closeChat } = useChat();

  return (
    <Flex direction="column" minHeight="100vh">
      <Header />
      <Box as="main" flex="1">
        {children}
      </Box>
      {/* Chat Panel - slides from right with blur effect */}
      <ChatPanel isOpen={isChatOpen} onClose={closeChat} />
    </Flex>
  );
};

export default MainLayout;
