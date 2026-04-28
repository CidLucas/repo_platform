import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import {
    Box,
    HStack,
    Text,
    Badge,
    Button,
    useDisclosure,
} from '@chakra-ui/react';
import {
    ReactFlow,
    Background,
    Controls,
    type Node,
    type Edge,
    type NodeTypes,
    type Connection,
    type OnNodesChange,
    type OnEdgesChange,
    MarkerType,
    BackgroundVariant,
    applyNodeChanges,
    applyEdgeChanges,
    addEdge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FiEdit3, FiRotateCcw } from 'react-icons/fi';
import WorkflowNode, { type WorkflowNodeData } from './WorkflowNode';
import { NodePalette } from './NodePalette';
import { EdgeConfigModal } from './EdgeConfigModal';
import type { AgentBuilderFormData } from '../../../hooks/useAgentBuilder';
import type {
    WorkflowGraph,
    WorkflowNodeDef,
    WorkflowEdgeDef,
    CatalogNodeMetadata,
} from '../../../services/agentBuilderService';

interface WorkflowPreviewSectionProps {
    formData: AgentBuilderFormData;
    catalogNodes: CatalogNodeMetadata[];
    loadingNodes: boolean;
    onWorkflowGraphChange: (graph: WorkflowGraph | null) => void;
    onResetToDefault: () => void;
}

// ── Layout constants ─────────────────────────────────────────────
const COL_SPACING = 220;
const ROW_SPACING = 120;

// Positions: arranged in a top-down DAG layout
// Row 0: START
// Row 1: init
// Row 2: elicit (center), respond (right)
// Row 3: execute_tool (center)
// Row 4: end
// Row 5: END
const NODE_POSITIONS: Record<string, { x: number; y: number }> = {
    __start__: { x: COL_SPACING, y: 0 },
    init: { x: COL_SPACING, y: ROW_SPACING },
    elicit: { x: 0, y: ROW_SPACING * 2 },
    respond: { x: COL_SPACING * 2, y: ROW_SPACING * 2 },
    execute_tool: { x: 0, y: ROW_SPACING * 3 },
    end: { x: COL_SPACING, y: ROW_SPACING * 4 },
    __end__: { x: COL_SPACING, y: ROW_SPACING * 5 },
};

// ── Edge definitions (mirrors AgentBuilder.use_default_graph()) ──

interface DefaultEdgeDef {
    source: string;
    target: string;
    label?: string;
    animated?: boolean;
    condition?: (ctx: EdgeContext) => boolean;
}

interface EdgeContext {
    hasTools: boolean;
    hasContext: boolean;
    hasFiles: boolean;
}

const DEFAULT_EDGE_DEFS: DefaultEdgeDef[] = [
    { source: '__start__', target: 'init' },
    { source: 'init', target: 'elicit', label: 'elicit', condition: (c) => c.hasContext || c.hasFiles },
    { source: 'init', target: 'respond', label: 'respond' },
    { source: 'init', target: 'end', label: 'end' },
    { source: 'elicit', target: 'execute_tool', label: 'needs_tool', condition: (c) => c.hasTools },
    { source: 'elicit', target: 'elicit', label: 'wait loop', animated: true, condition: (c) => c.hasContext },
    { source: 'elicit', target: 'respond', label: 'ready' },
    { source: 'elicit', target: 'end', label: 'end' },
    { source: 'execute_tool', target: 'respond', label: 'success / error', condition: (c) => c.hasTools },
    { source: 'execute_tool', target: 'elicit', label: 'needs_elicit', condition: (c) => c.hasTools },
    { source: 'execute_tool', target: 'end', label: 'end', condition: (c) => c.hasTools },
    { source: 'respond', target: 'init', label: 'multi-turn', animated: true },
    { source: 'respond', target: 'end', label: 'end' },
    { source: 'end', target: '__end__' },
];

const NODE_TYPE_MAP: Record<string, WorkflowNodeData['nodeType']> = {
    __start__: 'start',
    init: 'init',
    elicit: 'elicit',
    execute_tool: 'execute_tool',
    respond: 'respond',
    end: 'end',
    __end__: 'terminal',
    error_recovery: 'init',
    context_enrichment: 'init',
    rate_limit: 'end',
};

const NODE_LABEL_MAP: Record<string, string> = {
    __start__: 'START',
    init: 'Initialize',
    elicit: 'Elicit Context',
    execute_tool: 'Execute Tools',
    respond: 'Respond',
    end: 'End',
    __end__: 'END',
    error_recovery: 'Error Recovery',
    context_enrichment: 'Enrich Context',
    rate_limit: 'Rate Limit',
};

const nodeTypes: NodeTypes = { workflow: WorkflowNode };

let nodeIdCounter = 0;

export const WorkflowPreviewSection = ({
    formData,
    catalogNodes,
    loadingNodes,
    onWorkflowGraphChange,
    onResetToDefault,
}: WorkflowPreviewSectionProps) => {
    const isCustom = formData.workflow_graph !== null;
    const [editMode, setEditMode] = useState(isCustom);
    const reactFlowWrapper = useRef<HTMLDivElement>(null);

    // Edge config modal
    const { isOpen: isEdgeModalOpen, onOpen: openEdgeModal, onClose: closeEdgeModal } = useDisclosure();
    const [selectedEdge, setSelectedEdge] = useState<Edge | null>(null);

    // Custom graph nodes & edges (mutable editor state)
    const [customNodes, setCustomNodes] = useState<Node[]>([]);
    const [customEdges, setCustomEdges] = useState<Edge[]>([]);

    // Refs for latest state (avoids stale closures in serialization)
    const customNodesRef = useRef(customNodes);
    const customEdgesRef = useRef(customEdges);
    useEffect(() => { customNodesRef.current = customNodes; }, [customNodes]);
    useEffect(() => { customEdgesRef.current = customEdges; }, [customEdges]);

    const hasTools = formData.agent_config.enabled_tools.length > 0;
    const hasContext = formData.required_context.length > 0;
    const hasFiles = !!(formData.required_files.csv || formData.required_files.document);

    const edgeCtx: EdgeContext = useMemo(
        () => ({ hasTools, hasContext, hasFiles }),
        [hasTools, hasContext, hasFiles],
    );

    // Determine which nodes are active based on config
    const nodeActivity: Record<string, boolean> = useMemo(() => ({
        __start__: true,
        init: true,
        elicit: hasContext || hasFiles,
        execute_tool: hasTools,
        respond: true,
        end: true,
        __end__: true,
    }), [hasTools, hasContext, hasFiles]);

    // ── Default (read-only) nodes & edges ────────────────────────

    const defaultFlowNodes: Node[] = useMemo(() => {
        const defs: { id: string; label: string; nodeType: WorkflowNodeData['nodeType'] }[] = [
            { id: '__start__', label: 'START', nodeType: 'start' },
            { id: 'init', label: 'Initialize', nodeType: 'init' },
            { id: 'elicit', label: 'Elicit Context', nodeType: 'elicit' },
            { id: 'execute_tool', label: 'Execute Tools', nodeType: 'execute_tool' },
            { id: 'respond', label: 'Respond', nodeType: 'respond' },
            { id: 'end', label: 'End', nodeType: 'end' },
            { id: '__end__', label: 'END', nodeType: 'terminal' },
        ];

        return defs.map((d) => ({
            id: d.id,
            type: 'workflow',
            position: NODE_POSITIONS[d.id],
            data: {
                label: d.label,
                active: nodeActivity[d.id],
                nodeType: d.nodeType,
            } satisfies WorkflowNodeData,
            draggable: false,
            selectable: false,
            connectable: false,
        }));
    }, [nodeActivity]);

    const defaultFlowEdges: Edge[] = useMemo(() => {
        return DEFAULT_EDGE_DEFS.map((def, idx) => {
            const conditionMet = def.condition ? def.condition(edgeCtx) : true;
            const sourceActive = nodeActivity[def.source];
            const targetActive = nodeActivity[def.target];
            const active = conditionMet && sourceActive && targetActive;

            return {
                id: `e-${idx}`,
                source: def.source,
                target: def.target,
                label: def.label,
                animated: def.animated && active,
                style: {
                    stroke: active ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.15)',
                    strokeWidth: active ? 2 : 1,
                },
                labelStyle: {
                    fontSize: 10,
                    fill: active ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.3)',
                    fontWeight: active ? 600 : 400,
                },
                labelBgStyle: {
                    fill: '#1a1b2e',
                    fillOpacity: 0.9,
                },
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    color: active ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.15)',
                    width: 16,
                    height: 16,
                },
                selectable: false,
                focusable: false,
            };
        });
    }, [edgeCtx, nodeActivity]);

    // ── Initialize custom graph from saved data or default ───────

    const initCustomFromSaved = useCallback(() => {
        const wg = formData.workflow_graph;
        if (wg) {
            const nodes: Node[] = wg.nodes.map((n: WorkflowNodeDef) => ({
                id: n.id,
                type: 'workflow',
                position: n.position,
                data: {
                    label: n.label || NODE_LABEL_MAP[n.type] || n.type,
                    active: true,
                    nodeType: NODE_TYPE_MAP[n.type] || 'init',
                    registryType: n.type,
                } satisfies WorkflowNodeData,
            }));
            const edges: Edge[] = wg.edges.map((e: WorkflowEdgeDef, idx: number) => ({
                id: `ce-${idx}`,
                source: e.source,
                target: e.target,
                label: e.label,
                animated: e.animated ?? false,
                data: { condition: e.condition },
                style: { stroke: 'rgba(255,255,255,0.6)', strokeWidth: 2 },
                labelStyle: { fontSize: 10, fill: 'rgba(255,255,255,0.85)', fontWeight: 600 },
                labelBgStyle: { fill: '#1a1b2e', fillOpacity: 0.9 },
                markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(255,255,255,0.6)', width: 16, height: 16 },
            }));
            setCustomNodes(nodes);
            setCustomEdges(edges);
        } else {
            setCustomNodes(defaultFlowNodes.map((n) => ({ ...n, draggable: true, selectable: true, connectable: true })));
            setCustomEdges(defaultFlowEdges.map((e) => ({ ...e, selectable: true, focusable: true })));
        }
    }, [formData.workflow_graph, defaultFlowNodes, defaultFlowEdges]);

    // ── Serialize custom graph to parent state ───────────────────

    const serializeGraph = useCallback((nodes: Node[], edges: Edge[]) => {
        const wgNodes: WorkflowNodeDef[] = nodes.map((n) => {
            const data = n.data as unknown as WorkflowNodeData;
            return {
                id: n.id,
                type: data.registryType || (n.id === '__start__' ? '__start__' : n.id === '__end__' ? '__end__' : (data.nodeType || n.id)),
                position: n.position,
                label: data.label,
            };
        });
        const wgEdges: WorkflowEdgeDef[] = edges.map((e) => ({
            source: e.source,
            target: e.target,
            label: typeof e.label === 'string' ? e.label : undefined,
            condition: (e.data as Record<string, unknown>)?.condition as string | undefined,
            animated: e.animated,
        }));
        onWorkflowGraphChange({ nodes: wgNodes, edges: wgEdges });
    }, [onWorkflowGraphChange]);

    // ── Editor event handlers ────────────────────────────────────

    const onNodesChange: OnNodesChange = useCallback((changes) => {
        setCustomNodes((nds) => {
            const updated = applyNodeChanges(changes, nds);
            setTimeout(() => serializeGraph(updated, customEdgesRef.current), 0);
            return updated;
        });
    }, [serializeGraph]);

    const onEdgesChange: OnEdgesChange = useCallback((changes) => {
        setCustomEdges((eds) => {
            const updated = applyEdgeChanges(changes, eds);
            setTimeout(() => serializeGraph(customNodesRef.current, updated), 0);
            return updated;
        });
    }, [serializeGraph]);

    const onConnect = useCallback((connection: Connection) => {
        setCustomEdges((eds) => {
            const newEdge: Edge = {
                ...connection,
                id: `ce-new-${Date.now()}`,
                style: { stroke: 'rgba(255,255,255,0.6)', strokeWidth: 2 },
                labelStyle: { fontSize: 10, fill: 'rgba(255,255,255,0.85)', fontWeight: 600 },
                labelBgStyle: { fill: '#1a1b2e', fillOpacity: 0.9 },
                markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(255,255,255,0.6)', width: 16, height: 16 },
            };
            const updated = addEdge(newEdge, eds);
            setTimeout(() => serializeGraph(customNodesRef.current, updated), 0);
            return updated;
        });
    }, [serializeGraph]);

    // ── Drop handler for palette nodes ───────────────────────────

    const onDragOver = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback((event: React.DragEvent) => {
        event.preventDefault();
        const nodeType = event.dataTransfer.getData('application/reactflow-type');
        if (!nodeType) return;

        const bounds = reactFlowWrapper.current?.getBoundingClientRect();
        if (!bounds) return;

        const position = {
            x: event.clientX - bounds.left - 70,
            y: event.clientY - bounds.top - 20,
        };

        nodeIdCounter += 1;
        const newId = `${nodeType}_${nodeIdCounter}`;
        const newNode: Node = {
            id: newId,
            type: 'workflow',
            position,
            data: {
                label: NODE_LABEL_MAP[nodeType] || nodeType,
                active: true,
                nodeType: NODE_TYPE_MAP[nodeType] || 'init',
                registryType: nodeType,
            } satisfies WorkflowNodeData,
        };

        setCustomNodes((nds) => {
            const updated = [...nds, newNode];
            setTimeout(() => serializeGraph(updated, customEdgesRef.current), 0);
            return updated;
        });
    }, [serializeGraph]);

    // ── Edge click → open config modal ───────────────────────────

    const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
        if (!editMode) return;
        setSelectedEdge(edge);
        openEdgeModal();
    }, [editMode, openEdgeModal]);

    const handleEdgeSave = useCallback((edgeId: string, updates: { label?: string; animated?: boolean; data?: Record<string, unknown> }) => {
        setCustomEdges((eds) => {
            const updated = eds.map((e) =>
                e.id === edgeId
                    ? { ...e, label: updates.label ?? e.label, animated: updates.animated ?? e.animated, data: { ...e.data, ...updates.data }, style: { stroke: 'rgba(255,255,255,0.6)', strokeWidth: 2 }, labelStyle: { fontSize: 10, fill: 'rgba(255,255,255,0.85)', fontWeight: 600 }, labelBgStyle: { fill: '#1a1b2e', fillOpacity: 0.9 } }
                    : e
            );
            setTimeout(() => serializeGraph(customNodesRef.current, updated), 0);
            return updated;
        });
    }, [serializeGraph]);

    // ── Toggle edit / reset ──────────────────────────────────────

    const enterEditMode = useCallback(() => {
        setEditMode(true);
        initCustomFromSaved();
    }, [initCustomFromSaved]);

    const handleReset = useCallback(() => {
        setEditMode(false);
        setCustomNodes([]);
        setCustomEdges([]);
        onResetToDefault();
    }, [onResetToDefault]);

    // ── Render ───────────────────────────────────────────────────

    return (
        <Box>
            <HStack justify="space-between" mb={4}>
                <Text fontSize="sm" color="whiteAlpha.700">
                    {editMode
                        ? 'Drag nodes from the palette, connect them, and click edges to configure routing.'
                        : 'Read-only preview of the agent workflow. Click "Customize" to edit.'}
                </Text>
                <HStack spacing={2}>
                    {!editMode ? (
                        <Button size="sm" leftIcon={<FiEdit3 />} variant="outline" onClick={enterEditMode}>
                            Customize
                        </Button>
                    ) : (
                        <Button size="sm" leftIcon={<FiRotateCcw />} variant="outline" colorScheme="orange" onClick={handleReset}>
                            Reset to Default
                        </Button>
                    )}
                    {isCustom && !editMode && (
                        <Badge colorScheme="purple">Custom Graph</Badge>
                    )}
                </HStack>
            </HStack>

            <HStack align="stretch" spacing={0}>
                {editMode && (
                    <Box
                        w="200px"
                        flexShrink={0}
                        borderWidth="1px"
                        borderColor="rgba(255,255,255,0.1)"
                        borderRightWidth="0"
                        borderRadius="md"
                        borderRightRadius="0"
                        p={3}
                        bg="#14151f"
                        overflowY="auto"
                        maxH="580px"
                    >
                        <NodePalette catalogNodes={catalogNodes} loading={loadingNodes} />
                    </Box>
                )}

                <Box
                    ref={reactFlowWrapper}
                    h="580px"
                    flex={1}
                    borderRadius="md"
                    borderWidth="1px"
                    borderColor="rgba(255,255,255,0.1)"
                    overflow="hidden"
                    borderLeftRadius={editMode ? '0' : 'md'}
                    sx={{ '.react-flow': { background: '#0d0e1f' }, '.react-flow__controls': { background: '#1a1b2e', border: '1px solid rgba(255,255,255,0.1)' }, '.react-flow__controls-button': { background: '#1a1b2e', borderColor: 'rgba(255,255,255,0.08)', color: 'white', fill: 'white', _hover: { background: '#2a2b3e' } } }}
                >
                    {editMode ? (
                        <ReactFlow
                            nodes={customNodes}
                            edges={customEdges}
                            nodeTypes={nodeTypes}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onDragOver={onDragOver}
                            onDrop={onDrop}
                            onEdgeClick={onEdgeClick}
                            nodesDraggable
                            nodesConnectable
                            elementsSelectable
                            panOnDrag
                            zoomOnScroll
                            fitView
                            fitViewOptions={{ padding: 0.3 }}
                            minZoom={0.3}
                            maxZoom={2}
                            proOptions={{ hideAttribution: true }}
                            deleteKeyCode="Backspace"
                        >
                            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="rgba(255,255,255,0.08)" />
                            <Controls />
                        </ReactFlow>
                    ) : (
                        <ReactFlow
                            nodes={defaultFlowNodes}
                            edges={defaultFlowEdges}
                            nodeTypes={nodeTypes}
                            nodesDraggable={false}
                            nodesConnectable={false}
                            elementsSelectable={false}
                            panOnDrag
                            zoomOnScroll
                            fitView
                            fitViewOptions={{ padding: 0.3 }}
                            minZoom={0.5}
                            maxZoom={1.5}
                            proOptions={{ hideAttribution: true }}
                        >
                            <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="rgba(255,255,255,0.08)" />
                            <Controls showInteractive={false} />
                        </ReactFlow>
                    )}
                </Box>
            </HStack>

            <Box mt={4}>
                <Text fontSize="sm" fontWeight="medium" mb={2} color="whiteAlpha.800">Summary</Text>
                <HStack spacing={2} flexWrap="wrap">
                    <Badge colorScheme="green">
                        {formData.agent_config.enabled_tools.length} tools
                    </Badge>
                    <Badge colorScheme="blue">
                        {formData.required_context.length} context fields
                    </Badge>
                    <Badge colorScheme={formData.agent_config.model?.includes('gpt-4o-mini') ? 'gray' : 'purple'}>
                        {formData.agent_config.model}
                    </Badge>
                    <Badge colorScheme="orange">
                        max {formData.agent_config.max_turns} turns
                    </Badge>
                    {formData.requires_google && (
                        <Badge colorScheme="red">Google Suite</Badge>
                    )}
                </HStack>
            </Box>

            <EdgeConfigModal
                isOpen={isEdgeModalOpen}
                onClose={closeEdgeModal}
                edge={selectedEdge}
                onSave={handleEdgeSave}
            />
        </Box>
    );
};

export default WorkflowPreviewSection;
