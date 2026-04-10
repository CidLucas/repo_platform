import {
    Box,
    SimpleGrid,
    Card,
    CardBody,
    CardHeader,
    Heading,
    Text,
    Icon,
    Button,
    HStack,
    Badge,
    VStack,
    Spinner,
    Center,
    useDisclosure,
} from '@chakra-ui/react';
import { FiZap, FiPlus } from 'react-icons/fi';
import { useState } from 'react';
import type { AgentCatalogEntry } from '../../services/standaloneAgentService';
import { QuickCreateAgentModal } from './QuickCreateAgentModal';

interface AgentSelectorProps {
    agents: AgentCatalogEntry[];
    selectedAgent: AgentCatalogEntry | null;
    loading: boolean;
    onSelectAgent: (agent: AgentCatalogEntry) => void;
    onCreateSession: (agentId: string) => Promise<void>;
    onAgentCreated?: () => void;
    isAdmin?: boolean;
}

export const AgentSelector = ({
    agents,
    selectedAgent,
    loading,
    onSelectAgent,
    onCreateSession,
    onAgentCreated,
    isAdmin = false,
}: AgentSelectorProps) => {
    const [startingAgentId, setStartingAgentId] = useState<string | null>(null);
    const { isOpen, onOpen, onClose } = useDisclosure();

    if (loading) {
        return (
            <Center minH="300px">
                <VStack spacing={3}>
                    <Spinner size="lg" color="black" />
                    <Text color="gray.600">Carregando catálogo de agentes...</Text>
                </VStack>
            </Center>
        );
    }

    if (agents.length === 0) {
        return (
            <Center minH="300px">
                <Text color="gray.600">Nenhum agente disponível no seu plano</Text>
            </Center>
        );
    }

    return (
        <Box>
            <Heading size="md" mb={2}>
                Selecione um Agente
            </Heading>
            <Text color="gray.600" mb={6} fontSize="sm">
                Clique em um agente para começar a configuração
            </Text>

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                {agents.map((agent) => {
                    const isStarting = startingAgentId === agent.id;
                    return (
                        <Card
                            key={agent.id}
                            borderWidth="2px"
                            borderColor={selectedAgent?.id === agent.id ? 'black' : 'gray.200'}
                            borderRadius="lg"
                            cursor={isStarting ? 'wait' : 'pointer'}
                            transition="all 0.2s"
                            _hover={{
                                borderColor: 'gray.400',
                                boxShadow: 'md',
                            }}
                            opacity={isStarting ? 0.7 : 1}
                            onClick={async () => {
                                if (startingAgentId) return;
                                setStartingAgentId(agent.id);
                                try {
                                    onSelectAgent(agent);
                                    await onCreateSession(agent.id);
                                } finally {
                                    setStartingAgentId(null);
                                }
                            }}
                        >
                            <CardHeader pb={3}>
                                <HStack justify="space-between" mb={3}>
                                    <Icon as={FiZap} boxSize={6} color="gray.600" />
                                    {isStarting && <Spinner size="sm" />}
                                </HStack>
                                <Heading size="sm">{agent.name}</Heading>
                            </CardHeader>

                            <CardBody>
                                <VStack align="start" spacing={3}>
                                    <Text fontSize="sm" color="gray.600">
                                        {agent.description}
                                    </Text>

                                    <HStack>
                                        <Badge colorScheme="blue" variant="outline" fontSize="xs">
                                            {agent.category}
                                        </Badge>
                                        {agent.requires_google && (
                                            <Badge colorScheme="orange" variant="outline" fontSize="xs">
                                                Google Sheets
                                            </Badge>
                                        )}
                                    </HStack>
                                </VStack>
                            </CardBody>
                        </Card>
                    );
                })}

                {isAdmin && (
                    <Card
                        borderWidth="2px"
                        borderColor="gray.300"
                        borderStyle="dashed"
                        borderRadius="lg"
                        cursor="pointer"
                        transition="all 0.2s"
                        _hover={{
                            borderColor: 'gray.500',
                            boxShadow: 'md',
                            bg: 'gray.50',
                        }}
                        onClick={onOpen}
                        minH="180px"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                    >
                        <CardBody textAlign="center">
                            <VStack spacing={3}>
                                <Icon as={FiPlus} boxSize={8} color="gray.400" />
                                <Text fontWeight="medium" color="gray.500">
                                    Create Custom Agent
                                </Text>
                            </VStack>
                        </CardBody>
                    </Card>
                )}
            </SimpleGrid>

            {isAdmin && (
                <QuickCreateAgentModal
                    isOpen={isOpen}
                    onClose={onClose}
                    onCreated={onAgentCreated}
                />
            )}
        </Box>
    );
};
