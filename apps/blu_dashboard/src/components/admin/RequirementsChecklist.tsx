import {
    Box,
    VStack,
    HStack,
    Heading,
    Text,
    Progress,
    Badge,
    Icon,
    Input,
    FormControl,
    FormLabel,
    Button,
} from '@chakra-ui/react';
import { FiCheck, FiAlertCircle, FiInfo } from 'react-icons/fi';
import type { RequirementsStatus } from '../../services/standaloneAgentService';
import type { AgentCatalogEntry } from '../../services/standaloneAgentService';
import { useState, useEffect, useRef } from 'react';

interface RequirementsChecklistProps {
    agent: AgentCatalogEntry | null;
    requirements: RequirementsStatus | null;
    collectedContext: Record<string, string | boolean>;
    csvCount: number;
    docCount: number;
    googleConnected: boolean;
    onSaveField: (fieldName: string, value: string | boolean) => Promise<void>;
    onConnectGoogle: () => void;
    onFinalize: () => Promise<void>;
    saving: boolean;
    finalizing: boolean;
}

export const RequirementsChecklist = ({
    agent,
    requirements,
    collectedContext,
    csvCount,
    docCount,
    googleConnected,
    onSaveField,
    onConnectGoogle,
    onFinalize,
    saving: _saving,
    finalizing,
}: RequirementsChecklistProps) => {
    const [localValues, setLocalValues] = useState<Record<string, string>>({});
    const initializedRef = useRef(false);

    // Sync localValues from collectedContext when it changes externally
    useEffect(() => {
        const newValues: Record<string, string> = {};
        for (const [key, val] of Object.entries(collectedContext)) {
            newValues[key] = String(val || '');
        }
        setLocalValues((prev) => {
            // Only overwrite keys that haven't been locally edited yet or on first load
            if (!initializedRef.current) {
                initializedRef.current = true;
                return newValues;
            }
            // Merge: backend wins for keys not currently being edited
            const merged = { ...prev };
            for (const [key, val] of Object.entries(newValues)) {
                if (!(key in merged) || merged[key] === '') {
                    merged[key] = val;
                }
            }
            return merged;
        });
    }, [collectedContext]);

    if (!agent || !requirements) {
        return null;
    }

    const handleBlur = async (fieldName: string) => {
        const localVal = localValues[fieldName] || '';
        const remoteVal = String(collectedContext[fieldName] || '');
        if (localVal.trim() !== '' && localVal !== remoteVal) {
            await onSaveField(fieldName, localVal);
        }
    };

    const isComplete =
        requirements.completion_pct === 100 &&
        requirements.missing.length === 0 &&
        csvCount >= requirements.files_required.csv.min &&
        docCount >= requirements.files_required.document.min &&
        (!agent.requires_google || googleConnected);

    return (
        <Box borderWidth="1px" borderColor="rgba(255,255,255,0.08)" borderRadius="lg" bg="#1a1b2e" p={6}>
            <VStack align="stretch" spacing={6}>
                {/* Progress Bar */}
                <Box>
                    <HStack justify="space-between" mb={2}>
                        <Heading size="md" color="white">Progresso da Configuração</Heading>
                        <Badge
                            bgGradient={requirements.completion_pct === 100 ? 'linear(to-r, #06ffa5, #06d6a0)' : 'linear(to-r, #ff6b35, #ff006e)'}
                            color={requirements.completion_pct === 100 ? 'black' : 'white'}
                            fontSize="md"
                            px={3}
                            py={1}
                            borderRadius="full"
                        >
                            {Math.round(requirements.completion_pct)}%
                        </Badge>
                    </HStack>
                    <Progress
                        value={requirements.completion_pct}
                        borderRadius="full"
                        height="8px"
                        bg="rgba(255,255,255,0.08)"
                        sx={{ '& > div': { background: requirements.completion_pct === 100 ? 'linear-gradient(90deg, #06ffa5, #06d6a0)' : 'linear-gradient(90deg, #ff6b35, #ff006e)' } }}
                    />
                </Box>

                {/* Context Fields — always visible and editable */}
                {agent.required_context.filter((field: { required: boolean }) => field.required).length > 0 && (
                    <Box>
                        <Heading size="sm" mb={4}>
                            Informações Necessárias
                        </Heading>
                        <VStack align="stretch" spacing={3}>
                            {agent.required_context
                                .filter((field: { required: boolean }) => field.required)
                                .map((field: { field: string; label?: string; description?: string; type?: string; prompt_hint?: string }) => {
                                    const localVal = localValues[field.field] || '';
                                    const isFilled = localVal.trim().length > 0;

                                    return (
                                        <FormControl key={field.field}>
                                            <HStack justify="space-between">
                                                <FormLabel fontSize="sm" mb={0}>
                                                    {field.label}
                                                </FormLabel>
                                                {isFilled ? (
                                                    <Icon as={FiCheck} color="green.500" boxSize={4} />
                                                ) : (
                                                    <Icon as={FiAlertCircle} color="orange.500" boxSize={4} />
                                                )}
                                            </HStack>
                                            <Input
                                                placeholder={field.prompt_hint}
                                                value={localVal}
                                                onChange={(e) =>
                                                    setLocalValues((prev) => ({
                                                        ...prev,
                                                        [field.field]: e.target.value,
                                                    }))
                                                }
                                                onBlur={() => handleBlur(field.field)}
                                                size="sm"
                                                _placeholder={{ color: 'whiteAlpha.400' }}
                                            />
                                        </FormControl>
                                    );
                                })}
                        </VStack>
                    </Box>
                )}

                {/* Files Required */}
                {(requirements.files_required.csv.min > 0 || requirements.files_required.document.min > 0) && (
                    <Box>
                        <Heading size="sm" mb={3}>
                            Arquivos
                        </Heading>
                        <VStack align="stretch" spacing={2}>
                            {requirements.files_required.csv.min > 0 && (
                                <HStack justify="space-between">
                                    <Text fontSize="sm">
                                        Arquivos CSV: {csvCount}/{requirements.files_required.csv.min}
                                    </Text>
                                    {csvCount >= requirements.files_required.csv.min ? (
                                        <Icon as={FiCheck} color="green.500" boxSize={4} />
                                    ) : (
                                        <Badge colorScheme="orange" variant="outline">
                                            Necessário
                                        </Badge>
                                    )}
                                </HStack>
                            )}

                            {requirements.files_required.document.min > 0 && (
                                <HStack justify="space-between">
                                    <Text fontSize="sm">
                                        Documentos: {docCount}/{requirements.files_required.document.min}
                                    </Text>
                                    {docCount >= requirements.files_required.document.min ? (
                                        <Icon as={FiCheck} color="green.500" boxSize={4} />
                                    ) : (
                                        <Badge colorScheme="orange" variant="outline">
                                            Necessário
                                        </Badge>
                                    )}
                                </HStack>
                            )}
                        </VStack>
                    </Box>
                )}

                {/* Google Sheets */}
                {agent.requires_google && (
                    <Box>
                        <HStack justify="space-between" align="start">
                            <Box>
                                <Heading size="sm">Google Sheets</Heading>
                                <Text fontSize="sm" color="whiteAlpha.600">
                                    Conexão necessária para exportar dados
                                </Text>
                            </Box>
                            {googleConnected ? (
                                <Badge colorScheme="green">Conectado</Badge>
                            ) : (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={onConnectGoogle}
                                    fontSize="sm"
                                >
                                    Conectar
                                </Button>
                            )}
                        </HStack>
                    </Box>
                )}

                {/* Ready to Activate */}
                {isComplete && (
                    <Box bg="rgba(6,255,165,0.08)" borderWidth="1px" borderColor="rgba(6,255,165,0.18)" borderRadius="xl" p={4}>
                        <HStack spacing={2} mb={3}>
                            <Icon as={FiCheck} color="#06ffa5" boxSize={5} />
                            <Text fontWeight="medium" color="white">
                                Todas as configurações estão prontas!
                            </Text>
                        </HStack>
                        <Button
                            width="100%"
                            bgGradient="linear(to-r, #06ffa5, #06d6a0)"
                            color="black"
                            _hover={{ opacity: 0.9 }}
                            onClick={onFinalize}
                            isLoading={finalizing}
                            loadingText="Ativando..."
                        >
                            Ativar Agente
                        </Button>
                    </Box>
                )}

                {!isComplete && (
                    <Box bg="rgba(59,130,246,0.08)" borderWidth="1px" borderColor="rgba(59,130,246,0.18)" borderRadius="xl" p={4}>
                        <HStack spacing={2}>
                            <Icon as={FiInfo} color="#3b82f6" boxSize={4} />
                            <Text fontSize="sm" color="whiteAlpha.800">
                                Complete todos os requisitos para ativar o agente
                            </Text>
                        </HStack>
                    </Box>
                )}
            </VStack>
        </Box>
    );
};
