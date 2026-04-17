import { useState, useMemo } from 'react';
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
  Spinner,
  Progress,
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import {
  FiSearch,
  FiPlus,
  FiDatabase,
  FiShoppingCart,
  FiFileText,
  FiCheck,
  FiClock,
  FiAlertCircle,
  FiZap,
} from 'react-icons/fi';
import {
  SiShopify,
  SiGooglebigquery,
  SiPostgresql,
  SiMysql,
} from 'react-icons/si';
import ConnectorModal from '../../components/admin/ConnectorModal';
import { useConnectorStatus } from '../../hooks/useConnectorStatus';
import type { ConnectorStatusResponse } from '../../services/connectorStatusService';

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

interface ConnectorMetadata {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  category: ConnectorCategory;
  isNew?: boolean;
  comingSoon?: boolean;
}

const CONNECTOR_METADATA: Record<string, ConnectorMetadata> = {
  BIGQUERY: {
    id: 'bigquery',
    name: 'Google BigQuery',
    description: 'Data Warehouse para análises avançadas',
    icon: SiGooglebigquery,
    iconColor: '#4285F4',
    category: 'database',
  },
  SHOPIFY: {
    id: 'shopify',
    name: 'Shopify',
    description: 'Produtos, pedidos e clientes',
    icon: SiShopify,
    iconColor: '#96BF48',
    category: 'ecommerce',
    isNew: true,
  },
  VTEX: {
    id: 'vtex',
    name: 'VTEX',
    description: 'Dados de vendas e catálogo',
    icon: FiShoppingCart,
    iconColor: '#F71963',
    category: 'ecommerce',
    isNew: true,
  },
  LOJA_INTEGRADA: {
    id: 'loja_integrada',
    name: 'Loja Integrada',
    description: 'Análise completa de vendas',
    icon: FiShoppingCart,
    iconColor: '#00A650',
    category: 'ecommerce',
    isNew: true,
  },
  POSTGRES: {
    id: 'postgresql',
    name: 'PostgreSQL',
    description: 'Dados transacionais SQL',
    icon: SiPostgresql,
    iconColor: '#336791',
    category: 'database',
  },
  MYSQL: {
    id: 'mysql',
    name: 'MySQL',
    description: 'Bancos MySQL ou MariaDB',
    icon: SiMysql,
    iconColor: '#4479A1',
    category: 'database',
  },
  CSV_UPLOAD: {
    id: 'csv_upload',
    name: 'Upload CSV/Excel',
    description: 'Arquivos para análise rápida',
    icon: FiFileText,
    iconColor: '#10B981',
    category: 'files',
  },
  DEFAULT: {
    id: 'unknown',
    name: 'Conector',
    description: 'Fonte de dados',
    icon: FiDatabase,
    iconColor: '#6366F1',
    category: 'database',
  },
};

function mapConnectorToUI(backend: ConnectorStatusResponse): ConnectorConfig {
  const meta = CONNECTOR_METADATA[backend.tipo_servico] || CONNECTOR_METADATA.DEFAULT;
  let uiStatus: ConnectionStatus;
  switch (backend.status) {
    case 'active':
      uiStatus = 'connected';
      break;
    case 'error':
      uiStatus = 'error';
      break;
    case 'pending':
      uiStatus = 'pending';
      break;
    default:
      uiStatus = 'not_configured';
  }
  return {
    ...meta,
    name: backend.nome_servico || meta.name,
    status: uiStatus,
    lastSync: backend.last_sync_at || undefined,
    recordsCount: backend.records_count || undefined,
  };
}

// --- Figma-style Connector Card ---
const ConnectorCard = ({
  connector,
  onConnect,
}: {
  connector: ConnectorConfig;
  onConnect: (c: ConnectorConfig) => void;
}) => {
  const statusColor: Record<ConnectionStatus, string> = {
    connected: 'green',
    pending: 'yellow',
    error: 'red',
    not_configured: 'gray',
  };

  const statusIcon: Record<ConnectionStatus, React.ElementType> = {
    connected: FiCheck,
    pending: FiClock,
    error: FiAlertCircle,
    not_configured: FiPlus,
  };

  const statusLabel: Record<ConnectionStatus, string> = {
    connected: 'Conectado',
    pending: 'Sincronizando',
    error: 'Erro',
    not_configured: 'Disponível',
  };

  return (
    <Box
      bg="white"
      borderRadius="20px"
      border="1px solid"
      borderColor={connector.status === 'connected' ? `${statusColor[connector.status]}.200` : 'gray.100'}
      p={0}
      overflow="hidden"
      transition="all 0.25s ease"
      _hover={{
        shadow: 'lg',
        transform: 'translateY(-3px)',
        borderColor: connector.iconColor,
      }}
      opacity={connector.comingSoon ? 0.5 : 1}
      cursor={connector.comingSoon ? 'default' : 'pointer'}
      onClick={() => !connector.comingSoon && onConnect(connector)}
    >
      {/* Color accent bar */}
      <Box h="4px" bg={connector.iconColor} />

      <Box p={5}>
        <Flex justify="space-between" align="flex-start" mb={4}>
          <Flex
            w="44px"
            h="44px"
            bg={`${connector.iconColor}15`}
            borderRadius="12px"
            align="center"
            justify="center"
          >
            <Icon as={connector.icon} boxSize={5} color={connector.iconColor} />
          </Flex>
          <HStack spacing={1}>
            {connector.isNew && (
              <Badge
                bg="purple.50"
                color="purple.600"
                fontSize="10px"
                borderRadius="full"
                px={2}
              >
                NOVO
              </Badge>
            )}
            {connector.comingSoon && (
              <Badge
                bg="gray.100"
                color="gray.500"
                fontSize="10px"
                borderRadius="full"
                px={2}
              >
                EM BREVE
              </Badge>
            )}
            <Badge
              bg={`${statusColor[connector.status]}.50`}
              color={`${statusColor[connector.status]}.600`}
              fontSize="10px"
              borderRadius="full"
              px={2}
              display="flex"
              alignItems="center"
              gap={1}
            >
              <Icon as={statusIcon[connector.status]} boxSize={2.5} />
              {statusLabel[connector.status]}
            </Badge>
          </HStack>
        </Flex>

        <Text fontSize="15px" fontWeight="600" color="gray.900" mb={1}>
          {connector.name}
        </Text>
        <Text fontSize="12px" color="gray.500" lineHeight="1.4" mb={4}>
          {connector.description}
        </Text>

        {/* Sync stats */}
        {connector.status === 'connected' && (
          <HStack spacing={4} mb={3} fontSize="12px">
            {connector.recordsCount != null && (
              <VStack align="start" spacing={0}>
                <Text color="gray.400">Registros</Text>
                <Text fontWeight="600" color="gray.700">
                  {connector.recordsCount.toLocaleString('pt-BR')}
                </Text>
              </VStack>
            )}
            {connector.lastSync && (
              <VStack align="start" spacing={0}>
                <Text color="gray.400">Última sync</Text>
                <Text fontWeight="600" color="gray.700">
                  {new Date(connector.lastSync).toLocaleDateString('pt-BR')}
                </Text>
              </VStack>
            )}
          </HStack>
        )}

        {connector.status === 'pending' && (
          <Progress
            size="xs"
            isIndeterminate
            colorScheme="blue"
            borderRadius="full"
            mb={3}
          />
        )}
      </Box>
    </Box>
  );
};

// --- Main Page ---
function AdminConnectorsPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<ConnectorCategory>('all');
  const [selectedConnector, setSelectedConnector] = useState<ConnectorConfig | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

  const { connectors: connectorsData, loading, error } = useConnectorStatus();

  const allConnectors: ConnectorConfig[] = useMemo(() => {
    const available: ConnectorConfig[] = Object.values(CONNECTOR_METADATA)
      .filter(m => m.id !== 'unknown')
      .map(m => ({ ...m, status: 'not_configured' as ConnectionStatus }));

    if (connectorsData?.connectors.length) {
      const backendMap = new Map(
        connectorsData.connectors.map(bc => [bc.tipo_servico.toLowerCase(), bc])
      );
      return available.map(ac => {
        const bc = backendMap.get(ac.id);
        return bc ? mapConnectorToUI(bc) : ac;
      });
    }

    return available;
  }, [connectorsData]);

  const filteredConnectors = allConnectors.filter(c => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const connectedCount = allConnectors.filter(c => c.status === 'connected').length;
  const totalCount = allConnectors.length;

  const handleConnect = (connector: ConnectorConfig) => {
    setSelectedConnector(connector);
    onOpen();
  };

  const categories = [
    { id: 'all', label: 'Todos', count: totalCount },
    { id: 'ecommerce', label: 'E-commerce', count: allConnectors.filter(c => c.category === 'ecommerce').length },
    { id: 'database', label: 'Bancos', count: allConnectors.filter(c => c.category === 'database').length },
    { id: 'files', label: 'Arquivos', count: allConnectors.filter(c => c.category === 'files').length },
    { id: 'api', label: 'APIs', count: allConnectors.filter(c => c.category === 'api').length },
  ];

  if (loading) {
    return (
      <AdminLayout>
        <Flex justify="center" align="center" h="60vh">
          <Spinner size="xl" />
        </Flex>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <Flex direction="column" align="center" justify="center" h="60vh" gap={3}>
          <Icon as={FiAlertCircle} boxSize={12} color="red.400" />
          <Text fontSize="lg" color="gray.700">Erro ao carregar conectores</Text>
          <Text fontSize="sm" color="gray.500">{error.message}</Text>
        </Flex>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <Box p={{ base: 4, md: 8 }} maxW="1100px" mx="auto">
        {/* Header with status summary */}
        <Flex
          justify="space-between"
          align="center"
          mb={8}
          direction={{ base: 'column', md: 'row' }}
          gap={4}
        >
          <VStack align="start" spacing={1}>
            <HStack spacing={2}>
              <Icon as={FiZap} boxSize={5} color="purple.500" />
              <Text fontSize="22px" fontWeight="700" color="gray.900">
                Conectores
              </Text>
            </HStack>
            <Text fontSize="13px" color="gray.500">
              {connectedCount > 0
                ? `${connectedCount} de ${totalCount} fontes conectadas`
                : 'Conecte suas fontes de dados para começar'}
            </Text>
          </VStack>

          {/* Connection health bar */}
          {connectedCount > 0 && (
            <HStack
              bg="green.50"
              px={4}
              py={2}
              borderRadius="full"
              spacing={2}
            >
              <Icon as={FiCheck} color="green.500" boxSize={4} />
              <Text fontSize="13px" fontWeight="600" color="green.700">
                {connectedCount} ativas
              </Text>
            </HStack>
          )}
        </Flex>

        {/* Search and category filters */}
        <Flex
          mb={6}
          gap={4}
          direction={{ base: 'column', md: 'row' }}
          align={{ base: 'stretch', md: 'center' }}
        >
          <InputGroup maxW={{ base: '100%', md: '280px' }}>
            <InputLeftElement pointerEvents="none">
              <Icon as={FiSearch} color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Buscar..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              borderRadius="full"
              bg="white"
              border="1px solid"
              borderColor="gray.200"
              fontSize="14px"
              _focus={{ borderColor: 'purple.400', shadow: '0 0 0 1px var(--chakra-colors-purple-400)' }}
            />
          </InputGroup>

          <Tabs
            variant="soft-rounded"
            size="sm"
            index={categories.findIndex(c => c.id === selectedCategory)}
            onChange={i => setSelectedCategory(categories[i].id as ConnectorCategory)}
          >
            <TabList flexWrap="wrap" gap={1}>
              {categories.map(cat => (
                <Tab
                  key={cat.id}
                  fontSize="12px"
                  fontWeight="500"
                  px={3}
                  py={1.5}
                  borderRadius="full"
                  color="gray.600"
                  _selected={{ bg: 'gray.900', color: 'white' }}
                >
                  {cat.label}
                  <Text as="span" ml={1} opacity={0.6}>
                    {cat.count}
                  </Text>
                </Tab>
              ))}
            </TabList>
          </Tabs>
        </Flex>

        {/* Connector grid */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {filteredConnectors.map(connector => (
            <ConnectorCard
              key={connector.id}
              connector={connector}
              onConnect={handleConnect}
            />
          ))}
        </SimpleGrid>

        {/* Empty state */}
        {filteredConnectors.length === 0 && (
          <Flex
            direction="column"
            align="center"
            justify="center"
            py={16}
            bg="gray.50"
            borderRadius="20px"
          >
            <Icon as={FiSearch} boxSize={8} color="gray.300" mb={3} />
            <Text fontSize="15px" color="gray.500" fontWeight="500">
              Nenhum conector encontrado
            </Text>
            <Text fontSize="13px" color="gray.400">
              Ajuste sua busca ou filtros
            </Text>
          </Flex>
        )}
      </Box>

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

export default AdminConnectorsPage;
