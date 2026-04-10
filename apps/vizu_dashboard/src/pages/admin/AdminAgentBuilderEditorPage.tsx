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
    useToast,
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
    const toast = useToast();
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
                navigate(`/dashboard/admin/agent-builder/${result.id}`, { replace: true });
            }
        }
    };

    if (!initialized || loadingCatalog) {
        return (
            <AdminLayout>
                <Center minH="400px">
                    <VStack spacing={3}>
                        <Spinner size="lg" color="black" />
                        <Text color="gray.600">
                            {isNew ? 'Preparing editor...' : 'Loading agent...'}
                        </Text>
                    </VStack>
                </Center>
            </AdminLayout>
        );
    }

    return (
        <AdminLayout>
            <Box p={8} maxW="1000px" mx="auto">
                {/* Header */}
                <HStack justify="space-between" mb={6}>
                    <HStack spacing={4}>
                        <Button
                            variant="ghost"
                            leftIcon={<FiArrowLeft />}
                            onClick={() => navigate('/dashboard/admin/agent-builder')}
                        >
                            Back
                        </Button>
                        <VStack align="start" spacing={0}>
                            <Heading size="md">
                                {isNew ? 'Create New Agent' : `Edit: ${formData.name || 'Untitled'}`}
                            </Heading>
                            {editingAgentId && (
                                <Text fontSize="xs" color="gray.500">ID: {editingAgentId}</Text>
                            )}
                        </VStack>
                    </HStack>
                    <HStack spacing={3}>
                        {isDirty && (
                            <Badge colorScheme="orange" fontSize="xs">Unsaved changes</Badge>
                        )}
                        {saveError && (
                            <Text fontSize="xs" color="red.500">{saveError}</Text>
                        )}
                        <Button
                            leftIcon={saving ? undefined : (isDirty ? <FiSave /> : <FiCheck />)}
                            bg="black"
                            color="white"
                            _hover={{ bg: 'gray.800' }}
                            onClick={handleSave}
                            isLoading={saving}
                            isDisabled={!isDirty && !isNew}
                        >
                            {isNew ? 'Create' : 'Save'}
                        </Button>
                    </HStack>
                </HStack>

                <Divider mb={6} />

                {/* Tabbed Form */}
                <Tabs isLazy variant="enclosed" colorScheme="blackAlpha">
                    <TabList overflowX="auto" flexWrap="nowrap">
                        {TAB_LABELS.map((label) => (
                            <Tab key={label} fontSize="sm" whiteSpace="nowrap">
                                {label}
                            </Tab>
                        ))}
                    </TabList>

                    <TabPanels>
                        {/* A. Identity */}
                        <TabPanel>
                            <AgentIdentitySection
                                formData={formData}
                                setField={setField}
                            />
                        </TabPanel>

                        {/* B. Agent Config */}
                        <TabPanel>
                            <AgentConfigSection
                                agentConfig={formData.agent_config}
                                setAgentConfigField={setAgentConfigField}
                            />
                        </TabPanel>

                        {/* C. Tools */}
                        <TabPanel>
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
                        <TabPanel>
                            <PromptConfigSection
                                formData={formData}
                                setField={setField}
                                availablePrompts={availablePrompts}
                                loadingPrompts={loadingPrompts}
                            />
                        </TabPanel>

                        {/* E. Context Requirements */}
                        <TabPanel>
                            <ContextRequirementsSection
                                fields={formData.required_context}
                                addContextField={addContextField}
                                updateContextField={updateContextField}
                                removeContextField={removeContextField}
                                reorderContextFields={reorderContextFields}
                            />
                        </TabPanel>

                        {/* F. File Requirements */}
                        <TabPanel>
                            <FileRequirementsSection
                                formData={formData}
                                setField={setField}
                            />
                        </TabPanel>

                        {/* G. Workflow Preview */}
                        <TabPanel>
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
