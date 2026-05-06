import { useState, useCallback, useEffect, useContext, useRef } from 'react';
import { AuthContext } from '@/contexts/AuthContext';
import {
    fetchCatalogAgentsAdmin,
    fetchCatalogAgent,
    createCatalogAgent,
    updateCatalogAgent,
    deleteCatalogAgent,
    duplicateCatalogAgent,
    fetchAvailableTools,
    validateTools,
    fetchAvailablePrompts,
    fetchCatalogNodes,
    type CatalogAgent,
    type CatalogAgentCreate,
    type CatalogAgentUpdate,
    type AgentConfigData,
    type ContextFieldDefinition,
    type FileRequirements,
    type ToolMetadata,
    type ValidateToolsResult,
    type PromptInfo,
    type WorkflowGraph,
    type CatalogNodeMetadata,
} from '@/services/agentBuilderService';

// ── Form Data ──────────────────────────────────────────────────

export interface AgentBuilderFormData {
    name: string;
    description: string;
    category: string;
    icon: string;
    tier_required: string;
    is_active: boolean;
    agent_config: AgentConfigData;
    prompt_name: string;
    required_context: ContextFieldDefinition[];
    required_files: FileRequirements;
    requires_google: boolean;
    workflow_graph: WorkflowGraph | null;
}

const EMPTY_FORM: AgentBuilderFormData = {
    name: '',
    description: '',
    category: '',
    icon: '',
    tier_required: 'BASIC',
    is_active: true,
    agent_config: {
        name: '',
        role: '',
        elicitation_strategy: 'support_triage',
        enabled_tools: [],
        max_turns: 20,
        model: 'openai:gpt-4o-mini',
    },
    prompt_name: '',
    required_context: [],
    required_files: {},
    requires_google: false,
    workflow_graph: null,
};

// ── State ──────────────────────────────────────────────────────

export interface AgentBuilderState {
    agents: CatalogAgent[];
    loadingCatalog: boolean;
    catalogError: string | null;

    editingAgentId: string | null;
    formData: AgentBuilderFormData;
    isDirty: boolean;

    availableTools: ToolMetadata[];
    loadingTools: boolean;
    availablePrompts: PromptInfo[];
    loadingPrompts: boolean;
    catalogNodes: CatalogNodeMetadata[];
    loadingNodes: boolean;

    toolValidation: ValidateToolsResult | null;
    validating: boolean;

    saving: boolean;
    saveError: string | null;

    // Validation errors returned instead of toast
    validationErrors: string[];
}

// ── Hook ───────────────────────────────────────────────────────

export function useAgentBuilder() {
    const auth = useContext(AuthContext);

    const [state, setState] = useState<AgentBuilderState>({
        agents: [],
        loadingCatalog: true,
        catalogError: null,
        editingAgentId: null,
        formData: { ...EMPTY_FORM, agent_config: { ...EMPTY_FORM.agent_config } },
        isDirty: false,
        availableTools: [],
        loadingTools: false,
        availablePrompts: [],
        loadingPrompts: false,
        catalogNodes: [],
        loadingNodes: false,
        toolValidation: null,
        validating: false,
        saving: false,
        saveError: null,
        validationErrors: [],
    });

    const accessToken = auth?.session?.access_token;
    const validateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // ── Load catalog on mount ──────────────────────────────────

    const loadCatalog = useCallback(async () => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingCatalog: true, catalogError: null }));
            const agents = await fetchCatalogAgentsAdmin(accessToken);
            setState((prev) => ({ ...prev, agents, loadingCatalog: false }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load catalog';
            setState((prev) => ({ ...prev, catalogError: message, loadingCatalog: false }));
        }
    }, [accessToken]);

    useEffect(() => {
        loadCatalog();
    }, [loadCatalog]);

    // ── Load available tools & prompts ─────────────────────────

    const loadTools = useCallback(async (tier: string) => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingTools: true }));
            const result = await fetchAvailableTools(tier, accessToken);
            setState((prev) => ({ ...prev, availableTools: result.tools, loadingTools: false }));
        } catch (err) {
            console.error('Failed to load tools:', err);
            setState((prev) => ({ ...prev, loadingTools: false }));
        }
    }, [accessToken]);

    const loadPrompts = useCallback(async () => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingPrompts: true }));
            const prompts = await fetchAvailablePrompts(accessToken);
            setState((prev) => ({ ...prev, availablePrompts: prompts, loadingPrompts: false }));
        } catch (err) {
            console.error('Failed to load prompts:', err);
            setState((prev) => ({ ...prev, loadingPrompts: false }));
        }
    }, [accessToken]);

    const loadNodes = useCallback(async () => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingNodes: true }));
            const nodes = await fetchCatalogNodes(accessToken);
            setState((prev) => ({ ...prev, catalogNodes: nodes, loadingNodes: false }));
        } catch (err) {
            console.error('Failed to load catalog nodes:', err);
            setState((prev) => ({ ...prev, loadingNodes: false }));
        }
    }, [accessToken]);

    // ── Workflow graph helpers ──────────────────────────────────

    const setWorkflowGraph = useCallback((graph: WorkflowGraph | null) => {
        setState((prev) => ({
            ...prev,
            formData: { ...prev.formData, workflow_graph: graph },
            isDirty: true,
        }));
    }, []);

    const resetWorkflowGraph = useCallback(() => {
        setState((prev) => ({
            ...prev,
            formData: { ...prev.formData, workflow_graph: null },
            isDirty: true,
        }));
    }, []);

    // ── Tool validation (debounced) ────────────────────────────

    const runToolValidation = useCallback(async (enabledTools: string[], tier: string) => {
        if (!accessToken || enabledTools.length === 0) {
            setState((prev) => ({ ...prev, toolValidation: null, validating: false }));
            return;
        }
        try {
            setState((prev) => ({ ...prev, validating: true }));
            const result = await validateTools(enabledTools, tier, accessToken);
            setState((prev) => ({ ...prev, toolValidation: result, validating: false }));
        } catch (err) {
            console.error('Tool validation failed:', err);
            setState((prev) => ({ ...prev, validating: false }));
        }
    }, [accessToken]);

    const triggerToolValidation = useCallback((enabledTools: string[], tier: string) => {
        if (validateTimeoutRef.current) clearTimeout(validateTimeoutRef.current);
        validateTimeoutRef.current = setTimeout(() => {
            runToolValidation(enabledTools, tier);
        }, 500);
    }, [runToolValidation]);

    // ── Form field setters ─────────────────────────────────────

    const setField = useCallback(<K extends keyof AgentBuilderFormData>(
        field: K,
        value: AgentBuilderFormData[K],
    ) => {
        setState((prev) => {
            const next = { ...prev, formData: { ...prev.formData, [field]: value }, isDirty: true };

            if (field === 'name' && typeof value === 'string') {
                next.formData.agent_config = {
                    ...next.formData.agent_config,
                    name: value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, ''),
                };
            }

            if (field === 'tier_required') {
                loadTools(value as string);
                triggerToolValidation(next.formData.agent_config.enabled_tools, value as string);
            }

            return next;
        });
    }, [loadTools, triggerToolValidation]);

    const setAgentConfigField = useCallback(<K extends keyof AgentConfigData>(
        field: K,
        value: AgentConfigData[K],
    ) => {
        setState((prev) => {
            const newConfig = { ...prev.formData.agent_config, [field]: value };
            const next = {
                ...prev,
                formData: { ...prev.formData, agent_config: newConfig },
                isDirty: true,
            };

            if (field === 'enabled_tools') {
                triggerToolValidation(value as string[], prev.formData.tier_required);
            }

            return next;
        });
    }, [triggerToolValidation]);

    // ── Tool helpers ───────────────────────────────────────────

    const addTool = useCallback((toolName: string) => {
        setState((prev) => {
            const current = prev.formData.agent_config.enabled_tools;
            if (current.includes(toolName)) return prev;
            const updated = [...current, toolName];
            triggerToolValidation(updated, prev.formData.tier_required);
            return {
                ...prev,
                formData: {
                    ...prev.formData,
                    agent_config: { ...prev.formData.agent_config, enabled_tools: updated },
                },
                isDirty: true,
            };
        });
    }, [triggerToolValidation]);

    const removeTool = useCallback((toolName: string) => {
        setState((prev) => {
            const updated = prev.formData.agent_config.enabled_tools.filter((t) => t !== toolName);
            triggerToolValidation(updated, prev.formData.tier_required);
            return {
                ...prev,
                formData: {
                    ...prev.formData,
                    agent_config: { ...prev.formData.agent_config, enabled_tools: updated },
                },
                isDirty: true,
            };
        });
    }, [triggerToolValidation]);

    // ── Context field helpers ──────────────────────────────────

    const addContextField = useCallback((field: ContextFieldDefinition) => {
        setState((prev) => ({
            ...prev,
            formData: {
                ...prev.formData,
                required_context: [...prev.formData.required_context, field],
            },
            isDirty: true,
        }));
    }, []);

    const updateContextField = useCallback((index: number, field: ContextFieldDefinition) => {
        setState((prev) => {
            const updated = [...prev.formData.required_context];
            updated[index] = field;
            return {
                ...prev,
                formData: { ...prev.formData, required_context: updated },
                isDirty: true,
            };
        });
    }, []);

    const removeContextField = useCallback((index: number) => {
        setState((prev) => ({
            ...prev,
            formData: {
                ...prev.formData,
                required_context: prev.formData.required_context.filter((_, i) => i !== index),
            },
            isDirty: true,
        }));
    }, []);

    const reorderContextFields = useCallback((fromIndex: number, toIndex: number) => {
        setState((prev) => {
            const updated = [...prev.formData.required_context];
            const [moved] = updated.splice(fromIndex, 1);
            updated.splice(toIndex, 0, moved);
            return {
                ...prev,
                formData: { ...prev.formData, required_context: updated },
                isDirty: true,
            };
        });
    }, []);

    // ── Save / Create / Update ─────────────────────────────────

    const save = useCallback(async (): Promise<CatalogAgent | null> => {
        if (!accessToken) return null;

        const { formData, editingAgentId } = state;
        const errors: string[] = [];

        if (!formData.name.trim()) errors.push('Agent name is required');
        if (!formData.agent_config.role.trim()) errors.push('Agent role is required');
        if (!formData.prompt_name.trim()) errors.push('Prompt name is required');

        if (errors.length > 0) {
            setState((prev) => ({ ...prev, validationErrors: errors }));
            return null;
        }

        try {
            setState((prev) => ({ ...prev, saving: true, saveError: null, validationErrors: [] }));

            let saved: CatalogAgent;

            if (editingAgentId) {
                const updateData: CatalogAgentUpdate = { ...formData };
                saved = await updateCatalogAgent(editingAgentId, updateData, accessToken);
            } else {
                const createData: CatalogAgentCreate = { ...formData };
                saved = await createCatalogAgent(createData, accessToken);
            }

            const agents = await fetchCatalogAgentsAdmin(accessToken);
            setState((prev) => ({
                ...prev,
                agents,
                saving: false,
                isDirty: false,
                editingAgentId: saved.id,
            }));

            return saved;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to save agent';
            setState((prev) => ({ ...prev, saving: false, saveError: message }));
            return null;
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accessToken, state.formData, state.editingAgentId]);

    // ── Load agent for editing ─────────────────────────────────

    const loadAgent = useCallback(async (agentId: string) => {
        if (!accessToken) return;
        try {
            setState((prev) => ({ ...prev, loadingCatalog: true }));
            const agent = await fetchCatalogAgent(agentId, accessToken);

            const formData: AgentBuilderFormData = {
                name: agent.name,
                description: agent.description ?? '',
                category: agent.category ?? '',
                icon: agent.icon ?? '',
                tier_required: agent.tier_required,
                is_active: agent.is_active,
                agent_config: {
                    name: agent.agent_config.name,
                    role: agent.agent_config.role,
                    elicitation_strategy: agent.agent_config.elicitation_strategy ?? 'support_triage',
                    enabled_tools: agent.agent_config.enabled_tools ?? [],
                    max_turns: agent.agent_config.max_turns ?? 20,
                    model: agent.agent_config.model ?? 'openai:gpt-4o-mini',
                    metadata: agent.agent_config.metadata,
                },
                prompt_name: agent.prompt_name,
                required_context: agent.required_context ?? [],
                required_files: agent.required_files ?? {},
                requires_google: agent.requires_google,
                workflow_graph: agent.workflow_graph ?? null,
            };

            setState((prev) => ({
                ...prev,
                editingAgentId: agentId,
                formData,
                isDirty: false,
                loadingCatalog: false,
            }));

            await Promise.all([loadTools(agent.tier_required), loadPrompts(), loadNodes()]);

            if (agent.agent_config.enabled_tools?.length) {
                triggerToolValidation(agent.agent_config.enabled_tools, agent.tier_required);
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load agent';
            setState((prev) => ({ ...prev, loadingCatalog: false, saveError: message }));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accessToken, loadTools, loadPrompts, triggerToolValidation]);

    // ── Reset form ─────────────────────────────────────────────

    const reset = useCallback(() => {
        setState((prev) => ({
            ...prev,
            editingAgentId: null,
            formData: { ...EMPTY_FORM, agent_config: { ...EMPTY_FORM.agent_config } },
            isDirty: false,
            toolValidation: null,
            saveError: null,
            validationErrors: [],
        }));
    }, []);

    const initNewAgent = useCallback(async () => {
        reset();
        await Promise.all([loadTools('BASIC'), loadPrompts(), loadNodes()]);
    }, [reset, loadTools, loadPrompts, loadNodes]);

    // ── Validate current form ──────────────────────────────────

    const validate = useCallback(async (): Promise<boolean> => {
        const { formData } = state;
        const errors: string[] = [];

        if (!formData.name.trim()) errors.push('Name is required');
        if (!formData.agent_config.role.trim()) errors.push('Role is required');
        if (!formData.prompt_name.trim()) errors.push('Prompt name is required');
        if (formData.agent_config.max_turns < 1) errors.push('Max turns must be at least 1');

        if (errors.length > 0) {
            setState((prev) => ({ ...prev, validationErrors: errors }));
            return false;
        }

        if (formData.agent_config.enabled_tools.length > 0 && accessToken) {
            const result = await validateTools(
                formData.agent_config.enabled_tools,
                formData.tier_required,
                accessToken,
            );
            setState((prev) => ({ ...prev, toolValidation: result }));
            if (!result.valid) {
                setState((prev) => ({ ...prev, validationErrors: result.errors }));
                return false;
            }
        }

        setState((prev) => ({ ...prev, validationErrors: [] }));
        return true;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [state.formData, accessToken]);

    // ── Delete agent ───────────────────────────────────────────

    const deleteAgent = useCallback(async (agentId: string) => {
        if (!accessToken) return;
        try {
            await deleteCatalogAgent(agentId, accessToken);
            const agents = await fetchCatalogAgentsAdmin(accessToken);
            setState((prev) => ({ ...prev, agents }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to delete agent';
            setState((prev) => ({ ...prev, saveError: message }));
        }
    }, [accessToken]);

    // ── Duplicate agent ────────────────────────────────────────

    const duplicateAgent = useCallback(async (agentId: string) => {
        if (!accessToken) return null;
        try {
            const duplicated = await duplicateCatalogAgent(agentId, accessToken);
            const agents = await fetchCatalogAgentsAdmin(accessToken);
            setState((prev) => ({ ...prev, agents }));
            return duplicated;
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to duplicate agent';
            setState((prev) => ({ ...prev, saveError: message }));
            return null;
        }
    }, [accessToken]);

    // ── Toggle active ──────────────────────────────────────────

    const toggleActive = useCallback(async (agentId: string, isActive: boolean) => {
        if (!accessToken) return;
        try {
            await updateCatalogAgent(agentId, { is_active: isActive }, accessToken);
            const agents = await fetchCatalogAgentsAdmin(accessToken);
            setState((prev) => ({ ...prev, agents }));
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to update agent';
            setState((prev) => ({ ...prev, saveError: message }));
        }
    }, [accessToken]);

    // ── Return ─────────────────────────────────────────────────

    return {
        ...state,

        loadCatalog,
        deleteAgent,
        duplicateAgent,
        toggleActive,

        loadAgent,
        initNewAgent,
        reset,
        save,
        validate,

        setField,
        setAgentConfigField,

        addTool,
        removeTool,
        loadTools,

        addContextField,
        updateContextField,
        removeContextField,
        reorderContextFields,

        loadPrompts,

        loadNodes,
        setWorkflowGraph,
        resetWorkflowGraph,
    };
}
