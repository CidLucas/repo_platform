import { Box, Heading } from '@chakra-ui/react';
import { MainLayout } from '../components/layouts/MainLayout';

function ChartsPage() {
  return (
    <MainLayout>
      <Box p={8}>
        <Heading>Página de Gráficos</Heading>
        <p>Conteúdo da página de gráficos...</p>
      </Box>
    </MainLayout>
  );
}

export default ChartsPage;
