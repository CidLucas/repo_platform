import { Box, VStack, HStack, Text, Icon, Flex, Badge, Button, SimpleGrid } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiCreditCard, FiCheck, FiDatabase, FiUsers, FiArrowRight, FiZap } from 'react-icons/fi';

function AdminPlanosPage() {
  const planFeatures = [
    { icon: FiDatabase, label: 'Conectores de dados', value: '5 fontes', color: '#3b82f6' },
    { icon: FiUsers, label: 'Agentes de IA', value: '1 agente', color: '#a855f7' },
    { icon: FiZap, label: 'Consultas/mês', value: 'Ilimitadas', color: '#10b981' },
  ];

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack spacing={2} mb={8} align="start">
          <Flex w="48px" h="48px" borderRadius="12px" align="center" justify="center" bg="#a855f720" mb={2}>
            <Icon as={FiCreditCard} boxSize={6} color="#a855f7" />
          </Flex>
          <Text fontSize="24px" fontWeight="semibold" color="white" letterSpacing="-0.3px">
            Planos Contratados
          </Text>
          <Text fontSize="14px" color="whiteAlpha.600" lineHeight="20px">
            Gerencie seus planos, assinaturas e uso da plataforma.
          </Text>
        </VStack>

        {/* Current Plan Card */}
        <Box
          bg="#1a1b2e"
          borderRadius="1rem"
          border="1px solid"
          borderColor="rgba(255,255,255,0.08)"
          p={6}
          position="relative"
          overflow="hidden"
          mb={6}
          transition="all 0.2s"
          _hover={{ borderColor: 'rgba(255,255,255,0.15)' }}
        >
          <Box position="absolute" top={0} left={0} w="3px" h="100%" bgGradient="linear(to-b, #3b82f6, #a855f7)" />
          <HStack justify="space-between" mb={4}>
            <VStack align="start" spacing={1}>
              <HStack spacing={2}>
                <Text fontSize="xs" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" color="#3b82f6">
                  Plano Atual
                </Text>
                <Badge bg="#10b98120" color="#10b981" fontSize="xs" borderRadius="full" px={2}>
                  Ativo
                </Badge>
              </HStack>
              <Text fontSize="xl" fontWeight="bold" color="white">Premium</Text>
            </VStack>
            <VStack align="end" spacing={0}>
              <Text fontSize="2xl" fontWeight="bold" color="white">
                <Text as="span" fontSize="sm" color="whiteAlpha.500">R$</Text> 297
                <Text as="span" fontSize="sm" color="whiteAlpha.500">/mês</Text>
              </Text>
            </VStack>
          </HStack>

          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
            {planFeatures.map((feature) => (
              <HStack key={feature.label} spacing={3} bg="rgba(255,255,255,0.03)" borderRadius="lg" p={3}>
                <Flex w="36px" h="36px" borderRadius="lg" align="center" justify="center" bg={`${feature.color}20`}>
                  <Icon as={feature.icon} boxSize={4} color={feature.color} />
                </Flex>
                <VStack align="start" spacing={0}>
                  <Text fontSize="xs" color="whiteAlpha.500">{feature.label}</Text>
                  <Text fontSize="sm" fontWeight="medium" color="white">{feature.value}</Text>
                </VStack>
              </HStack>
            ))}
          </SimpleGrid>

          <Button
            variant="ghost"
            size="sm"
            color="#3b82f6"
            rightIcon={<FiArrowRight />}
            _hover={{ bg: '#3b82f615' }}
            mt={2}
          >
            Gerenciar assinatura
          </Button>
        </Box>

        {/* Included Features */}
        <Box
          bg="#1a1b2e"
          borderRadius="1rem"
          border="1px solid rgba(255,255,255,0.08)"
          p={6}
        >
          <Text fontSize="xs" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" color="#10b981" mb={4}>
            Incluso no seu plano
          </Text>
          <VStack align="start" spacing={3}>
            {[
              'Conectores ilimitados de CSV e arquivos',
              'Integração com BigQuery, Shopify, VTEX',
              'Base de conhecimento com até 100 documentos',
              'Agente de IA personalizado',
              'Suporte prioritário por e-mail',
              'Exportação de dados e relatórios',
            ].map((feature) => (
              <HStack key={feature} spacing={3}>
                <Flex w="20px" h="20px" borderRadius="full" align="center" justify="center" bg="#10b98120">
                  <Icon as={FiCheck} boxSize={3} color="#10b981" />
                </Flex>
                <Text fontSize="sm" color="whiteAlpha.700">{feature}</Text>
              </HStack>
            ))}
          </VStack>
        </Box>
      </Box>
    </AdminLayout>
  );
}

export default AdminPlanosPage;
