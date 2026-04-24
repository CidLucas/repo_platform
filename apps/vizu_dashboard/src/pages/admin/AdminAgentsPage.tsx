import {
    Box,
    SimpleGrid,
    Card,
    CardHeader,
    CardBody,
    Heading,
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
    Flex,
} from '@chakra-ui/react';
import { FiPlus, FiEdit, FiRotateCcw, FiArchive, FiSettings } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useAgentBuilder } from '../../hooks/useAgentBuilder';
import { useAuth } from '../../hooks/useAuth';

// Category color mapping
const categoryColors: Record<string, { from: string; to: string }> = {
    procurement: { from: '#ff6b35', to: '#ff006e' },
    communication: { from: '#4361ee', to: '#7209b7' },
    report: { from: '#06ffa5', to: '#06d6a0' },
    analytics: { from: '#f72585', to: '#b5179e' },
    default: { from: '#0ea5e9', to: '#0284c7' },
};

function getCategoryColor(category: string | null) {
    if (!category) return categoryColors.default;
    const key = category.toLowerCase();
    for (const [k, v] of Object.entries(categoryColors)) {
        if (key.includes(k)) return v;
    }
    // Cycle through colors based on hash
    const colors = Object.values(categoryColors);
    const hash = (category || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    return colors[hash % colors.length];
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
            <Box p={8} maxW="1400px" mx="auto">
                {/* Header */}
                <Flex justify="space-between" align="center" mb={8}>
                    <Box>
                        <Heading
                            size="xl"
                            fontFamily="'Playfair Display', serif"
                            fontWeight="bold"
                            mb={1}
                        >
                            <Text as="span" color="white">AI </Text>
                            <Text
                                as="span"
                                bgGradient="linear(to-r, #ff6b35, #ff006e)"
                                bgClip="text"
                            >
                                Agents
                            </Text>
                        </Heading>
                        <Text fontSize="sm" color="gray.400" mt={1}>
                            Configure and monitor your AI-powered agents
                        </Text>
                    </Box>
                    <HStack spacing={3}>
                        {archivedCount > 0 && (
                            <HStack spacing={2}>
                                <HStack spacing={1}>
                                    <Icon as={FiArchive} boxSize={4} color="gray.500" />
                                    <Text fontSize="sm" color="gray.500">
                                        {archivedCount} archived
                                    </Text>
                                </HStack>
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
                                leftIcon={<FiPlus />}
                                bgGradient="linear(to-r, #4361ee, #7209b7)"
                                color="white"
                                _hover={{ opacity: 0.9 }}
                                onClick={() => navigate('/dashboard/admin/agents/new')}
                            >
                                Configure New Agent
                            </Button>
                        )}
                    </HStack>
                </Flex>

                {/* Loading */}
                {loadingCatalog && (
                    <Center minH="300px">
                        <VStack spacing={3}>
                            <Spinner size="lg" color="blue.400" />
                            <Text color="gray.400">Loading agents...</Text>
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
                            <Text color="gray.400">No agents configured yet.</Text>
                            {isAdmin && (
                                <Button
                                    variant="outline"
                                    leftIcon={<FiPlus />}
                                    borderColor="gray.600"
                                    color="white"
                                    _hover={{ borderColor: 'gray.400' }}
                                    onClick={() => navigate('/dashboard/admin/agents/new')}
                                >
                                    Create your first agent
                                </Button>
                            )}
                        </VStack>
                    </Center>
                )}

                {/* No active agents */}
                {!loadingCatalog && !catalogError && agents.length > 0 && filteredAgents.length === 0 && (
                    <Center minH="200px">
                        <Text color="gray.500">No active agents. Toggle "archived" to see inactive agents.</Text>
                    </Center>
                )}

                {/* Agents Grid */}
                {!loadingCatalog && !catalogError && filteredAgents.length > 0 && (
                    <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
                        {filteredAgents.map((agent) => {
                            const color = getCategoryColor(agent.category);
                            const toolCount = agent.agent_config.enabled_tools?.length ?? 0;

                            return (
                                <Card
                                    key={agent.id}
                                    bg="#1a1b2e"
                                    borderWidth="1px"
                                    borderColor="rgba(255,255,255,0.08)"
                                    borderRadius="xl"
                                    opacity={agent.is_active ? 1 : 0.6}
                                    transition="all 0.2s"
                                    overflow="hidden"
                                    position="relative"
                                    _hover={{
                                        borderColor: 'whiteAlpha.200',
                                        transform: 'translateY(-2px)',
                                        boxShadow: `0 8px 30px rgba(0,0,0,0.3)`,
                                    }}
                                    _before={{
                                        content: '""',
                                        position: 'absolute',
                                        top: 0,
                                        left: 0,
                                        right: 0,
                                        height: '3px',
                                        bgGradient: `linear(to-r, ${color.from}, ${color.to})`,
                                    }}
                                >
                                    <CardHeader pb={2}>
                                        <Flex justify="space-between" align="flex-start">
                                            <HStack spacing={4} align="flex-start">
                                                {/* Agent Icon */}
                                                <Flex
                                                    position="relative"
                                                    w="56px"
                                                    h="56px"
                                                    borderRadius="1rem"
                                                    align="center"
                                                    justify="center"
                                                    overflow="hidden"
                                                    flexShrink={0}
                                                    bgGradient={`linear(135deg, ${color.from}, ${color.to})`}
                                                    boxShadow={`0 8px 24px ${color.from}40, 0 0 0 1px ${color.from}20`}
                                                >
                                                    <Box
                                                        position="absolute"
                                                        inset={0}
                                                        bgGradient="linear(to-br, whiteAlpha.200, transparent)"
                                                    />
                                                    <Text fontSize="2xl" position="relative" zIndex={1}>
                                                        {agent.icon || '🤖'}
                                                    </Text>
                                                </Flex>
                                                <Box>
                                                    <Heading
                                                        size="sm"
                                                        color="white"
                                                        textDecoration={agent.is_active ? 'none' : 'line-through'}
                                                    >
                                                        {agent.name}
                                                    </Heading>
                                                    <Text fontSize="sm" color="gray.400" mt={1} noOfLines={2}>
                                                        {agent.description || 'No description'}
                                                    </Text>
                                                </Box>
                                            </HStack>
                                            <Switch
                                                size="md"
                                                isChecked={agent.is_active}
                                                onChange={(e) => toggleActive(agent.id, e.target.checked)}
                                                colorScheme="green"
                                            />
                                        </Flex>
                                    </CardHeader>

                                    <CardBody pt={0}>
                                        <VStack spacing={4} align="stretch">
                                            {/* Status */}
                                            <Flex justify="space-between" align="center">
                                                <Text fontSize="sm" color="gray.400">Status</Text>
                                                <Badge
                                                    px={2}
                                                    py={0.5}
                                                    borderRadius="full"
                                                    fontSize="xs"
                                                    {...(agent.is_active
                                                        ? {
                                                            bgGradient: 'linear(to-r, #06ffa5, #06d6a0)',
                                                            color: 'black',
                                                        }
                                                        : {
                                                            bg: 'gray.700',
                                                            color: 'gray.300',
                                                        }
                                                    )}
                                                >
                                                    {agent.is_active ? 'Active' : 'Inactive'}
                                                </Badge>
                                            </Flex>

                                            {/* Stats */}
                                            <VStack spacing={2} align="stretch">
                                                <Flex justify="space-between" align="center">
                                                    <Text fontSize="sm" color="gray.400">Tools</Text>
                                                    <Text fontSize="sm" fontWeight="medium" color="white">
                                                        {toolCount}
                                                    </Text>
                                                </Flex>
                                                <Flex justify="space-between" align="center">
                                                    <Text fontSize="sm" color="gray.400">Category</Text>
                                                    <Text fontSize="sm" fontWeight="medium" color="white">
                                                        {agent.category || '—'}
                                                    </Text>
                                                </Flex>
                                                <Flex justify="space-between" align="center">
                                                    <Text fontSize="sm" color="gray.400">Tier</Text>
                                                    <Badge
                                                        variant="outline"
                                                        colorScheme="blue"
                                                        fontSize="xs"
                                                    >
                                                        {agent.tier_required}
                                                    </Badge>
                                                </Flex>
                                                {/* Progress bar */}
                                                <Box w="full" h="4px" bg="gray.800" borderRadius="full" overflow="hidden">
                                                    <Box
                                                        h="full"
                                                        borderRadius="full"
                                                        bgGradient={`linear(90deg, ${color.from}, ${color.to})`}
                                                        w={`${Math.min(toolCount * 15, 100)}%`}
                                                        transition="all 0.3s"
                                                    />
                                                </Box>
                                            </VStack>

                                            {/* Actions */}
                                            <HStack spacing={2} pt={2}>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    flex={1}
                                                    borderColor="gray.600"
                                                    color="white"
                                                    _hover={{ borderColor: 'gray.400' }}
                                                    leftIcon={<FiSettings />}
                                                    onClick={() => navigate('/dashboard/admin/chat')}
                                                >
                                                    Configure
                                                </Button>
                                                {isAdmin && (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        flex={1}
                                                        borderColor="gray.600"
                                                        color="white"
                                                        _hover={{ borderColor: 'gray.400' }}
                                                        leftIcon={<FiEdit />}
                                                        onClick={() => navigate(`/dashboard/admin/agents/${agent.id}`)}
                                                    >
                                                        Edit
                                                    </Button>
                                                )}
                                                {isAdmin && agent.is_active && (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        borderColor="gray.600"
                                                        color="red.300"
                                                        _hover={{ borderColor: 'red.400' }}
                                                        onClick={() => confirmArchive(agent.id)}
                                                    >
                                                        <Icon as={FiArchive} />
                                                    </Button>
                                                )}
                                                {isAdmin && !agent.is_active && (
                                                    <Button
                                                        variant="outline"
                                                        size="sm"
                                                        borderColor="gray.600"
                                                        color="green.300"
                                                        _hover={{ borderColor: 'green.400' }}
                                                        onClick={() => toggleActive(agent.id, true)}
                                                    >
                                                        <Icon as={FiRotateCcw} />
                                                    </Button>
                                                )}
                                            </HStack>
                                        </VStack>
                                    </CardBody>
                                </Card>
                            );
                        })}
                    </SimpleGrid>
                )}
            </Box>

            {/* Archive confirmation modal */}
            <Modal isOpen={isOpen} onClose={onClose} isCentered>
                <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(4px)" />
                <ModalContent bg="#1a1b2e" borderColor="rgba(255,255,255,0.08)" borderWidth="1px" color="white">
                    <ModalHeader>Archive Agent</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        <Text>
                            Are you sure you want to archive{' '}
                            <strong>{archiveTargetAgent?.name}</strong>?
                        </Text>
                        <Text mt={2} fontSize="sm" color="gray.400">
                            This agent will be archived and hidden from users.
                            Existing sessions will continue to work.
                        </Text>
                    </ModalBody>
                    <ModalFooter>
                        <Button variant="ghost" mr={3} onClick={onClose} color="gray.300" _hover={{ bg: 'whiteAlpha.100' }}>
                            Cancel
                        </Button>
                        <Button colorScheme="red" onClick={handleArchive}>
                            Archive
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </AdminLayout>
    );
};

export default AdminAgentsPage;
