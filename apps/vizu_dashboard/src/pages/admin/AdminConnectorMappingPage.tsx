/**
 * AdminConnectorMappingPage - Column mapping confirmation page.
 *
 * After a connector is tested and saved, users are redirected here to:
 * 1. Review auto-matched columns (confidence >= 0.85)
 * 2. Disambiguate columns with medium confidence (0.70 - 0.85)
 * 3. Map or ignore unmatched columns
 * 4. Confirm and trigger data synchronization
 */

import { useState, useEffect, useCallback, useContext } from 'react';
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
import { useParams, useNavigate } from 'react-router-dom';
import { AuthContext } from '../../contexts/AuthContext';
import { FiCheck, FiAlertTriangle, FiX, FiDatabase, FiArrowRight, FiRefreshCw } from 'react-icons/fi';
import {
    useColumnMatching,
    buildFinalColumnMapping,
    type SchemaMatchResult,
} from '../../hooks/useColumnMatching';
import { supabase } from '../../lib/supabase';

// Canonical columns for display (Portuguese names matching fato_transacoes pipeline)
// These are the mappable canonical columns that the sync function knows how to route
const CANONICAL_COLUMNS: Record<string, string> = {
    // Transaction fields (-> fato_transacoes)
    pedido_id: 'ID do Pedido (documento)',
    data_transacao: 'Data da Transação',
    quantidade: 'Quantidade',
    valor_unitario: 'Valor Unitário',
    valor_total: 'Valor Total',
    status: 'Status',
    // Customer fields (-> dim_clientes)
    cliente_cpf_cnpj: 'CPF/CNPJ do Cliente',
    cliente_nome: 'Nome do Cliente',
    cliente_telefone: 'Telefone do Cliente',
    cliente_rua: 'Rua do Cliente',
    cliente_numero: 'Número do Cliente',
    cliente_bairro: 'Bairro do Cliente',
    cliente_cidade: 'Cidade do Cliente',
    cliente_uf: 'UF do Cliente',
    cliente_cep: 'CEP do Cliente',
    // Supplier fields (-> dim_fornecedores)
    fornecedor_cnpj: 'CNPJ do Fornecedor',
    fornecedor_nome: 'Nome do Fornecedor',
    fornecedor_telefone: 'Telefone do Fornecedor',
    fornecedor_cidade: 'Cidade do Fornecedor',
    fornecedor_uf: 'UF do Fornecedor',
    // Product fields (-> dim_produtos)
    produto_descricao: 'Descrição do Produto',
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
    const navigate = useNavigate();
    const toast = useToast();
    const auth = useContext(AuthContext);
    const clienteVizuId = auth?.clientId || '';

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
        nome_servico: string;
        tipo_servico: string;
        table_name?: string;
    } | null>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [sampleData, setSampleData] = useState<Record<string, any[]>>({});
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [_loadingSampleData, setLoadingSampleData] = useState(false);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [ingestionQuality, setIngestionQuality] = useState<Record<string, any> | null>(null);

    const { matchColumns, loading: matchLoading, error: matchError } = useColumnMatching();

    // Load credential info and source columns
    useEffect(() => {
        async function loadCredentialData() {
            if (!credentialId) return;
            if (!clienteVizuId) {
                toast({
                    title: 'Erro de autenticação',
                    description: 'Não foi possível identificar o cliente.',
                    status: 'error',
                    duration: 5000,
                });
                return;
            }

            try {
                // Get credential info
                const { data: credential, error: credError } = await supabase
                    .from('credencial_servico_externo')
                    .select('nome_servico, tipo_servico, connection_metadata')
                    .eq('id', parseInt(credentialId))
                    .single();

                if (credError) throw credError;

                setCredentialInfo({
                    nome_servico: credential.nome_servico,
                    tipo_servico: credential.tipo_servico,
                    table_name: credential.connection_metadata?.table_name,
                });

                // Get source columns and Edge Function results from client_data_sources
                const { data: dataSource, error } = await supabase
                    .from('client_data_sources')
                    .select(`
                        source_columns,
                        column_mapping,
                        source_sample_data,
                        unmapped_columns,
                        needs_review_columns,
                        match_confidence,
                        detected_entity_context,
                        sync_status
                    `)
                    .eq('credential_id', parseInt(credentialId))
                    .maybeSingle();

                if (error) {
                    console.error('Error loading data source:', error);
                    toast({
                        title: 'Erro ao carregar credencial',
                        description: 'Certifique-se de que o descobrimento de colunas foi concluído.',
                        status: 'error',
                        duration: 5000,
                    });
                    return;
                }

                if (!dataSource) {
                    // PGRST116: 0 rows — discovery hasn't completed yet
                    toast({
                        title: 'Descoberta de colunas em andamento',
                        description: 'Aguarde alguns segundos e recarregue a página.',
                        status: 'warning',
                        duration: 5000,
                    });
                    return;
                }

                if (dataSource?.source_columns) {
                    // Extract column names from source_columns
                    const columns = Array.isArray(dataSource.source_columns)
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        ? dataSource.source_columns.map((col: any) => typeof col === 'object' ? col.name : col)
                        : Object.keys(dataSource.source_columns);
                    setSourceColumns(columns);

                    // Load sample data if available
                    if (dataSource.source_sample_data) {
                        setLoadingSampleData(true);
                        try {
                            const samples = Array.isArray(dataSource.source_sample_data)
                                ? dataSource.source_sample_data
                                : [];

                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const sampleByColumn: Record<string, any[]> = {};
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            samples.forEach((row: any) => {
                                Object.entries(row).forEach(([col, val]) => {
                                    if (!sampleByColumn[col]) sampleByColumn[col] = [];
                                    sampleByColumn[col].push(val);
                                });
                            });

                            setSampleData(sampleByColumn);
                        } catch (err) {
                            console.error('Error parsing sample data:', err);
                        } finally {
                            setLoadingSampleData(false);
                        }
                    }

                    // If source_columns exist but column_mapping is empty, auto-trigger edge function matching
                    const hasMapping = dataSource.column_mapping && Object.keys(dataSource.column_mapping).length > 0;

                    if (!hasMapping && columns.length > 0) {
                        // Column matching hasn't been done yet — call edge function
                        try {
                            toast({
                                title: 'Mapeando colunas...',
                                description: 'Analisando esquema automaticamente.',
                                status: 'info',
                                duration: null,
                                isClosable: false,
                                id: 'matching-toast',
                            });

                            const edgeResult = await matchColumns(columns, 'invoices');

                            // Persist match results back to client_data_sources
                            // Save both as column_mapping (working copy) and auto_column_mapping (immutable record)
                            await supabase
                                .from('client_data_sources')
                                .update({
                                    column_mapping: edgeResult.matched,
                                    auto_column_mapping: edgeResult.matched,
                                    unmapped_columns: edgeResult.unmatched,
                                    needs_review_columns: edgeResult.needs_review,
                                    match_confidence: edgeResult.confidence_scores,
                                    detected_entity_context: edgeResult.detected_context || 'neutral',
                                })
                                .eq('credential_id', parseInt(credentialId));

                            toast.close('matching-toast');

                            setMatchResult(edgeResult);
                            setMappingState({
                                autoMatched: edgeResult.matched,
                                userSelections: {},
                                ignoredColumns: new Set(),
                            });
                        } catch (matchErr) {
                            console.error('Edge function matching error:', matchErr);
                            toast.close('matching-toast');
                            toast({
                                title: 'Erro ao mapear colunas',
                                description: 'Você pode mapear manualmente abaixo.',
                                status: 'warning',
                                duration: 5000,
                            });
                            // Set empty match result so user can map manually
                            setMatchResult({
                                matched: {},
                                unmatched: columns,
                                confidence_scores: {},
                                needs_review: [],
                                details: [],
                                detected_context: 'neutral',
                            });
                            setMappingState({
                                autoMatched: {},
                                userSelections: {},
                                ignoredColumns: new Set(),
                            });
                        }
                    } else {
                        // Build SchemaMatchResult from stored results
                        const edgeFunctionResult: SchemaMatchResult = {
                            matched: dataSource.column_mapping || {},
                            unmatched: Array.isArray(dataSource.unmapped_columns)
                                ? dataSource.unmapped_columns
                                : (dataSource.unmapped_columns ? Object.values(dataSource.unmapped_columns) : []),
                            confidence_scores: dataSource.match_confidence || {},
                            needs_review: Array.isArray(dataSource.needs_review_columns)
                                ? dataSource.needs_review_columns
                                : (dataSource.needs_review_columns ? [dataSource.needs_review_columns] : []),
                            details: [],
                            detected_context: dataSource.detected_entity_context || 'neutral',
                        };

                        setMatchResult(edgeFunctionResult);
                        setMappingState({
                            autoMatched: edgeFunctionResult.matched,
                            userSelections: {},
                            ignoredColumns: new Set(),
                        });
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
    }, [credentialId, toast]);

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
                .eq('id', parseInt(credentialId))
                .single();

            if (!credential?.client_id) {
                throw new Error('client_id não encontrado na credencial');
            }

            setSyncProgress(30);

            // Compute diff: what did the user change vs the auto match?
            const userChanges: Record<string, { from: string | null; to: string }> = {};
            const autoMatched = matchResult.matched || {};
            for (const [source, canonical] of Object.entries(finalMapping)) {
                if (autoMatched[source] !== canonical) {
                    userChanges[source] = {
                        from: autoMatched[source] || null,
                        to: canonical,
                    };
                }
            }
            // Columns that were auto-matched but user removed/ignored
            for (const [source, canonical] of Object.entries(autoMatched)) {
                if (!finalMapping[source]) {
                    userChanges[source] = { from: canonical, to: '__ignored__' };
                }
            }

            // Update client_data_sources with final mapping + change history
            const { error: updateError } = await supabase
                .from('client_data_sources')
                .update({
                    column_mapping: finalMapping,
                    user_column_changes: Object.keys(userChanges).length > 0 ? userChanges : null,
                    match_confidence: matchResult.confidence_scores,
                    ignored_columns: Array.from(mappingState.ignoredColumns),
                    is_auto_generated: false,
                    reviewed_at: new Date().toISOString(),
                    sync_status: 'syncing',
                })
                .eq('credential_id', parseInt(credentialId));

            if (updateError) throw updateError;

            setSyncProgress(50);

            // Call run-sync edge function (fire-and-forget)
            const { data: syncResponse, error: invokeError } = await supabase.functions.invoke('run-sync', {
                body: {
                    client_id: credential.client_id,
                    credential_id: parseInt(credentialId),
                    force_full_sync: true,
                },
            });

            if (invokeError) throw invokeError;
            if (!syncResponse?.job_id) throw new Error('Falha ao criar job de sincronização');

            const jobId = syncResponse.job_id;
            setSyncProgress(55);

            // Poll reg_jobs for progress
            let pollAttempts = 0;
            const maxPollAttempts = 360; // 30 min max (5s intervals)
            let finalResult: { status: string; result?: Record<string, unknown>; error_message?: string } | null = null;

            while (pollAttempts < maxPollAttempts) {
                await new Promise(r => setTimeout(r, 5000)); // 5s interval
                pollAttempts++;

                const { data: job, error: pollError } = await supabase
                    .schema('analytics_v2')
                    .from('reg_jobs')
                    .select('status, progress_pct, result, error_message')
                    .eq('job_id', jobId)
                    .single();

                if (pollError) {
                    console.warn('Poll error:', pollError);
                    continue;
                }

                // Map progress: 55% (our start) to 95% based on job's 0-100%
                const mappedProgress = 55 + Math.floor((job.progress_pct || 0) * 0.40);
                setSyncProgress(Math.min(mappedProgress, 95));

                if (job.status === 'completed' || job.status === 'failed') {
                    finalResult = job;
                    break;
                }
            }

            if (!finalResult) {
                throw new Error('Sincronização expirou após 30 minutos');
            }

            if (finalResult.status === 'failed') {
                throw new Error(finalResult.error_message || 'Falha na sincronização');
            }

            setSyncProgress(100);

            const rowsInserted = (finalResult.result as Record<string, unknown>)?.rows_inserted || 0;
            const targetTable = (finalResult.result as Record<string, unknown>)?.target_table || 'tabela';

            // Fetch ingestion quality stats from client_data_sources
            try {
                const { data: qualityData } = await supabase
                    .from('client_data_sources')
                    .select('ingestion_quality, quality_assessed_at')
                    .eq('credential_id', parseInt(credentialId))
                    .single();
                if (qualityData?.ingestion_quality) {
                    setIngestionQuality(qualityData.ingestion_quality);
                }
            } catch (qErr) {
                console.warn('Failed to fetch ingestion quality:', qErr);
            }

            toast({
                title: 'Sincronização concluída!',
                description: `${rowsInserted} registros sincronizados para ${targetTable}`,
                status: 'success',
                duration: 5000,
            });

            // Don't redirect — let user see quality report
            // User can navigate away manually

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

    // Sample data preview component
    const SampleDataPreview = ({ sourceColumn }: { sourceColumn: string }) => {
        const samples = sampleData[sourceColumn]?.slice(0, 5) || [];

        if (samples.length === 0) return null;

        return (
            <Box mt={2} p={3} bg="gray.50" borderRadius="md" fontSize="sm">
                <Text fontWeight="medium" color="gray.600" mb={2}>
                    📊 Dados de Exemplo:
                </Text>
                <VStack align="start" spacing={1}>
                    {samples.map((val, idx) => (
                        <HStack key={idx} spacing={2}>
                            <Badge colorScheme="gray" fontSize="xs">{idx + 1}</Badge>
                            <Text fontFamily="mono" fontSize="xs" color="gray.700">
                                {String(val).substring(0, 100)}
                                {String(val).length > 100 && '...'}
                            </Text>
                        </HStack>
                    ))}
                </VStack>
            </Box>
        );
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
                                {credentialInfo?.nome_servico || 'Carregando...'} • {credentialInfo?.tipo_servico}
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
                                                <>
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
                                                    {sampleData[source] && (
                                                        <Tr>
                                                            <Td colSpan={4} p={0} borderTop="none">
                                                                <Box p={2}>
                                                                    <SampleDataPreview sourceColumn={source} />
                                                                </Box>
                                                            </Td>
                                                        </Tr>
                                                    )}
                                                </>
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
                                                    {sampleData[source] && <SampleDataPreview sourceColumn={source} />}
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

                        {/* Ingestion Quality Report */}
                        {ingestionQuality && (
                            <Box border="1px solid" borderColor="blue.200" borderRadius="lg" p={5} bg="blue.50">
                                <HStack mb={4}>
                                    <Icon as={FiDatabase} color="blue.600" />
                                    <Text fontWeight="semibold" color="blue.800" fontSize="lg">
                                        Relatório de Qualidade da Ingestão
                                    </Text>
                                </HStack>

                                {/* Summary cards */}
                                <HStack spacing={4} mb={4} flexWrap="wrap">
                                    {ingestionQuality.summary && (
                                        <>
                                            <Box bg="white" p={3} borderRadius="md" minW="150px">
                                                <Text fontSize="xs" color="gray.500">Linhas carregadas (FDW)</Text>
                                                <Text fontSize="xl" fontWeight="bold" color="blue.700">
                                                    {(ingestionQuality.summary.rows_loaded || 0).toLocaleString()}
                                                </Text>
                                            </Box>
                                            <Box bg="white" p={3} borderRadius="md" minW="150px">
                                                <Text fontSize="xs" color="gray.500">Linhas inseridas</Text>
                                                <Text fontSize="xl" fontWeight="bold" color="green.600">
                                                    {(ingestionQuality.summary.rows_inserted || 0).toLocaleString()}
                                                </Text>
                                            </Box>
                                            <Box bg="white" p={3} borderRadius="md" minW="150px">
                                                <Text fontSize="xs" color="gray.500">Período dos dados</Text>
                                                <Text fontSize="sm" fontWeight="bold" color="purple.600">
                                                    {ingestionQuality.summary.date_range_min || '?'} → {ingestionQuality.summary.date_range_max || '?'}
                                                </Text>
                                            </Box>
                                            <Box bg="white" p={3} borderRadius="md" minW="150px">
                                                <Text fontSize="xs" color="gray.500">Duração</Text>
                                                <Text fontSize="xl" fontWeight="bold" color="gray.700">
                                                    {(() => {
                                                        const sec = ingestionQuality.summary.duration_seconds || 0;
                                                        if (sec >= 60) {
                                                            const m = Math.floor(sec / 60);
                                                            const s = sec % 60;
                                                            return `${m}m ${s}s`;
                                                        }
                                                        return `${sec}s`;
                                                    })()}
                                                </Text>
                                            </Box>
                                        </>
                                    )}
                                </HStack>

                                {/* Per-table stats */}
                                <Accordion allowMultiple>
                                    {/* Fato Transacoes quality */}
                                    {ingestionQuality.fato_transacoes && (
                                        <AccordionItem border="1px solid" borderColor="gray.200" borderRadius="md" mb={2} bg="white">
                                            <AccordionButton>
                                                <HStack flex={1}>
                                                    <Text fontWeight="medium">fato_transacoes</Text>
                                                    <Badge colorScheme="blue">{(ingestionQuality.fato_transacoes.total_rows || 0).toLocaleString()} linhas</Badge>
                                                </HStack>
                                                <AccordionIcon />
                                            </AccordionButton>
                                            <AccordionPanel>
                                                <Table size="sm">
                                                    <Thead>
                                                        <Tr>
                                                            <Th>Coluna</Th>
                                                            <Th isNumeric>Nulos</Th>
                                                            <Th isNumeric>Únicos</Th>
                                                            <Th isNumeric>Zeros</Th>
                                                            <Th>Min</Th>
                                                            <Th>Max</Th>
                                                        </Tr>
                                                    </Thead>
                                                    <Tbody>
                                                        {Object.keys(ingestionQuality.fato_transacoes.null_counts || {}).map((col) => (
                                                            <Tr key={col}>
                                                                <Td fontFamily="mono" fontSize="xs">{col}</Td>
                                                                <Td isNumeric>
                                                                    <Text color={ingestionQuality.fato_transacoes.null_counts[col] > 0 ? 'orange.500' : 'green.500'}>
                                                                        {ingestionQuality.fato_transacoes.null_counts[col] || 0}
                                                                    </Text>
                                                                </Td>
                                                                <Td isNumeric>{ingestionQuality.fato_transacoes.unique_counts?.[col] || '-'}</Td>
                                                                <Td isNumeric>{ingestionQuality.fato_transacoes.zero_counts?.[col] || '-'}</Td>
                                                                <Td fontSize="xs">{ingestionQuality.fato_transacoes.min_values?.[col] ?? '-'}</Td>
                                                                <Td fontSize="xs">{ingestionQuality.fato_transacoes.max_values?.[col] ?? '-'}</Td>
                                                            </Tr>
                                                        ))}
                                                    </Tbody>
                                                </Table>
                                            </AccordionPanel>
                                        </AccordionItem>
                                    )}

                                    {/* Dimension tables */}
                                    {['dim_clientes', 'dim_fornecedores', 'dim_inventory', 'dim_tipo_transacao', 'dim_categoria'].map((dim) => (
                                        ingestionQuality[dim] && (
                                            <AccordionItem key={dim} border="1px solid" borderColor="gray.200" borderRadius="md" mb={2} bg="white">
                                                <AccordionButton>
                                                    <HStack flex={1}>
                                                        <Text fontWeight="medium">{dim}</Text>
                                                        <Badge colorScheme="purple">{(ingestionQuality[dim].total_rows || 0).toLocaleString()} registros</Badge>
                                                    </HStack>
                                                    <AccordionIcon />
                                                </AccordionButton>
                                                <AccordionPanel>
                                                    {/* Null / Unique counts table */}
                                                    {ingestionQuality[dim].null_counts && (
                                                        <Table size="sm" mb={3}>
                                                            <Thead>
                                                                <Tr>
                                                                    <Th>Coluna</Th>
                                                                    <Th isNumeric>Nulos</Th>
                                                                    <Th isNumeric>Únicos</Th>
                                                                </Tr>
                                                            </Thead>
                                                            <Tbody>
                                                                {Object.keys(ingestionQuality[dim].null_counts).map((col: string) => (
                                                                    <Tr key={col}>
                                                                        <Td fontFamily="mono" fontSize="xs">{col}</Td>
                                                                        <Td isNumeric>
                                                                            <Text color={ingestionQuality[dim].null_counts[col] > 0 ? 'orange.500' : 'green.500'}>
                                                                                {(ingestionQuality[dim].null_counts[col] || 0).toLocaleString()}
                                                                            </Text>
                                                                        </Td>
                                                                        <Td isNumeric>{ingestionQuality[dim].unique_counts?.[col]?.toLocaleString() || '-'}</Td>
                                                                    </Tr>
                                                                ))}
                                                            </Tbody>
                                                        </Table>
                                                    )}

                                                    {/* Top UFs (clientes / fornecedores) */}
                                                    {ingestionQuality[dim].sample_ufs && (
                                                        <HStack spacing={2} mb={2} flexWrap="wrap">
                                                            <Text fontSize="xs" color="gray.500">Top UFs:</Text>
                                                            {ingestionQuality[dim].sample_ufs.map((uf: string, i: number) => (
                                                                <Badge key={i} colorScheme="teal" fontSize="xs">{uf}</Badge>
                                                            ))}
                                                        </HStack>
                                                    )}

                                                    {/* By categoria (dim_tipo_transacao) */}
                                                    {ingestionQuality[dim].by_categoria && (
                                                        <HStack spacing={3} mb={2} flexWrap="wrap">
                                                            {Object.entries(ingestionQuality[dim].by_categoria).map(([cat, cnt]) => (
                                                                <Box key={cat} bg="gray.50" p={2} borderRadius="md">
                                                                    <Text fontSize="xs" color="gray.500">{cat}</Text>
                                                                    <Text fontSize="md" fontWeight="bold">{(cnt as number).toLocaleString()}</Text>
                                                                </Box>
                                                            ))}
                                                        </HStack>
                                                    )}

                                                    {/* Nomes list (dim_categoria) */}
                                                    {ingestionQuality[dim].nomes && (
                                                        <HStack spacing={2} flexWrap="wrap">
                                                            {ingestionQuality[dim].nomes.map((n: string, i: number) => (
                                                                <Badge key={i} colorScheme="gray" fontSize="xs">{n}</Badge>
                                                            ))}
                                                        </HStack>
                                                    )}

                                                    {/* Fallback if no detail */}
                                                    {!ingestionQuality[dim].null_counts && !ingestionQuality[dim].by_categoria && !ingestionQuality[dim].nomes && (
                                                        <Text fontSize="sm" color="gray.500">Sem detalhes adicionais</Text>
                                                    )}
                                                </AccordionPanel>
                                            </AccordionItem>
                                        )
                                    ))}
                                </Accordion>

                                {/* Warnings */}
                                {ingestionQuality.warnings && ingestionQuality.warnings.length > 0 && (
                                    <Alert status="warning" mt={4} borderRadius="md">
                                        <AlertIcon />
                                        <VStack align="start" spacing={1}>
                                            {ingestionQuality.warnings.map((w: string, i: number) => (
                                                <Text key={i} fontSize="sm">{w}</Text>
                                            ))}
                                        </VStack>
                                    </Alert>
                                )}

                                <HStack mt={4} justify="flex-end">
                                    <Button size="sm" colorScheme="blue" variant="outline" onClick={() => navigate('/dashboard/admin/fontes')}>
                                        Ir para Fontes de Dados
                                    </Button>
                                </HStack>
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
