/**
 * Generic List Page
 *
 * Config-driven replacement for ClientesListPage, FornecedoresListPage, ProdutosListPage.
 * Handles:
 *   - Default "all" view with entity-specific table columns
 *   - URL-param driven filtered views (by-product, by-customer, by-supplier)
 *   - Product filter toggle+select (clientes only, via config.hasProductFilter)
 *   - Row click → detail modal
 */
import {
    Box, Text, Flex, Table, Thead, Tbody, Tr, Th, Td,
    Button, useDisclosure, Spinner, Alert, AlertIcon,
    IconButton, Select,
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { GenericDetailsModal } from '../components/GenericDetailsModal';
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { DimensionConfig, ViewMode, TableColumnConfig } from '../types/dimensionConfig';

/* eslint-disable @typescript-eslint/no-explicit-any */

interface GenericListPageProps {
    config: DimensionConfig<any, any>;
}

export default function GenericListPage({ config }: GenericListPageProps) {
    const { isOpen, onOpen, onClose } = useDisclosure();
    const [searchParams, setSearchParams] = useSearchParams();

    // Entity detail for modal
    const [selectedEntity, setSelectedEntity] = useState<any>(null);

    // Data from React Query
    const listHook = config.hooks.useListData(config.defaultPeriod);
    const { data: overviewData, loading, error: queryError, refetch, extra } = listHook;

    // Local errors from user actions
    const [localError, setLocalError] = useState<string | null>(null);
    const error = queryError || localError;
    const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

    // ─── URL params ────────────────────────────────────────────
    const viewParam = searchParams.get('view');
    const productParam = searchParams.get('product');
    const productNameParam = searchParams.get('productName');
    const customerParam = searchParams.get('customer');
    const customerNameParam = searchParams.get('customerName');
    const supplierParam = searchParams.get('supplier');
    const supplierNameParam = searchParams.get('supplierName');
    const clientParam = searchParams.get('client');

    // Resolve initial view mode from URL
    const resolveInitialViewMode = useCallback((): ViewMode => {
        if (viewParam === 'product' || viewParam === 'by-product') return 'by-product';
        if (viewParam === 'customer' || viewParam === 'by-customer') return 'by-customer';
        if (viewParam === 'by-supplier') return 'by-supplier';
        return 'all';
    }, [viewParam]);

    const [viewMode, setViewMode] = useState<ViewMode>(resolveInitialViewMode);
    const [filteredData, setFilteredData] = useState<any[]>([]);
    const [loadingFiltered, setLoadingFiltered] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState<string>(productParam || '');

    // ─── Fetch filtered data based on URL params ───────────────
    const fetchFilteredData = useCallback(async (mode: ViewMode) => {
        setLoadingFiltered(true);
        try {
            let data: any[] = [];
            if (mode === 'by-product' && (productParam || selectedProduct)) {
                const identifier = productParam || selectedProduct;
                if (config.services.getByProduct) {
                    data = await config.services.getByProduct(identifier);
                }
            } else if (mode === 'by-customer' && (customerParam || clientParam)) {
                const identifier = customerParam || clientParam || '';
                if (config.services.getByCustomer) {
                    // For clientes by-customer view: we may need to fetch detail first for CPF/CNPJ
                    if (config.dimensionName === 'cliente' && clientParam) {
                        // The original ClientesListPage fetches cliente details first to get CNPJ
                        const details = await config.services.getDetail(clientParam);
                        const cpfCnpj = details?.dados_cadastrais?.receiver_cnpj;
                        if (cpfCnpj && config.services.getByCustomer) {
                            data = await config.services.getByCustomer(cpfCnpj);
                        }
                    } else {
                        data = await config.services.getByCustomer(identifier);
                    }
                }
            } else if (mode === 'by-supplier' && supplierParam) {
                if (config.services.getBySupplier) {
                    data = await config.services.getBySupplier(supplierParam);
                }
            }
            setFilteredData(data);
        } catch (err) {
            console.error(`Error fetching filtered data for ${config.dimensionName}:`, err);
            setFilteredData([]);
        } finally {
            setLoadingFiltered(false);
        }
    }, [config, productParam, customerParam, clientParam, supplierParam, selectedProduct]);

    // On mount / URL change, fetch filtered data
    useEffect(() => {
        if (loading) return;
        const mode = resolveInitialViewMode();
        setViewMode(mode);
        if (mode !== 'all') {
            fetchFilteredData(mode);
        }
    }, [loading, viewParam, productParam, customerParam, supplierParam, clientParam, resolveInitialViewMode, fetchFilteredData]);

    // Refetch filtered data when product filter selection changes (clientes)
    useEffect(() => {
        if (viewMode === 'by-product' && selectedProduct) {
            fetchFilteredData('by-product');
        }
    }, [selectedProduct, viewMode, fetchFilteredData]);

    // ─── Handlers ──────────────────────────────────────────────
    const handleRefresh = async () => {
        await refetch();
        setLastUpdate(new Date());
    };

    const handleRowClick = async (name: string) => {
        try {
            if (!name || name.trim() === '') {
                setLocalError(`Nome inválido.`);
                return;
            }
            setSelectedEntity(null);
            const details = await config.services.getDetail(name);
            setSelectedEntity(details);
            onOpen();
        } catch (err: unknown) {
            console.error(`Error loading ${config.dimensionName} details:`, err);
            setLocalError(err instanceof Error ? err.message : 'Erro ao carregar detalhes.');
        }
    };

    const handleViewModeChange = (mode: ViewMode) => {
        setViewMode(mode);
        if (mode === 'all') {
            setFilteredData([]);
            setSelectedProduct('');
            setSearchParams({});
        }
    };

    const handleProductChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const product = e.target.value;
        setSelectedProduct(product);
        if (product) {
            setSearchParams({ view: 'product', product });
        } else {
            setSearchParams({ view: 'product' });
        }
    };

    // ─── Derived state ─────────────────────────────────────────
    const isFiltered = viewMode !== 'all' && filteredData.length > 0;
    const defaultList: any[] = overviewData
        ? ((overviewData as any)[config.defaultRankingKey] || [])
        : [];

    // Products filter list (clientesConfig has this in extra)
    const productsFilter: any[] = extra?.productsFilter || [];

    // ─── Title ─────────────────────────────────────────────────
    const getPageTitle = () => {
        if (isFiltered && config.listLabels.filteredTitleBuilder) {
            return config.listLabels.filteredTitleBuilder(viewMode, {
                product: productParam || selectedProduct,
                productName: productNameParam,
                customer: customerParam,
                customerName: customerNameParam,
                supplier: supplierParam,
                supplierName: supplierNameParam,
                client: clientParam,
            });
        }
        return config.listLabels.pageTitle;
    };

    // ─── Column logic ──────────────────────────────────────────
    const getColumns = (): TableColumnConfig[] => {
        if (isFiltered) {
            return config.tableColumns[viewMode] || config.tableColumns.all || [];
        }
        return config.tableColumns.all || [];
    };

    const getDataSource = (): any[] => {
        if (isFiltered) return filteredData;
        return defaultList;
    };

    const getRowName = (item: any): string => {
        // Try different key names depending on entity type
        return item.nome || item.supplier_name || item.customer_name || item.name || '';
    };

    // ─── Loading / Error ───────────────────────────────────────
    if (loading) {
        return (
            <MainLayout>
                <Flex justify="center" align="center" height="100vh">
                    <Spinner size="xl" />
                </Flex>
            </MainLayout>
        );
    }

    if (error || !overviewData) {
        return (
            <MainLayout>
                <Flex justify="center" align="center" height="100vh">
                    <Alert status="error">
                        <AlertIcon />
                        {error || 'Não foi possível carregar os dados.'}
                    </Alert>
                </Flex>
            </MainLayout>
        );
    }

    const columns = getColumns();
    const dataSource = getDataSource();

    // ─── Render ────────────────────────────────────────────────
    return (
        <MainLayout>
            <Flex
                direction="column"
                flex="1"
                px={{ base: '20px', md: '40px', lg: '80px' }}
                pt={{ base: '20px', md: '40px', lg: '20px' }}
                pb={{ base: '80px', md: '40px', lg: '20px' }}
                bg={config.colors.pageBg}
                color="gray.800"
            >
                {/* Header */}
                <Flex justify="space-between" align="flex-end" mb="24px">
                    <Box>
                        <Flex align="center" gap={2} mb={2}>
                            <Text fontSize="sm" color="gray.600">
                                Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                            </Text>
                            <IconButton
                                icon={<RepeatIcon />}
                                aria-label="Atualizar dados"
                                size="xs"
                                onClick={handleRefresh}
                                isLoading={loading}
                            />
                        </Flex>
                        <Text as="h1" textStyle="pageTitle" mt="32px">
                            {getPageTitle()}
                        </Text>
                        {isFiltered && (
                            <Text fontSize="sm" color="gray.600" mt={1}>
                                {filteredData.length} itens encontrados
                            </Text>
                        )}
                    </Box>
                    {viewMode !== 'all' ? (
                        <Button
                            variant="outline"
                            borderColor="gray.800"
                            onClick={() => handleViewModeChange('all')}
                        >
                            Ver Todos
                        </Button>
                    ) : (
                        <Button variant="solid" bg="white" color="gray.800" _hover={{ bg: 'gray.100' }}>
                            {config.listLabels.newButtonLabel}
                        </Button>
                    )}
                </Flex>

                {/* Filters (only for entities with product filter toggle like Clientes) */}
                {config.hasProductFilter && viewMode === 'all' && (
                    <Flex gap={4} mb={6} align="center" flexWrap="wrap">
                        <Flex gap={2}>
                            <Button
                                size="sm"
                                variant={viewMode === 'all' ? 'solid' : 'outline'}
                                bg={viewMode === 'all' ? 'white' : 'transparent'}
                                borderColor="gray.800"
                                onClick={() => handleViewModeChange('all')}
                            >
                                Todos
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                bg="transparent"
                                borderColor="gray.800"
                                onClick={() => handleViewModeChange('by-product')}
                            >
                                Filtrar por Produto
                            </Button>
                        </Flex>
                    </Flex>
                )}

                {config.hasProductFilter && viewMode === 'by-product' && (
                    <Flex gap={4} mb={6} align="center" flexWrap="wrap">
                        <Flex gap={2}>
                            <Button
                                size="sm"
                                variant="outline"
                                bg="transparent"
                                borderColor="gray.800"
                                onClick={() => handleViewModeChange('all')}
                            >
                                Todos
                            </Button>
                            <Button
                                size="sm"
                                variant="solid"
                                bg="white"
                                borderColor="gray.800"
                            >
                                Filtrar por Produto
                            </Button>
                        </Flex>
                        <Select
                            placeholder="Selecione um produto..."
                            bg="white"
                            maxW="400px"
                            value={selectedProduct}
                            onChange={handleProductChange}
                        >
                            {productsFilter.map((product: any) => (
                                <option key={product.nome} value={product.nome}>
                                    {product.nome.substring(0, 50)}{product.nome.length > 50 ? '...' : ''}
                                    {product.total_clientes ? ` (${product.total_clientes} clientes)` : ''}
                                </option>
                            ))}
                        </Select>
                    </Flex>
                )}

                {/* Table */}
                {loadingFiltered ? (
                    <Flex justify="center" align="center" height="200px">
                        <Spinner size="xl" />
                    </Flex>
                ) : dataSource.length > 0 ? (
                    <Table variant="unstyled">
                        <Thead>
                            <Tr borderBottom="3px solid black">
                                {columns.map((col) => (
                                    <Th key={col.key} py={4} isNumeric={col.isNumeric}>
                                        {col.label}
                                    </Th>
                                ))}
                            </Tr>
                        </Thead>
                        <Tbody>
                            {dataSource.map((item: any, rowIndex: number) => {
                                const rowName = getRowName(item);
                                return (
                                    <Tr
                                        key={rowName || rowIndex}
                                        borderBottom={rowIndex < dataSource.length - 1 ? '1px solid black' : 'none'}
                                        cursor="pointer"
                                        _hover={{ bg: config.colors.hoverBg }}
                                        onClick={() => handleRowClick(rowName)}
                                    >
                                        {columns.map((col) => (
                                            <Td key={col.key} py={5} isNumeric={col.isNumeric}>
                                                {col.render
                                                    ? col.render(item as Record<string, unknown>)
                                                    : String(item[col.key] ?? '')}
                                            </Td>
                                        ))}
                                    </Tr>
                                );
                            })}
                        </Tbody>
                    </Table>
                ) : (
                    <Flex justify="center" align="center" height="200px">
                        <Text color="gray.600">
                            {viewMode !== 'all'
                                ? `Nenhum resultado encontrado para o filtro aplicado.`
                                : `Nenhum ${config.dimensionName} encontrado.`}
                        </Text>
                    </Flex>
                )}

                {/* Prompt to select product (clientes only) */}
                {config.hasProductFilter && viewMode === 'by-product' && !selectedProduct && !loadingFiltered && (
                    <Flex justify="center" align="center" height="200px">
                        <Text color="gray.600">Selecione um produto para ver os resultados.</Text>
                    </Flex>
                )}
            </Flex>

            {/* Detail Modal */}
            <GenericDetailsModal
                isOpen={isOpen}
                onClose={onClose}
                entity={selectedEntity}
                overviewData={overviewData}
                config={config.detailModal}
            />
        </MainLayout>
    );
}
