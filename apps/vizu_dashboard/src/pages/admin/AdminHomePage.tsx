import { 
  Box, 
  VStack, 
  HStack, 
  Text, 
  Avatar, 
  Icon,
  SimpleGrid,
  Flex,
  Link
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { FiDatabase, FiUsers, FiExternalLink } from 'react-icons/fi';

// Card component for plan info
interface InfoCardProps {
  title: string;
  description: string;
  items: {
    icon: React.ElementType;
    title: string;
    subtitle: string;
  }[];
  linkText: string;
  linkHref: string;
  image?: React.ReactNode;
}

const InfoCard = ({ title, description, items, linkText, linkHref, image }: InfoCardProps) => {
  return (
    <Box
      bg="white"
      borderRadius="22px"
      border="1px solid"
      borderColor="gray.200"
      p={6}
      h="310px"
      position="relative"
    >
      <VStack align="start" spacing={3}>
        <Text 
          fontSize="16px" 
          fontWeight="normal" 
          color="gray.900"
          letterSpacing="-0.3px"
        >
          {title}
        </Text>
        
        <Text 
          fontSize="14px" 
          color="gray.500" 
          lineHeight="20px"
          letterSpacing="-0.15px"
        >
          {description}
        </Text>
        
        <VStack align="start" spacing={4} mt={4} w="full">
          {items.map((item, index) => (
            <HStack key={index} spacing={4} w="full" borderTop={index > 0 ? "1px solid" : "none"} borderColor="gray.200" pt={index > 0 ? 4 : 0}>
              <Flex
                w="40px"
                h="40px"
                align="center"
                justify="center"
              >
                <Icon as={item.icon} boxSize={6} color="gray.600" />
              </Flex>
              <VStack align="start" spacing={0}>
                <Text fontSize="14px" fontWeight="normal" color="gray.900" letterSpacing="-0.15px">
                  {item.title}
                </Text>
                <Text fontSize="12px" color="gray.500">
                  {item.subtitle}
                </Text>
              </VStack>
            </HStack>
          ))}
        </VStack>
        
        <Link 
          href={linkHref} 
          color="blue.600" 
          fontSize="14px" 
          mt="auto"
          display="flex"
          alignItems="center"
          gap={1}
        >
          {linkText}
          <Icon as={FiExternalLink} boxSize={3} />
        </Link>
      </VStack>
      
      {image && (
        <Box position="absolute" right={4} bottom={4}>
          {image}
        </Box>
      )}
    </Box>
  );
};

function AdminHomePage() {
  // TODO: Get user name from auth context
  const userName = "Fábio S.";
  const userInitials = "FB";

  return (
    <AdminLayout>
      <Box p={8} maxW="900px" mx="auto">
        {/* Welcome Section */}
        <VStack spacing={6} mb={12}>
          {/* Avatar */}
          <Avatar 
            size="xl"
            name={userName}
            bg="black"
            color="white"
            fontSize="18px"
          >
            <Text fontSize="18px" fontWeight="normal">{userInitials}</Text>
          </Avatar>
          
          {/* Welcome Text */}
          <Text 
            fontSize="34px" 
            fontWeight="normal" 
            color="gray.900"
            letterSpacing="-0.3px"
            textAlign="center"
          >
            Bem-vindo, {userName}
          </Text>
          
          <Text 
            fontSize="16px" 
            color="black" 
            textAlign="center"
            maxW="413px"
            lineHeight="24px"
            letterSpacing="-0.3px"
          >
            Gerencia suas informações, privacidade e segurança para que a VIZU atenda suas necessidades.
          </Text>
        </VStack>
        
        {/* Cards Grid */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          <InfoCard
            title="MEU PLANO"
            description="Com seu plano VIZUXX, você tem mais mais conectores de dados disponíveis, acesso a um agente e muito mais"
            items={[
              {
                icon: FiDatabase,
                title: "8 fontes de dados conectadas",
                subtitle: "Uso: 12,96 GB de 2 TB"
              },
              {
                icon: FiUsers,
                title: "Agente especialista contratado",
                subtitle: "Potencialize sua jornada com o agente VIZU"
              }
            ]}
            linkText="Ver detalhes do plano"
            linkHref="/dashboard/admin/planos"
          />
          
          <InfoCard
            title="Privacidade e personalização"
            description="Veja os termos de privacidade e segurança referentes ao seu plano VIZUXX"
            items={[]}
            linkText="Gerenciar privacidade e personalização"
            linkHref="/dashboard/admin/privacidade"
          />
        </SimpleGrid>
      </Box>
    </AdminLayout>
  );
}

export default AdminHomePage;
