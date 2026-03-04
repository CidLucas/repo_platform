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
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    IconButton,
    Spinner,
    Progress,
    Tooltip,
    useToast,
    Flex,
} from "@chakra-ui/react";
import { AdminLayout } from "../../components/layouts/AdminLayout";
import {
    FiUploadCloud,
    FiTrash2,
    FiRefreshCw,
    FiFile,
    FiBook,
} from "react-icons/fi";
import { useKnowledgeBase } from "../../hooks/useKnowledgeBase";
import { getAcceptedExtensions, type KBDocument } from "../../services/knowledgeBaseService";

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
        <Text fontSize="sm" color="gray.600">
            {doc.chunk_count}
        </Text>
    );
}

// ── Upload Zone ─────────────────────────────────────────────

interface UploadZoneProps {
    onFiles: (files: File[], forceComplex: boolean) => void;
    uploading: boolean;
}

function UploadZone({ onFiles, uploading }: UploadZoneProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);
    const [advancedProcessing, setAdvancedProcessing] = useState(false);

    const handleFiles = useCallback(
        (files: FileList | null) => {
            if (!files || files.length === 0) return;
            onFiles(Array.from(files), advancedProcessing);
        },
        [onFiles, advancedProcessing]
    );

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
        },
        [handleFiles]
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
                borderColor={dragOver ? "blue.400" : "gray.300"}
                borderRadius="xl"
                bg={dragOver ? "blue.50" : "gray.50"}
                p={8}
                textAlign="center"
                cursor="pointer"
                transition="all 0.2s"
                _hover={{ borderColor: "gray.400", bg: "gray.100" }}
                onClick={() => fileInputRef.current?.click()}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
            >
                {uploading ? (
                    <VStack spacing={3}>
                        <Spinner size="lg" color="blue.500" />
                        <Text color="gray.600" fontSize="sm">
                            Enviando arquivo(s)...
                        </Text>
                    </VStack>
                ) : (
                    <VStack spacing={3}>
                        <Icon as={FiUploadCloud} boxSize={10} color="gray.400" />
                        <Text fontWeight="medium" color="gray.700">
                            Arraste arquivos ou clique para selecionar
                        </Text>
                        <Text fontSize="xs" color="gray.500">
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
                        handleFiles(e.target.files);
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
                <Text fontSize="xs" color="gray.600">
                    Processamento avançado (OCR / tabelas complexas)
                </Text>
            </Checkbox>
        </VStack>
    );
}

// ── Documents Table ─────────────────────────────────────────

interface DocumentsTableProps {
    documents: KBDocument[];
    onDelete: (doc: KBDocument) => void;
}

function DocumentsTable({ documents, onDelete }: DocumentsTableProps) {
    if (documents.length === 0) {
        return (
            <VStack py={12} spacing={4} color="gray.400">
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
        <Box overflowX="auto">
            <Table variant="simple" size="sm">
                <Thead>
                    <Tr>
                        <Th>Nome</Th>
                        <Th>Tipo</Th>
                        <Th>Modo</Th>
                        <Th>Status</Th>
                        <Th>Chunks</Th>
                        <Th>Data</Th>
                        <Th w="50px" />
                    </Tr>
                </Thead>
                <Tbody>
                    {documents.map((doc) => (
                        <Tr key={doc.id} _hover={{ bg: "gray.50" }}>
                            <Td>
                                <HStack spacing={2}>
                                    <Icon as={FiFile} color="gray.400" />
                                    <Text
                                        fontSize="sm"
                                        fontWeight="medium"
                                        maxW="250px"
                                        isTruncated
                                        title={doc.file_name}
                                    >
                                        {doc.file_name}
                                    </Text>
                                </HStack>
                            </Td>
                            <Td>
                                <Badge variant="subtle" colorScheme="purple" fontSize="xs">
                                    {doc.file_type || "—"}
                                </Badge>
                            </Td>
                            <Td>
                                <Badge
                                    variant="outline"
                                    colorScheme={doc.processing_mode === "complex" ? "orange" : "gray"}
                                    fontSize="xs"
                                >
                                    {doc.processing_mode === "complex" ? "Avançado" : "Simples"}
                                </Badge>
                            </Td>
                            <Td>
                                <StatusBadge doc={doc} />
                            </Td>
                            <Td>
                                <ChunkInfo doc={doc} />
                            </Td>
                            <Td>
                                <Text fontSize="xs" color="gray.500">
                                    {formatDate(doc.created_at)}
                                </Text>
                            </Td>
                            <Td>
                                <IconButton
                                    aria-label="Deletar documento"
                                    icon={<FiTrash2 />}
                                    size="sm"
                                    variant="ghost"
                                    colorScheme="red"
                                    onClick={() => onDelete(doc)}
                                />
                            </Td>
                        </Tr>
                    ))}
                </Tbody>
            </Table>
        </Box>
    );
}

// ── Main Page ───────────────────────────────────────────────

function AdminKnowledgeBasePage() {
    const { documents, loading, uploading, error, upload, remove, refresh } =
        useKnowledgeBase();
    const toast = useToast();

    const handleUpload = useCallback(
        async (files: File[], forceComplex: boolean) => {
            try {
                await upload(files, forceComplex);
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

    return (
        <AdminLayout>
            <Box p={8} maxW="960px" mx="auto">
                <VStack spacing={6} align="stretch">
                    {/* Header */}
                    <Flex justify="space-between" align="center">
                        <Box>
                            <Heading size="lg" fontWeight="semibold">
                                Base de Conhecimento
                            </Heading>
                            <Text fontSize="sm" color="gray.500" mt={1}>
                                Faça upload de documentos para alimentar a IA com contexto personalizado.
                            </Text>
                        </Box>
                        <Button
                            leftIcon={<FiRefreshCw />}
                            size="sm"
                            variant="ghost"
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
                        <HStack spacing={6} py={2} borderBottom="1px solid" borderColor="gray.100">
                            <Text fontSize="xs" color="gray.500">
                                <Text as="span" fontWeight="bold" color="gray.700">
                                    {documents.length}
                                </Text>{" "}
                                documento(s)
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                                <Text as="span" fontWeight="bold" color="gray.700">
                                    {documents.reduce((sum, d) => sum + d.chunk_count, 0)}
                                </Text>{" "}
                                chunks totais
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                                <Text as="span" fontWeight="bold" color="green.600">
                                    {documents.filter((d) => d.status === "completed").length}
                                </Text>{" "}
                                concluído(s)
                            </Text>
                            {documents.some((d) => d.status === "processing" || d.status === "pending") && (
                                <HStack spacing={1}>
                                    <Spinner size="xs" color="blue.400" />
                                    <Text fontSize="xs" color="blue.500">
                                        {documents.filter((d) => d.status === "processing" || d.status === "pending").length}{" "}
                                        em processamento
                                    </Text>
                                </HStack>
                            )}
                        </HStack>
                    )}

                    {/* Error banner */}
                    {error && (
                        <Box bg="red.50" border="1px solid" borderColor="red.200" borderRadius="md" p={3}>
                            <Text fontSize="sm" color="red.600">
                                {error}
                            </Text>
                        </Box>
                    )}

                    {/* Documents Table */}
                    {loading && documents.length === 0 ? (
                        <Flex justify="center" py={12}>
                            <Spinner size="lg" color="gray.400" />
                        </Flex>
                    ) : (
                        <DocumentsTable documents={documents} onDelete={handleDelete} />
                    )}
                </VStack>
            </Box>
        </AdminLayout>
    );
}

export default AdminKnowledgeBasePage;
