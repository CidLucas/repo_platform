import { Box, VStack, HStack, Text, Icon, Flex, Switch, Badge } from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiShield, FiLock, FiEye, FiTrash2, FiDownload, FiAlertTriangle } from 'react-icons/fi';

function AdminPrivacidadePage() {
  const privacySettings = [
    {
      icon: FiLock,
      title: 'Criptografia de dados',
      description: 'Todos os dados são criptografados em trânsito e em repouso usando AES-256.',
      color: '#10b981',
      status: 'Ativo',
      isToggle: false,
    },
    {
      icon: FiEye,
      title: 'Histórico de conversas',
      description: 'Armazene o histórico de interações com o agente para melhorar respostas futuras.',
      color: '#3b82f6',
      isToggle: true,
      defaultOn: true,
    },
    {
      icon: FiDownload,
      title: 'Exportação de dados',
      description: 'Solicite uma cópia completa de todos os seus dados armazenados na plataforma.',
      color: '#a855f7',
      isToggle: false,
      action: 'Solicitar exportação',
    },
    {
      icon: FiTrash2,
      title: 'Exclusão de dados',
      description: 'Solicite a exclusão permanente de todos os seus dados. Esta ação é irreversível.',
      color: '#ef4444',
      isToggle: false,
      action: 'Solicitar exclusão',
    },
  ];

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        <VStack spacing={2} mb={8} align="start">
          <Flex w="48px" h="48px" borderRadius="12px" align="center" justify="center" bg="#10b98120" mb={2}>
            <Icon as={FiShield} boxSize={6} color="#10b981" />
          </Flex>
          <Text fontSize="24px" fontWeight="semibold" color="white" letterSpacing="-0.3px">
            Dados e Privacidade
          </Text>
          <Text fontSize="14px" color="whiteAlpha.600" lineHeight="20px">
            Gerencie suas configurações de privacidade, segurança e controle de dados.
          </Text>
        </VStack>

        {/* Security Status */}
        <Box
          bg="#1a1b2e"
          borderRadius="1rem"
          border="1px solid rgba(255,255,255,0.08)"
          p={6}
          mb={6}
          position="relative"
          overflow="hidden"
        >
          <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#10b981" />
          <HStack spacing={4}>
            <Flex w="48px" h="48px" borderRadius="12px" align="center" justify="center" bg="#10b98120">
              <Icon as={FiShield} boxSize={6} color="#10b981" />
            </Flex>
            <VStack align="start" spacing={0} flex={1}>
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="semibold" color="white">Status de Segurança</Text>
                <Badge bg="#10b98120" color="#10b981" fontSize="xs" borderRadius="full" px={2}>Protegido</Badge>
              </HStack>
              <Text fontSize="xs" color="whiteAlpha.500">Seus dados estão protegidos com criptografia de ponta a ponta.</Text>
            </VStack>
          </HStack>
        </Box>

        {/* Privacy Settings */}
        <VStack spacing={4}>
          {privacySettings.map((setting) => (
            <Box
              key={setting.title}
              bg="#1a1b2e"
              borderRadius="1rem"
              border="1px solid rgba(255,255,255,0.08)"
              p={6}
              w="full"
              transition="all 0.2s"
              _hover={{ borderColor: 'rgba(255,255,255,0.15)' }}
            >
              <HStack spacing={4} justify="space-between">
                <HStack spacing={4} flex={1}>
                  <Flex w="40px" h="40px" borderRadius="lg" align="center" justify="center" bg={`${setting.color}20`} flexShrink={0}>
                    <Icon as={setting.icon} boxSize={5} color={setting.color} />
                  </Flex>
                  <VStack align="start" spacing={1}>
                    <Text fontSize="sm" fontWeight="medium" color="white">{setting.title}</Text>
                    <Text fontSize="xs" color="whiteAlpha.500" lineHeight="16px">{setting.description}</Text>
                  </VStack>
                </HStack>
                {setting.isToggle ? (
                  <Switch defaultChecked={setting.defaultOn} colorScheme="green" size="md" />
                ) : setting.status ? (
                  <Badge bg={`${setting.color}20`} color={setting.color} fontSize="xs" borderRadius="full" px={3} py={1}>
                    {setting.status}
                  </Badge>
                ) : null}
              </HStack>
            </Box>
          ))}
        </VStack>

        {/* LGPD Notice */}
        <Box
          mt={6}
          bg="rgba(234,179,8,0.08)"
          borderRadius="1rem"
          border="1px solid rgba(234,179,8,0.15)"
          p={5}
        >
          <HStack spacing={3} align="start">
            <Icon as={FiAlertTriangle} boxSize={5} color="#eab308" mt={0.5} />
            <VStack align="start" spacing={1}>
              <Text fontSize="sm" fontWeight="medium" color="#eab308">Conformidade LGPD</Text>
              <Text fontSize="xs" color="whiteAlpha.500" lineHeight="18px">
                A Blu está em conformidade com a Lei Geral de Proteção de Dados (LGPD).
                Seus dados são processados de acordo com nossa política de privacidade e você pode
                solicitar acesso, correção ou exclusão a qualquer momento.
              </Text>
            </VStack>
          </HStack>
        </Box>
      </Box>
    </AdminLayout>
  );
}

export default AdminPrivacidadePage;
