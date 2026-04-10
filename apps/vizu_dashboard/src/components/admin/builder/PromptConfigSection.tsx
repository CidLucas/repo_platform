import {
    Box,
    FormControl,
    FormLabel,
    Select,
    Text,
    Spinner,
    HStack,
    Badge,
    Input,
    InputGroup,
    InputLeftElement,
    Icon,
    VStack,
    Button,
    useDisclosure,
} from '@chakra-ui/react';
import { FiSearch, FiEdit2 } from 'react-icons/fi';
import { useState, useMemo } from 'react';
import type { PromptInfo } from '../../../services/agentBuilderService';
import type { AgentBuilderFormData } from '../../../hooks/useAgentBuilder';
import { PromptEditorModal } from './PromptEditorModal';

interface PromptConfigSectionProps {
    formData: AgentBuilderFormData;
    setField: <K extends keyof AgentBuilderFormData>(field: K, value: AgentBuilderFormData[K]) => void;
    availablePrompts: PromptInfo[];
    loadingPrompts: boolean;
}

export const PromptConfigSection = ({
    formData,
    setField,
    availablePrompts,
    loadingPrompts,
}: PromptConfigSectionProps) => {
    const [search, setSearch] = useState('');
    const { isOpen, onOpen, onClose } = useDisclosure();

    const filteredPrompts = useMemo(() => {
        if (!search) return availablePrompts;
        const q = search.toLowerCase();
        return availablePrompts.filter(
            (p) =>
                p.name.toLowerCase().includes(q) ||
                (p.category?.toLowerCase().includes(q)) ||
                (p.description?.toLowerCase().includes(q)),
        );
    }, [availablePrompts, search]);

    const selectedPrompt = availablePrompts.find((p) => p.name === formData.prompt_name);

    if (loadingPrompts) {
        return (
            <Box textAlign="center" py={8}>
                <Spinner size="lg" color="black" />
                <Text mt={2} color="gray.600">Loading prompts...</Text>
            </Box>
        );
    }

    return (
        <Box>
            <VStack align="stretch" spacing={4}>
                <InputGroup maxW="400px">
                    <InputLeftElement>
                        <Icon as={FiSearch} color="gray.400" />
                    </InputLeftElement>
                    <Input
                        placeholder="Search prompts..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </InputGroup>

                <FormControl isRequired>
                    <FormLabel>Prompt Name</FormLabel>
                    <Select
                        value={formData.prompt_name}
                        onChange={(e) => setField('prompt_name', e.target.value)}
                        placeholder="Select a prompt"
                    >
                        {filteredPrompts.map((prompt) => (
                            <option key={prompt.name} value={prompt.name}>
                                {prompt.name}
                                {prompt.source === 'langfuse' ? ' (Langfuse)' : ' (Built-in)'}
                            </option>
                        ))}
                    </Select>
                </FormControl>

                {selectedPrompt && (
                    <Box p={4} borderWidth="1px" borderColor="gray.200" borderRadius="md" bg="gray.50">
                        <HStack mb={2}>
                            <Text fontWeight="medium">{selectedPrompt.name}</Text>
                            <Badge
                                colorScheme={selectedPrompt.source === 'langfuse' ? 'purple' : 'blue'}
                                fontSize="xs"
                            >
                                {selectedPrompt.source}
                            </Badge>
                            {selectedPrompt.category && (
                                <Badge colorScheme="gray" fontSize="xs">
                                    {selectedPrompt.category}
                                </Badge>
                            )}
                        </HStack>
                        {selectedPrompt.description && (
                            <Text fontSize="sm" color="gray.600">
                                {selectedPrompt.description}
                            </Text>
                        )}
                        {selectedPrompt.source === 'langfuse' && (
                            <Button
                                size="sm"
                                variant="outline"
                                leftIcon={<FiEdit2 />}
                                mt={2}
                                onClick={onOpen}
                            >
                                Edit Prompt
                            </Button>
                        )}
                    </Box>
                )}

                {availablePrompts.length === 0 && (
                    <Text color="gray.600" fontSize="sm">
                        No prompts available. Create prompts in Langfuse or via the prompt loader.
                    </Text>
                )}
            </VStack>

            {selectedPrompt && (
                <PromptEditorModal
                    isOpen={isOpen}
                    onClose={onClose}
                    promptName={selectedPrompt.name}
                    requiredContext={formData.required_context?.map((c) => ({
                        field: c.field,
                        label: c.label,
                    }))}
                />
            )}
        </Box>
    );
};

export default PromptConfigSection;
