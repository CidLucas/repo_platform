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
} from '@chakra-ui/react';
import { FiZap } from 'react-icons/fi';
import { useState } from 'react';
import type { AgentCatalogEntry } from '../../services/standaloneAgentService';

interface AgentSelectorProps {
    agents: AgentCatalogEntry[];
    selectedAgent: AgentCatalogEntry | null;
    loading: boolean;
    onSelectAgent: (agent: AgentCatalogEntry) => void;
    onCreateSession: (agentId: string) => Promise<void>;
}

export const AgentSelector = ({
    agents,
    selectedAgent,
    loading,
    onSelectAgent,
    onCreateSession,
}: AgentSelectorProps) => {
    const [startingAgentId, setStartingAgentId] = useState<string | null>(null);

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
            </SimpleGrid>
        </Box>
    );
};
