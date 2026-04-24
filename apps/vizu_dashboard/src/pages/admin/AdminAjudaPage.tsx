import { Box, VStack, HStack, Text, Icon, Flex, SimpleGrid, Button } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiHelpCircle, FiBook, FiMessageCircle, FiVideo, FiArrowRight, FiMail } from 'react-icons/fi';

function AdminAjudaPage() {
  const helpCategories = [
    {
      icon: FiBook,
      title: 'Documentação',
      description: 'Guias detalhados sobre como configurar e usar cada recurso da plataforma.',
      color: '#3b82f6',
      items: [
        { title: 'Primeiros passos', subtitle: 'Configure sua conta e conecte seus dados' },
        { title: 'Conectores de dados', subtitle: 'Como integrar suas fontes de dados' },
        { title: 'Agente de IA', subtitle: 'Personalize e otimize seu agente' },
      ],
    },
    {
      icon: FiVideo,
      title: 'Tutoriais em Vídeo',
      description: 'Aprenda visualmente com nossos tutoriais passo a passo.',
      color: '#a855f7',
      items: [
        { title: 'Tour pela plataforma', subtitle: 'Visão geral em 5 minutos' },
        { title: 'Configurando conectores', subtitle: 'BigQuery, Shopify, VTEX e mais' },
        { title: 'Base de conhecimento', subtitle: 'Upload e gestão de documentos' },
      ],
    },
    {
      icon: FiMessageCircle,
      title: 'Suporte',
      description: 'Fale diretamente com nosso time de suporte técnico.',
      color: '#10b981',
      items: [
        { title: 'Chat ao vivo', subtitle: 'Disponível em horário comercial' },
        { title: 'E-mail', subtitle: 'Resposta em até 24 horas' },
      ],
    },
  ];

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack spacing={2} mb={8} align="start">
          <Flex w="48px" h="48px" borderRadius="12px" align="center" justify="center" bg="#3b82f620" mb={2}>
            <Icon as={FiHelpCircle} boxSize={6} color="#3b82f6" />
          </Flex>
          <Text fontSize="24px" fontWeight="semibold" color="white" letterSpacing="-0.3px">
            Central de Ajuda
          </Text>
          <Text fontSize="14px" color="whiteAlpha.600" lineHeight="20px">
            Encontre respostas para suas dúvidas, tutoriais e canais de suporte.
          </Text>
        </VStack>

        <SimpleGrid columns={{ base: 1, md: 1 }} spacing={6}>
          {helpCategories.map((category) => (
            <Box
              key={category.title}
              bg="#1a1b2e"
              borderRadius="1rem"
              border="1px solid"
              borderColor="rgba(255,255,255,0.08)"
              p={6}
              position="relative"
              overflow="hidden"
              transition="all 0.2s"
              _hover={{ borderColor: 'rgba(255,255,255,0.15)' }}
            >
              <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={category.color} />
              <HStack spacing={4} mb={4}>
                <Flex w="40px" h="40px" borderRadius="lg" align="center" justify="center" bg={`${category.color}20`}>
                  <Icon as={category.icon} boxSize={5} color={category.color} />
                </Flex>
                <VStack align="start" spacing={0}>
                  <Text fontSize="sm" fontWeight="semibold" color="white">{category.title}</Text>
                  <Text fontSize="xs" color="whiteAlpha.500">{category.description}</Text>
                </VStack>
              </HStack>
              <VStack align="start" spacing={3} pl={14}>
                {category.items.map((item) => (
                  <HStack key={item.title} spacing={3} w="full" cursor="pointer" _hover={{ '& > p:first-of-type': { color: 'white' } }}>
                    <VStack align="start" spacing={0}>
                      <Text fontSize="sm" fontWeight="medium" color="whiteAlpha.800" transition="color 0.2s">{item.title}</Text>
                      <Text fontSize="xs" color="whiteAlpha.500">{item.subtitle}</Text>
                    </VStack>
                  </HStack>
                ))}
              </VStack>
            </Box>
          ))}
        </SimpleGrid>

        <Box
          mt={6}
          bg="#1a1b2e"
          borderRadius="1rem"
          border="1px solid rgba(255,255,255,0.08)"
          p={6}
          textAlign="center"
        >
          <Icon as={FiMail} boxSize={6} color="#3b82f6" mb={3} />
          <Text fontSize="sm" fontWeight="medium" color="white" mb={1}>Precisa de mais ajuda?</Text>
          <Text fontSize="xs" color="whiteAlpha.500" mb={4}>Nossa equipe está pronta para ajudar.</Text>
          <Button
            size="sm"
            bgGradient="linear(to-r, #3b82f6, #2563eb)"
            color="white"
            borderRadius="full"
            px={6}
            fontWeight={600}
            _hover={{ bgGradient: 'linear(to-r, #2563eb, #1d4ed8)' }}
            rightIcon={<FiArrowRight />}
          >
            Falar com suporte
          </Button>
        </Box>
      </Box>
    </AdminLayout>
  );
}

export default AdminAjudaPage;
