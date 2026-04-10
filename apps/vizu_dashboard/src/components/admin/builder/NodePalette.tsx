import { useMemo } from 'react';
import {
    Box,
    VStack,
    Text,
    Heading,
    Badge,
    Spinner,
    Center,
    Tooltip,
} from '@chakra-ui/react';
import { Icon } from '@chakra-ui/react';
import {
    FiPlay,
    FiMessageCircle,
    FiTool,
    FiCpu,
    FiStopCircle,
    FiHelpCircle,
    FiShield,
    FiDatabase,
    FiClock,
} from 'react-icons/fi';
import type { CatalogNodeMetadata } from '../../../services/agentBuilderService';

interface NodePaletteProps {
    catalogNodes: CatalogNodeMetadata[];
    loading: boolean;
}

const NODE_ICONS: Record<string, React.ElementType> = {
    init: FiPlay,
    elicit: FiHelpCircle,
    execute_tool: FiTool,
    respond: FiMessageCircle,
    end: FiStopCircle,
    error_recovery: FiShield,
    context_enrichment: FiDatabase,
    rate_limit: FiClock,
};

const CATEGORY_COLORS: Record<string, string> = {
    core: 'blue',
    specialized: 'purple',
};

export const NodePalette = ({ catalogNodes, loading }: NodePaletteProps) => {
    const grouped = useMemo(() => {
        const groups: Record<string, CatalogNodeMetadata[]> = {};
        for (const node of catalogNodes) {
            const cat = node.category || 'core';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(node);
        }
        return groups;
    }, [catalogNodes]);

    const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
        event.dataTransfer.setData('application/reactflow-type', nodeType);
        event.dataTransfer.setData('application/reactflow-label', label);
        event.dataTransfer.effectAllowed = 'move';
    };

    if (loading) {
        return (
            <Center py={8}>
                <Spinner size="sm" />
            </Center>
        );
    }

    return (
        <Box>
            <Heading size="xs" mb={3} color="gray.600" textTransform="uppercase" letterSpacing="wide">
                Node Palette
            </Heading>
            <Text fontSize="xs" color="gray.500" mb={3}>
                Drag nodes onto the canvas to build your workflow.
            </Text>
            <VStack spacing={2} align="stretch">
                {Object.entries(grouped).map(([category, nodes]) => (
                    <Box key={category}>
                        <Badge
                            colorScheme={CATEGORY_COLORS[category] || 'gray'}
                            fontSize="2xs"
                            mb={1}
                        >
                            {category}
                        </Badge>
                        <VStack spacing={1} align="stretch">
                            {nodes.map((node) => {
                                const IconComp = NODE_ICONS[node.name] || FiCpu;
                                return (
                                    <Tooltip
                                        key={node.name}
                                        label={node.description}
                                        placement="right"
                                        fontSize="xs"
                                    >
                                        <Box
                                            px={3}
                                            py={2}
                                            borderWidth="1px"
                                            borderColor="gray.200"
                                            borderRadius="md"
                                            bg="white"
                                            cursor="grab"
                                            _hover={{ borderColor: 'blue.300', bg: 'blue.50' }}
                                            _active={{ cursor: 'grabbing' }}
                                            draggable
                                            onDragStart={(e) => onDragStart(e, node.name, node.name)}
                                        >
                                            <Box display="flex" alignItems="center" gap={2}>
                                                <Icon as={IconComp} boxSize={3} color="gray.600" />
                                                <Text fontSize="xs" fontWeight="medium" noOfLines={1}>
                                                    {node.name}
                                                </Text>
                                            </Box>
                                        </Box>
                                    </Tooltip>
                                );
                            })}
                        </VStack>
                    </Box>
                ))}
            </VStack>
        </Box>
    );
};

export default NodePalette;
