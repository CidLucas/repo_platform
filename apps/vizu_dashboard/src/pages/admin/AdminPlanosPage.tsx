// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminPlanosPage.tsx
import { Box, VStack, Text, Icon } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiCreditCard } from 'react-icons/fi';

function AdminPlanosPage() {
  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack align="start" spacing={4}>
          <Icon as={FiCreditCard} boxSize={8} color="gray.400" />
          <Text fontSize="24px" fontWeight="medium" color="gray.900">
            Planos Contratados
          </Text>
          <Text fontSize="14px" color="gray.500">
            Gerencie seus planos e assinaturas.
          </Text>
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminPlanosPage;
