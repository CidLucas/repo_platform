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
    start: { bg: 'rgba(6,255,165,0.08)', border: '#06ffa5', accent: '#06ffa5' },
    init: { bg: 'rgba(67,97,238,0.12)', border: '#4361ee', accent: '#7c9fff' },
    elicit: { bg: 'rgba(114,9,183,0.12)', border: '#7209b7', accent: '#c084fc' },
    execute_tool: { bg: 'rgba(255,107,53,0.12)', border: '#ff6b35', accent: '#ff6b35' },
    respond: { bg: 'rgba(20,184,166,0.1)', border: '#14b8a6', accent: '#5eead4' },
    end: { bg: 'rgba(239,68,68,0.1)', border: '#ef4444', accent: '#fca5a5' },
    terminal: { bg: 'rgba(255,255,255,0.05)', border: 'rgba(255,255,255,0.3)', accent: 'rgba(255,255,255,0.6)' },
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
                borderColor={active ? colors.border : 'rgba(255,255,255,0.08)'}
                borderRadius={isTerminal ? 'full' : 'lg'}
                bg={active ? colors.bg : 'rgba(255,255,255,0.02)'}
                opacity={active ? 1 : 0.35}
                textAlign="center"
                transition="all 0.2s"
                boxShadow={active ? `0 0 12px ${colors.border}33` : 'none'}
                _hover={active ? { boxShadow: `0 0 18px ${colors.border}55` } : undefined}
            >
                <Icon
                    as={IconComponent}
                    color={active ? colors.accent : 'rgba(255,255,255,0.2)'}
                    boxSize={4}
                    mb={1}
                />
                <Text
                    fontSize="xs"
                    fontWeight={active ? 'bold' : 'normal'}
                    color={active ? 'white' : 'rgba(255,255,255,0.25)'}
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
                        background: active ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.15)',
                        width: 8,
                        height: 8,
                        border: '2px solid rgba(255,255,255,0.3)',
                    }}
                />
            )}
        </>
    );
};

export default memo(WorkflowNode);
