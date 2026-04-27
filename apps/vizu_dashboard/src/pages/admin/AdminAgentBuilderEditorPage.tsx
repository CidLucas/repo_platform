import {
    Box,
    Heading,
    Text,
    Button,
    HStack,
    VStack,
    Spinner,
    Center,
    Tabs,
    TabList,
    Tab,
    TabPanels,
    TabPanel,
    Badge,
    Divider,
} from '@chakra-ui/react';
import { FiArrowLeft, FiSave, FiCheck } from 'react-icons/fi';
import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useAgentBuilder } from '../../hooks/useAgentBuilder';
import { AgentIdentitySection } from '../../components/admin/builder/AgentIdentitySection';
import { AgentConfigSection } from '../../components/admin/builder/AgentConfigSection';
import { ToolSelectionSection } from '../../components/admin/builder/ToolSelectionSection';
import { PromptConfigSection } from '../../components/admin/builder/PromptConfigSection';
import { ContextRequirementsSection } from '../../components/admin/builder/ContextRequirementsSection';
import { FileRequirementsSection } from '../../components/admin/builder/FileRequirementsSection';
import { WorkflowPreviewSection } from '../../components/admin/builder/WorkflowPreviewSection';

const TAB_LABELS = [
    'A. Identity',
    'B. Agent Config',
    'C. Tools',
    'D. Prompt',
    'E. Context',
    'F. Files',
    'G. Workflow',
];

const AdminAgentBuilderEditorPage = () => {
    const { agentId } = useParams<{ agentId: string }>();
    const navigate = useNavigate();
    const isNew = agentId === 'new';

    const {
        formData,
        editingAgentId,
        isDirty,
        loadingCatalog,
        saving,
        saveError,
        // Tools
        availableTools,
        loadingTools,
        toolValidation,
        validating,
        // Prompts
        availablePrompts,
        loadingPrompts,
        // Workflow
        catalogNodes,
        loadingNodes,
        setWorkflowGraph,
        resetWorkflowGraph,
        // Actions
        loadAgent,
        initNewAgent,
        save,
        validate,
        setField,
        setAgentConfigField,
        addTool,
        removeTool,
        // Context
        addContextField,
        updateContextField,
        removeContextField,
        reorderContextFields,
    } = useAgentBuilder();

    const [initialized, setInitialized] = useState(false);

    useEffect(() => {
        if (initialized) return;
        if (isNew) {
            initNewAgent().then(() => setInitialized(true));
        } else if (agentId) {
            loadAgent(agentId).then(() => setInitialized(true));
        }
    }, [agentId, isNew, initNewAgent, loadAgent, initialized]);

    const handleSave = async () => {
        const valid = await validate();
        if (!valid) return;
        const result = await save();
        if (result) {
            if (isNew) {
                navigate(`/dashboard/configurar/agent-builder/${result.id}`, { replace: true });
            }
        }
    };

    if (!initialized || loadingCatalog) {
        return (
            <AdminLayout>
                <Center minH="400px">
                    <VStack spacing={3}>
                        <Spinner size="lg" color="orange.400" />
                        <Text color="gray.400">
                            {isNew ? 'Preparing editor...' : 'Loading agent...'}
                        </Text>
                    </VStack>
                </Center>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
            <Box
                p={8}
                maxW="1200px"
                mx="auto"
                sx={{
                    '.chakra-input, .chakra-textarea, .chakra-select, .chakra-numberinput__field': {
                        bg: '#14151f',
                        color: 'white',
                        borderColor: 'rgba(255,255,255,0.08)',
                    },
                    '.chakra-input::placeholder, .chakra-textarea::placeholder': {
                        color: 'rgba(255,255,255,0.4)',
                    },
                    '.chakra-input[readonly], .chakra-textarea[readonly], .chakra-select[readonly]': {
                        bg: 'rgba(255,255,255,0.04)',
                        color: 'whiteAlpha.700',
                    },
                    '.chakra-input:hover, .chakra-textarea:hover, .chakra-select:hover': {
                        borderColor: 'rgba(255,255,255,0.16)',
                    },
                    '.chakra-input:focus, .chakra-textarea:focus, .chakra-select:focus': {
                        borderColor: '#ff6b35',
                        boxShadow: '0 0 0 1px #ff6b35',
                    },
                    '.chakra-form__label, .chakra-text, .chakra-heading': {
                        color: 'white',
                    },
                    '.chakra-table th': {
                        color: 'whiteAlpha.700',
                        borderColor: 'rgba(255,255,255,0.08)',
                    },
                    '.chakra-table td': {
                        color: 'white',
                        borderColor: 'rgba(255,255,255,0.06)',
                    },
                }}
            >
                {/* Header */}
                <HStack justify="space-between" mb={6} align="flex-start">
                    <HStack spacing={4} align="flex-start">
                        <Button
                            variant="ghost"
                            leftIcon={<FiArrowLeft />}
                            onClick={() => navigate('/dashboard/configurar/agent-builder')}
                            color="white"
                            _hover={{ bg: 'whiteAlpha.100' }}
                        >
                            Back
                        </Button>
                        <VStack align="start" spacing={0}>
                            <Heading size="lg" fontFamily="'Playfair Display', serif" fontWeight="400">
                                <Text as="span" color="white">
                                    {isNew ? 'Create ' : 'Edit '}
                                </Text>
                                <Text
                                    as="span"
                                    bgGradient="linear(to-r, #ff6b35, #ff006e)"
                                    bgClip="text"
                                >
                                    {isNew ? 'Agent' : (formData.name || 'Untitled')}
                                </Text>
                            </Heading>
                            <Text fontSize="sm" color="gray.400">
                                Configure identity, tools, prompts, context and workflow.
                            </Text>
                            {editingAgentId && (
                                <Text fontSize="xs" color="gray.500">ID: {editingAgentId}</Text>
                            )}
                        </VStack>
                    </HStack>
                    <HStack spacing={3}>
                        {isDirty && (
                            <Badge bg="orange.500" color="white" fontSize="xs">Unsaved changes</Badge>
                        )}
                        {saveError && (
                            <Text fontSize="xs" color="red.300">{saveError}</Text>
                        )}
                        <Button
                            leftIcon={saving ? undefined : (isDirty ? <FiSave /> : <FiCheck />)}
                            bgGradient="linear(to-r, #ff6b35, #ff006e)"
                            color="white"
                            _hover={{ opacity: 0.9 }}
                            boxShadow="0 8px 24px rgba(255,107,53,0.25)"
                            onClick={handleSave}
                            isLoading={saving}
                            isDisabled={!isDirty && !isNew}
                        >
                            {isNew ? 'Create' : 'Save'}
                        </Button>
                    </HStack>
                </HStack>

                <Divider mb={6} borderColor="rgba(255,255,255,0.08)" />

                {/* Tabbed Form */}
                <Tabs
                    isLazy
                    variant="unstyled"
                    colorScheme="blackAlpha"
                    bg="#1a1b2e"
                    borderWidth="1px"
                    borderColor="rgba(255,255,255,0.08)"
                    borderRadius="2xl"
                    p={4}
                >
                    <TabList overflowX="auto" flexWrap="nowrap" gap={2} pb={4} borderBottomWidth="1px" borderColor="rgba(255,255,255,0.08)">
                        {TAB_LABELS.map((label) => (
                            <Tab
                                key={label}
                                fontSize="sm"
                                whiteSpace="nowrap"
                                color="gray.400"
                                borderRadius="full"
                                _selected={{
                                    color: 'white',
                                    bgGradient: 'linear(to-r, #ff6b35, #ff006e)',
                                }}
                                _hover={{ bg: 'whiteAlpha.100', color: 'white' }}
                            >
                                {label}
                            </Tab>
                        ))}
                    </TabList>

                    <TabPanels>
                        {/* A. Identity */}
                        <TabPanel px={2} pt={6}>
                            <AgentIdentitySection
                                formData={formData}
                                setField={setField}
                            />
                        </TabPanel>

                        {/* B. Agent Config */}
                        <TabPanel px={2} pt={6}>
                            <AgentConfigSection
                                agentConfig={formData.agent_config}
                                setAgentConfigField={setAgentConfigField}
                            />
                        </TabPanel>

                        {/* C. Tools */}
                        <TabPanel px={2} pt={6}>
                            <ToolSelectionSection
                                availableTools={availableTools}
                                enabledTools={formData.agent_config.enabled_tools}
                                loadingTools={loadingTools}
                                toolValidation={toolValidation}
                                validating={validating}
                                addTool={addTool}
                                removeTool={removeTool}
                            />
                        </TabPanel>

                        {/* D. Prompt */}
                        <TabPanel px={2} pt={6}>
                            <PromptConfigSection
                                formData={formData}
                                setField={setField}
                                availablePrompts={availablePrompts}
                                loadingPrompts={loadingPrompts}
                            />
                        </TabPanel>

                        {/* E. Context Requirements */}
                        <TabPanel px={2} pt={6}>
                            <ContextRequirementsSection
                                fields={formData.required_context}
                                addContextField={addContextField}
                                updateContextField={updateContextField}
                                removeContextField={removeContextField}
                                reorderContextFields={reorderContextFields}
                            />
                        </TabPanel>

                        {/* F. File Requirements */}
                        <TabPanel px={2} pt={6}>
                            <FileRequirementsSection
                                formData={formData}
                                setField={setField}
                            />
                        </TabPanel>

                        {/* G. Workflow Preview */}
                        <TabPanel px={2} pt={6}>
                            <WorkflowPreviewSection
                                formData={formData}
                                catalogNodes={catalogNodes}
                                loadingNodes={loadingNodes}
                                onWorkflowGraphChange={setWorkflowGraph}
                                onResetToDefault={resetWorkflowGraph}
                            />
                        </TabPanel>
                    </TabPanels>
                </Tabs>
            </Box>
        </AdminLayout>
    );
};

export default AdminAgentBuilderEditorPage;
