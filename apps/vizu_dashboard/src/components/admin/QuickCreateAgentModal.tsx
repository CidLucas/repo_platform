import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    FormControl,
    FormLabel,
    Input,
    Textarea,
    Select,
    Button,
    VStack,
    HStack,
    Checkbox,
    SimpleGrid,
    Text,
    Spinner,
    useToast,
    Divider,
} from '@chakra-ui/react';
import { useState, useEffect, useCallback, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiArrowRight } from 'react-icons/fi';
import { AuthContext } from '../../contexts/AuthContext';
import {
    createCatalogAgent,
    fetchAvailableTools,
    type ToolMetadata,
    type CatalogAgentCreate,
} from '../../services/agentBuilderService';

interface QuickCreateAgentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onCreated?: () => void;
}

const MODEL_OPTIONS = [
    { value: 'openai:gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'openai:gpt-4o', label: 'GPT-4o' },
    { value: 'anthropic:claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
];

const CATEGORY_OPTIONS = [
    'data_analyst',
    'report_generator',
    'knowledge_assistant',
    'support_agent',
    'custom',
];

export const QuickCreateAgentModal = ({
    isOpen,
    onClose,
    onCreated,
}: QuickCreateAgentModalProps) => {
    const auth = useContext(AuthContext);
    const toast = useToast();
    const navigate = useNavigate();

    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [category, setCategory] = useState('custom');
    const [model, setModel] = useState('openai:gpt-4o-mini');
    const [selectedTools, setSelectedTools] = useState<string[]>([]);
    const [availableTools, setAvailableTools] = useState<ToolMetadata[]>([]);
    const [loadingTools, setLoadingTools] = useState(false);
    const [saving, setSaving] = useState(false);

    const accessToken = auth?.session?.access_token;

    const loadTools = useCallback(async () => {
        if (!accessToken) return;
        setLoadingTools(true);
        try {
            const result = await fetchAvailableTools('BASIC', accessToken);
            setAvailableTools(result.tools);
        } catch (err) {
            console.error('Failed to load tools:', err);
        } finally {
            setLoadingTools(false);
        }
    }, [accessToken]);

    useEffect(() => {
        if (isOpen) {
            loadTools();
        }
    }, [isOpen, loadTools]);

    const resetForm = () => {
        setName('');
        setDescription('');
        setCategory('custom');
        setModel('openai:gpt-4o-mini');
        setSelectedTools([]);
    };

    const handleClose = () => {
        resetForm();
        onClose();
    };

    const toggleTool = (toolName: string) => {
        setSelectedTools((prev) =>
            prev.includes(toolName)
                ? prev.filter((t) => t !== toolName)
                : [...prev, toolName],
        );
    };

    const handleCreate = async () => {
        if (!accessToken) return;
        if (!name.trim()) {
            toast({ title: 'Name is required', status: 'warning', duration: 2000 });
            return;
        }

        setSaving(true);
        try {
            const slug = name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
            const data: CatalogAgentCreate = {
                name,
                description: description || undefined,
                category,
                agent_config: {
                    name: slug,
                    role: description || `${name} agent`,
                    elicitation_strategy: 'support_triage',
                    enabled_tools: selectedTools,
                    max_turns: 20,
                    model,
                },
                prompt_name: '',
                tier_required: 'BASIC',
                is_active: true,
            };

            await createCatalogAgent(data, accessToken);
            toast({ title: 'Agent created!', status: 'success', duration: 2000 });
            handleClose();
            onCreated?.();
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to create agent';
            toast({ title: 'Error', description: message, status: 'error', duration: 4000 });
        } finally {
            setSaving(false);
        }
    };

    const handleAdvanced = () => {
        handleClose();
        navigate('/dashboard/admin/agent-builder/new');
    };

    return (
        <Modal isOpen={isOpen} onClose={handleClose} size="xl">
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>Create Custom Agent</ModalHeader>
                <ModalCloseButton />

                <ModalBody>
                    <VStack spacing={4} align="stretch">
                        <FormControl isRequired>
                            <FormLabel>Name</FormLabel>
                            <Input
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="My Custom Agent"
                            />
                        </FormControl>

                        <FormControl>
                            <FormLabel>Description</FormLabel>
                            <Textarea
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                                placeholder="What does this agent do?"
                                rows={2}
                            />
                        </FormControl>

                        <HStack spacing={4}>
                            <FormControl>
                                <FormLabel>Category</FormLabel>
                                <Select
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                >
                                    {CATEGORY_OPTIONS.map((cat) => (
                                        <option key={cat} value={cat}>
                                            {cat.replace(/_/g, ' ')}
                                        </option>
                                    ))}
                                </Select>
                            </FormControl>

                            <FormControl>
                                <FormLabel>Model</FormLabel>
                                <Select
                                    value={model}
                                    onChange={(e) => setModel(e.target.value)}
                                >
                                    {MODEL_OPTIONS.map((m) => (
                                        <option key={m.value} value={m.value}>
                                            {m.label}
                                        </option>
                                    ))}
                                </Select>
                            </FormControl>
                        </HStack>

                        <FormControl>
                            <FormLabel>Tools</FormLabel>
                            {loadingTools ? (
                                <HStack>
                                    <Spinner size="sm" />
                                    <Text fontSize="sm" color="gray.500">Loading tools...</Text>
                                </HStack>
                            ) : availableTools.length === 0 ? (
                                <Text fontSize="sm" color="gray.500">No tools available</Text>
                            ) : (
                                <SimpleGrid columns={2} spacing={2}>
                                    {availableTools.map((tool) => (
                                        <Checkbox
                                            key={tool.name}
                                            isChecked={selectedTools.includes(tool.name)}
                                            onChange={() => toggleTool(tool.name)}
                                            size="sm"
                                        >
                                            <Text fontSize="sm">{tool.name}</Text>
                                        </Checkbox>
                                    ))}
                                </SimpleGrid>
                            )}
                        </FormControl>
                    </VStack>
                </ModalBody>

                <ModalFooter>
                    <VStack w="full" spacing={3}>
                        <HStack w="full" justify="space-between">
                            <Button variant="ghost" onClick={handleClose}>
                                Cancel
                            </Button>
                            <HStack>
                                <Button
                                    colorScheme="blackAlpha"
                                    bg="black"
                                    color="white"
                                    onClick={handleCreate}
                                    isLoading={saving}
                                    isDisabled={!name.trim()}
                                >
                                    Create Agent
                                </Button>
                            </HStack>
                        </HStack>
                        <Divider />
                        <Button
                            variant="link"
                            size="sm"
                            color="gray.600"
                            rightIcon={<FiArrowRight />}
                            onClick={handleAdvanced}
                        >
                            Advanced Configuration
                        </Button>
                    </VStack>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};
