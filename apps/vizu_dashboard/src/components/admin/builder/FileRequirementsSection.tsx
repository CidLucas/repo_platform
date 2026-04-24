import {
    Box,
    FormControl,
    FormLabel,
    Input,
    Switch,
    SimpleGrid,
    HStack,
    Text,
    VStack,
} from '@chakra-ui/react';
import type { FileRequirements } from '../../../services/agentBuilderService';
import type { AgentBuilderFormData } from '../../../hooks/useAgentBuilder';

interface FileRequirementsSectionProps {
    formData: AgentBuilderFormData;
    setField: <K extends keyof AgentBuilderFormData>(field: K, value: AgentBuilderFormData[K]) => void;
}

export const FileRequirementsSection = ({ formData, setField }: FileRequirementsSectionProps) => {
    const { required_files } = formData;

    const hasCsv = !!required_files.csv;
    const hasDocument = !!required_files.document;

    const updateFileReq = (updated: FileRequirements) => {
        setField('required_files', updated);
    };

    const toggleCsv = (enabled: boolean) => {
        if (enabled) {
            updateFileReq({
                ...required_files,
                csv: { min: 1, max: 5, description: 'Upload CSV data files' },
            });
        } else {
            const { csv: _csv, ...rest } = required_files;
            updateFileReq(rest);
        }
    };

    const toggleDocument = (enabled: boolean) => {
        if (enabled) {
            updateFileReq({
                ...required_files,
                document: { min: 0, max: 3, description: 'Upload text documents' },
            });
        } else {
            const { document: _doc, ...rest } = required_files;
            updateFileReq(rest);
        }
    };

    return (
        <Box>
            <Text fontSize="sm" color="gray.600" mb={4}>
                Configure what files users can upload when starting a session with this agent.
            </Text>

            <VStack spacing={6} align="stretch">
                {/* CSV Section */}
                <Box p={4} borderWidth="1px" borderColor="gray.200" borderRadius="md">
                    <HStack justify="space-between" mb={hasCsv ? 4 : 0}>
                        <Text fontWeight="medium">CSV Files</Text>
                        <Switch
                            isChecked={hasCsv}
                            onChange={(e) => toggleCsv(e.target.checked)}
                            colorScheme="green"
                        />
                    </HStack>
                    {hasCsv && required_files.csv && (
                        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={3}>
                            <FormControl>
                                <FormLabel fontSize="xs">Min Files</FormLabel>
                                <Input
                                    size="sm"
                                    type="number"
                                    min={0}
                                    value={required_files.csv.min}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            csv: { ...required_files.csv!, min: parseInt(e.target.value) || 0 },
                                        })
                                    }
                                />
                            </FormControl>
                            <FormControl>
                                <FormLabel fontSize="xs">Max Files</FormLabel>
                                <Input
                                    size="sm"
                                    type="number"
                                    min={1}
                                    value={required_files.csv.max}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            csv: { ...required_files.csv!, max: parseInt(e.target.value) || 1 },
                                        })
                                    }
                                />
                            </FormControl>
                            <FormControl>
                                <FormLabel fontSize="xs">Description</FormLabel>
                                <Input
                                    size="sm"
                                    value={required_files.csv.description}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            csv: { ...required_files.csv!, description: e.target.value },
                                        })
                                    }
                                />
                            </FormControl>
                        </SimpleGrid>
                    )}
                </Box>

                {/* Text/Document Section */}
                <Box p={4} borderWidth="1px" borderColor="gray.200" borderRadius="md">
                    <HStack justify="space-between" mb={hasDocument ? 4 : 0}>
                        <Text fontWeight="medium">Text Documents</Text>
                        <Switch
                            isChecked={hasDocument}
                            onChange={(e) => toggleDocument(e.target.checked)}
                            colorScheme="green"
                        />
                    </HStack>
                    {hasDocument && required_files.document && (
                        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={3}>
                            <FormControl>
                                <FormLabel fontSize="xs">Min Files</FormLabel>
                                <Input
                                    size="sm"
                                    type="number"
                                    min={0}
                                    value={required_files.document.min}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            document: { ...required_files.document!, min: parseInt(e.target.value) || 0 },
                                        })
                                    }
                                />
                            </FormControl>
                            <FormControl>
                                <FormLabel fontSize="xs">Max Files</FormLabel>
                                <Input
                                    size="sm"
                                    type="number"
                                    min={1}
                                    value={required_files.document.max}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            document: { ...required_files.document!, max: parseInt(e.target.value) || 1 },
                                        })
                                    }
                                />
                            </FormControl>
                            <FormControl>
                                <FormLabel fontSize="xs">Description</FormLabel>
                                <Input
                                    size="sm"
                                    value={required_files.document.description}
                                    onChange={(e) =>
                                        updateFileReq({
                                            ...required_files,
                                            document: { ...required_files.document!, description: e.target.value },
                                        })
                                    }
                                />
                            </FormControl>
                        </SimpleGrid>
                    )}
                </Box>

                {/* Google Requirement */}
                <Box p={4} borderWidth="1px" borderColor="gray.200" borderRadius="md">
                    <HStack justify="space-between">
                        <VStack align="start" spacing={0}>
                            <Text fontWeight="medium">Requires Google Suite</Text>
                            <Text fontSize="xs" color="gray.500">
                                Agent needs Google Sheets / Docs access
                            </Text>
                        </VStack>
                        <Switch
                            isChecked={formData.requires_google}
                            onChange={(e) => setField('requires_google', e.target.checked)}
                            colorScheme="green"
                        />
                    </HStack>
                </Box>
            </VStack>
        </Box>
    );
};

export default FileRequirementsSection;
