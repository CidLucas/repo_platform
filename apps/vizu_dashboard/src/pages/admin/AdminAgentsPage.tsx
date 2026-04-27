import {
    Box,
    SimpleGrid,
    Text,
    Button,
    HStack,
    Badge,
    VStack,
    Spinner,
    Center,
    Switch,
    useDisclosure,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    Icon,
    IconButton,
    Tooltip,
    Flex,
    Divider,
} from '@chakra-ui/react';
import type { IconType } from 'react-icons';
import {
    FiPlus,
    FiEdit2,
    FiRotateCcw,
    FiArchive,
    FiSettings,
    FiCpu,
    FiBarChart2,
    FiBookOpen,
    FiFileText,
    FiSearch,
    FiTool,
    FiMessageSquare,
    FiShoppingCart,
    FiTrendingUp,
    FiDatabase,
    FiZap,
    FiPieChart,
    FiLayers,
    FiShield,
    FiMail,
    FiUsers,
} from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useAgentBuilder } from '../../hooks/useAgentBuilder';
import { useAuth } from '../../hooks/useAuth';

// Category accent color mapping — aligns with the palette used across
// AdminHome / AdminPrivacidade so the agents page feels part of the same system.
const CATEGORY_COLORS: Record<string, string> = {
    analytics: '#3b82f6',
    procurement: '#f97316',
    communication: '#a855f7',
    reporting: '#06d6a0',
    report: '#06d6a0',
    knowledge: '#f59e0b',
    data_analysis: '#3b82f6',
    default: '#3b82f6',
};

function getCategoryColor(category: string | null): string {
    if (!category) return CATEGORY_COLORS.default;
    const key = category.toLowerCase();
    for (const [k, v] of Object.entries(CATEGORY_COLORS)) {
        if (key.includes(k)) return v;
    }
    return CATEGORY_COLORS.default;
}

// Map the icon name stored in `agent_catalog.icon` (Lucide-style names) to a
// react-icons/fi component. Anything unknown falls back to a sensible default
// so the UI never renders a raw string like "BarChart2".
const ICON_MAP: Record<string, IconType> = {
    BarChart2: FiBarChart2,
    BarChart: FiBarChart2,
    PieChart: FiPieChart,
    TrendingUp: FiTrendingUp,
    BookOpen: FiBookOpen,
    FileText: FiFileText,
    FileSpreadsheet: FiFileText,
    FileSearch: FiSearch,
    Search: FiSearch,
    Database: FiDatabase,
    Layers: FiLayers,
    Shield: FiShield,
    Mail: FiMail,
    Users: FiUsers,
    MessageSquare: FiMessageSquare,
    ShoppingCart: FiShoppingCart,
    Zap: FiZap,
    Tool: FiTool,
    Cpu: FiCpu,
};

function resolveAgentIcon(iconName: string | null | undefined): IconType {
    if (!iconName) return FiCpu;
    return ICON_MAP[iconName] ?? FiCpu;
}

const AdminAgentsPage = () => {
    const navigate = useNavigate();
    const { tier } = useAuth();
    const isAdmin = tier === 'ADMIN';
    const {
        agents,
        loadingCatalog,
        catalogError,
        deleteAgent,
        toggleActive,
    } = useAgentBuilder();

    const { isOpen, onOpen, onClose } = useDisclosure();
    const [archiveTargetId, setArchiveTargetId] = useState<string | null>(null);
    const [showArchived, setShowArchived] = useState(false);
    const archiveTargetAgent = agents.find((a) => a.id === archiveTargetId);

    const filteredAgents = showArchived ? agents : agents.filter((a) => a.is_active);
    const archivedCount = agents.filter((a) => !a.is_active).length;

    const confirmArchive = (agentId: string) => {
        setArchiveTargetId(agentId);
        onOpen();
    };

    const handleArchive = async () => {
        if (archiveTargetId) {
            await deleteAgent(archiveTargetId);
            onClose();
            setArchiveTargetId(null);
        }
    };

    return (
        <AdminLayout>
            <Box p={8} maxW="1200px" mx="auto">
                {/* Header */}
                <VStack spacing={2} mb={8} align="start">
                    <Flex
                        w="48px"
                        h="48px"
                        borderRadius="12px"
                        align="center"
                        justify="center"
                        bg="#3b82f620"
                        mb={2}
                    >
                        <Icon as={FiCpu} boxSize={6} color="#3b82f6" />
                    </Flex>
                    <Flex w="full" justify="space-between" align="center" flexWrap="wrap" gap={3}>
                        <Box>
                            <Text
                                fontSize="24px"
                                fontWeight="semibold"
                                color="white"
                                letterSpacing="-0.3px"
                            >
                                Agentes de IA
                            </Text>
                            <Text fontSize="14px" color="whiteAlpha.600" lineHeight="20px">
                                Configure e monitore os agentes que trabalham para o seu time.
                            </Text>
                        </Box>
                        <HStack spacing={3}>
                            {archivedCount > 0 && (
                                <HStack
                                    spacing={2}
                                    px={3}
                                    py={2}
                                    borderRadius="lg"
                                    bg="whiteAlpha.50"
                                    border="1px solid"
                                    borderColor="whiteAlpha.100"
                                >
                                    <Icon as={FiArchive} boxSize={4} color="whiteAlpha.500" />
                                    <Text fontSize="xs" color="whiteAlpha.600">
                                        {archivedCount} arquivado{archivedCount !== 1 && 's'}
                                    </Text>
                                    <Switch
                                        size="sm"
                                        isChecked={showArchived}
                                        onChange={(e) => setShowArchived(e.target.checked)}
                                        colorScheme="gray"
                                    />
                                </HStack>
                            )}
                            {isAdmin && (
                                <Button
                                    leftIcon={<Icon as={FiPlus} />}
                                    bgGradient="linear(to-r, #3b82f6, #a855f7)"
                                    color="white"
                                    size="sm"
                                    h="40px"
                                    px={5}
                                    borderRadius="lg"
                                    _hover={{ filter: 'brightness(1.1)' }}
                                    onClick={() => navigate('/dashboard/admin/agents/new')}
                                >
                                    Novo agente
                                </Button>
                            )}
                        </HStack>
                    </Flex>
                </VStack>

                {/* Loading */}
                {loadingCatalog && (
                    <Center minH="300px">
                        <VStack spacing={3}>
                            <Spinner size="lg" color="#3b82f6" thickness="3px" />
                            <Text color="whiteAlpha.600">Carregando agentes...</Text>
                        </VStack>
                    </Center>
                )}

                {/* Error */}
                {catalogError && !loadingCatalog && (
                    <Center minH="200px">
                        <Text color="red.400">{catalogError}</Text>
                    </Center>
                )}

                {/* Empty */}
                {!loadingCatalog && !catalogError && agents.length === 0 && (
                    <Center minH="300px">
                        <VStack spacing={3}>
                            <Icon as={FiCpu} boxSize={10} color="whiteAlpha.300" />
                            <Text color="whiteAlpha.600">Nenhum agente configurado ainda.</Text>
                            {isAdmin && (
                                <Button
                                    variant="outline"
                                    leftIcon={<Icon as={FiPlus} />}
                                    borderColor="whiteAlpha.200"
                                    color="white"
                                    _hover={{ borderColor: 'whiteAlpha.400', bg: 'whiteAlpha.50' }}
                                    onClick={() => navigate('/dashboard/admin/agents/new')}
                                >
                                    Criar o primeiro agente
                                </Button>
                            )}
                        </VStack>
                    </Center>
                )}

                {/* No active agents */}
                {!loadingCatalog && !catalogError && agents.length > 0 && filteredAgents.length === 0 && (
                    <Center minH="200px">
                        <Text color="whiteAlpha.500">
                            Nenhum agente ativo. Ative "arquivados" para ver os inativos.
                        </Text>
                    </Center>
                )}

                {/* Agents Grid */}
                {!loadingCatalog && !catalogError && filteredAgents.length > 0 && (
                    <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} spacing={5}>
                        {filteredAgents.map((agent) => {
                            const accent = getCategoryColor(agent.category);
                            const AgentIcon = resolveAgentIcon(agent.icon);
                            const toolCount = agent.agent_config.enabled_tools?.length ?? 0;

                            return (
                                <Box
                                    key={agent.id}
                                    bg="#1a1b2e"
                                    borderRadius="1rem"
                                    border="1px solid rgba(255,255,255,0.08)"
                                    p={6}
                                    position="relative"
                                    overflow="hidden"
                                    opacity={agent.is_active ? 1 : 0.6}
                                    transition="all 0.2s"
                                    _hover={{
                                        borderColor: 'rgba(255,255,255,0.15)',
                                        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                                    }}
                                >
                                    {/* Left accent bar */}
                                    <Box
                                        position="absolute"
                                        top={0}
                                        left={0}
                                        w="3px"
                                        h="100%"
                                        bg={accent}
                                    />

                                    {/* Header row */}
                                    <Flex justify="space-between" align="flex-start" mb={4}>
                                        <HStack spacing={4} align="flex-start" flex={1} minW={0}>
                                            <Flex
                                                w="48px"
                                                h="48px"
                                                borderRadius="12px"
                                                align="center"
                                                justify="center"
                                                bg={`${accent}20`}
                                                flexShrink={0}
                                            >
                                                <Icon as={AgentIcon} boxSize={6} color={accent} />
                                            </Flex>
                                            <VStack align="start" spacing={1} minW={0}>
                                                <Text
                                                    fontSize="sm"
                                                    fontWeight="semibold"
                                                    color="white"
                                                    textDecoration={agent.is_active ? 'none' : 'line-through'}
                                                    noOfLines={1}
                                                >
                                                    {agent.name}
                                                </Text>
                                                <Text
                                                    fontSize="xs"
                                                    color="whiteAlpha.500"
                                                    noOfLines={2}
                                                    lineHeight="16px"
                                                >
                                                    {agent.description || 'Sem descrição'}
                                                </Text>
                                            </VStack>
                                        </HStack>
                                        <Tooltip
                                            label={agent.is_active ? 'Desativar agente' : 'Ativar agente'}
                                            hasArrow
                                        >
                                            <Box>
                                                <Switch
                                                    size="sm"
                                                    isChecked={agent.is_active}
                                                    onChange={(e) => toggleActive(agent.id, e.target.checked)}
                                                    colorScheme="green"
                                                />
                                            </Box>
                                        </Tooltip>
                                    </Flex>

                                    <Divider borderColor="whiteAlpha.100" mb={4} />

                                    {/* Stats */}
                                    <VStack spacing={3} align="stretch" mb={4}>
                                        <Flex justify="space-between" align="center">
                                            <Text fontSize="xs" color="whiteAlpha.500">Status</Text>
                                            <Badge
                                                px={2}
                                                py={0.5}
                                                borderRadius="full"
                                                fontSize="10px"
                                                textTransform="none"
                                                fontWeight="medium"
                                                bg={agent.is_active ? '#10b98120' : 'whiteAlpha.100'}
                                                color={agent.is_active ? '#10b981' : 'whiteAlpha.500'}
                                            >
                                                {agent.is_active ? 'Ativo' : 'Inativo'}
                                            </Badge>
                                        </Flex>
                                        <Flex justify="space-between" align="center">
                                            <HStack spacing={2}>
                                                <Icon as={FiTool} boxSize={3.5} color="whiteAlpha.400" />
                                                <Text fontSize="xs" color="whiteAlpha.500">Ferramentas</Text>
                                            </HStack>
                                            <Text fontSize="xs" fontWeight="medium" color="white">
                                                {toolCount}
                                            </Text>
                                        </Flex>
                                        <Flex justify="space-between" align="center">
                                            <HStack spacing={2}>
                                                <Icon as={FiLayers} boxSize={3.5} color="whiteAlpha.400" />
                                                <Text fontSize="xs" color="whiteAlpha.500">Categoria</Text>
                                            </HStack>
                                            <Text
                                                fontSize="xs"
                                                fontWeight="medium"
                                                color="white"
                                                textTransform="capitalize"
                                            >
                                                {agent.category?.replace(/_/g, ' ') || '—'}
                                            </Text>
                                        </Flex>
                                        <Flex justify="space-between" align="center">
                                            <HStack spacing={2}>
                                                <Icon as={FiShield} boxSize={3.5} color="whiteAlpha.400" />
                                                <Text fontSize="xs" color="whiteAlpha.500">Plano</Text>
                                            </HStack>
                                            <Badge
                                                bg="whiteAlpha.100"
                                                color="whiteAlpha.700"
                                                fontSize="10px"
                                                px={2}
                                                borderRadius="full"
                                                textTransform="none"
                                            >
                                                {agent.tier_required}
                                            </Badge>
                                        </Flex>
                                    </VStack>

                                    {/* Actions */}
                                    <HStack spacing={2}>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            flex={1}
                                            h="36px"
                                            borderColor="whiteAlpha.200"
                                            color="whiteAlpha.800"
                                            leftIcon={<Icon as={FiSettings} boxSize={3.5} />}
                                            _hover={{ borderColor: 'whiteAlpha.400', bg: 'whiteAlpha.50' }}
                                            onClick={() => navigate('/dashboard/admin/chat')}
                                        >
                                            Configurar
                                        </Button>
                                        {isAdmin && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                flex={1}
                                                h="36px"
                                                borderColor="whiteAlpha.200"
                                                color="whiteAlpha.800"
                                                leftIcon={<Icon as={FiEdit2} boxSize={3.5} />}
                                                _hover={{ borderColor: 'whiteAlpha.400', bg: 'whiteAlpha.50' }}
                                                onClick={() => navigate(`/dashboard/admin/agents/${agent.id}`)}
                                            >
                                                Editar
                                            </Button>
                                        )}
                                        {isAdmin && agent.is_active && (
                                            <Tooltip label="Arquivar agente" hasArrow>
                                                <IconButton
                                                    aria-label="Arquivar agente"
                                                    icon={<Icon as={FiArchive} boxSize={4} />}
                                                    variant="outline"
                                                    size="sm"
                                                    h="36px"
                                                    borderColor="whiteAlpha.200"
                                                    color="red.300"
                                                    _hover={{
                                                        borderColor: 'red.400',
                                                        bg: 'red.900',
                                                        color: 'red.200',
                                                    }}
                                                    onClick={() => confirmArchive(agent.id)}
                                                />
                                            </Tooltip>
                                        )}
                                        {isAdmin && !agent.is_active && (
                                            <Tooltip label="Reativar agente" hasArrow>
                                                <IconButton
                                                    aria-label="Reativar agente"
                                                    icon={<Icon as={FiRotateCcw} boxSize={4} />}
                                                    variant="outline"
                                                    size="sm"
                                                    h="36px"
                                                    borderColor="whiteAlpha.200"
                                                    color="green.300"
                                                    _hover={{
                                                        borderColor: 'green.400',
                                                        bg: 'green.900',
                                                        color: 'green.200',
                                                    }}
                                                    onClick={() => toggleActive(agent.id, true)}
                                                />
                                            </Tooltip>
                                        )}
                                    </HStack>
                                </Box>
                            );
                        })}
                    </SimpleGrid>
                )}
            </Box>

            {/* Archive confirmation modal */}
            <Modal isOpen={isOpen} onClose={onClose} isCentered>
                <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(4px)" />
                <ModalContent
                    bg="#1a1b2e"
                    borderColor="rgba(255,255,255,0.08)"
                    borderWidth="1px"
                    borderRadius="1rem"
                    color="white"
                >
                    <ModalHeader fontSize="lg" fontWeight="semibold">
                        Arquivar agente
                    </ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        <Text fontSize="sm" color="whiteAlpha.800">
                            Tem certeza que deseja arquivar{' '}
                            <Text as="span" fontWeight="semibold" color="white">
                                {archiveTargetAgent?.name}
                            </Text>
                            ?
                        </Text>
                        <Text mt={3} fontSize="xs" color="whiteAlpha.500">
                            O agente será ocultado dos usuários. Sessões existentes continuarão
                            funcionando.
                        </Text>
                    </ModalBody>
                    <ModalFooter>
                        <Button
                            variant="ghost"
                            mr={3}
                            onClick={onClose}
                            color="whiteAlpha.700"
                            _hover={{ bg: 'whiteAlpha.100' }}
                        >
                            Cancelar
                        </Button>
                        <Button colorScheme="red" onClick={handleArchive}>
                            Arquivar
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </AdminLayout>
    );
};

export default AdminAgentsPage;
