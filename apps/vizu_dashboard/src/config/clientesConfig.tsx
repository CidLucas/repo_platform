/**
 * Clientes Dimension Configuration
 *
 * Extracted from ClientesPage + ClientesListPage + ClienteDetailsModal.
 * Key differences from produtosConfig:
 *   - period='all'
 *   - Uses MV fallback (useMVMonthlySales) for chart data
 *   - 4 view modes on list page (+ product filter toggle)
 *   - ExpandableScorecardCard in modal (monthly orders chart)
 *   - receiver_* field extraction
 */
import React from 'react';
import { Box, Text, Badge } from '@chakra-ui/react';
import { useClientes, useClientesPageData } from '../hooks/useListData';
import {
    getCliente,
    getCustomersByProduct,
    getProductsByCustomer,
    getCustomersBySupplier,
    getCustomerMonthlyOrders,
} from '../services/analyticsService';
import type {
    ClientesOverviewResponse,
    ClienteDetailResponse,
    RankingItem,
} from '../services/analyticsService';
import type { DimensionConfig, ViewMode } from '../types/dimensionConfig';
import type { InsightBullet } from '../types';

// ─── Helpers ────────────────────────────────────────────────
const formatCurrency = (value: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
const formatCurrencyShort = (value: number) =>
    new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(value);
const formatNumber = (value: number) =>
    new Intl.NumberFormat('pt-BR').format(value);
const truncate = (name: string, max = 18) =>
    name.length > max ? name.substring(0, max) + '...' : name;

// ─── Config ─────────────────────────────────────────────────
export const clientesConfig: DimensionConfig<ClientesOverviewResponse, ClienteDetailResponse> = {

    // Identity
    dimensionName: 'cliente',
    dimensionNamePlural: 'clientes',
    basePath: '/dashboard/clientes',
    listPath: '/dashboard/clientes/lista',

    // Colors
    colors: {
        pageBg: '#FFB6C1',
        cardBg: '#FFD1DC',
        modalLeftBg: '#FFD1DC',
        modalRightBg: '#FFB6C1',
        hoverBg: 'pink.100',
    },

    // Data
    defaultPeriod: 'all',
    hooks: {
        useOverview: (opts) => {
            const result = useClientes({ period: opts?.period ?? 'all', enabled: opts?.enabled });
            return { data: result.data, isLoading: result.isLoading, error: result.error, refetch: result.refetch };
        },
        useListData: (period = 'all') => {
            const result = useClientesPageData(period);
            return {
                data: result.clientes,
                loading: result.loading,
                error: result.error,
                refetch: result.refetch,
                extra: { productsFilter: result.productsFilter },
            };
        },
    },

    // Overview — Header
    growthMessageBuilder: (data, userName) => {
        const crescimento = data?.scorecard_crescimento_percentual;
        if (crescimento !== null && crescimento !== undefined) {
            return `${userName}, sua base de clientes ${crescimento >= 0 ? 'aumentou' : 'reduziu'} em ${crescimento >= 0 ? '+' : ''}${crescimento.toFixed(2)}%`;
        }
        return `${userName}, sua base de clientes está sendo analisada`;
    },

    totalStat: {
        label: 'TOTAL DE CLIENTES',
        valueExtractor: (data) => data?.scorecard_total_clientes ?? 0,
    },

    // Overview — Performance Card
    performanceCardTitle: 'Performance de Clientes',

    performanceSlidesBuilder: (data) => {
        if (!data) return [];

        const clientes = data.ranking_por_receita || [];
        const totalReceita = clientes.reduce((sum, c: RankingItem) => sum + (c.receita_total || 0), 0);
        const totalPedidos = clientes.reduce((sum, c: RankingItem) => sum + (c.num_pedidos_unicos || 0), 0);
        const avgTicket = totalPedidos > 0 ? totalReceita / totalPedidos : 0;

        // Chart data — pulled directly from overview response
        // NOTE: In the original ClientesPage, MV fallback was used for chart data.
        // The MV data was identical in structure (name/value), so we keep the overview
        // data here — the caller can overlay MV data in the OverviewPage component if needed.
        const chartRevenueData = (data.chart_receita_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({
                name: d.name || '', value: (d.total ?? d.value ?? 0) as number,
            }),
        );
        const chartOrdersData = (data.chart_clientes_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({
                name: d.name || '', value: (d.total ?? d.value ?? 0) as number,
            }),
        );
        const chartCustomersData = (data.chart_clientes_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({
                name: d.name || '', value: (d.total ?? d.value ?? 0) as number,
            }),
        );
        const chartAvgOrderData = (data.chart_ticketmedio_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({
                name: d.name || '', value: (d.total ?? d.value ?? 0) as number,
            }),
        );

        return [
            { id: 'receita', title: 'Receita no Tempo', data: chartRevenueData, dataKey: 'value', lineColor: '#82ca9d', metricLabel: 'RECEITA TOTAL', metricValue: formatCurrency(totalReceita), rankingKey: 'ranking_por_receita' },
            { id: 'ticket_medio', title: 'Ticket Médio no Tempo', data: chartAvgOrderData, dataKey: 'value', lineColor: '#ffc658', metricLabel: 'TICKET MÉDIO', metricValue: formatCurrency(avgTicket), rankingKey: 'ranking_por_ticket_medio' },
            { id: 'qtd_pedidos', title: 'Pedidos no Tempo', data: chartOrdersData, dataKey: 'value', lineColor: '#8884d8', metricLabel: 'TOTAL DE PEDIDOS', metricValue: formatNumber(totalPedidos), rankingKey: 'ranking_por_qtd_pedidos' },
            { id: 'clientes', title: 'Clientes Únicos no Tempo', data: chartCustomersData, dataKey: 'value', lineColor: '#ff7300', metricLabel: 'TOTAL DE CLIENTES', metricValue: formatNumber(data.scorecard_total_clientes || 0), rankingKey: 'ranking_por_receita' },
        ];
    },

    kpiItemsBuilder: (data) => {
        if (!data) return [];
        const clientes = data.ranking_por_receita || [];
        const totalClientes = clientes.length || 1;
        const mediaReceitaPorCliente = clientes.reduce((sum, c: RankingItem) => sum + (c.receita_total || 0), 0) / totalClientes;
        const mediaFrequencia = clientes.reduce((sum, c: RankingItem) => sum + (c.frequencia_pedidos_mes || 0), 0) / totalClientes;
        const mediaTicketMedio = clientes.reduce((sum, c: RankingItem) => sum + (c.ticket_medio || 0), 0) / totalClientes;
        const mediaPedidos = clientes.reduce((sum, c: RankingItem) => sum + (c.num_pedidos_unicos || 0), 0) / totalClientes;
        return [
            { label: `Média de Receita por Cliente: R$ ${mediaReceitaPorCliente.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, content: (<Box><Text>Receita média gerada por cada cliente da base</Text><Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de clientes ({totalClientes})</Text></Box>) },
            { label: `Frequência Média de Pedidos: ${mediaFrequencia.toFixed(2)} pedidos/mês`, content: (<Box><Text>Frequência média de compras por cliente por mês</Text><Text mt={2} fontSize="sm">Indica a regularidade de compras dos clientes</Text></Box>) },
            { label: `Ticket Médio por Cliente: R$ ${mediaTicketMedio.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, content: (<Box><Text>Valor médio gasto por pedido por cliente</Text><Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text></Box>) },
            { label: `Média de Pedidos por Cliente: ${mediaPedidos.toFixed(1)} pedidos`, content: (<Box><Text>Número médio de pedidos realizados por cliente</Text><Text mt={2} fontSize="sm">Total de pedidos únicos dividido pelo número de clientes</Text></Box>) },
        ];
    },

    // Overview — Insights Card
    insightsCardTitle: 'Insights de Clientes',

    insightsScorecardBuilder: (data) => {
        if (!data) return { value: '0', label: 'Novos Cadastros' };
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        const newCount = (data.ranking_por_receita || []).filter((item: RankingItem) => {
            const firstSaleDate = new Date(item.primeira_venda);
            return firstSaleDate >= thirtyDaysAgo;
        }).length;
        return { value: String(newCount), label: 'Novos Cadastros' };
    },

    insightBulletsBuilder: (data): InsightBullet[] => {
        if (!data) return [];
        const clientes = data.ranking_por_receita || [];
        const totalClientes = clientes.length || 1;

        const tierA = clientes.filter((c: RankingItem) => c.cluster_tier === 'A');
        const tierACount = tierA.length;
        const tierAPercent = ((tierACount / totalClientes) * 100).toFixed(1);
        const receitaTierA = tierA.reduce((sum: number, c: RankingItem) => sum + (c.receita_total || 0), 0);
        const receitaTotal = clientes.reduce((sum: number, c: RankingItem) => sum + (c.receita_total || 0), 0);
        const tierAReceitaPercent = receitaTotal > 0 ? ((receitaTierA / receitaTotal) * 100).toFixed(1) : '0';

        const crescimento = data.scorecard_crescimento_percentual;

        const totalPedidosGeral = clientes.reduce((sum: number, c: RankingItem) => sum + (c.num_pedidos_unicos || 0), 0);
        const ticketMedio = totalPedidosGeral > 0 ? receitaTotal / totalPedidosGeral : 0;
        const ticketFormatado = formatCurrencyShort(ticketMedio);

        const topCliente = clientes[0];
        const topNome = topCliente?.nome ? truncate(topCliente.nome) : 'N/A';

        return [
            { text: `${tierACount} clientes Tier A (${tierAPercent}%) geram ${tierAReceitaPercent}% da receita`, type: 'star' },
            {
                text: crescimento !== null && crescimento !== undefined
                    ? `Base ${crescimento >= 0 ? 'cresceu' : 'reduziu'} ${Math.abs(crescimento).toFixed(1)}% no período`
                    : 'Analisando crescimento...',
                type: crescimento !== null && crescimento !== undefined && crescimento >= 0 ? 'positive' : 'warning',
            },
            { text: `Top cliente: ${topNome}`, type: 'star' },
            { text: `Ticket médio: ${ticketFormatado}`, type: 'neutral' },
        ];
    },

    carouselGraphsBuilder: (data) => {
        if (!data) return undefined;
        const chartCustomersData = (data.chart_clientes_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number }),
        );
        const chartRevenueData = (data.chart_receita_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number }),
        );
        const chartAvgOrderData = (data.chart_ticketmedio_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number }),
        );
        const chartOrdersData = (data.chart_clientes_no_tempo || []).map(
            (d: { name: string; total?: number; value?: number }) => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number }),
        );
        return [
            { data: chartCustomersData, dataKey: 'value', lineColor: '#82ca9d', title: 'Clientes Únicos por Mês', description: 'Evolução mensal do número de clientes únicos.' },
            { data: chartRevenueData, dataKey: 'value', lineColor: '#8884d8', title: 'Receita Mensal', description: 'Flutuação mensal da receita total.' },
            { data: chartAvgOrderData, dataKey: 'value', lineColor: '#ffc658', title: 'Ticket Médio no Tempo', description: 'Valor médio por pedido ao longo dos meses.' },
            { data: chartOrdersData, dataKey: 'value', lineColor: '#ff7300', title: 'Pedidos por Mês', description: 'Total de pedidos realizados mês a mês.' },
        ];
    },

    // Overview — List Card
    listCard: {
        rankingKeyMap: {
            receita: 'ranking_por_receita',
            ticket_medio: 'ranking_por_ticket_medio',
            qtd_pedidos: 'ranking_por_qtd_pedidos',
            clientes: 'ranking_por_receita',
        },
        descriptionFormatter: (item: Record<string, unknown>, metric: string) => {
            if (metric === 'receita' || metric === 'clientes')
                return `Receita: R$ ${((item.receita_total as number) ?? 0).toLocaleString('pt-BR')}`;
            if (metric === 'ticket_medio')
                return `Ticket Médio: R$ ${((item.ticket_medio as number) ?? 0).toLocaleString('pt-BR')}`;
            if (metric === 'qtd_pedidos')
                return `Qtd Pedidos: ${((item.num_pedidos_unicos as number) ?? 0).toLocaleString('pt-BR')}`;
            return '';
        },
        titleFormatter: (metric: string) => {
            switch (metric) {
                case 'receita': return 'Clientes com Maior Receita';
                case 'ticket_medio': return 'Clientes com Maior Ticket Médio';
                case 'qtd_pedidos': return 'Clientes com Mais Pedidos';
                case 'clientes': return 'Clientes com Maior Receita';
                default: return 'Clientes com Maior Receita';
            }
        },
    },

    // Overview — Map
    mapCardTitle: 'Distribuição Geográfica de Clientes',
    mapCardMainText: 'Principais regiões de atuação dos clientes.',

    // Services
    services: {
        getDetail: getCliente,
        getByProduct: getCustomersByProduct,
        getByCustomer: getProductsByCustomer,
        getBySupplier: getCustomersBySupplier,
    },

    // List Page
    listViewModes: ['all', 'by-product', 'by-customer', 'by-supplier'],
    defaultRankingKey: 'ranking_por_receita',
    hasProductFilter: true,

    tableColumns: {
        all: [
            { key: 'nome', label: 'Nome' },
            { key: 'receita_total', label: 'Receita Total', render: (item) => `R$ ${((item.receita_total as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'ticket_medio', label: 'Ticket Médio', render: (item) => `R$ ${((item.ticket_medio as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'frequencia_pedidos_mes', label: 'Frequência de Pedidos', render: (item) => `${((item.frequencia_pedidos_mes as number) ?? 0).toFixed(2)} / mês` },
            { key: 'cluster_tier', label: 'Tier' },
        ],
        'by-product': [
            { key: 'nome', label: 'Cliente' },
            { key: 'produto_receita', label: 'Gasto no Produto', isNumeric: true, render: (item) => (<Text fontWeight="bold" color="green.700">R$ {((item.produto_receita as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>) as React.ReactNode },
            { key: 'produto_quantidade', label: 'Quantidade', isNumeric: true, render: (item) => `${((item.produto_quantidade as number) ?? 0).toLocaleString('pt-BR')} kg` },
            { key: 'produto_pedidos', label: 'Pedidos', isNumeric: true },
            { key: 'cliente_receita_total', label: 'Total Gasto (Geral)', isNumeric: true, render: (item) => `R$ ${((item.cliente_receita_total as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
            { key: 'percentual_do_total', label: '% do Total', isNumeric: true, render: (item) => (<Badge colorScheme={Number(item.percentual_do_total) > 50 ? 'green' : Number(item.percentual_do_total) > 20 ? 'yellow' : 'gray'} fontSize="sm" px={2}>{Number(item.percentual_do_total).toFixed(1)}%</Badge>) as React.ReactNode },
        ],
        'by-customer': [
            { key: 'nome', label: 'Produto' },
            { key: 'receita_total', label: 'Receita Total', isNumeric: true, render: (item) => (<Text fontWeight="bold" color="green.700">R$ {((item.receita_total as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>) as React.ReactNode },
            { key: 'quantidade_total', label: 'Quantidade', isNumeric: true, render: (item) => `${((item.quantidade_total as number) ?? 0).toLocaleString('pt-BR')} kg` },
            { key: 'num_pedidos', label: 'Pedidos', isNumeric: true },
            { key: 'valor_unitario_medio', label: 'Preço Médio', isNumeric: true, render: (item) => `R$ ${((item.valor_unitario_medio as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
        ],
        'by-supplier': [
            { key: 'nome', label: 'Cliente' },
            { key: 'receita_total', label: 'Receita Total', isNumeric: true, render: (item) => (<Text fontWeight="bold" color="green.700">R$ {((item.receita_total as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>) as React.ReactNode },
            { key: 'quantidade_total', label: 'Quantidade', isNumeric: true, render: (item) => `${((item.quantidade_total as number) ?? 0).toLocaleString('pt-BR')} kg` },
            { key: 'num_pedidos', label: 'Pedidos', isNumeric: true },
            { key: 'ticket_medio', label: 'Ticket Médio', isNumeric: true, render: (item) => `R$ ${((item.ticket_medio as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
        ],
    },

    listLabels: {
        pageTitle: 'Clientes por Receita',
        newButtonLabel: 'Cadastrar Novo Cliente',
        filteredTitleBuilder: (viewMode: ViewMode, params: Record<string, string | null>) => {
            if (viewMode === 'by-product' && params.product) {
                return `Clientes que compraram: ${decodeURIComponent(params.product).substring(0, 40)}${params.product.length > 40 ? '...' : ''}`;
            }
            if (viewMode === 'by-customer' && params.client) {
                return `Produtos comprados por: ${decodeURIComponent(params.client).substring(0, 40)}${params.client.length > 40 ? '...' : ''}`;
            }
            if (viewMode === 'by-supplier' && params.supplierName) {
                return `Clientes de: ${decodeURIComponent(params.supplierName).substring(0, 40)}${params.supplierName.length > 40 ? '...' : ''}`;
            }
            return 'Clientes por Receita';
        },
    },

    // Detail Modal
    detailModal: {
        colors: { leftBg: '#FFD1DC', rightBg: '#FFB6C1', scorecardBg: '#FFD1DC' },
        showLoadingWhenNull: true,
        headerBuilder: (c) => ({
            subtitle: c.dados_cadastrais?.receiver_nome || 'N/A',
            title: `Cliente: ${c.dados_cadastrais?.receiver_nome || 'N/A'}`,
        }),
        leftPanelFields: [
            { label: 'CNPJ', valueExtractor: (c) => c.dados_cadastrais?.receiver_cnpj || 'N/A' },
            { label: 'TELEFONE', valueExtractor: (c) => c.dados_cadastrais?.receiver_telefone || 'N/A' },
            {
                label: 'ENDEREÇO', valueExtractor: (c) => {
                    const city = c.dados_cadastrais?.receiver_cidade || '';
                    const state = c.dados_cadastrais?.receiver_estado ? `, ${c.dados_cadastrais.receiver_estado}` : '';
                    return `${city}${state}`.trim() || 'N/A';
                }
            },
            { label: 'TIER', valueExtractor: (c) => c.scorecards?.cluster_tier || 'N/A' },
        ],
        rightPanelCards: [
            {
                titleExtractor: () => 'Produto Mais Comprado',
                valueExtractor: (c) => {
                    const top = c.rankings_internos?.mix_de_produtos_por_receita?.[0];
                    return top ? `${top.nome.substring(0, 30)}${top.nome.length > 30 ? '...' : ''}` : 'N/A';
                },
                subtitleExtractor: (c) => {
                    const top = c.rankings_internos?.mix_de_produtos_por_receita?.[0];
                    if (!top) return undefined;
                    return `R$ ${top.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}${top.quantidade_total ? ` | ${top.quantidade_total.toLocaleString('pt-BR')} kg` : ''}`;
                },
                bgColor: '#FFD1DC',
                getNavigateTo: (c) => {
                    const cnpj = c.dados_cadastrais?.receiver_cnpj;
                    const name = c.dados_cadastrais?.receiver_nome;
                    if (!cnpj || !name) return undefined;
                    return `/dashboard/produtos/lista?view=by-customer&customer=${encodeURIComponent(cnpj)}&customerName=${encodeURIComponent(name)}`;
                },
            },
            {
                titleExtractor: () => 'Total de Receita',
                valueExtractor: (c) => c.scorecards?.receita_total ? `R$ ${c.scorecards.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : 'N/A',
                subtitleExtractor: () => 'Lifetime Value',
                bgColor: '#FFD1DC',
                getNavigateTo: (c) => {
                    const name = c.dados_cadastrais?.receiver_nome;
                    return name ? `/dashboard/clientes/lista?view=customer&client=${encodeURIComponent(name)}` : undefined;
                },
            },
        ],
        expandableCard: {
            labelExtractor: () => 'Frequência de Compra',
            valueExtractor: (c) => c.scorecards?.frequencia_pedidos_mes ? `${c.scorecards.frequencia_pedidos_mes.toFixed(1)} pedidos/mês` : 'N/A',
            subtitleExtractor: (c) => {
                const city = c.dados_cadastrais?.receiver_cidade || '';
                const state = c.dados_cadastrais?.receiver_estado ? `, ${c.dados_cadastrais.receiver_estado}` : '';
                return `${city}${state}`.trim() || 'N/A';
            },
            bgColor: '#FFD1DC',
            fetchChartData: async (c) => {
                const cnpj = c.dados_cadastrais?.receiver_cnpj;
                if (!cnpj) return [];
                try {
                    const data = await getCustomerMonthlyOrders(cnpj);
                    return data.map(item => ({
                        name: item.month.substring(5),
                        pedidos: item.num_pedidos,
                    }));
                } catch {
                    return [];
                }
            },
            graphDataKey: 'pedidos',
            graphLineColor: '#FF69B4',
        },
    },
};
