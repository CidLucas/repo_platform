import { Box, Flex, IconButton, useMediaQuery } from '@chakra-ui/react';
import { Header } from '../Header';
import { ChatPanel } from '../ChatPanel';
import { ChatRail } from '../ChatRail';
import { useChat } from '../../contexts/ChatContext';
import React from 'react';
import { ChatIcon } from '@chakra-ui/icons';

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  const { isChatOpen, openChat, closeChat, initialMessage, consumeInitialMessage } = useChat();
  const [isDesktopRail] = useMediaQuery('(min-width: 1280px)');

  return (
    <Flex direction="column" minHeight="100vh" bg="#0d0e1f">
      <Header />
      <Box as="main" flex="1" bg="#0d0e1f" pr={{ base: 0, '2xl': isChatOpen ? 0 : '320px' }}>
        {children}
      </Box>
      <ChatRail />
      {!isDesktopRail && !isChatOpen && (
        <IconButton
          position="fixed"
          bottom={6}
          right={6}
          zIndex={30}
          aria-label="Abrir chat do Blu"
          icon={<ChatIcon />}
          color="white"
          bgGradient="linear(to-r, #2563eb, #1d4ed8)"
          boxShadow="0 8px 24px rgba(37,99,235,0.4)"
          borderRadius="full"
          size="lg"
          _hover={{ bgGradient: 'linear(to-r, #1d4ed8, #1e40af)' }}
          onClick={() => openChat()}
        />
      )}
      {/* Chat Panel - slides from right with blur effect */}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={closeChat}
        initialMessage={initialMessage}
        onInitialMessageConsumed={consumeInitialMessage}
      />
    </Flex>
  );
};

export default MainLayout;
