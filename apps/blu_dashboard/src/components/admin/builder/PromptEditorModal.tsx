import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    Box,
    Button,
    HStack,
    VStack,
    Text,
    Textarea,
    Badge,
    Spinner,
    useToast,
    Heading,
    Code,
    Flex,
} from '@chakra-ui/react';
import { useState, useEffect, useCallback, useContext, useMemo } from 'react';
import { FiSave, FiClock, FiEye } from 'react-icons/fi';
import { AuthContext } from '../../../contexts/AuthContext';
import {
    fetchPromptDetail,
    updatePrompt,
    fetchPromptVersions,
    type PromptDetail,
    type PromptVersionInfo,
} from '../../../services/agentBuilderService';

interface PromptEditorModalProps {
    isOpen: boolean;
    onClose: () => void;
    promptName: string;
    requiredContext?: Array<{ field: string; label: string }>;
}

export const PromptEditorModal = ({
    isOpen,
    onClose,
    promptName,
    requiredContext = [],
}: PromptEditorModalProps) => {
    const auth = useContext(AuthContext);
    const toast = useToast();
    const accessToken = auth?.session?.access_token;

    const [prompt, setPrompt] = useState<PromptDetail | null>(null);
    const [content, setContent] = useState('');
    const [versions, setVersions] = useState<PromptVersionInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [isDirty, setIsDirty] = useState(false);

    const loadPrompt = useCallback(async () => {
        if (!accessToken || !promptName) return;
        setLoading(true);
        try {
            const [detail, versionsResp] = await Promise.all([
                fetchPromptDetail(promptName, accessToken),
                fetchPromptVersions(promptName, accessToken),
            ]);
            setPrompt(detail);
            setContent(detail.content);
            setVersions(versionsResp.versions);
            setIsDirty(false);
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to load prompt';
            toast({ title: 'Error', description: message, status: 'error', duration: 3000 });
        } finally {
            setLoading(false);
        }
    }, [accessToken, promptName, toast]);

    useEffect(() => {
        if (isOpen && promptName) {
            loadPrompt();
        }
    }, [isOpen, promptName, loadPrompt]);

    const handleContentChange = (value: string) => {
        setContent(value);
        setIsDirty(value !== prompt?.content);
    };

    const handleSave = async () => {
        if (!accessToken || !promptName) return;
        setSaving(true);
        try {
            const updated = await updatePrompt(promptName, content, accessToken);
            setPrompt(updated);
            setIsDirty(false);
            // Refresh versions
            const versionsResp = await fetchPromptVersions(promptName, accessToken);
            setVersions(versionsResp.versions);
            toast({ title: 'Prompt saved!', description: `Version ${updated.version}`, status: 'success', duration: 2000 });
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to save prompt';
            toast({ title: 'Error', description: message, status: 'error', duration: 4000 });
        } finally {
            setSaving(false);
        }
    };

    const handleVersionSelect = async (_version: number) => {
        if (!accessToken || !promptName) return;
        setLoading(true);
        try {
            // Fetch specific version by getting the prompt with version param
            const detail = await fetchPromptDetail(promptName, accessToken);
            // The API returns production version — for viewing other versions we load and display
            // For now, we show the content from the selected production version
            setContent(detail.content);
            setPrompt(detail);
            setIsDirty(false);
        } catch (err) {
            console.error('Failed to load version:', err);
        } finally {
            setLoading(false);
        }
    };

    // Render preview with sample variables
    const renderedPreview = useMemo(() => {
        let preview = content;
        // Replace {{var}} with sample values from requiredContext
        const contextMap = new Map(requiredContext.map((c) => [c.field, c.label]));
        preview = preview.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
            const label = contextMap.get(varName);
            return label ? `[${label}]` : `[${varName}]`;
        });
        return preview;
    }, [content, requiredContext]);

    // Highlight variables in content
    const variables = useMemo(() => {
        const matches = content.match(/\{\{(\w+)\}\}/g) || [];
        return [...new Set(matches.map((m) => m.replace(/\{|\}/g, '')))];
    }, [content]);

    const isBuiltin = prompt?.source === 'builtin';

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="full">
            <ModalOverlay />
            <ModalContent m={4} borderRadius="lg" maxH="calc(100vh - 32px)">
                <ModalHeader>
                    <HStack justify="space-between" pr={8}>
                        <HStack spacing={3}>
                            <Heading size="md">Edit Prompt</Heading>
                            <Badge
                                colorScheme={prompt?.source === 'langfuse' ? 'purple' : 'blue'}
                                fontSize="xs"
                            >
                                {prompt?.source}
                            </Badge>
                            {prompt && (
                                <Badge colorScheme="gray" fontSize="xs">
                                    v{prompt.version}
                                </Badge>
                            )}
                            {isDirty && (
                                <Badge colorScheme="orange" fontSize="xs">
                                    unsaved
                                </Badge>
                            )}
                        </HStack>
                        <Text fontSize="sm" color="gray.500" fontWeight="normal">
                            {promptName}
                        </Text>
                    </HStack>
                </ModalHeader>
                <ModalCloseButton />

                <ModalBody overflow="hidden" pb={0}>
                    {loading ? (
                        <Flex justify="center" align="center" h="400px">
                            <VStack>
                                <Spinner size="lg" color="black" />
                                <Text color="gray.600">Loading prompt...</Text>
                            </VStack>
                        </Flex>
                    ) : (
                        <Flex h="calc(100vh - 200px)" gap={4}>
                            {/* Main Editor */}
                            <Box flex={1} display="flex" flexDirection="column">
                                {/* Variable tags */}
                                {variables.length > 0 && (
                                    <HStack mb={3} flexWrap="wrap">
                                        <Text fontSize="xs" color="gray.500" fontWeight="medium">
                                            Variables:
                                        </Text>
                                        {variables.map((v) => (
                                            <Code
                                                key={v}
                                                fontSize="xs"
                                                colorScheme="purple"
                                                px={2}
                                                py={0.5}
                                                borderRadius="md"
                                            >
                                                {`{{${v}}}`}
                                            </Code>
                                        ))}
                                    </HStack>
                                )}

                                {showPreview ? (
                                    <Box
                                        flex={1}
                                        overflowY="auto"
                                        p={4}
                                        bg="gray.50"
                                        borderRadius="md"
                                        borderWidth="1px"
                                        borderColor="gray.200"
                                        fontFamily="mono"
                                        fontSize="sm"
                                        whiteSpace="pre-wrap"
                                    >
                                        {renderedPreview}
                                    </Box>
                                ) : (
                                    <Textarea
                                        flex={1}
                                        value={content}
                                        onChange={(e) => handleContentChange(e.target.value)}
                                        fontFamily="mono"
                                        fontSize="sm"
                                        resize="none"
                                        borderColor="gray.300"
                                        _focus={{ borderColor: 'black', boxShadow: '0 0 0 1px black' }}
                                        isReadOnly={isBuiltin}
                                        placeholder="Enter prompt content..."
                                    />
                                )}
                            </Box>

                            {/* Right Sidebar: Version History */}
                            <Box
                                w="260px"
                                borderLeftWidth="1px"
                                borderColor="gray.200"
                                pl={4}
                                display="flex"
                                flexDirection="column"
                                overflowY="auto"
                            >
                                <HStack mb={3}>
                                    <FiClock />
                                    <Heading size="xs">Version History</Heading>
                                </HStack>

                                {versions.length === 0 ? (
                                    <Text fontSize="sm" color="gray.500">No versions found</Text>
                                ) : (
                                    <VStack align="stretch" spacing={2}>
                                        {versions.map((v) => (
                                            <Box
                                                key={v.version}
                                                p={2}
                                                borderWidth="1px"
                                                borderColor={v.version === prompt?.version ? 'black' : 'gray.200'}
                                                borderRadius="md"
                                                bg={v.version === prompt?.version ? 'gray.50' : 'white'}
                                                cursor="pointer"
                                                _hover={{ bg: 'gray.50' }}
                                                onClick={() => handleVersionSelect(v.version)}
                                            >
                                                <HStack justify="space-between">
                                                    <Text fontSize="sm" fontWeight="medium">
                                                        v{v.version}
                                                    </Text>
                                                    <HStack spacing={1}>
                                                        {v.labels.map((label) => (
                                                            <Badge
                                                                key={label}
                                                                colorScheme={label === 'production' ? 'green' : 'gray'}
                                                                fontSize="2xs"
                                                            >
                                                                {label}
                                                            </Badge>
                                                        ))}
                                                    </HStack>
                                                </HStack>
                                                {v.created_at && (
                                                    <Text fontSize="xs" color="gray.500">
                                                        {new Date(v.created_at).toLocaleDateString()}
                                                    </Text>
                                                )}
                                            </Box>
                                        ))}
                                    </VStack>
                                )}
                            </Box>
                        </Flex>
                    )}
                </ModalBody>

                <ModalFooter borderTopWidth="1px" borderColor="gray.200">
                    <HStack w="full" justify="space-between">
                        <Button
                            variant="ghost"
                            leftIcon={<FiEye />}
                            size="sm"
                            onClick={() => setShowPreview(!showPreview)}
                        >
                            {showPreview ? 'Edit' : 'Preview'}
                        </Button>

                        <HStack>
                            <Button variant="ghost" onClick={onClose}>
                                Cancel
                            </Button>
                            <Button
                                colorScheme="blackAlpha"
                                bg="black"
                                color="white"
                                leftIcon={<FiSave />}
                                onClick={handleSave}
                                isLoading={saving}
                                isDisabled={!isDirty || isBuiltin}
                            >
                                Save New Version
                            </Button>
                        </HStack>
                    </HStack>
                </ModalFooter>
            </ModalContent>
        </Modal>
    );
};

export default PromptEditorModal;
