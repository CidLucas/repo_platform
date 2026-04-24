import {
    Box,
    SimpleGrid,
    Card,
    CardBody,
    CardHeader,
    Heading,
    Text,
    Icon,
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
                    <Spinner size="lg" color="blue.400" />
                    <Text color="whiteAlpha.600">Carregando catálogo de agentes...</Text>
                </VStack>
            </Center>
        );
    }

    if (agents.length === 0) {
        return (
            <Center minH="300px">
                <Text color="whiteAlpha.600">Nenhum agente disponível no seu plano</Text>
            </Center>
        );
    }

    return (
        <Box>
            <Heading size="md" mb={2} color="white">
                Selecione um Agente
            </Heading>
            <Text color="whiteAlpha.600" mb={6} fontSize="sm">
                Clique em um agente para começar a configuração
            </Text>

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                {agents.map((agent) => {
                    const isStarting = startingAgentId === agent.id;
                    const isSelected = selectedAgent?.id === agent.id;
                    return (
                        <Card
                            key={agent.id}
                            borderWidth="1px"
                            borderColor={isSelected ? 'transparent' : 'rgba(255,255,255,0.08)'}
                            borderRadius="xl"
                            bg="#1a1b2e"
                            cursor={isStarting ? 'wait' : 'pointer'}
                            transition="all 0.2s"
                            position="relative"
                            overflow="hidden"
                            _hover={{
                                borderColor: 'rgba(255,255,255,0.2)',
                                boxShadow: '0 12px 32px rgba(0,0,0,0.32)',
                                transform: 'translateY(-2px)',
                            }}
                            _before={{
                                content: '""',
                                position: 'absolute',
                                inset: 0,
                                borderRadius: 'inherit',
                                padding: isSelected ? '1px' : '0',
                                bgGradient: isSelected ? 'linear(to-r, #ff6b35, #ff006e)' : 'none',
                                WebkitMask: isSelected ? 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)' : undefined,
                                WebkitMaskComposite: isSelected ? 'xor' : undefined,
                                pointerEvents: 'none',
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
                                    <Box
                                        w="48px"
                                        h="48px"
                                        borderRadius="xl"
                                        display="flex"
                                        alignItems="center"
                                        justifyContent="center"
                                        bgGradient="linear(to-br, #ff6b35, #ff006e)"
                                        boxShadow="0 8px 24px rgba(255,107,53,0.22)"
                                    >
                                        <Icon as={FiZap} boxSize={5} color="white" />
                                    </Box>
                                    {isStarting && <Spinner size="sm" color="orange.300" />}
                                </HStack>
                                <Heading size="sm" color="white">{agent.name}</Heading>
                            </CardHeader>

                            <CardBody>
                                <VStack align="start" spacing={3}>
                                    <Text fontSize="sm" color="whiteAlpha.600">
                                        {agent.description}
                                    </Text>

                                    <HStack>
                                        <Badge bg="rgba(255,255,255,0.06)" color="white" borderWidth="1px" borderColor="rgba(255,255,255,0.08)" fontSize="xs">
                                            {agent.category}
                                        </Badge>
                                        {agent.requires_google && (
                                            <Badge bg="rgba(255,107,53,0.14)" color="orange.200" borderWidth="1px" borderColor="rgba(255,107,53,0.22)" fontSize="xs">
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
                        borderColor="rgba(255,255,255,0.15)"
                        borderStyle="dashed"
                        borderRadius="lg"
                        bg="#1a1b2e"
                        cursor="pointer"
                        transition="all 0.2s"
                        _hover={{
                            borderColor: 'rgba(255,255,255,0.3)',
                            boxShadow: 'md',
                            bg: '#1e1f34',
                        }}
                        onClick={onOpen}
                        minH="180px"
                        display="flex"
                        alignItems="center"
                        justifyContent="center"
                    >
                        <CardBody textAlign="center">
                            <VStack spacing={3}>
                                <Icon as={FiPlus} boxSize={8} color="whiteAlpha.400" />
                                <Text fontWeight="medium" color="whiteAlpha.500">
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
