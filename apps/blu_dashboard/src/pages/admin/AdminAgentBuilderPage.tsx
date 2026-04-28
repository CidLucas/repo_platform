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
    IconButton,
    Switch,
    useDisclosure,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    Menu,
    MenuButton,
    MenuList,
    MenuItem,
    Icon,
} from '@chakra-ui/react';
import { FiPlus, FiMoreVertical, FiEdit, FiCopy, FiTrash2, FiTool, FiRotateCcw, FiArchive } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useAgentBuilder } from '../../hooks/useAgentBuilder';

const AdminAgentBuilderPage = () => {
    const navigate = useNavigate();
    const {
        agents,
        loadingCatalog,
        catalogError,
        deleteAgent,
        duplicateAgent,
        toggleActive,
    } = useAgentBuilder();

    const { isOpen, onOpen, onClose } = useDisclosure();
    const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
    const [showArchived, setShowArchived] = useState(false);
    const deleteTargetAgent = agents.find((a) => a.id === deleteTargetId);

    const filteredAgents = showArchived ? agents : agents.filter((a) => a.is_active);
    const archivedCount = agents.filter((a) => !a.is_active).length;

    const confirmDelete = (agentId: string) => {
        setDeleteTargetId(agentId);
        onOpen();
    };

    const handleDelete = async () => {
        if (deleteTargetId) {
            await deleteAgent(deleteTargetId);
            onClose();
            setDeleteTargetId(null);
        }
    };

    return (
        <AdminLayout>
            <Box p={8} maxW="1200px" mx="auto">
                <HStack justify="space-between" mb={6}>
                    <VStack align="start" spacing={1}>
                        <Heading size="lg">Agent Builder</Heading>
                        <Text color="gray.600" fontSize="sm">
                            Create, configure, and manage agents in the catalog
                        </Text>
                    </VStack>
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
                        <Button
                            leftIcon={<FiPlus />}
                            bg="black"
                            color="white"
                            _hover={{ bg: 'gray.800' }}
                            onClick={() => navigate('/dashboard/configurar/agent-builder/new')}
                        >
                            Create New Agent
                        </Button>
                    </HStack>
                </HStack>

                {loadingCatalog && (
                    <Center minH="300px">
                        <VStack spacing={3}>
                            <Spinner size="lg" color="black" />
                            <Text color="gray.600">Loading agent catalog...</Text>
                        </VStack>
                    </Center>
                )}

                {catalogError && !loadingCatalog && (
                    <Center minH="200px">
                        <Text color="red.500">{catalogError}</Text>
                    </Center>
                )}

                {!loadingCatalog && !catalogError && agents.length === 0 && (
                    <Center minH="300px">
                        <VStack spacing={3}>
                            <Text color="gray.600">No agents in the catalog yet.</Text>
                            <Button
                                variant="outline"
                                leftIcon={<FiPlus />}
                                onClick={() => navigate('/dashboard/configurar/agent-builder/new')}
                            >
                                Create your first agent
                            </Button>
                        </VStack>
                    </Center>
                )}

                {!loadingCatalog && !catalogError && agents.length > 0 && filteredAgents.length === 0 && (
                    <Center minH="200px">
                        <Text color="gray.500">No active agents. Toggle "archived" to see inactive agents.</Text>
                    </Center>
                )}

                {!loadingCatalog && !catalogError && filteredAgents.length > 0 && (
                    <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                        {filteredAgents.map((agent) => (
                            <Card
                                key={agent.id}
                                borderWidth="2px"
                                borderColor={agent.is_active ? 'gray.200' : 'gray.100'}
                                borderRadius="lg"
                                opacity={agent.is_active ? 1 : 0.6}
                                transition="all 0.2s"
                                _hover={{
                                    borderColor: 'gray.400',
                                    boxShadow: 'md',
                                }}
                            >
                                <CardHeader pb={2}>
                                    <HStack justify="space-between">
                                        <HStack spacing={2}>
                                            {agent.icon && (
                                                <Text fontSize="xl">{agent.icon}</Text>
                                            )}
                                            <Heading
                                                size="sm"
                                                textDecoration={agent.is_active ? 'none' : 'line-through'}
                                                color={agent.is_active ? 'inherit' : 'gray.400'}
                                            >
                                                {agent.name}
                                            </Heading>
                                            {!agent.is_active && (
                                                <Badge colorScheme="orange" fontSize="xs">
                                                    Archived
                                                </Badge>
                                            )}
                                        </HStack>
                                        <Menu>
                                            <MenuButton
                                                as={IconButton}
                                                icon={<FiMoreVertical />}
                                                variant="ghost"
                                                size="sm"
                                                aria-label="Agent actions"
                                            />
                                            <MenuList>
                                                <MenuItem
                                                    icon={<FiEdit />}
                                                    onClick={() => navigate(`/dashboard/configurar/agent-builder/${agent.id}`)}
                                                >
                                                    Edit
                                                </MenuItem>
                                                <MenuItem
                                                    icon={<FiCopy />}
                                                    onClick={() => duplicateAgent(agent.id)}
                                                >
                                                    Duplicate
                                                </MenuItem>
                                                {!agent.is_active && (
                                                    <MenuItem
                                                        icon={<FiRotateCcw />}
                                                        color="green.500"
                                                        onClick={() => toggleActive(agent.id, true)}
                                                    >
                                                        Restore
                                                    </MenuItem>
                                                )}
                                                {agent.is_active && (
                                                    <MenuItem
                                                        icon={<FiTrash2 />}
                                                        color="red.500"
                                                        onClick={() => confirmDelete(agent.id)}
                                                    >
                                                        Archive
                                                    </MenuItem>
                                                )}
                                            </MenuList>
                                        </Menu>
                                    </HStack>
                                </CardHeader>

                                <CardBody pt={0}>
                                    <VStack align="start" spacing={3}>
                                        <Text fontSize="sm" color="gray.600" noOfLines={2}>
                                            {agent.description || 'No description'}
                                        </Text>

                                        <HStack spacing={2} flexWrap="wrap">
                                            {agent.category && (
                                                <Badge colorScheme="blue" variant="outline" fontSize="xs">
                                                    {agent.category}
                                                </Badge>
                                            )}
                                            <Badge colorScheme="gray" variant="outline" fontSize="xs">
                                                {agent.tier_required}
                                            </Badge>
                                            <HStack spacing={1}>
                                                <Icon as={FiTool} boxSize={3} color="gray.500" />
                                                <Text fontSize="xs" color="gray.500">
                                                    {agent.agent_config.enabled_tools?.length ?? 0}
                                                </Text>
                                            </HStack>
                                        </HStack>

                                        <HStack justify="space-between" w="full">
                                            <Text fontSize="xs" color="gray.500">
                                                {agent.is_active ? 'Active' : 'Inactive'}
                                            </Text>
                                            <Switch
                                                size="sm"
                                                isChecked={agent.is_active}
                                                onChange={(e) => toggleActive(agent.id, e.target.checked)}
                                                colorScheme="green"
                                            />
                                        </HStack>
                                    </VStack>
                                </CardBody>
                            </Card>
                        ))}
                    </SimpleGrid>
                )}
            </Box>

            {/* Delete confirmation modal */}
            <Modal isOpen={isOpen} onClose={onClose} isCentered>
                <ModalOverlay />
                <ModalContent>
                    <ModalHeader>Archive Agent</ModalHeader>
                    <ModalCloseButton />
                    <ModalBody>
                        <Text>
                            Are you sure you want to archive{' '}
                            <strong>{deleteTargetAgent?.name}</strong>?
                        </Text>
                        <Text mt={2} fontSize="sm" color="gray.600">
                            This agent will be archived and hidden from users.
                            Existing sessions will continue to work.
                        </Text>
                    </ModalBody>
                    <ModalFooter>
                        <Button variant="ghost" mr={3} onClick={onClose}>
                            Cancel
                        </Button>
                        <Button colorScheme="red" onClick={handleDelete}>
                            Archive
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </AdminLayout>
    );
};

export default AdminAgentBuilderPage;
