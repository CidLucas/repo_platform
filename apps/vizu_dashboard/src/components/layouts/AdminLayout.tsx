// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/components/layouts/AdminLayout.tsx
import { Box, Flex } from '@chakra-ui/react';
import { Header } from '../Header';
import AdminSidebar from '../admin/AdminSidebar';
import { ChatPanel } from '../ChatPanel';
import { useChat } from '../../contexts/ChatContext';
import React from 'react';

interface AdminLayoutProps {
  children: React.ReactNode;
}

export const AdminLayout = ({ children }: AdminLayoutProps) => {
  const { isChatOpen, closeChat } = useChat();

  return (
    <Flex direction="column" minHeight="100vh" bg="#f6f6f6">
      <Header />
      <Flex flex="1">
        <AdminSidebar />
        <Box as="main" flex="1" overflowY="auto">
          {children}
        </Box>
      </Flex>
      <ChatPanel isOpen={isChatOpen} onClose={closeChat} />
    </Flex>
  );
};

export default AdminLayout;
