// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx
import { useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Text,
  SimpleGrid,
  Icon,
  Badge,
  Button,
  Input,
  InputGroup,
  InputLeftElement,
  Tabs,
  TabList,
  Tab,
  Flex,
  useDisclosure,
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { 
  FiSearch, 
  FiPlus, 
  FiDatabase, 
  FiShoppingCart,
  FiCloud,
  FiFileText,
  FiCheck,
  FiClock,
  FiAlertCircle
} from 'react-icons/fi';
import { 
  SiShopify, 
  SiGooglebigquery, 
  SiPostgresql, 
  SiMysql, 
  SiRedis,
  SiMongodb
} from 'react-icons/si';
import ConnectorModal from '../../components/admin/ConnectorModal';

// Tipos
type ConnectorCategory = 'all' | 'ecommerce' | 'database' | 'files' | 'api';
type ConnectionStatus = 'connected' | 'pending' | 'error' | 'not_configured';

interface ConnectorConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  category: ConnectorCategory;
  status: ConnectionStatus;
  lastSync?: string;
  recordsCount?: number;
  isNew?: boolean;
  comingSoon?: boolean;
}

// Configuração dos conectores disponíveis
const CONNECTORS: ConnectorConfig[] = [
  // E-commerce
  {
    id: 'shopify',
    name: 'Shopify',
    description: 'Sincronize produtos, pedidos e clientes da sua loja Shopify',
    icon: SiShopify,
    iconColor: '#96BF48',
    category: 'ecommerce',
    status: 'not_configured',
    isNew: true,
  },
  {
    id: 'vtex',
    name: 'VTEX',
    description: 'Conecte sua loja VTEX e importe todos os dados de vendas',
    icon: FiShoppingCart,
    iconColor: '#F71963',
    category: 'ecommerce',
    status: 'not_configured',
    isNew: true,
  },
  {
    id: 'loja_integrada',
    name: 'Loja Integrada',
    description: 'Integre sua Loja Integrada para análise de vendas completa',
    icon: FiShoppingCart,
    iconColor: '#00A650',
    category: 'ecommerce',
    status: 'not_configured',
    isNew: true,
  },
  // Databases
  {
    id: 'bigquery',
    name: 'Google BigQuery',
    description: 'Conecte seu Data Warehouse BigQuery para análises avançadas',
    icon: SiGooglebigquery,
    iconColor: '#4285F4',
    category: 'database',
    status: 'connected',
    lastSync: '2024-12-09T10:30:00',
    recordsCount: 125430,
  },
  {
    id: 'postgresql',
    name: 'PostgreSQL',
    description: 'Conecte bancos PostgreSQL para importar dados transacionais',
    icon: SiPostgresql,
    iconColor: '#336791',
    category: 'database',
    status: 'not_configured',
  },
  {
    id: 'mysql',
    name: 'MySQL',
    description: 'Importe dados de bancos MySQL ou MariaDB',
    icon: SiMysql,
    iconColor: '#4479A1',
    category: 'database',
    status: 'not_configured',
  },
  {
    id: 'redis',
    name: 'Redis',
    description: 'Conecte ao Redis para dados em tempo real',
    icon: SiRedis,
    iconColor: '#DC382D',
    category: 'database',
    status: 'not_configured',
    comingSoon: true,
  },
  {
    id: 'mongodb',
    name: 'MongoDB',
    description: 'Importe dados de coleções MongoDB',
    icon: SiMongodb,
    iconColor: '#47A248',
    category: 'database',
    status: 'not_configured',
    comingSoon: true,
  },
  // Files
  {
    id: 'csv_upload',
    name: 'Upload CSV/Excel',
    description: 'Faça upload de arquivos CSV ou Excel para análise',
    icon: FiFileText,
    iconColor: '#10B981',
    category: 'files',
    status: 'connected',
    recordsCount: 5420,
  },
  // APIs
  {
    id: 'rest_api',
    name: 'API REST',
    description: 'Conecte qualquer API REST para importação de dados',
    icon: FiCloud,
    iconColor: '#6366F1',
    category: 'api',
    status: 'not_configured',
    comingSoon: true,
  },
];

// Componente de Card do Conector
interface ConnectorCardProps {
  connector: ConnectorConfig;
  onConnect: (connector: ConnectorConfig) => void;
}

const ConnectorCard = ({ connector, onConnect }: ConnectorCardProps) => {
  const getStatusBadge = (status: ConnectionStatus) => {
    switch (status) {
      case 'connected':
        return (
          <Badge colorScheme="green" display="flex" alignItems="center" gap={1}>
            <Icon as={FiCheck} boxSize={3} />
            Conectado
          </Badge>
        );
      case 'pending':
        return (
          <Badge colorScheme="yellow" display="flex" alignItems="center" gap={1}>
            <Icon as={FiClock} boxSize={3} />
            Sincronizando
          </Badge>
        );
      case 'error':
        return (
          <Badge colorScheme="red" display="flex" alignItems="center" gap={1}>
            <Icon as={FiAlertCircle} boxSize={3} />
            Erro
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <Box
      bg="white"
      borderRadius="16px"
      border="1px solid"
      borderColor="gray.200"
      p={5}
      position="relative"
      transition="all 0.2s"
      _hover={{
        borderColor: 'gray.300',
        shadow: 'sm',
      }}
      opacity={connector.comingSoon ? 0.6 : 1}
    >
      {/* Badges */}
      <HStack position="absolute" top={4} right={4} spacing={2}>
        {connector.isNew && (
          <Badge colorScheme="purple" fontSize="10px">
            NOVO
          </Badge>
        )}
        {connector.comingSoon && (
          <Badge colorScheme="gray" fontSize="10px">
            EM BREVE
          </Badge>
        )}
        {getStatusBadge(connector.status)}
      </HStack>

      <VStack align="start" spacing={4}>
        {/* Icon */}
        <Flex
          w="48px"
          h="48px"
          bg="gray.50"
          borderRadius="12px"
          align="center"
          justify="center"
        >
          <Icon 
            as={connector.icon} 
            boxSize={6} 
            color={connector.iconColor}
          />
        </Flex>

        {/* Info */}
        <VStack align="start" spacing={1}>
          <Text fontSize="16px" fontWeight="medium" color="gray.900">
            {connector.name}
          </Text>
          <Text fontSize="13px" color="gray.500" lineHeight="18px">
            {connector.description}
          </Text>
        </VStack>

        {/* Stats (se conectado) */}
        {connector.status === 'connected' && connector.recordsCount && (
          <HStack spacing={4} pt={2}>
            <VStack align="start" spacing={0}>
              <Text fontSize="12px" color="gray.400">
                Registros
              </Text>
              <Text fontSize="14px" fontWeight="medium" color="gray.700">
                {connector.recordsCount.toLocaleString('pt-BR')}
              </Text>
            </VStack>
            {connector.lastSync && (
              <VStack align="start" spacing={0}>
                <Text fontSize="12px" color="gray.400">
                  Última sync
                </Text>
                <Text fontSize="14px" fontWeight="medium" color="gray.700">
                  {new Date(connector.lastSync).toLocaleDateString('pt-BR')}
                </Text>
              </VStack>
            )}
          </HStack>
        )}

        {/* Action Button */}
        <Button
          size="sm"
          variant={connector.status === 'connected' ? 'outline' : 'solid'}
          colorScheme={connector.status === 'connected' ? 'gray' : 'blue'}
          w="full"
          mt={2}
          isDisabled={connector.comingSoon}
          onClick={() => onConnect(connector)}
          leftIcon={connector.status === 'not_configured' ? <FiPlus /> : undefined}
        >
          {connector.status === 'connected' 
            ? 'Gerenciar' 
            : connector.status === 'error'
            ? 'Reconectar'
            : 'Conectar'}
        </Button>
      </VStack>
    </Box>
  );
};

// Página Principal
function AdminFontesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<ConnectorCategory>('all');
  const [selectedConnector, setSelectedConnector] = useState<ConnectorConfig | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Filtra conectores
  const filteredConnectors = CONNECTORS.filter((connector) => {
    const matchesSearch = connector.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         connector.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || connector.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Contadores por categoria
  const connectedCount = CONNECTORS.filter(c => c.status === 'connected').length;
  const totalCount = CONNECTORS.length;

  const handleConnectClick = (connector: ConnectorConfig) => {
    setSelectedConnector(connector);
    onOpen();
  };

  const categories = [
    { id: 'all', label: 'Todos', count: totalCount },
    { id: 'ecommerce', label: 'E-commerce', count: CONNECTORS.filter(c => c.category === 'ecommerce').length },
    { id: 'database', label: 'Bancos de Dados', count: CONNECTORS.filter(c => c.category === 'database').length },
    { id: 'files', label: 'Arquivos', count: CONNECTORS.filter(c => c.category === 'files').length },
    { id: 'api', label: 'APIs', count: CONNECTORS.filter(c => c.category === 'api').length },
  ];

  return (
    <AdminLayout>
      <Box p={8} maxW="1200px" mx="auto">
        {/* Header */}
        <VStack align="start" spacing={2} mb={8}>
          <HStack spacing={3}>
            <Icon as={FiDatabase} boxSize={6} color="gray.700" />
            <Text fontSize="24px" fontWeight="medium" color="gray.900">
              Minhas Fontes de Dados
            </Text>
          </HStack>
          <Text fontSize="14px" color="gray.500">
            Conecte suas fontes de dados para começar a analisar. 
            <Text as="span" fontWeight="medium" color="gray.700">
              {' '}{connectedCount} de {totalCount} conectadas
            </Text>
          </Text>
        </VStack>

        {/* Search and Filters */}
        <HStack mb={6} spacing={4}>
          <InputGroup maxW="320px">
            <InputLeftElement pointerEvents="none">
              <Icon as={FiSearch} color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Buscar conectores..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              borderRadius="full"
              bg="white"
            />
          </InputGroup>

          <Tabs 
            variant="soft-rounded" 
            colorScheme="gray"
            index={categories.findIndex(c => c.id === selectedCategory)}
            onChange={(index) => setSelectedCategory(categories[index].id as ConnectorCategory)}
          >
            <TabList>
              {categories.map((cat) => (
                <Tab 
                  key={cat.id}
                  fontSize="13px"
                  fontWeight="normal"
                  px={4}
                  _selected={{ bg: 'black', color: 'white' }}
                >
                  {cat.label} ({cat.count})
                </Tab>
              ))}
            </TabList>
          </Tabs>
        </HStack>

        {/* Grid de Conectores */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={5}>
          {filteredConnectors.map((connector) => (
            <ConnectorCard 
              key={connector.id} 
              connector={connector}
              onConnect={handleConnectClick}
            />
          ))}
        </SimpleGrid>

        {/* Empty State */}
        {filteredConnectors.length === 0 && (
          <Box 
            textAlign="center" 
            py={16}
            bg="gray.50"
            borderRadius="16px"
          >
            <Icon as={FiSearch} boxSize={10} color="gray.300" mb={4} />
            <Text fontSize="16px" color="gray.500">
              Nenhum conector encontrado
            </Text>
            <Text fontSize="14px" color="gray.400">
              Tente ajustar sua busca ou filtros
            </Text>
          </Box>
        )}
      </Box>

      {/* Modal de Conexão */}
      {selectedConnector && (
        <ConnectorModal
          isOpen={isOpen}
          onClose={onClose}
          connector={selectedConnector}
        />
      )}
    </AdminLayout>
  );
}

export default AdminFontesPage;
