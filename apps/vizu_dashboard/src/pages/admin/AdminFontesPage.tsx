// filepath: /Users/tarsobarreto/Documents/vizu-mono/apps/vizu_dashboard/src/pages/admin/AdminFontesPage.tsx
import { useState, useMemo, useEffect, useCallback } from 'react';
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
  Flex,
  useDisclosure,
  Spinner,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useToast,
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  FiSearch,
  FiPlus,
  FiDatabase,
  FiShoppingCart,
  FiFileText,
  FiCheck,
  FiClock,
  FiAlertCircle,
  FiRefreshCw,
  FiGrid,
} from 'react-icons/fi';
import {
  SiShopify,
  SiGooglebigquery,
  SiPostgresql,
  SiMysql,
  SiSlack,
  SiWhatsapp,
  SiAsana,
  SiTrello,
  SiGoogle,
} from 'react-icons/si';
import ConnectorModal from '../../components/admin/ConnectorModal';
import { useConnectorStatus } from '../../hooks/useConnectorStatus';
import type { ConnectorStatusResponse } from '../../services/connectorStatusService';
import { MappingReviewBanner } from '../../components/MappingReviewBanner';

// Tipos
type ConnectorCategory = 'ecommerce' | 'database' | 'files' | 'api' | 'messaging' | 'productivity';
type ConnectorGroup = 'data_source' | 'integration';
type ConnectionStatus = 'connected' | 'pending' | 'error' | 'not_configured';

interface ConnectorConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  iconColor: string;
  category: ConnectorCategory;
  group: ConnectorGroup;
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
  group: ConnectorGroup;
  isNew?: boolean;
  comingSoon?: boolean;
}

const CONNECTOR_METADATA: Record<string, ConnectorMetadata> = {
  // ─── Fontes de dados ─────────────────────────────────────────
  'BIGQUERY': {
    id: 'bigquery',
    name: 'Google BigQuery',
    description: 'Conecte seu Data Warehouse BigQuery para análises avançadas',
    icon: SiGooglebigquery,
    iconColor: '#4285F4',
    category: 'database',
    group: 'data_source',
  },
  'SHOPIFY': {
    id: 'shopify',
    name: 'Shopify',
    description: 'Sincronize produtos, pedidos e clientes da sua loja Shopify',
    icon: SiShopify,
    iconColor: '#96BF48',
    category: 'ecommerce',
    group: 'data_source',
    isNew: true,
  },
  'VTEX': {
    id: 'vtex',
    name: 'VTEX',
    description: 'Conecte sua loja VTEX e importe todos os dados de vendas',
    icon: FiShoppingCart,
    iconColor: '#F71963',
    category: 'ecommerce',
    group: 'data_source',
    isNew: true,
  },
  'LOJA_INTEGRADA': {
    id: 'loja_integrada',
    name: 'Loja Integrada',
    description: 'Integre sua Loja Integrada para análise de vendas completa',
    icon: FiShoppingCart,
    iconColor: '#00A650',
    category: 'ecommerce',
    group: 'data_source',
    isNew: true,
  },
  'POSTGRES': {
    id: 'postgresql',
    name: 'PostgreSQL',
    description: 'Conecte bancos PostgreSQL para importar dados transacionais',
    icon: SiPostgresql,
    iconColor: '#336791',
    category: 'database',
    group: 'data_source',
  },
  'MYSQL': {
    id: 'mysql',
    name: 'MySQL',
    description: 'Importe dados de bancos MySQL ou MariaDB',
    icon: SiMysql,
    iconColor: '#4479A1',
    category: 'database',
    group: 'data_source',
  },
  'CSV_UPLOAD': {
    id: 'csv_upload',
    name: 'Upload CSV/Excel',
    description: 'Faça upload de arquivos CSV ou Excel para análise',
    icon: FiFileText,
    iconColor: '#10B981',
    category: 'files',
    group: 'data_source',
  },
  // ─── Integrações de comunicação / produtividade ──────────────
  'WHATSAPP': {
    id: 'whatsapp',
    name: 'WhatsApp',
    description: 'Receba notificações e converse com agentes via WhatsApp',
    icon: SiWhatsapp,
    iconColor: '#25D366',
    category: 'messaging',
    group: 'integration',
  },
  'SLACK': {
    id: 'slack',
    name: 'Slack',
    description: 'Notificações e comandos diretamente no seu workspace Slack',
    icon: SiSlack,
    iconColor: '#4A154B',
    category: 'messaging',
    group: 'integration',
    comingSoon: true,
  },
  'GOOGLE_WORKSPACE': {
    id: 'google_workspace',
    name: 'Google Workspace',
    description: 'Gmail, Sheets, Agenda e Drive com um único OAuth',
    icon: SiGoogle,
    iconColor: '#EA4335',
    category: 'productivity',
    group: 'integration',
    comingSoon: true,
  },
  'ASANA': {
    id: 'asana',
    name: 'Asana',
    description: 'Crie e acompanhe tarefas a partir das ações do agente',
    icon: SiAsana,
    iconColor: '#F06A6A',
    category: 'productivity',
    group: 'integration',
    comingSoon: true,
  },
  'TRELLO': {
    id: 'trello',
    name: 'Trello',
    description: 'Sincronize cards do Trello com seus fluxos de trabalho',
    icon: SiTrello,
    iconColor: '#0079BF',
    category: 'productivity',
    group: 'integration',
    comingSoon: true,
  },
  'DEFAULT': {
    id: 'unknown',
    name: 'Conector',
    description: 'Fonte de dados conectada',
    icon: FiDatabase,
    iconColor: '#6366F1',
    category: 'database',
    group: 'data_source',
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
  /** Render a subtle "configured" check badge on top of the icon. */
  showConfiguredFlag?: boolean;
}

const ConnectorCard = ({ connector, onConnect, showConfiguredFlag = true }: ConnectorCardProps) => {
  const isConfigured = connector.status === 'connected';

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
        {/* Icon + configured flag */}
        <Box position="relative">
          <Flex
            w="48px"
            h="48px"
            bg={`${connector.iconColor}20`}
            borderRadius="12px"
            align="center"
            justify="center"
            boxShadow={`0 4px 12px ${connector.iconColor}30`}
          >
            <Icon as={connector.icon} boxSize={6} color={connector.iconColor} />
          </Flex>
          {showConfiguredFlag && isConfigured && (
            <Flex
              position="absolute"
              bottom="-4px"
              right="-4px"
              w="18px"
              h="18px"
              bg="#22c55e"
              borderRadius="full"
              align="center"
              justify="center"
              border="2px solid #1a1b2e"
              boxShadow="0 2px 6px rgba(34,197,94,0.4)"
            >
              <Icon as={FiCheck} boxSize={2.5} color="white" />
            </Flex>
          )}
        </Box>

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

// Card destacado mostrando a fonte de dados ativa (ou placeholder vazio).
interface ActiveDataSourceCardProps {
  connector: ConnectorConfig | null;
  onManage: () => void;
  onChange: () => void;
}

const ActiveDataSourceCard = ({ connector, onManage, onChange }: ActiveDataSourceCardProps) => {
  if (!connector) {
    // Empty state — nenhuma fonte conectada ainda.
    return (
      <Box
        bg="#1a1b2e"
        borderRadius="1rem"
        border="1px dashed rgba(255,255,255,0.15)"
        p={6}
      >
        <HStack spacing={4} align="center">
          <Flex
            w="56px"
            h="56px"
            bg="whiteAlpha.50"
            borderRadius="14px"
            align="center"
            justify="center"
          >
            <Icon as={FiDatabase} boxSize={6} color="whiteAlpha.500" />
          </Flex>
          <VStack align="start" spacing={1} flex={1}>
            <Text fontSize="md" fontWeight="medium" color="white">
              Nenhuma fonte de dados conectada
            </Text>
            <Text fontSize="xs" color="whiteAlpha.500">
              Escolha uma fonte (Shopify, VTEX, BigQuery…) para começar a analisar.
            </Text>
          </VStack>
          <Button
            size="sm"
            leftIcon={<FiPlus />}
            bgGradient="linear(to-r, #3b82f6, #2563eb)"
            color="white"
            _hover={{ bgGradient: 'linear(to-r, #2563eb, #1d4ed8)' }}
            boxShadow="0 4px 12px rgba(59,130,246,0.4)"
            onClick={onChange}
          >
            Conectar fonte
          </Button>
        </HStack>
      </Box>
    );
  }

  return (
    <Box
      bg="#1a1b2e"
      borderRadius="1rem"
      border="1px solid"
      borderColor="rgba(255,255,255,0.08)"
      boxShadow="0 4px 24px rgba(0,0,0,0.4)"
      p={6}
    >
      <HStack spacing={5} align="center">
        <Box position="relative">
          <Flex
            w="56px"
            h="56px"
            bg={`${connector.iconColor}20`}
            borderRadius="14px"
            align="center"
            justify="center"
            boxShadow={`0 4px 12px ${connector.iconColor}30`}
          >
            <Icon as={connector.icon} boxSize={7} color={connector.iconColor} />
          </Flex>
          {connector.status === 'connected' && (
            <Flex
              position="absolute"
              bottom="-4px"
              right="-4px"
              w="20px"
              h="20px"
              bg="#22c55e"
              borderRadius="full"
              align="center"
              justify="center"
              border="2px solid #1a1b2e"
              boxShadow="0 2px 6px rgba(34,197,94,0.4)"
            >
              <Icon as={FiCheck} boxSize={3} color="white" />
            </Flex>
          )}
        </Box>

        <VStack align="start" spacing={1} flex={1} minW={0}>
          <HStack spacing={2}>
            <Text fontSize="md" fontWeight="medium" color="white">
              {connector.name}
            </Text>
            <Badge
              colorScheme={
                connector.status === 'connected'
                  ? 'green'
                  : connector.status === 'pending'
                    ? 'yellow'
                    : 'red'
              }
              fontSize="10px"
              borderRadius="full"
              px={2}
            >
              {connector.status === 'connected'
                ? 'Conectado'
                : connector.status === 'pending'
                  ? 'Sincronizando'
                  : 'Erro'}
            </Badge>
          </HStack>
          <HStack spacing={4} fontSize="xs" color="whiteAlpha.500">
            {connector.recordsCount != null && (
              <Text>{connector.recordsCount.toLocaleString('pt-BR')} registros</Text>
            )}
            {connector.lastSync && (
              <Text>Última sync: {new Date(connector.lastSync).toLocaleDateString('pt-BR')}</Text>
            )}
          </HStack>
        </VStack>

        <HStack spacing={2}>
          <Button
            size="sm"
            variant="outline"
            color="white"
            borderColor="whiteAlpha.200"
            _hover={{ bg: 'whiteAlpha.100' }}
            onClick={onManage}
          >
            Gerenciar
          </Button>
          <Button
            size="sm"
            leftIcon={<FiRefreshCw />}
            bg="whiteAlpha.100"
            color="white"
            _hover={{ bg: 'whiteAlpha.200' }}
            onClick={onChange}
          >
            Trocar fonte
          </Button>
        </HStack>
      </HStack>
    </Box>
  );
};

// Picker de troca de fonte de dados — mostra todas as opções num modal.
interface DataSourcePickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  dataSources: ConnectorConfig[];
  onSelect: (connector: ConnectorConfig) => void;
}

const DataSourcePickerModal = ({
  isOpen,
  onClose,
  dataSources,
  onSelect,
}: DataSourcePickerModalProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" isCentered>
      <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(4px)" />
      <ModalContent bg="#0f1128" border="1px solid" borderColor="rgba(255,255,255,0.08)" color="white">
        <ModalHeader>
          <VStack align="start" spacing={1}>
            <Text fontSize="lg" fontWeight="medium">Escolher fonte de dados</Text>
            <Text fontSize="xs" color="whiteAlpha.500" fontWeight="normal">
              Selecione qual sistema será a fonte principal de dados do seu cliente.
            </Text>
          </VStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
            {dataSources.map((connector) => (
              <ConnectorCard
                key={connector.id}
                connector={connector}
                onConnect={(c) => {
                  onSelect(c);
                  onClose();
                }}
              />
            ))}
          </SimpleGrid>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

// Página Principal
function AdminFontesPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedConnector, setSelectedConnector] = useState<ConnectorConfig | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isPickerOpen,
    onOpen: onPickerOpen,
    onClose: onPickerClose,
  } = useDisclosure();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const connectSlug = searchParams.get('connect');
  const returnTo = searchParams.get('return');

  // Fetch real connector data
  const { connectors: connectorsData, loading, error } = useConnectorStatus();

  // Map backend connectors to UI format and merge with all available connector types
  const allConnectors: ConnectorConfig[] = useMemo(() => {
    // Start with all available connector types from metadata
    const availableConnectorTypes: ConnectorConfig[] = Object.values(CONNECTOR_METADATA)
      .filter((meta) => meta.id !== 'unknown') // Exclude DEFAULT/unknown
      .map((meta) => ({
        ...meta,
        status: 'not_configured' as ConnectionStatus,
      }));

    // If we have backend data, merge it
    if (connectorsData && connectorsData.connectors.length > 0) {
      const backendConnectorMap = new Map(
        connectorsData.connectors.map((bc) => [bc.tipo_servico.toLowerCase(), bc]),
      );

      return availableConnectorTypes.map((availableConn) => {
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

  // Particiona em fontes de dados vs integrações
  const dataSources = useMemo(
    () => allConnectors.filter((c) => c.group === 'data_source'),
    [allConnectors],
  );
  const integrations = useMemo(
    () => allConnectors.filter((c) => c.group === 'integration'),
    [allConnectors],
  );

  // Fonte de dados ativa = primeira com status='connected'. Caso nenhuma esteja
  // conectada, mas exista uma 'pending'/'error', mostramos ela. Caso contrário,
  // empty state.
  const activeDataSource = useMemo<ConnectorConfig | null>(() => {
    return (
      dataSources.find((c) => c.status === 'connected') ||
      dataSources.find((c) => c.status === 'pending') ||
      dataSources.find((c) => c.status === 'error') ||
      null
    );
  }, [dataSources]);

  const hasConfiguredMapping = !!activeDataSource && activeDataSource.status === 'connected';

  // Filtros de busca aplicados a integrações (a fonte de dados ativa é única).
  const filteredIntegrations = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return integrations;
    return integrations.filter(
      (c) => c.name.toLowerCase().includes(term) || c.description.toLowerCase().includes(term),
    );
  }, [integrations, searchTerm]);

  const connectedCount = allConnectors.filter((c) => c.status === 'connected').length;
  const totalCount = allConnectors.filter((c) => !c.comingSoon).length;

  const handleConnectClick = useCallback(
    (connector: ConnectorConfig) => {
      setSelectedConnector(connector);
      onOpen();
    },
    [onOpen],
  );

  const handleChangeDataSource = useCallback(() => {
    if (hasConfiguredMapping) {
      toast({
        title: 'Trocar fonte de dados',
        description:
          'Você já tem uma fonte conectada. Trocar criará uma nova conexão e o mapeamento de colunas precisará ser refeito.',
        status: 'warning',
        duration: 6000,
        isClosable: true,
      });
    }
    onPickerOpen();
  }, [hasConfiguredMapping, onPickerOpen, toast]);

  // Auto-open modal when ?connect=<id> is present (used by onboarding hand-off).
  useEffect(() => {
    if (!connectSlug || isOpen || loading) return;
    const match = allConnectors.find((c) => c.id === connectSlug.toLowerCase());
    if (match) {
      setSelectedConnector(match);
      onOpen();
    }
  }, [connectSlug, allConnectors, isOpen, loading, onOpen]);

  // On modal close, either go back to onboarding or just clear the query params.
  const handleModalClose = useCallback(() => {
    onClose();
    if (returnTo && returnTo.startsWith('/')) {
      // External SPA (landing) — use full navigation so the session/localStorage is picked up there.
      window.location.href = returnTo;
      return;
    }
    if (connectSlug) {
      const next = new URLSearchParams(searchParams);
      next.delete('connect');
      next.delete('return');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onClose, returnTo, connectSlug, searchParams, setSearchParams, navigate]);

  // Loading state (only show spinner if truly loading from API)
  if (loading) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Spinner size="xl" color="blue.400" />
          <Text mt={4} color="whiteAlpha.600">Carregando integrações...</Text>
        </Box>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <Box p={8} textAlign="center">
          <Icon as={FiAlertCircle} boxSize={12} color="red.400" mb={4} />
          <Text fontSize="18px" color="whiteAlpha.800">Erro ao carregar integrações</Text>
          <Text fontSize="14px" color="whiteAlpha.500" mt={2}>{error.message}</Text>
        </Box>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <MappingReviewBanner mx={8} mt={6} />
      <Box p={8} maxW="1200px" mx="auto">
        {/* Header */}
        <VStack align="start" spacing={2} mb={8}>
          <HStack spacing={3}>
            <Flex w={10} h={10} borderRadius="lg" align="center" justify="center" bg="#3b82f620">
              <Icon as={FiGrid} boxSize={5} color="#3b82f6" />
            </Flex>
            <Text
              fontSize="1.5rem"
              fontWeight="normal"
              fontFamily="'Playfair Display', serif"
              color="white"
            >
              Integrações
            </Text>
          </HStack>
          <Text fontSize="sm" color="whiteAlpha.500">
            Gerencie sua fonte de dados e as integrações de comunicação e produtividade.
            <Text as="span" fontWeight="medium" color="#3b82f6">
              {' '}
              {connectedCount} de {totalCount} ativas
            </Text>
          </Text>
        </VStack>

        {/* ─── Seção: Fonte de Dados ───────────────────────────── */}
        <VStack align="stretch" spacing={4} mb={10}>
          <HStack justify="space-between" align="end">
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" textTransform="uppercase" color="whiteAlpha.400" letterSpacing="0.1em">
                Fonte de dados
              </Text>
              <Text fontSize="md" color="white" fontWeight="medium">
                Sistema operacional principal
              </Text>
            </VStack>
          </HStack>

          <ActiveDataSourceCard
            connector={activeDataSource}
            onManage={() => activeDataSource && handleConnectClick(activeDataSource)}
            onChange={handleChangeDataSource}
          />
        </VStack>

        {/* ─── Seção: Integrações ──────────────────────────────── */}
        <VStack align="stretch" spacing={4}>
          <HStack justify="space-between" align="end" flexWrap="wrap" gap={3}>
            <VStack align="start" spacing={0}>
              <Text fontSize="xs" textTransform="uppercase" color="whiteAlpha.400" letterSpacing="0.1em">
                Integrações
              </Text>
              <Text fontSize="md" color="white" fontWeight="medium">
                Comunicação e produtividade
              </Text>
            </VStack>
            <InputGroup maxW="280px">
              <InputLeftElement pointerEvents="none">
                <Icon as={FiSearch} color="whiteAlpha.400" />
              </InputLeftElement>
              <Input
                placeholder="Buscar integrações..."
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
          </HStack>

          <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={5}>
            {filteredIntegrations.map((connector) => (
              <ConnectorCard
                key={connector.id}
                connector={connector}
                onConnect={handleConnectClick}
              />
            ))}
          </SimpleGrid>

          {filteredIntegrations.length === 0 && (
            <Box
              textAlign="center"
              py={12}
              bg="#1a1b2e"
              borderRadius="1rem"
              border="1px solid"
              borderColor="rgba(255,255,255,0.08)"
            >
              <Icon as={FiSearch} boxSize={8} color="whiteAlpha.300" mb={3} />
              <Text fontSize="sm" color="whiteAlpha.600">
                Nenhuma integração encontrada
              </Text>
            </Box>
          )}
        </VStack>
      </Box>

      {/* Picker de troca de fonte de dados */}
      <DataSourcePickerModal
        isOpen={isPickerOpen}
        onClose={onPickerClose}
        dataSources={dataSources}
        onSelect={(connector) => handleConnectClick(connector)}
      />

      {/* Modal de Conexão */}
      {selectedConnector && (
        <ConnectorModal
          isOpen={isOpen}
          onClose={handleModalClose}
          connector={selectedConnector}
          returnTo={returnTo}
        />
      )}
    </AdminLayout>
  );
}

export default AdminFontesPage;
