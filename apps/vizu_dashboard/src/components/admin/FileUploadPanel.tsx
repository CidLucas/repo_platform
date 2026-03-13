import {
    Box,
    VStack,
    HStack,
    Heading,
    Text,
    Button,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Icon,
    IconButton,
    useToast,
    Badge,
    TabList,
    TabPanels,
    Tabs,
    Tab,
    TabPanel,
    Spinner,
    Input,
    FormControl,
    FormLabel,
} from '@chakra-ui/react';
import { useRef } from 'react';
import { FiTrash2, FiUploadCloud, FiFile, FiFileText } from 'react-icons/fi';
import type { UploadedFile } from '../../services/standaloneAgentService';

interface FileUploadPanelProps {
    csvFiles: UploadedFile[];
    documentFiles: UploadedFile[];
    uploading: boolean;
    onUploadCsv: (file: File) => Promise<UploadedFile | void>;
    onUploadDocument: (file: File) => Promise<UploadedFile | void>;
    onRemoveFile: (fileId: string, type: 'csv' | 'document') => Promise<void>;
    maxCsvFiles?: number;
    maxDocFiles?: number;
}

export const FileUploadPanel = ({
    csvFiles,
    documentFiles,
    uploading,
    onUploadCsv,
    onUploadDocument,
    onRemoveFile,
    maxCsvFiles = 5,
    maxDocFiles = 10,
}: FileUploadPanelProps) => {
    const csvInputRef = useRef<HTMLInputElement>(null);
    const docInputRef = useRef<HTMLInputElement>(null);
    const toast = useToast();

    const handleCsvSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (csvFiles.length >= maxCsvFiles) {
            toast({
                title: 'Limite atingido',
                description: `Máximo de ${maxCsvFiles} arquivos CSV`,
                status: 'warning',
                duration: 3000,
            });
            return;
        }

        const files = e.currentTarget.files;
        if (!files?.length) return;

        const file = files[0];

        // Validate CSV file
        if (!file.name.endsWith('.csv')) {
            toast({
                title: 'Formato inválido',
                description: 'Por favor, envie um arquivo .csv',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        // Validate file size (30MB max)
        if (file.size > 30 * 1024 * 1024) {
            toast({
                title: 'Arquivo muito grande',
                description: 'Máximo de 30MB por arquivo',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        try {
            await onUploadCsv(file);
        } finally {
            if (csvInputRef.current) csvInputRef.current.value = '';
        }
    };

    const handleDocSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (documentFiles.length >= maxDocFiles) {
            toast({
                title: 'Limite atingido',
                description: `Máximo de ${maxDocFiles} documentos`,
                status: 'warning',
                duration: 3000,
            });
            return;
        }

        const files = e.currentTarget.files;
        if (!files?.length) return;

        const file = files[0];

        // Validate file type
        const allowedTypes = [
            'application/pdf',
            'text/plain',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ];
        if (!allowedTypes.includes(file.type)) {
            toast({
                title: 'Tipo de arquivo não suportado',
                description: 'Suportamos: PDF, TXT, DOCX',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        // Validate file size (50MB max for documents)
        if (file.size > 50 * 1024 * 1024) {
            toast({
                title: 'Arquivo muito grande',
                description: 'Máximo de 50MB por arquivo',
                status: 'error',
                duration: 3000,
            });
            return;
        }

        try {
            await onUploadDocument(file);
        } finally {
            if (docInputRef.current) docInputRef.current.value = '';
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'green';
            case 'processing':
                return 'blue';
            case 'failed':
                return 'red';
            default:
                return 'gray';
        }
    };

    const getStatusLabel = (status: string) => {
        const labels: Record<string, string> = {
            completed: 'Concluído',
            processing: 'Processando',
            failed: 'Erro',
            pending: 'Pendente',
        };
        return labels[status] || status;
    };

    return (
        <Box borderWidth="1px" borderColor="gray.200" borderRadius="lg" p={6}>
            <Heading size="md" mb={6}>
                Arquivos
            </Heading>

            <Tabs isLazy>
                <TabList>
                    <Tab>
                        Dados CSV ({csvFiles.length}/{maxCsvFiles})
                    </Tab>
                    <Tab>
                        Documentos ({documentFiles.length}/{maxDocFiles})
                    </Tab>
                </TabList>

                <TabPanels>
                    {/* CSV Tab */}
                    <TabPanel>
                        <VStack align="stretch" spacing={4}>
                            <FormControl>
                                <FormLabel fontSize="sm">Enviar arquivo CSV</FormLabel>
                                <Input
                                    ref={csvInputRef}
                                    type="file"
                                    accept=".csv"
                                    onChange={handleCsvSelect}
                                    disabled={uploading || csvFiles.length >= maxCsvFiles}
                                    display="none"
                                />
                                <Button
                                    leftIcon={uploading ? <Spinner size="sm" /> : <Icon as={FiUploadCloud} />}
                                    onClick={() => csvInputRef.current?.click()}
                                    isDisabled={uploading || csvFiles.length >= maxCsvFiles}
                                    width="100%"
                                    variant="outline"
                                    borderRadius="md"
                                    py={6}
                                    fontSize="sm"
                                >
                                    {uploading ? 'Enviando...' : 'Clique ou arraste um CSV'}
                                </Button>
                                <Text fontSize="xs" color="gray.500" mt={2}>
                                    Máximo 30MB por arquivo. Suporta valores separados por vírgula, ponto-e-vírgula ou tabulação.
                                </Text>
                            </FormControl>

                            {csvFiles.length > 0 && (
                                <Box width="100%">
                                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                                        Arquivos enviados
                                    </Text>
                                    <Table size="sm" variant="simple">
                                        <Thead>
                                            <Tr>
                                                <Th>Nome</Th>
                                                <Th>Registros</Th>
                                                <Th>Status</Th>
                                                <Th width="60px">Ação</Th>
                                            </Tr>
                                        </Thead>
                                        <Tbody>
                                            {csvFiles.map((file) => (
                                                <Tr key={file.id}>
                                                    <Td>
                                                        <HStack spacing={2}>
                                                            <Icon as={FiFile} color="blue.500" boxSize={4} />
                                                            <Text fontSize="sm">{file.file_name}</Text>
                                                        </HStack>
                                                    </Td>
                                                    <Td fontSize="sm">{file.records_count}</Td>
                                                    <Td>
                                                        <Badge colorScheme={getStatusColor(file.status)}>
                                                            {file.status === 'processing' ? (
                                                                <HStack spacing={1}>
                                                                    <Spinner size="xs" />
                                                                    <Text>{getStatusLabel(file.status)}</Text>
                                                                </HStack>
                                                            ) : (
                                                                getStatusLabel(file.status)
                                                            )}
                                                        </Badge>
                                                    </Td>
                                                    <Td>
                                                        <IconButton
                                                            aria-label="Delete"
                                                            icon={<FiTrash2 />}
                                                            size="sm"
                                                            variant="ghost"
                                                            colorScheme="red"
                                                            onClick={() => onRemoveFile(file.id, 'csv')}
                                                            isDisabled={uploading}
                                                        />
                                                    </Td>
                                                </Tr>
                                            ))}
                                        </Tbody>
                                    </Table>
                                </Box>
                            )}
                        </VStack>
                    </TabPanel>

                    {/* Documents Tab */}
                    <TabPanel>
                        <VStack align="stretch" spacing={4}>
                            <FormControl>
                                <FormLabel fontSize="sm">Enviar documento</FormLabel>
                                <Input
                                    ref={docInputRef}
                                    type="file"
                                    accept=".pdf,.txt,.docx"
                                    onChange={handleDocSelect}
                                    disabled={uploading || documentFiles.length >= maxDocFiles}
                                    display="none"
                                />
                                <Button
                                    leftIcon={uploading ? <Spinner size="sm" /> : <Icon as={FiUploadCloud} />}
                                    onClick={() => docInputRef.current?.click()}
                                    isDisabled={uploading || documentFiles.length >= maxDocFiles}
                                    width="100%"
                                    variant="outline"
                                    borderRadius="md"
                                    py={6}
                                    fontSize="sm"
                                >
                                    {uploading ? 'Enviando...' : 'Clique ou arraste um documento'}
                                </Button>
                                <Text fontSize="xs" color="gray.500" mt={2}>
                                    Máximo 50MB. Formatos: PDF, TXT, DOCX
                                </Text>
                            </FormControl>

                            {documentFiles.length > 0 && (
                                <Box width="100%">
                                    <Text fontSize="sm" fontWeight="medium" mb={2}>
                                        Documentos enviados
                                    </Text>
                                    <Table size="sm" variant="simple">
                                        <Thead>
                                            <Tr>
                                                <Th>Nome</Th>
                                                <Th>Status</Th>
                                                <Th width="60px">Ação</Th>
                                            </Tr>
                                        </Thead>
                                        <Tbody>
                                            {documentFiles.map((file) => (
                                                <Tr key={file.id}>
                                                    <Td>
                                                        <HStack spacing={2}>
                                                            <Icon as={FiFileText} color="orange.500" boxSize={4} />
                                                            <Text fontSize="sm">{file.file_name}</Text>
                                                        </HStack>
                                                    </Td>
                                                    <Td>
                                                        <Badge colorScheme={getStatusColor(file.status)}>
                                                            {file.status === 'processing' ? (
                                                                <HStack spacing={1}>
                                                                    <Spinner size="xs" />
                                                                    <Text>{getStatusLabel(file.status)}</Text>
                                                                </HStack>
                                                            ) : (
                                                                getStatusLabel(file.status)
                                                            )}
                                                        </Badge>
                                                    </Td>
                                                    <Td>
                                                        <IconButton
                                                            aria-label="Delete"
                                                            icon={<FiTrash2 />}
                                                            size="sm"
                                                            variant="ghost"
                                                            colorScheme="red"
                                                            onClick={() => onRemoveFile(file.id, 'document')}
                                                            isDisabled={uploading}
                                                        />
                                                    </Td>
                                                </Tr>
                                            ))}
                                        </Tbody>
                                    </Table>
                                </Box>
                            )}
                        </VStack>
                    </TabPanel>
                </TabPanels>
            </Tabs>
        </Box>
    );
};
