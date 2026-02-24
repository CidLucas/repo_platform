/**
 * AdminConnectorMappingPage - Column mapping confirmation page.
 *
 * After a connector is tested and saved, users are redirected here to:
 * 1. Review auto-matched columns (confidence >= 0.85)
 * 2. Disambiguate columns with medium confidence (0.70 - 0.85)
 * 3. Map or ignore unmatched columns
 * 4. Confirm and trigger data synchronization
 */

import { useState, useEffect, useCallback } from 'react';
import {
    Box,
    VStack,
    HStack,
    Text,
    Button,
    Icon,
    Alert,
    AlertIcon,
    Badge,
    Select,
    Checkbox,
    Spinner,
    useToast,
    Divider,
    Accordion,
    AccordionItem,
    AccordionButton,
    AccordionPanel,
    AccordionIcon,
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    Progress,
} from '@chakra-ui/react';
import { AdminLayout } from '../../components/layouts/AdminLayout';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { FiCheck, FiAlertTriangle, FiX, FiDatabase, FiArrowRight, FiRefreshCw } from 'react-icons/fi';
import {
    useColumnMatching,
    buildFinalColumnMapping,
    type SchemaMatchResult,
    type SchemaType
} from '../../hooks/useColumnMatching';
import { supabase } from '../../lib/supabase';

// Canonical columns for display (Portuguese names matching analytics_v2.vendas)
const CANONICAL_COLUMNS: Record<string, string> = {
    venda_id: 'ID da Venda',
    pedido_id: 'ID do Pedido',
    cliente_id: 'ID do Cliente',
    fornecedor_id: 'ID do Fornecedor',
    produto_id: 'ID do Produto',
    data_transacao: 'Data da Transação',
    quantidade: 'Quantidade',
    valor_unitario: 'Valor Unitário',
    valor_total: 'Valor Total',
    cliente_cpf_cnpj: 'CPF/CNPJ do Cliente',
    fornecedor_cnpj: 'CNPJ do Fornecedor',
    cliente_nome: 'Nome do Cliente',
    fornecedor_nome: 'Nome do Fornecedor',
    produto_descricao: 'Descrição do Produto',
    status: 'Status',
};

// All possible canonical columns for dropdown
const ALL_CANONICAL_OPTIONS = Object.entries(CANONICAL_COLUMNS).map(([value, label]) => ({
    value,
    label: `${label} (${value})`,
}));

interface MappingState {
    autoMatched: Record<string, string>;
    userSelections: Record<string, string>;
    ignoredColumns: Set<string>;
}

function AdminConnectorMappingPage() {
    const { credentialId } = useParams<{ credentialId: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const toast = useToast();

    // State
    const [sourceColumns, setSourceColumns] = useState<string[]>([]);
    const [matchResult, setMatchResult] = useState<SchemaMatchResult | null>(null);
    const [mappingState, setMappingState] = useState<MappingState>({
        autoMatched: {},
        userSelections: {},
        ignoredColumns: new Set(),
    });
    const [isSyncing, setIsSyncing] = useState(false);
    const [syncProgress, setSyncProgress] = useState(0);
    const [credentialInfo, setCredentialInfo] = useState<{
        nome_conexao: string;
        tipo_servico: string;
        table_name?: string;
    } | null>(null);

    const { matchColumns, loading: matchLoading, error: matchError } = useColumnMatching();

    // Load credential info and source columns
    useEffect(() => {
        async function loadCredentialData() {
            if (!credentialId) return;

            try {
                // Get credential info
                const { data: credential, error: credError } = await supabase
                    .from('credencial_servico_externo')
                    .select('nome_conexao, tipo_servico, connection_metadata')
                    .eq('id_credencial', parseInt(credentialId))
                    .single();

                if (credError) throw credError;

                setCredentialInfo({
                    nome_conexao: credential.nome_conexao,
                    tipo_servico: credential.tipo_servico,
                    table_name: credential.connection_metadata?.table_name,
                });

                // Get source columns from client_data_sources or query params
                const columnsParam = searchParams.get('columns');
                if (columnsParam) {
                    const columns = JSON.parse(decodeURIComponent(columnsParam));
                    setSourceColumns(columns);
                    // Auto-run matching
                    const result = await matchColumns(columns, 'invoices');
                    setMatchResult(result);
                    setMappingState({
                        autoMatched: result.matched,
                        userSelections: {},
                        ignoredColumns: new Set(),
                    });
                } else {
                    // Try to get from client_data_sources
                    const { data: dataSource } = await supabase
                        .from('client_data_sources')
                        .select('source_columns, column_mapping')
                        .eq('credential_id', parseInt(credentialId))
                        .single();

                    if (dataSource?.source_columns) {
                        const columns = Array.isArray(dataSource.source_columns)
                            ? dataSource.source_columns
                            : Object.keys(dataSource.source_columns);
                        setSourceColumns(columns);

                        // If already has column_mapping, use it
                        if (dataSource.column_mapping) {
                            setMappingState({
                                autoMatched: dataSource.column_mapping,
                                userSelections: {},
                                ignoredColumns: new Set(),
                            });
                        } else {
                            // Run matching
                            const result = await matchColumns(columns, 'invoices');
                            setMatchResult(result);
                            setMappingState({
                                autoMatched: result.matched,
                                userSelections: {},
                                ignoredColumns: new Set(),
                            });
                        }
                    }
                }
            } catch (err) {
                console.error('Error loading credential data:', err);
                toast({
                    title: 'Erro ao carregar dados',
                    description: err instanceof Error ? err.message : 'Erro desconhecido',
                    status: 'error',
                    duration: 5000,
                });
            }
        }

        loadCredentialData();
    }, [credentialId, searchParams, matchColumns, toast]);

    // Handle user selection for a column
    const handleColumnSelection = useCallback((sourceColumn: string, canonicalColumn: string) => {
        setMappingState(prev => ({
            ...prev,
            userSelections: {
                ...prev.userSelections,
                [sourceColumn]: canonicalColumn,
            },
        }));
    }, []);

    // Handle ignore column toggle
    const handleIgnoreColumn = useCallback((sourceColumn: string, ignored: boolean) => {
        setMappingState(prev => {
            const newIgnored = new Set(prev.ignoredColumns);
            if (ignored) {
                newIgnored.add(sourceColumn);
            } else {
                newIgnored.delete(sourceColumn);
            }
            return { ...prev, ignoredColumns: newIgnored };
        });
    }, []);

    // Re-run column matching
    const handleRematch = useCallback(async () => {
        if (sourceColumns.length === 0) return;
        const result = await matchColumns(sourceColumns, 'invoices');
        setMatchResult(result);
        setMappingState({
            autoMatched: result.matched,
            userSelections: {},
            ignoredColumns: new Set(),
        });
    }, [sourceColumns, matchColumns]);

    // Confirm mapping and start sync
    const handleConfirmAndSync = useCallback(async () => {
        if (!credentialId || !matchResult) return;

        setIsSyncing(true);
        setSyncProgress(10);

        try {
            // Build final column mapping
            const finalMapping = buildFinalColumnMapping(
                matchResult,
                mappingState.userSelections,
                Array.from(mappingState.ignoredColumns)
            );

            setSyncProgress(20);

            // Get client_id from credential
            const { data: credential } = await supabase
                .from('credencial_servico_externo')
                .select('client_id')
                .eq('id_credencial', parseInt(credentialId))
                .single();

            if (!credential?.client_id) {
                throw new Error('client_id não encontrado na credencial');
            }

            setSyncProgress(30);

            // Update client_data_sources with final mapping
            const { error: updateError } = await supabase
                .from('client_data_sources')
                .update({
                    column_mapping: finalMapping,
                    match_confidence: matchResult.confidence_scores,
                    ignored_columns: Array.from(mappingState.ignoredColumns),
                    is_auto_generated: false,
                    reviewed_at: new Date().toISOString(),
                    sync_status: 'syncing',
                })
                .eq('credential_id', parseInt(credentialId));

            if (updateError) throw updateError;

            setSyncProgress(50);

            // Call sincronizar_dados_cliente RPC
            const { data: syncResult, error: syncError } = await supabase
                .rpc('sincronizar_dados_cliente', {
                    p_client_id: credential.client_id,
                    p_credential_id: parseInt(credentialId),
                    p_force_full_sync: true,
                });

            setSyncProgress(90);

            if (syncError) throw syncError;

            setSyncProgress(100);

            toast({
                title: 'Sincronização concluída!',
                description: `${syncResult?.rows_inserted || 0} registros sincronizados`,
                status: 'success',
                duration: 5000,
            });

            // Redirect to fontes page
            setTimeout(() => {
                navigate('/dashboard/admin/fontes');
            }, 2000);

        } catch (err) {
            console.error('Sync error:', err);
            toast({
                title: 'Erro na sincronização',
                description: err instanceof Error ? err.message : 'Erro desconhecido',
                status: 'error',
                duration: 5000,
            });
        } finally {
            setIsSyncing(false);
        }
    }, [credentialId, matchResult, mappingState, toast, navigate]);

    // Render confidence badge
    const renderConfidenceBadge = (confidence: number) => {
        if (confidence >= 0.85) {
            return <Badge colorScheme="green" fontSize="xs">{Math.round(confidence * 100)}%</Badge>;
        } else if (confidence >= 0.70) {
            return <Badge colorScheme="yellow" fontSize="xs">{Math.round(confidence * 100)}%</Badge>;
        }
        return <Badge colorScheme="red" fontSize="xs">{Math.round(confidence * 100)}%</Badge>;
    };

    return (
        <AdminLayout>
            <Box p={8} maxW="1200px" mx="auto">
                {/* Header */}
                <VStack align="start" spacing={4} mb={8}>
                    <HStack spacing={3}>
                        <Icon as={FiDatabase} boxSize={6} color="blue.500" />
                        <VStack align="start" spacing={0}>
                            <Text fontSize="2xl" fontWeight="semibold">
                                Mapeamento de Colunas
                            </Text>
                            <Text fontSize="sm" color="gray.500">
                                {credentialInfo?.nome_conexao || 'Carregando...'} • {credentialInfo?.tipo_servico}
                            </Text>
                        </VStack>
                    </HStack>

                    {matchError && (
                        <Alert status="error" borderRadius="md">
                            <AlertIcon />
                            {matchError}
                        </Alert>
                    )}
                </VStack>

                {/* Loading state */}
                {matchLoading && (
                    <VStack py={12} spacing={4}>
                        <Spinner size="xl" color="blue.500" />
                        <Text color="gray.500">Analisando colunas...</Text>
                    </VStack>
                )}

                {/* Mapping interface */}
                {matchResult && !matchLoading && (
                    <VStack spacing={6} align="stretch">
                        {/* Summary cards */}
                        <HStack spacing={4}>
                            <Box bg="green.50" p={4} borderRadius="lg" flex={1}>
                                <HStack>
                                    <Icon as={FiCheck} color="green.500" />
                                    <Text fontWeight="medium" color="green.700">
                                        {Object.keys(matchResult.matched).length} Mapeadas Automaticamente
                                    </Text>
                                </HStack>
                            </Box>
                            <Box bg="yellow.50" p={4} borderRadius="lg" flex={1}>
                                <HStack>
                                    <Icon as={FiAlertTriangle} color="yellow.600" />
                                    <Text fontWeight="medium" color="yellow.700">
                                        {matchResult.needs_review.length} Precisam Revisão
                                    </Text>
                                </HStack>
                            </Box>
                            <Box bg="red.50" p={4} borderRadius="lg" flex={1}>
                                <HStack>
                                    <Icon as={FiX} color="red.500" />
                                    <Text fontWeight="medium" color="red.700">
                                        {matchResult.unmatched.length} Não Mapeadas
                                    </Text>
                                </HStack>
                            </Box>
                        </HStack>

                        {/* Context detection indicator */}
                        {matchResult.detected_context && matchResult.detected_context !== 'neutral' && (
                            <Alert status="info" borderRadius="lg">
                                <AlertIcon />
                                <Box>
                                    <Text fontWeight="medium">
                                        Contexto detectado: {matchResult.detected_context === 'customer' ? 'Cliente' :
                                            matchResult.detected_context === 'supplier' ? 'Fornecedor' : 'Produto'}
                                    </Text>
                                    <Text fontSize="sm" color="gray.600">
                                        Colunas ambíguas como "cnpj", "telefone" e "cidade" foram mapeadas
                                        para campos de {matchResult.detected_context === 'customer' ? 'cliente' :
                                            matchResult.detected_context === 'supplier' ? 'fornecedor' : 'produto'}
                                        com base nas outras colunas da tabela.
                                    </Text>
                                </Box>
                            </Alert>
                        )}

                        <Accordion allowMultiple defaultIndex={[0, 1]}>
                            {/* Auto-matched columns */}
                            <AccordionItem border="1px solid" borderColor="gray.200" borderRadius="lg" mb={4}>
                                <AccordionButton py={4}>
                                    <HStack flex={1}>
                                        <Icon as={FiCheck} color="green.500" />
                                        <Text fontWeight="medium">Mapeadas Automaticamente</Text>
                                        <Badge colorScheme="green">{Object.keys(matchResult.matched).length}</Badge>
                                    </HStack>
                                    <AccordionIcon />
                                </AccordionButton>
                                <AccordionPanel>
                                    <Table size="sm">
                                        <Thead>
                                            <Tr>
                                                <Th>Coluna Origem</Th>
                                                <Th></Th>
                                                <Th>Coluna Destino</Th>
                                                <Th>Confiança</Th>
                                            </Tr>
                                        </Thead>
                                        <Tbody>
                                            {Object.entries(matchResult.matched).map(([source, canonical]) => (
                                                <Tr key={source}>
                                                    <Td fontFamily="mono" fontSize="sm">{source}</Td>
                                                    <Td><Icon as={FiArrowRight} color="gray.400" /></Td>
                                                    <Td>
                                                        <Text fontWeight="medium">
                                                            {CANONICAL_COLUMNS[canonical] || canonical}
                                                        </Text>
                                                        <Text fontSize="xs" color="gray.500">{canonical}</Text>
                                                    </Td>
                                                    <Td>{renderConfidenceBadge(matchResult.confidence_scores[source] || 1)}</Td>
                                                </Tr>
                                            ))}
                                        </Tbody>
                                    </Table>
                                </AccordionPanel>
                            </AccordionItem>

                            {/* Needs review columns */}
                            {matchResult.needs_review.length > 0 && (
                                <AccordionItem border="1px solid" borderColor="yellow.200" borderRadius="lg" mb={4} bg="yellow.50">
                                    <AccordionButton py={4}>
                                        <HStack flex={1}>
                                            <Icon as={FiAlertTriangle} color="yellow.600" />
                                            <Text fontWeight="medium">Precisam de Revisão</Text>
                                            <Badge colorScheme="yellow">{matchResult.needs_review.length}</Badge>
                                        </HStack>
                                        <AccordionIcon />
                                    </AccordionButton>
                                    <AccordionPanel bg="white" borderRadius="md" p={4}>
                                        <VStack spacing={4} align="stretch">
                                            {matchResult.needs_review.map(({ source, candidates }) => (
                                                <Box key={source} p={4} border="1px solid" borderColor="gray.200" borderRadius="md">
                                                    <HStack justify="space-between" mb={3}>
                                                        <VStack align="start" spacing={0}>
                                                            <Text fontFamily="mono" fontWeight="medium">{source}</Text>
                                                            <Text fontSize="xs" color="gray.500">
                                                                Melhor correspondência: {renderConfidenceBadge(candidates[0]?.confidence || 0)}
                                                            </Text>
                                                        </VStack>
                                                        <Checkbox
                                                            isChecked={mappingState.ignoredColumns.has(source)}
                                                            onChange={(e) => handleIgnoreColumn(source, e.target.checked)}
                                                        >
                                                            Ignorar
                                                        </Checkbox>
                                                    </HStack>
                                                    <Select
                                                        size="sm"
                                                        placeholder="Selecione a coluna de destino"
                                                        value={mappingState.userSelections[source] || candidates[0]?.canonical || ''}
                                                        onChange={(e) => handleColumnSelection(source, e.target.value)}
                                                        isDisabled={mappingState.ignoredColumns.has(source)}
                                                    >
                                                        {ALL_CANONICAL_OPTIONS.map(opt => (
                                                            <option key={opt.value} value={opt.value}>
                                                                {opt.label}
                                                                {candidates.find(c => c.canonical === opt.value)
                                                                    ? ` (${Math.round(candidates.find(c => c.canonical === opt.value)!.confidence * 100)}%)`
                                                                    : ''}
                                                            </option>
                                                        ))}
                                                    </Select>
                                                </Box>
                                            ))}
                                        </VStack>
                                    </AccordionPanel>
                                </AccordionItem>
                            )}

                            {/* Unmatched columns */}
                            {matchResult.unmatched.length > 0 && (
                                <AccordionItem border="1px solid" borderColor="red.200" borderRadius="lg" mb={4}>
                                    <AccordionButton py={4}>
                                        <HStack flex={1}>
                                            <Icon as={FiX} color="red.500" />
                                            <Text fontWeight="medium">Não Mapeadas</Text>
                                            <Badge colorScheme="red">{matchResult.unmatched.length}</Badge>
                                        </HStack>
                                        <AccordionIcon />
                                    </AccordionButton>
                                    <AccordionPanel>
                                        <VStack spacing={3} align="stretch">
                                            {matchResult.unmatched.map((source) => (
                                                <Box key={source} p={3} border="1px solid" borderColor="gray.200" borderRadius="md">
                                                    <HStack justify="space-between" mb={2}>
                                                        <Text fontFamily="mono" fontSize="sm">{source}</Text>
                                                        <Checkbox
                                                            isChecked={mappingState.ignoredColumns.has(source)}
                                                            onChange={(e) => handleIgnoreColumn(source, e.target.checked)}
                                                        >
                                                            Ignorar
                                                        </Checkbox>
                                                    </HStack>
                                                    <Select
                                                        size="sm"
                                                        placeholder="Mapear para..."
                                                        value={mappingState.userSelections[source] || ''}
                                                        onChange={(e) => handleColumnSelection(source, e.target.value)}
                                                        isDisabled={mappingState.ignoredColumns.has(source)}
                                                    >
                                                        {ALL_CANONICAL_OPTIONS.map(opt => (
                                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                        ))}
                                                    </Select>
                                                </Box>
                                            ))}
                                        </VStack>
                                    </AccordionPanel>
                                </AccordionItem>
                            )}
                        </Accordion>

                        <Divider />

                        {/* Sync progress */}
                        {isSyncing && (
                            <Box>
                                <Text mb={2} fontSize="sm" color="gray.600">
                                    Sincronizando dados...
                                </Text>
                                <Progress value={syncProgress} colorScheme="blue" borderRadius="full" />
                            </Box>
                        )}

                        {/* Action buttons */}
                        <HStack justify="flex-end" spacing={4}>
                            <Button
                                variant="outline"
                                leftIcon={<FiRefreshCw />}
                                onClick={handleRematch}
                                isDisabled={matchLoading || isSyncing}
                            >
                                Remapear
                            </Button>
                            <Button
                                colorScheme="blue"
                                onClick={handleConfirmAndSync}
                                isLoading={isSyncing}
                                loadingText="Sincronizando..."
                                isDisabled={matchLoading}
                            >
                                Confirmar e Sincronizar
                            </Button>
                        </HStack>
                    </VStack>
                )}
            </Box>
        </AdminLayout>
    );
}

export default AdminConnectorMappingPage;
