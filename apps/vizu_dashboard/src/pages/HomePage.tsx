import { Box, Flex, Text } from '@chakra-ui/react';
import { StatCard } from '../components/StatCard';
import { MainLayout } from '../components/layouts/MainLayout';
import { Link } from 'react-router-dom';

function HomePage() {
  return (
    <MainLayout>
      <Flex 
        direction="column" 
        px={{ base: '20px', md: '40px', lg: '80px' }} 
        pt={{ base: '20px', md: '40px', lg: '20px' }} 
        pb={{ base: '80px', md: '40px', lg: '20px' }} // Added responsive padding-bottom
        mt="32px"
        bg="#F6F6F6" // Explicitly set background for HomePage
      >
        <Text as="h1" textStyle="pageTitle" mb="36px">Olá, Fábio. Sua<br />receita em agosto</Text>
        <Text as="h2" textStyle="pageBigNumber" mb="36px">$132.000</Text>
        <Box mt="36px">
          <Flex wrap="wrap" justify="center" gap="16px">
            <Link to="/fornecedores">
              <StatCard 
                title="FORNECEDORES" 
                percentage="+0.85%" 
                total="800" 
                totalLabel="TOTAL" 
                frequency="2 / mês" 
                frequencyLabel="FREQUÊNCIA" 
                color="#92DAFF" // Updated Blue
              />
            </Link>
            <Link to="/produtos">
              <StatCard 
                title="PRODUTOS" 
                percentage="+0.85%" 
                total="400" 
                totalLabel="TOTAL" 
                frequency="2 / mês" 
                frequencyLabel="FREQUÊNCIA" 
                color="#FFF856" // Updated Yellow
              />
            </Link>
            <Link to="/pedidos">
              <StatCard 
                title="PEDIDOS" 
                percentage="+0.85%" 
                total="35" 
                totalLabel="TOTAL" 
                frequency="2 / mês" 
                frequencyLabel="FREQUÊNCIA" 
                color="#FFB6C1" // Pink
              />
            </Link>
          </Flex>
        </Box>
      </Flex>
    </MainLayout>
  )
}

export default HomePage
