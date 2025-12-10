// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminAjudaPage.tsx
import { Box, VStack, Text, Icon } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiHelpCircle } from 'react-icons/fi';

function AdminAjudaPage() {
  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack align="start" spacing={4}>
          <Icon as={FiHelpCircle} boxSize={8} color="gray.400" />
          <Text fontSize="24px" fontWeight="medium" color="gray.900">
            Central de Ajuda
          </Text>
          <Text fontSize="14px" color="gray.500">
            Encontre respostas para suas dúvidas e tutoriais.
          </Text>
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminAjudaPage;
