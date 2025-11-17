import { Box, Heading } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';

function SettingsPage() {
  return (
    <MainLayout>
      <Box p={8}>
        <Heading>Página de Configurações</Heading>
        <p>Conteúdo da página de configurações...</p>
      </Box>
    </MainLayout>
  );
}

export default SettingsPage;
