import {
  Box,
  VStack,
  HStack,
  Text,
  Avatar,
  Icon,
  SimpleGrid,
  Flex,
  Spinner,
  Button
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiDatabase, FiUsers, FiAlertCircle, FiSettings, FiChevronRight, FiShield, FiCpu, FiArrowRight } from 'react-icons/fi';
import { useContext } from 'react';
import { AuthContext } from '../../contexts/AuthContext';
import { useDashboardStats } from '../../hooks/useDashboardStats';
import { useNavigate } from 'react-router-dom';

// Card component for plan info
interface InfoCardProps {
  title: string;
  description: string;
  items: {
    icon: React.ElementType;
    title: string;
    subtitle: string;
    color: string;
  }[];
  linkText: string;
  linkHref: string;
  accentColor: string;
}

const InfoCard = ({ title, description, items, linkText, linkHref, accentColor }: InfoCardProps) => {
  const navigate = useNavigate();
  return (
    <Box
      bg="#1a1b2e"
      borderRadius="1rem"
      border="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      boxShadow="0 4px 24px rgba(0,0,0,0.4)"
      p={6}
      position="relative"
      overflow="hidden"
      transition="all 0.2s"
      _hover={{ borderColor: 'rgba(255,255,255,0.15)', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}
    >
      <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={accentColor} />
      <VStack align="start" spacing={3}>
        <Text
          fontSize="xs"
          fontWeight="semibold"
          textTransform="uppercase"
          letterSpacing="wider"
          color={accentColor}
        >
          {title}
        </Text>

        <Text
          fontSize="sm"
          color="whiteAlpha.600"
          lineHeight="20px"
        >
          {description}
        </Text>

        <VStack align="start" spacing={4} mt={2} w="full">
          {items.map((item, index) => (
            <HStack key={index} spacing={4} w="full" borderTop={index > 0 ? "1px solid" : "none"} borderColor="whiteAlpha.100" pt={index > 0 ? 4 : 0}>
              <Flex
                w="40px"
                h="40px"
                align="center"
                justify="center"
                borderRadius="lg"
                bg={`${item.color}20`}
              >
                <Icon as={item.icon} boxSize={5} color={item.color} />
              </Flex>
              <VStack align="start" spacing={0}>
                <Text fontSize="sm" fontWeight="medium" color="white">
                  {item.title}
                </Text>
                <Text fontSize="xs" color="whiteAlpha.500">
                  {item.subtitle}
                </Text>
              </VStack>
            </HStack>
          ))}
        </VStack>

        <Button
          variant="ghost"
          size="sm"
          color={accentColor}
          rightIcon={<FiArrowRight />}
          _hover={{ bg: `${accentColor}15` }}
          mt={2}
          onClick={() => navigate(linkHref)}
        >
          {linkText}
        </Button>
      </VStack>
    </Box>
  );
};

function AdminHomePage() {
  const auth = useContext(AuthContext);
  const { stats, loading, error } = useDashboardStats();
  const navigate = useNavigate();

  const userName = auth?.user?.user_metadata?.full_name ||
    auth?.user?.email?.split('@')[0] ||
    'Usuário';

  const formatStorage = (gb: number): string => {
    if (gb < 1) return `${(gb * 1024).toFixed(2)} MB`;
    return `${gb.toFixed(2)} GB`;
  };

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        {/* Welcome Section */}
        <VStack spacing={6} mb={12}>
          <Avatar
            size="xl"
            name={userName}
            bg="linear-gradient(135deg, #3b82f6, #a855f7)"
            color="white"
            fontSize="18px"
          />

          <Text
            fontSize="2.5rem"
            fontWeight="normal"
            fontFamily="'Playfair Display', serif"
            textAlign="center"
          >
            <Box as="span" color="white">Bem-vindo, </Box>
            <Box as="span" bgGradient="linear(to-r, #3b82f6, #a855f7)" bgClip="text">{userName}</Box>
          </Text>

          <Text
            fontSize="md"
            color="whiteAlpha.600"
            textAlign="center"
            maxW="450px"
            lineHeight="24px"
          >
            Gerencie suas informações, privacidade e segurança para que a Blu atenda suas necessidades.
          </Text>
        </VStack>

        {/* Stats Summary Bar */}
        {stats && (
          <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4} mb={8}>
            {[
              { label: 'Conectores', value: stats.connected_connectors, color: '#3b82f6', icon: FiDatabase },
              { label: 'Armazenamento', value: formatStorage(stats.storage_usage.total_storage_gb), color: '#10b981', icon: FiCpu },
              { label: 'Agentes', value: '1', color: '#a855f7', icon: FiUsers },
              { label: 'Segurança', value: 'Ativo', color: '#10b981', icon: FiShield },
            ].map((stat) => (
              <Box
                key={stat.label}
                bg="#1a1b2e"
                borderRadius="lg"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                p={4}
                textAlign="center"
              >
                <Flex justify="center" mb={2}>
                  <Flex w={10} h={10} borderRadius="lg" align="center" justify="center" bg={`${stat.color}20`}>
                    <Icon as={stat.icon} boxSize={5} color={stat.color} />
                  </Flex>
                </Flex>
                <Text fontSize="lg" fontWeight="bold" color="white">{stat.value}</Text>
                <Text fontSize="xs" color="whiteAlpha.500">{stat.label}</Text>
              </Box>
            ))}
          </SimpleGrid>
        )}

        {/* Cards Grid */}
        {loading ? (
          <Box textAlign="center" py={12}>
            <Spinner size="xl" color="blue.400" />
            <Text mt={4} color="whiteAlpha.600">Carregando estatísticas...</Text>
          </Box>
        ) : error ? (
          <Box textAlign="center" py={12}>
            <Icon as={FiAlertCircle} boxSize={10} color="red.400" mb={4} />
            <Text fontSize="md" color="whiteAlpha.800">Erro ao carregar estatísticas</Text>
          </Box>
        ) : stats ? (
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
            <InfoCard
              title="MEU PLANO"
              description="Com seu plano premium, você tem mais conectores de dados disponíveis, acesso a um agente e muito mais"
              accentColor="#3b82f6"
              items={[
                {
                  icon: FiDatabase,
                  title: `${stats.connected_connectors} fontes de dados conectadas`,
                  subtitle: `Uso: ${formatStorage(stats.storage_usage.total_storage_gb)} de ${stats.storage_usage.quota_gb || 2000} GB`,
                  color: '#3b82f6'
                },
                {
                  icon: FiUsers,
                  title: "Agente especialista contratado",
                  subtitle: "Potencialize sua jornada com o agente Blu",
                  color: '#a855f7'
                }
              ]}
              linkText="Ver detalhes do plano"
              linkHref="/dashboard/admin/planos"
            />

            <InfoCard
              title="Privacidade e personalização"
              description="Veja os termos de privacidade e segurança referentes ao seu plano"
              accentColor="#10b981"
              items={[]}
              linkText="Gerenciar privacidade"
              linkHref="/dashboard/admin/privacidade"
            />

            <InfoCard
              title="Personalizar Agente"
              description="Configure o perfil da empresa, equipe, prioridades e políticas para que o agente responda de forma personalizada"
              accentColor="#a855f7"
              items={[
                {
                  icon: FiSettings,
                  title: "Contexto do agente",
                  subtitle: "Perfil, equipe, momento atual e regras",
                  color: '#a855f7'
                }
              ]}
              linkText="Configurar agente"
              linkHref="/dashboard/admin/onboarding"
            />
          </SimpleGrid>
        ) : null}
      </Box>
    </AdminLayout>
  );
}

export default AdminHomePage;
