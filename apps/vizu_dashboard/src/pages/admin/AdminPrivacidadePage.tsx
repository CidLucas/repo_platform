// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminPrivacidadePage.tsx
import { Box, VStack, Text, Icon } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiShield } from 'react-icons/fi';

function AdminPrivacidadePage() {
  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack align="start" spacing={4}>
          <Icon as={FiShield} boxSize={8} color="gray.400" />
          <Text fontSize="24px" fontWeight="medium" color="gray.900">
            Dados e Privacidade
          </Text>
          <Text fontSize="14px" color="gray.500">
            Gerencie suas configurações de privacidade e dados.
          </Text>
        </VStack>
      </Box>
    </AdminLayout>
  );
}

export default AdminPrivacidadePage;
