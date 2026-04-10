import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Box, Text, Icon } from '@chakra-ui/react';
import {
    FiPlay,
    FiMessageCircle,
    FiTool,
    FiCpu,
    FiStopCircle,
    FiHelpCircle,
} from 'react-icons/fi';

export interface WorkflowNodeData {
    label: string;
    active: boolean;
    nodeType: 'start' | 'end' | 'init' | 'elicit' | 'execute_tool' | 'respond' | 'terminal';
    /** Original registry type for serialization (e.g. 'error_recovery'). Falls back to nodeType. */
    registryType?: string;
}

const NODE_ICONS: Record<string, React.ElementType> = {
    start: FiPlay,
    init: FiPlay,
    elicit: FiHelpCircle,
    execute_tool: FiTool,
    respond: FiMessageCircle,
    end: FiStopCircle,
    terminal: FiCpu,
};

const NODE_COLORS: Record<string, { bg: string; border: string; accent: string }> = {
    start: { bg: 'green.50', border: 'green.400', accent: 'green.500' },
    init: { bg: 'blue.50', border: 'blue.400', accent: 'blue.500' },
    elicit: { bg: 'purple.50', border: 'purple.400', accent: 'purple.500' },
    execute_tool: { bg: 'orange.50', border: 'orange.400', accent: 'orange.500' },
    respond: { bg: 'teal.50', border: 'teal.400', accent: 'teal.500' },
    end: { bg: 'red.50', border: 'red.400', accent: 'red.500' },
    terminal: { bg: 'gray.50', border: 'gray.400', accent: 'gray.500' },
};

const WorkflowNode = ({ data }: NodeProps) => {
    const nodeData = data as unknown as WorkflowNodeData;
    const { label, active, nodeType } = nodeData;
    const colors = NODE_COLORS[nodeType] || NODE_COLORS.terminal;
    const IconComponent = NODE_ICONS[nodeType] || FiCpu;

    const isTerminal = nodeType === 'start' || nodeType === 'terminal';

    return (
        <>
            {nodeType !== 'start' && (
                <Handle
                    type="target"
                    position={Position.Top}
                    style={{
                        background: active ? '#333' : '#ccc',
                        width: 8,
                        height: 8,
                        border: '2px solid white',
                    }}
                />
            )}

            <Box
                px={4}
                py={3}
                minW={isTerminal ? '80px' : '140px'}
                borderWidth="2px"
                borderColor={active ? colors.border : 'gray.200'}
                borderRadius={isTerminal ? 'full' : 'lg'}
                bg={active ? colors.bg : 'gray.50'}
                opacity={active ? 1 : 0.45}
                textAlign="center"
                transition="all 0.2s"
                boxShadow={active ? 'sm' : 'none'}
                _hover={active ? { boxShadow: 'md' } : undefined}
            >
                <Icon
                    as={IconComponent}
                    color={active ? colors.accent : 'gray.400'}
                    boxSize={4}
                    mb={1}
                />
                <Text
                    fontSize="xs"
                    fontWeight={active ? 'bold' : 'normal'}
                    color={active ? 'gray.800' : 'gray.400'}
                    lineHeight="short"
                >
                    {label}
                </Text>
            </Box>

            {nodeType !== 'terminal' && (
                <Handle
                    type="source"
                    position={Position.Bottom}
                    style={{
                        background: active ? '#333' : '#ccc',
                        width: 8,
                        height: 8,
                        border: '2px solid white',
                    }}
                />
            )}
        </>
    );
};

export default memo(WorkflowNode);
