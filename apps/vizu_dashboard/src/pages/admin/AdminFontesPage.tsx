// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx
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
  FiAlertCircle
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

// UI metadata for connector types
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
  'BIGQUERY': {
    id: 'bigquery',
    name: 'Google BigQuery',
    description: 'Conecte seu Data Warehouse BigQuery para análises avançadas',
    icon: SiGooglebigquery,
    iconColor: '#4285F4',
    category: 'database',
  },
  'SHOPIFY': {
    id: 'shopify',
    name: 'Shopify',
    description: 'Sincronize produtos, pedidos e clientes da sua loja Shopify',
    icon: SiShopify,
    iconColor: '#96BF48',
    category: 'ecommerce',
    isNew: true,
  },
  'VTEX': {
    id: 'vtex',
    name: 'VTEX',
    description: 'Conecte sua loja VTEX e importe todos os dados de vendas',
    icon: FiShoppingCart,
    iconColor: '#F71963',
    category: 'ecommerce',
    isNew: true,
  },
  'LOJA_INTEGRADA': {
    id: 'loja_integrada',
    name: 'Loja Integrada',
    description: 'Integre sua Loja Integrada para análise de vendas completa',
    icon: FiShoppingCart,
    iconColor: '#00A650',
    category: 'ecommerce',
    isNew: true,
  },
  'POSTGRES': {
    id: 'postgresql',
    name: 'PostgreSQL',
    description: 'Conecte bancos PostgreSQL para importar dados transacionais',
    icon: SiPostgresql,
    iconColor: '#336791',
    category: 'database',
  },
  'MYSQL': {
    id: 'mysql',
    name: 'MySQL',
    description: 'Importe dados de bancos MySQL ou MariaDB',
    icon: SiMysql,
    iconColor: '#4479A1',
    category: 'database',
  },
  'CSV_UPLOAD': {
    id: 'csv_upload',
    name: 'Upload CSV/Excel',
    description: 'Faça upload de arquivos CSV ou Excel para análise',
    icon: FiFileText,
    iconColor: '#10B981',
    category: 'files',
  },
  'DEFAULT': {
    id: 'unknown',
    name: 'Conector',
    description: 'Fonte de dados conectada',
    icon: FiDatabase,
    iconColor: '#6366F1',
    category: 'database',
  },
};

// Helper function to map backend connector to UI format
function mapConnectorToUI(backendConnector: ConnectorStatusResponse): ConnectorConfig {
  const metadata = CONNECTOR_METADATA[backendConnector.tipo_servico] || CONNECTOR_METADATA['DEFAULT'];

  // Map backend status to UI status
  let uiStatus: ConnectionStatus;
  switch (backendConnector.status) {
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
    ...metadata,
    name: backendConnector.nome_servico || metadata.name,
    status: uiStatus,
    lastSync: backendConnector.last_sync_at || undefined,
    recordsCount: backendConnector.records_count || undefined,
  };
}

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
      bg="#1a1b2e"
      borderRadius="1rem"
      border="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      boxShadow="0 4px 24px rgba(0,0,0,0.4)"
      p={5}
      position="relative"
      transition="all 0.2s"
      _hover={{
        borderColor: 'rgba(255,255,255,0.15)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        transform: 'translateY(-2px)',
      }}
      opacity={connector.comingSoon ? 0.6 : 1}
    >
      {/* Badges */}
      <HStack position="absolute" top={4} right={4} spacing={2}>
        {connector.isNew && (
          <Badge bg="#a855f720" color="#a855f7" fontSize="10px" borderRadius="full" px={2}>
            NOVO
          </Badge>
        )}
        {connector.comingSoon && (
          <Badge bg="whiteAlpha.100" color="whiteAlpha.500" fontSize="10px" borderRadius="full" px={2}>
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
          bg={`${connector.iconColor}20`}
          borderRadius="12px"
          align="center"
          justify="center"
          boxShadow={`0 4px 12px ${connector.iconColor}30`}
        >
          <Icon
            as={connector.icon}
            boxSize={6}
            color={connector.iconColor}
          />
        </Flex>

        {/* Info */}
        <VStack align="start" spacing={1}>
          <Text fontSize="md" fontWeight="medium" color="white">
            {connector.name}
          </Text>
          <Text fontSize="xs" color="whiteAlpha.500" lineHeight="18px">
            {connector.description}
          </Text>
        </VStack>

        {/* Stats (se conectado) */}
        {connector.status === 'connected' && connector.recordsCount && (
          <HStack spacing={4} pt={2}>
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" color="whiteAlpha.400">
                Registros
              </Text>
              <Text fontSize="sm" fontWeight="medium" color="white">
                {connector.recordsCount.toLocaleString('pt-BR')}
              </Text>
            </VStack>
            {connector.lastSync && (
              <VStack align="start" spacing={0}>
                <Text fontSize="xs" color="whiteAlpha.400">
                  Última sync
                </Text>
                <Text fontSize="sm" fontWeight="medium" color="white">
                  {new Date(connector.lastSync).toLocaleDateString('pt-BR')}
                </Text>
              </VStack>
            )}
          </HStack>
        )}

        {/* Action Button */}
        <Button
          size="sm"
          w="full"
          mt={2}
          isDisabled={connector.comingSoon}
          onClick={() => onConnect(connector)}
          leftIcon={connector.status === 'not_configured' ? <FiPlus /> : undefined}
          bgGradient={connector.status === 'connected' ? undefined : 'linear(to-r, #3b82f6, #2563eb)'}
          bg={connector.status === 'connected' ? 'transparent' : undefined}
          color="white"
          border={connector.status === 'connected' ? '1px solid' : 'none'}
          borderColor={connector.status === 'connected' ? 'whiteAlpha.200' : undefined}
          _hover={{
            bgGradient: connector.status === 'connected' ? undefined : 'linear(to-r, #2563eb, #1d4ed8)',
            bg: connector.status === 'connected' ? 'whiteAlpha.100' : undefined,
          }}
          boxShadow={connector.status !== 'connected' ? '0 4px 12px rgba(59,130,246,0.4)' : 'none'}
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

  // Fetch real connector data
  const { connectors: connectorsData, loading, error } = useConnectorStatus();

  // Map backend connectors to UI format and merge with all available connector types
  const allConnectors: ConnectorConfig[] = useMemo(() => {
    // Start with all available connector types from metadata
    const availableConnectorTypes: ConnectorConfig[] = Object.values(CONNECTOR_METADATA)
      .filter(meta => meta.id !== 'unknown') // Exclude DEFAULT/unknown
      .map(meta => ({
        ...meta,
        status: 'not_configured' as ConnectionStatus,
      }));

    // If we have backend data, merge it
    if (connectorsData && connectorsData.connectors.length > 0) {
      const backendConnectorMap = new Map(
        connectorsData.connectors.map(bc => [bc.tipo_servico.toLowerCase(), bc])
      );

      return availableConnectorTypes.map(availableConn => {
        const backendConn = backendConnectorMap.get(availableConn.id);
        if (backendConn) {
          return mapConnectorToUI(backendConn);
        }
        return availableConn;
      });
    }

    // No backend data yet - return all connectors as not_configured
    return availableConnectorTypes;
  }, [connectorsData]);

  // Filtra conectores
  const filteredConnectors = allConnectors.filter((connector) => {
    const matchesSearch = connector.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      connector.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || connector.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Contadores por categoria
  const connectedCount = allConnectors.filter(c => c.status === 'connected').length;
  const totalCount = allConnectors.length;

  const handleConnectClick = (connector: ConnectorConfig) => {
    setSelectedConnector(connector);
    onOpen();
  };

  const categories = [
    { id: 'all', label: 'Todos', count: totalCount },
    { id: 'ecommerce', label: 'E-commerce', count: allConnectors.filter(c => c.category === 'ecommerce').length },
    { id: 'database', label: 'Bancos de Dados', count: allConnectors.filter(c => c.category === 'database').length },
    { id: 'files', label: 'Arquivos', count: allConnectors.filter(c => c.category === 'files').length },
    { id: 'api', label: 'APIs', count: allConnectors.filter(c => c.category === 'api').length },
  ];

  // Loading state (only show spinner if truly loading from API)
  if (loading) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Spinner size="xl" color="blue.400" />
          <Text mt={4} color="whiteAlpha.600">Carregando conectores...</Text>
        </Box>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Icon as={FiAlertCircle} boxSize={12} color="red.400" mb={4} />
          <Text fontSize="18px" color="whiteAlpha.800">Erro ao carregar conectores</Text>
          <Text fontSize="14px" color="whiteAlpha.500" mt={2}>{error.message}</Text>
        </Box>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <Box p={8} maxW="1200px" mx="auto">
        {/* Header */}
        <VStack align="start" spacing={2} mb={8}>
          <HStack spacing={3}>
            <Flex w={10} h={10} borderRadius="lg" align="center" justify="center" bg="#3b82f620">
              <Icon as={FiDatabase} boxSize={5} color="#3b82f6" />
            </Flex>
            <Text
              fontSize="1.5rem"
              fontWeight="normal"
              fontFamily="'Playfair Display', serif"
              color="white"
            >
              Minhas Fontes de Dados
            </Text>
          </HStack>
          <Text fontSize="sm" color="whiteAlpha.500">
            Conecte suas fontes de dados para começar a analisar.
            <Text as="span" fontWeight="medium" color="#3b82f6">
              {' '}{connectedCount} de {totalCount} conectadas
            </Text>
          </Text>
        </VStack>

        {/* Search and Filters */}
        <HStack mb={6} spacing={4}>
          <InputGroup maxW="320px">
            <InputLeftElement pointerEvents="none">
              <Icon as={FiSearch} color="whiteAlpha.400" />
            </InputLeftElement>
            <Input
              placeholder="Buscar conectores..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              borderRadius="full"
              bg="#1a1b2e"
              border="1px solid"
              borderColor="rgba(255,255,255,0.08)"
              color="white"
              _placeholder={{ color: 'whiteAlpha.400' }}
              _hover={{ borderColor: 'rgba(255,255,255,0.15)' }}
              _focus={{ borderColor: '#3b82f6', boxShadow: '0 0 0 1px #3b82f6' }}
            />
          </InputGroup>

          <Tabs
            variant="soft-rounded"
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
                  color="whiteAlpha.600"
                  _selected={{ bg: '#3b82f6', color: 'white' }}
                  _hover={{ color: 'white' }}
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
            bg="#1a1b2e"
            borderRadius="1rem"
            border="1px solid"
            borderColor="rgba(255,255,255,0.08)"
          >
            <Icon as={FiSearch} boxSize={10} color="whiteAlpha.300" mb={4} />
            <Text fontSize="md" color="whiteAlpha.600">
              Nenhum conector encontrado
            </Text>
            <Text fontSize="sm" color="whiteAlpha.400">
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
