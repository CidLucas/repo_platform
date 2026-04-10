import {
    Box,
    Checkbox,
    SimpleGrid,
    Text,
    Badge,
    VStack,
    HStack,
    Spinner,
    Alert,
    AlertIcon,
    AlertDescription,
    Input,
    InputGroup,
    InputLeftElement,
    Icon,
    Heading,
} from '@chakra-ui/react';
import { FiSearch } from 'react-icons/fi';
import { useState, useMemo } from 'react';
import type { ToolMetadata, ValidateToolsResult } from '../../../services/agentBuilderService';

interface ToolSelectionSectionProps {
    availableTools: ToolMetadata[];
    enabledTools: string[];
    loadingTools: boolean;
    toolValidation: ValidateToolsResult | null;
    validating: boolean;
    addTool: (toolName: string) => void;
    removeTool: (toolName: string) => void;
}

export const ToolSelectionSection = ({
    availableTools,
    enabledTools,
    loadingTools,
    toolValidation,
    validating,
    addTool,
    removeTool,
}: ToolSelectionSectionProps) => {
    const [search, setSearch] = useState('');

    const groupedTools = useMemo(() => {
        const filtered = availableTools.filter(
            (t) =>
                t.name.toLowerCase().includes(search.toLowerCase()) ||
                t.description.toLowerCase().includes(search.toLowerCase()) ||
                t.category.toLowerCase().includes(search.toLowerCase()),
        );

        const grouped: Record<string, ToolMetadata[]> = {};
        for (const tool of filtered) {
            const cat = tool.category || 'Other';
            if (!grouped[cat]) grouped[cat] = [];
            grouped[cat].push(tool);
        }
        return grouped;
    }, [availableTools, search]);

    if (loadingTools) {
        return (
            <Box textAlign="center" py={8}>
                <Spinner size="lg" color="black" />
                <Text mt={2} color="gray.600">Loading available tools...</Text>
            </Box>
        );
    }

    return (
        <Box>
            <HStack mb={4} justify="space-between">
                <InputGroup maxW="300px">
                    <InputLeftElement>
                        <Icon as={FiSearch} color="gray.400" />
                    </InputLeftElement>
                    <Input
                        placeholder="Search tools..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </InputGroup>
                <HStack spacing={2}>
                    <Badge colorScheme="green" fontSize="sm">
                        {enabledTools.length} selected
                    </Badge>
                    {validating && <Spinner size="xs" />}
                </HStack>
            </HStack>

            {toolValidation && !toolValidation.valid && (
                <Alert status="error" borderRadius="md" mb={4}>
                    <AlertIcon />
                    <AlertDescription>
                        {toolValidation.errors.join('; ')}
                    </AlertDescription>
                </Alert>
            )}

            {toolValidation?.warnings && toolValidation.warnings.length > 0 && (
                <Alert status="warning" borderRadius="md" mb={4}>
                    <AlertIcon />
                    <AlertDescription>
                        {toolValidation.warnings.join('; ')}
                    </AlertDescription>
                </Alert>
            )}

            {Object.keys(groupedTools).length === 0 && (
                <Text color="gray.600" textAlign="center" py={4}>
                    No tools available for this tier. Try changing the tier in the Identity section.
                </Text>
            )}

            <VStack align="stretch" spacing={5}>
                {Object.entries(groupedTools)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([category, tools]) => (
                        <Box key={category}>
                            <Heading size="xs" mb={2} textTransform="uppercase" color="gray.500">
                                {category}
                            </Heading>
                            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={2}>
                                {tools.map((tool) => {
                                    const isEnabled = enabledTools.includes(tool.name);
                                    return (
                                        <Box
                                            key={tool.name}
                                            p={3}
                                            borderWidth="1px"
                                            borderColor={isEnabled ? 'black' : 'gray.200'}
                                            borderRadius="md"
                                            bg={isEnabled ? 'gray.50' : 'white'}
                                            cursor="pointer"
                                            onClick={() => isEnabled ? removeTool(tool.name) : addTool(tool.name)}
                                            _hover={{ borderColor: 'gray.400' }}
                                            transition="all 0.15s"
                                        >
                                            <HStack justify="space-between" align="start">
                                                <VStack align="start" spacing={1} flex={1}>
                                                    <HStack>
                                                        <Checkbox
                                                            isChecked={isEnabled}
                                                            onChange={() => isEnabled ? removeTool(tool.name) : addTool(tool.name)}
                                                            colorScheme="blackAlpha"
                                                            onClick={(e) => e.stopPropagation()}
                                                        />
                                                        <Text fontWeight="medium" fontSize="sm">
                                                            {tool.name}
                                                        </Text>
                                                    </HStack>
                                                    <Text fontSize="xs" color="gray.600" pl={6}>
                                                        {tool.description}
                                                    </Text>
                                                </VStack>
                                                {tool.requires_confirmation && (
                                                    <Badge colorScheme="orange" fontSize="2xs">
                                                        confirm
                                                    </Badge>
                                                )}
                                            </HStack>
                                        </Box>
                                    );
                                })}
                            </SimpleGrid>
                        </Box>
                    ))}
            </VStack>
        </Box>
    );
};

export default ToolSelectionSection;
