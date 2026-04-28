import { useRef, useState, useCallback } from "react";
import {
    Box,
    VStack,
    HStack,
    Text,
    Heading,
    Icon,
    Badge,
    Button,
    Checkbox,
    IconButton,
    Spinner,
    Progress,
    Tooltip,
    useToast,
    Flex,
    Textarea,
    Select,
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalBody,
    ModalFooter,
    ModalCloseButton,
    FormControl,
    FormLabel,
    useDisclosure,
} from "@chakra-ui/react";
import { AdminLayout } from "../../components/layouts/AdminLayout";
import {
    FiUploadCloud,
    FiTrash2,
    FiRefreshCw,
    FiFile,
    FiBook,
    FiTag,
    FiRotateCw,
} from "react-icons/fi";
import { useKnowledgeBase } from "../../hooks/useKnowledgeBase";
import {
    getAcceptedExtensions,
    KB_CATEGORIES,
    retryDocument,
    type KBDocument,
    type UploadOptions,
} from "../../services/knowledgeBaseService";

// ── Helpers ─────────────────────────────────────────────────

function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
    });
}

function StatusBadge({ doc }: { doc: KBDocument }) {
    switch (doc.status) {
        case "completed":
            return (
                <Badge colorScheme="green" fontSize="xs">
                    Concluído
                </Badge>
            );
        case "processing":
            return (
                <Badge colorScheme="blue" fontSize="xs" display="flex" alignItems="center" gap={1}>
                    <Spinner size="xs" />
                    Processando
                </Badge>
            );
        case "pending":
            return (
                <Badge colorScheme="gray" fontSize="xs">
                    Pendente
                </Badge>
            );
        case "failed":
            return (
                <Tooltip label={doc.error_message || "Erro desconhecido"} hasArrow>
                    <Badge colorScheme="red" fontSize="xs" cursor="help">
                        Falhou
                    </Badge>
                </Tooltip>
            );
        case "partially_failed":
            return (
                <Tooltip label={doc.error_message || "Alguns chunks falharam"} hasArrow>
                    <Badge colorScheme="orange" fontSize="xs" cursor="help">
                        Parcial
                    </Badge>
                </Tooltip>
            );
        default:
            return null;
    }
}

function ChunkInfo({ doc }: { doc: KBDocument }) {
    if (doc.status === "processing" || doc.status === "pending") {
        return (
            <Box w="80px">
                <Progress size="xs" isIndeterminate colorScheme="blue" borderRadius="full" />
            </Box>
        );
    }
    return (
        <Text fontSize="sm" color="whiteAlpha.600">
            {doc.chunk_count}
        </Text>
    );
}

const CATEGORY_LABELS: Record<string, string> = Object.fromEntries(
    KB_CATEGORIES.map((c) => [c.value, c.label])
);

function CategoryBadge({ category }: { category: string | null }) {
    if (!category) return <Text fontSize="xs" color="whiteAlpha.400">—</Text>;
    return (
        <Badge variant="subtle" colorScheme="teal" fontSize="xs">
            <HStack spacing={1}>
                <Icon as={FiTag} boxSize="10px" />
                <Text>{CATEGORY_LABELS[category] || category}</Text>
            </HStack>
        </Badge>
    );
}

// ── Upload Zone ─────────────────────────────────────────────

interface UploadZoneProps {
    onFiles: (files: File[], forceComplex: boolean, options?: UploadOptions) => void;
    uploading: boolean;
}

function UploadZone({ onFiles, uploading }: UploadZoneProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);
    const [advancedProcessing, setAdvancedProcessing] = useState(false);
    const [pendingFiles, setPendingFiles] = useState<File[]>([]);
    const [description, setDescription] = useState("");
    const [category, setCategory] = useState("");
    const { isOpen, onOpen, onClose } = useDisclosure();

    const openMetadataModal = useCallback(
        (files: FileList | null) => {
            if (!files || files.length === 0) return;
            setPendingFiles(Array.from(files));
            onOpen();
        },
        [onOpen]
    );

    const handleConfirmUpload = useCallback(() => {
        const opts: UploadOptions = {};
        if (description.trim()) opts.description = description.trim();
        if (category) opts.category = category;
        onFiles(pendingFiles, advancedProcessing, opts);
        // Reset state
        setDescription("");
        setCategory("");
        setPendingFiles([]);
        onClose();
    }, [onFiles, pendingFiles, advancedProcessing, description, category, onClose]);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            openMetadataModal(e.dataTransfer.files);
        },
        [openMetadataModal]
    );

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(true);
    }, []);

    const handleDragLeave = useCallback(() => {
        setDragOver(false);
    }, []);

    return (
        <VStack spacing={3} align="stretch">
            <Box
                border="2px dashed"
                borderColor={dragOver ? "blue.400" : "rgba(255,255,255,0.15)"}
                borderRadius="xl"
                bg={dragOver ? "rgba(59,130,246,0.1)" : "#1a1b2e"}
                p={8}
                textAlign="center"
                cursor="pointer"
                transition="all 0.2s"
                _hover={{ borderColor: "rgba(255,255,255,0.25)", bg: "#1e1f34" }}
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
            >
                {uploading ? (
                    <VStack spacing={3}>
                        <Spinner size="lg" color="blue.400" />
                        <Text color="whiteAlpha.600" fontSize="sm">
                            Enviando arquivo(s)...
                        </Text>
                    </VStack>
                ) : (
                    <VStack spacing={3}>
                        <Icon as={FiUploadCloud} boxSize={10} color="whiteAlpha.400" />
                        <Text fontWeight="medium" color="white">
                            Arraste arquivos ou clique para selecionar
                        </Text>
                        <Text fontSize="xs" color="whiteAlpha.500">
                            PDF, DOCX, CSV, TXT, MD, JSON, XML, HTML, XLSX, PPTX
                        </Text>
                    </VStack>
                )}
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={getAcceptedExtensions()}
                    multiple
                    style={{ display: "none" }}
                    onChange={(e) => {
                        openMetadataModal(e.target.files);
                        e.target.value = "";
                    }}
                />
            </Box>

            <Checkbox
                size="sm"
                colorScheme="blue"
                isChecked={advancedProcessing}
                onChange={(e) => setAdvancedProcessing(e.target.checked)}
            >
                <Text fontSize="xs" color="whiteAlpha.600">
                    Processamento avançado (OCR / tabelas complexas)
                </Text>
            </Checkbox>

            {/* Upload Metadata Modal */}
            <Modal isOpen={isOpen} onClose={onClose} size="md">
                <ModalOverlay />
                <ModalContent bg="#1a1b2e" border="1px solid" borderColor="rgba(255,255,255,0.08)">
                    <ModalHeader color="white">Detalhes do Upload</ModalHeader>
                    <ModalCloseButton color="whiteAlpha.600" />
                    <ModalBody>
                        <VStack spacing={4}>
                            <Box w="100%">
                                <Text fontSize="sm" color="whiteAlpha.500" mb={2}>
                                    {pendingFiles.length} arquivo(s) selecionado(s):{" "}
                                    {pendingFiles.map((f) => f.name).join(", ")}
                                </Text>
                            </Box>

                            <FormControl>
                                <FormLabel fontSize="sm" color="whiteAlpha.700">Categoria</FormLabel>
                                <Select
                                    placeholder="Selecione uma categoria (opcional)"
                                    size="sm"
                                    value={category}
                                    onChange={(e) => setCategory(e.target.value)}
                                    bg="#0d0e1f"
                                    borderColor="rgba(255,255,255,0.1)"
                                    color="white"
                                    _hover={{ borderColor: "rgba(255,255,255,0.2)" }}
                                >
                                    {KB_CATEGORIES.map((c) => (
                                        <option key={c.value} value={c.value}>
                                            {c.label}
                                        </option>
                                    ))}
                                </Select>
                            </FormControl>

                            <FormControl>
                                <FormLabel fontSize="sm" color="whiteAlpha.700">Descrição</FormLabel>
                                <Textarea
                                    placeholder="Descreva o conteúdo do documento (opcional)"
                                    size="sm"
                                    rows={3}
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    bg="#0d0e1f"
                                    borderColor="rgba(255,255,255,0.1)"
                                    color="white"
                                    _hover={{ borderColor: "rgba(255,255,255,0.2)" }}
                                    _placeholder={{ color: "whiteAlpha.400" }}
                                />
                            </FormControl>
                        </VStack>
                    </ModalBody>
                    <ModalFooter>
                        <Button variant="ghost" mr={3} onClick={onClose} size="sm" color="whiteAlpha.700" _hover={{ bg: "whiteAlpha.100" }}>
                            Cancelar
                        </Button>
                        <Button
                            colorScheme="blue"
                            onClick={handleConfirmUpload}
                            size="sm"
                            isLoading={uploading}
                        >
                            Enviar
                        </Button>
                    </ModalFooter>
                </ModalContent>
            </Modal>
        </VStack>
    );
}

// ── Documents Table ─────────────────────────────────────────

interface DocumentsTableProps {
    documents: KBDocument[];
    onDelete: (doc: KBDocument) => void;
    onRetry: (doc: KBDocument) => void;
}

function getFileColor(fileType: string | null): string {
    if (!fileType) return '#3b82f6';
    const t = fileType.toLowerCase();
    if (t.includes('pdf')) return '#ef4444';
    if (t.includes('doc') || t.includes('docx')) return '#3b82f6';
    if (t.includes('csv') || t.includes('xlsx') || t.includes('xls')) return '#10b981';
    if (t.includes('ppt') || t.includes('pptx')) return '#f97316';
    if (t.includes('json') || t.includes('xml')) return '#a855f7';
    if (t.includes('md') || t.includes('txt')) return '#6366f1';
    if (t.includes('html')) return '#ec4899';
    return '#3b82f6';
}

function DocumentsTable({ documents, onDelete, onRetry }: DocumentsTableProps) {
    if (documents.length === 0) {
        return (
            <VStack py={12} spacing={4} color="whiteAlpha.400">
                <Icon as={FiBook} boxSize={12} />
                <Text fontSize="lg" fontWeight="medium">
                    Nenhum documento ainda
                </Text>
                <Text fontSize="sm">
                    Faça o upload do seu primeiro documento acima.
                </Text>
            </VStack>
        );
    }

    return (
        <VStack spacing={3} align="stretch">
            {documents.map((doc) => {
                const fileColor = getFileColor(doc.file_type);

                return (
                    <Box
                        key={doc.id}
                        bg="#1a1b2e"
                        borderRadius="1rem"
                        border="1px solid rgba(255,255,255,0.08)"
                        p={5}
                        w="full"
                        transition="all 0.2s"
                        _hover={{ borderColor: 'rgba(255,255,255,0.15)', boxShadow: '0 4px 20px rgba(0,0,0,0.3)' }}
                        position="relative"
                        overflow="hidden"
                    >
                        <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={fileColor} />
                        <Flex justify="space-between" align="start">
                            <HStack spacing={4} flex={1} minW={0}>
                                <Flex
                                    w="40px" h="40px"
                                    borderRadius="lg"
                                    align="center" justify="center"
                                    bg={`${fileColor}20`}
                                    flexShrink={0}
                                >
                                    <Icon as={FiFile} boxSize={5} color={fileColor} />
                                </Flex>
                                <Box flex={1} minW={0}>
                                    <HStack spacing={2} mb={1}>
                                        <Text
                                            fontSize="sm"
                                            fontWeight="medium"
                                            color="white"
                                            isTruncated
                                            title={doc.file_name}
                                        >
                                            {doc.file_name}
                                        </Text>
                                        <Badge variant="subtle" fontSize="2xs" bg={`${fileColor}20`} color={fileColor}>
                                            {doc.file_type || "—"}
                                        </Badge>
                                    </HStack>
                                    <HStack spacing={3} flexWrap="wrap">
                                        {doc.description ? (
                                            <Tooltip label={doc.description} hasArrow placement="top">
                                                <Text fontSize="xs" color="whiteAlpha.500" isTruncated maxW="300px" cursor="help">
                                                    {doc.description}
                                                </Text>
                                            </Tooltip>
                                        ) : (
                                            <Text fontSize="xs" color="whiteAlpha.400" fontStyle="italic">Sem descrição</Text>
                                        )}
                                    </HStack>
                                </Box>
                            </HStack>

                            <HStack spacing={3} flexShrink={0} ml={4}>
                                <VStack spacing={1} align="end">
                                    <HStack spacing={2}>
                                        <StatusBadge doc={doc} />
                                        <CategoryBadge category={doc.category} />
                                    </HStack>
                                    <HStack spacing={3}>
                                        <HStack spacing={1}>
                                            <ChunkInfo doc={doc} />
                                            {doc.status !== 'processing' && doc.status !== 'pending' && (
                                                <Text fontSize="xs" color="whiteAlpha.400">chunks</Text>
                                            )}
                                        </HStack>
                                        <Text fontSize="xs" color="whiteAlpha.400">{formatDate(doc.created_at)}</Text>
                                    </HStack>
                                </VStack>
                                <HStack spacing={1}>
                                    {(doc.status === "failed" || doc.status === "partially_failed") && (
                                        <Tooltip label="Reprocessar documento" hasArrow>
                                            <IconButton
                                                aria-label="Reprocessar documento"
                                                icon={<FiRotateCw />}
                                                size="sm"
                                                variant="ghost"
                                                color="blue.400"
                                                _hover={{ bg: 'rgba(59,130,246,0.15)' }}
                                                onClick={() => onRetry(doc)}
                                            />
                                        </Tooltip>
                                    )}
                                    <Tooltip label="Deletar documento" hasArrow>
                                        <IconButton
                                            aria-label="Deletar documento"
                                            icon={<FiTrash2 />}
                                            size="sm"
                                            variant="ghost"
                                            color="red.400"
                                            _hover={{ bg: 'rgba(239,68,68,0.15)' }}
                                            onClick={() => onDelete(doc)}
                                        />
                                    </Tooltip>
                                </HStack>
                            </HStack>
                        </Flex>
                    </Box>
                );
            })}
        </VStack>
    );
}

// ── Main Page ───────────────────────────────────────────────

function AdminKnowledgeBasePage() {
    const { documents, loading, uploading, error, upload, remove, refresh } =
        useKnowledgeBase();
    const toast = useToast();

    const handleUpload = useCallback(
        async (files: File[], forceComplex: boolean, options?: UploadOptions) => {
            try {
                await upload(files, forceComplex, options);
                toast({
                    title: `${files.length} arquivo(s) enviado(s)`,
                    status: "success",
                    duration: 3000,
                    isClosable: true,
                });
            } catch {
                toast({
                    title: "Erro no upload",
                    description: error || "Tente novamente.",
                    status: "error",
                    duration: 5000,
                    isClosable: true,
                });
            }
        },
        [upload, toast, error]
    );

    const handleDelete = useCallback(
        async (doc: KBDocument) => {
            try {
                await remove(doc);
                toast({
                    title: "Documento removido",
                    status: "info",
                    duration: 2000,
                    isClosable: true,
                });
            } catch {
                toast({
                    title: "Erro ao remover",
                    status: "error",
                    duration: 3000,
                    isClosable: true,
                });
            }
        },
        [remove, toast]
    );

    const handleRetry = useCallback(
        async (doc: KBDocument) => {
            try {
                await retryDocument(doc);
                toast({
                    title: "Reprocessando documento...",
                    status: "info",
                    duration: 3000,
                    isClosable: true,
                });
                refresh();
            } catch (err) {
                toast({
                    title: "Erro ao reprocessar",
                    description: err instanceof Error ? err.message : "Tente novamente.",
                    status: "error",
                    duration: 5000,
                    isClosable: true,
                });
            }
        },
        [toast, refresh]
    );

    return (
        <AdminLayout>
            <Box p={8} maxW="1100px" mx="auto">
                <VStack spacing={6} align="stretch">
                    {/* Header */}
                    <Flex justify="space-between" align="center">
                        <Box>
                            <Heading
                                size="lg"
                                fontFamily="'Playfair Display', serif"
                                fontWeight="bold"
                                color="white"
                            >
                                <Text as="span">Base de </Text>
                                <Text
                                    as="span"
                                    bgGradient="linear(to-r, #06ffa5, #06d6a0)"
                                    bgClip="text"
                                >
                                    Conhecimento
                                </Text>
                            </Heading>
                            <Text fontSize="sm" color="gray.400" mt={1}>
                                Faça upload de documentos para alimentar a IA com contexto personalizado.
                            </Text>
                        </Box>
                        <Button
                            leftIcon={<FiRefreshCw />}
                            size="sm"
                            variant="outline"
                            borderColor="rgba(255,255,255,0.1)"
                            color="gray.300"
                            _hover={{ bg: "whiteAlpha.100", color: "white", borderColor: "whiteAlpha.200" }}
                            onClick={refresh}
                            isLoading={loading}
                        >
                            Atualizar
                        </Button>
                    </Flex>

                    {/* Upload Zone */}
                    <UploadZone onFiles={handleUpload} uploading={uploading} />

                    {/* Stats bar */}
                    {documents.length > 0 && (
                        <HStack spacing={6} py={2} borderBottom="1px solid" borderColor="rgba(255,255,255,0.08)">
                            <Text fontSize="xs" color="whiteAlpha.500">
                                <Text as="span" fontWeight="bold" color="white">
                                    {documents.length}
                                </Text>{" "}
                                documento(s)
                            </Text>
                            <Text fontSize="xs" color="whiteAlpha.500">
                                <Text as="span" fontWeight="bold" color="white">
                                    {documents.reduce((sum, d) => sum + d.chunk_count, 0)}
                                </Text>{" "}
                                chunks totais
                            </Text>
                            <Text fontSize="xs" color="whiteAlpha.500">
                                <Text as="span" fontWeight="bold" color="green.400">
                                    {documents.filter((d) => d.status === "completed").length}
                                </Text>{" "}
                                concluído(s)
                            </Text>
                            {documents.some((d) => d.status === "processing" || d.status === "pending") && (
                                <HStack spacing={1}>
                                    <Spinner size="xs" color="blue.400" />
                                    <Text fontSize="xs" color="blue.400">
                                        {documents.filter((d) => d.status === "processing" || d.status === "pending").length}{" "}
                                        em processamento
                                    </Text>
                                </HStack>
                            )}
                        </HStack>
                    )}

                    {/* Error banner */}
                    {error && (
                        <Box bg="rgba(239,68,68,0.1)" border="1px solid" borderColor="rgba(239,68,68,0.3)" borderRadius="md" p={3}>
                            <Text fontSize="sm" color="red.300">
                                {error}
                            </Text>
                        </Box>
                    )}

                    {/* Documents Table */}
                    {loading && documents.length === 0 ? (
                        <Flex justify="center" py={12}>
                            <Spinner size="lg" color="whiteAlpha.400" />
                        </Flex>
                    ) : (
                        <DocumentsTable documents={documents} onDelete={handleDelete} onRetry={handleRetry} />
                    )}
                </VStack>
            </Box>
        </AdminLayout>
    );
}

export default AdminKnowledgeBasePage;
