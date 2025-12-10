// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminChatPage.tsx
import { Box, VStack, Text, Icon } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiMessageSquare } from 'react-icons/fi';

function AdminChatPage() {
  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack align="start" spacing={4}>
          <Icon as={FiMessageSquare} boxSize={8} color="gray.400" />
          <Text fontSize="24px" fontWeight="medium" color="gray.900">
            Chat Admin
          </Text>
          <Text fontSize="14px" color="gray.500">
            Converse com o suporte ou configure seu assistente.
          </Text>
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminChatPage;
