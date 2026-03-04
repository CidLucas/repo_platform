/**
 * Fornecedores Dimension Configuration
 *
 * Extracted from FornecedoresPage + FornecedoresListPage + FornecedorDetailsModal.
 * Key differences from produtosConfig:
 *   - period='month'
 *   - No carouselGraphs on insights card
 *   - 2 view modes on list page (all, by-product)
 *   - emitter_* field extraction in modal
 *   - GraphCarousel in modal (receita_no_tempo from detail response)
 */
import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { useFornecedores, useFornecedoresPageData } from '../hooks/useListData';
import {
    getFornecedor,
    getSuppliersByProduct,
    getProductsBySupplier,
    getCustomersBySupplier,
} from '../services/analyticsService';
import type {
    FornecedoresOverviewResponse,
    FornecedorDetailResponse,
    RankingItem,
} from '../services/analyticsService';
import type { DimensionConfig, ViewMode } from '../types/dimensionConfig';
import type { InsightBullet, ChartDataPoint } from '../types';

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
export const fornecedoresConfig: DimensionConfig<FornecedoresOverviewResponse, FornecedorDetailResponse> = {

    // Identity
    dimensionName: 'fornecedor',
    dimensionNamePlural: 'fornecedores',
    basePath: '/dashboard/fornecedores',
    listPath: '/dashboard/fornecedores/lista',

    // Colors
    colors: {
        pageBg: '#92DAFF',
        cardBg: '#D4F1F4',
        modalLeftBg: '#D4F1F4',
        modalRightBg: '#B2E7FF',
        hoverBg: 'blue.50',
    },

    // Data
    defaultPeriod: 'month',
    hooks: {
        useOverview: (opts) => {
            const result = useFornecedores({ period: opts?.period ?? 'month', enabled: opts?.enabled });
            return { data: result.data, isLoading: result.isLoading, error: result.error, refetch: result.refetch };
        },
        useListData: (period = 'month') => {
            const result = useFornecedoresPageData(period);
            return { data: result.fornecedores, loading: result.loading, error: result.error, refetch: result.refetch };
        },
    },

    // Overview — Header
    growthMessageBuilder: (data, userName) => {
        const crescimento = data?.scorecard_crescimento_percentual;
        if (crescimento !== null && crescimento !== undefined) {
            return `${userName}, sua base de fornecedores ${crescimento >= 0 ? 'aumentou' : 'reduziu'} em ${crescimento >= 0 ? '+' : ''}${crescimento.toFixed(2)}%`;
        }
        return `${userName}, sua base de fornecedores está sendo analisada`;
    },

    totalStat: {
        label: 'TOTAL DE FORNECEDORES',
        valueExtractor: (data) => data?.scorecard_total_fornecedores ?? 0,
    },

    // Overview — Performance Card
    performanceCardTitle: 'Performance de Fornecedores',

    performanceSlidesBuilder: (data) => {
        if (!data) return [];

        const totalReceita = (data.ranking_por_receita || []).reduce((sum, item: RankingItem) => sum + (item.receita_total || 0), 0);
        const totalQuantidade = (data.ranking_por_receita || []).reduce((sum, item: RankingItem) => sum + (item.quantidade_total || 0), 0);
        const totalPedidos = (data.ranking_por_receita || []).reduce((sum, item: RankingItem) => sum + (item.num_pedidos_unicos || 0), 0);
        const avgTicket = totalPedidos > 0 ? totalReceita / totalPedidos : 0;

        return [
            { id: 'receita', title: 'Receita no Tempo', data: (data.chart_receita_no_tempo || []).map(d => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number })), dataKey: 'value', lineColor: '#82ca9d', metricLabel: 'RECEITA TOTAL', metricValue: formatCurrency(totalReceita), rankingKey: 'ranking_por_receita' },
            { id: 'ticket_medio', title: 'Ticket Médio no Tempo', data: (data.chart_ticketmedio_no_tempo || []).map(d => ({ name: d.name || '', value: (d.total ?? d.value ?? 0) as number })), dataKey: 'value', lineColor: '#ffc658', metricLabel: 'TICKET MÉDIO', metricValue: formatCurrency(avgTicket), rankingKey: 'ranking_por_ticket_medio' },
            { id: 'quantidade', title: 'Quantidade no Tempo', data: (data.chart_quantidade_no_tempo || []).map((d: ChartDataPoint) => ({ name: d.name, value: (d.total ?? d.value ?? 0) as number })), dataKey: 'value', lineColor: '#8884d8', metricLabel: 'QUANTIDADE TOTAL', metricValue: formatNumber(totalQuantidade), rankingKey: 'ranking_por_qtd_media' },
            { id: 'fornecedores', title: 'Fornecedores Únicos no Tempo', data: (data.chart_fornecedores_no_tempo || []).map((d: ChartDataPoint) => ({ name: d.name, value: (d.total ?? d.value ?? 0) as number })), dataKey: 'value', lineColor: '#ff7300', metricLabel: 'TOTAL DE FORNECEDORES', metricValue: formatNumber(data.scorecard_total_fornecedores || 0), rankingKey: 'ranking_por_receita' },
        ];
    },

    kpiItemsBuilder: (data) => {
        if (!data) return [];
        const fornecedores = data.ranking_por_receita || [];
        const total = fornecedores.length || 1;
        const mediaReceita = fornecedores.reduce((sum, f: RankingItem) => sum + (f.receita_total || 0), 0) / total;
        const mediaFrequencia = fornecedores.reduce((sum, f: RankingItem) => sum + (f.frequencia_pedidos_mes || 0), 0) / total;
        const mediaTicket = fornecedores.reduce((sum, f: RankingItem) => sum + (f.ticket_medio || 0), 0) / total;
        const mediaQtd = fornecedores.reduce((sum, f: RankingItem) => sum + (f.qtd_media_por_pedido || 0), 0) / total;
        return [
            { label: `Média de Receita por Fornecedor: R$ ${mediaReceita.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, content: (<Box><Text>Receita média gerada por cada fornecedor da base</Text><Text mt={2} fontSize="sm">Calculado dividindo a receita total pelo número de fornecedores ({total})</Text></Box>) },
            { label: `Frequência Média de Vendas: ${mediaFrequencia.toFixed(2)} vendas/mês`, content: (<Box><Text>Frequência média de vendas por fornecedor por mês</Text><Text mt={2} fontSize="sm">Indica a regularidade de vendas dos fornecedores</Text></Box>) },
            { label: `Ticket Médio por Fornecedor: R$ ${mediaTicket.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, content: (<Box><Text>Valor médio gerado por pedido de cada fornecedor</Text><Text mt={2} fontSize="sm">Representa o valor médio de cada transação</Text></Box>) },
            { label: `Quantidade Média por Pedido: ${mediaQtd.toFixed(1)} unidades`, content: (<Box><Text>Quantidade média comercializada por pedido</Text><Text mt={2} fontSize="sm">Total de quantidade dividido pelo número de pedidos</Text></Box>) },
        ];
    },

    // Overview — Insights Card
    insightsCardTitle: 'Insights de Fornecedores',

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
        const fornecedores = data.ranking_por_receita || [];
        const totalFornecedores = fornecedores.length || 1;

        const tierA = fornecedores.filter((f: RankingItem) => f.cluster_tier === 'A');
        const tierACount = tierA.length;
        const tierAPercent = ((tierACount / totalFornecedores) * 100).toFixed(1);
        const receitaTierA = tierA.reduce((sum: number, f: RankingItem) => sum + (f.receita_total || 0), 0);
        const receitaTotal = fornecedores.reduce((sum: number, f: RankingItem) => sum + (f.receita_total || 0), 0);
        const tierAReceitaPercent = receitaTotal > 0 ? ((receitaTierA / receitaTotal) * 100).toFixed(1) : '0';

        const freqMedia = fornecedores.reduce((sum: number, f: RankingItem) => sum + (f.frequencia_pedidos_mes || 0), 0) / totalFornecedores;

        const totalPedidosGeral = fornecedores.reduce((sum: number, f: RankingItem) => sum + (f.num_pedidos_unicos || 0), 0);
        const ticketMedio = totalPedidosGeral > 0 ? receitaTotal / totalPedidosGeral : 0;
        const ticketFormatado = formatCurrencyShort(ticketMedio);

        const topFornecedor = fornecedores[0];
        const topNome = topFornecedor?.nome ? truncate(topFornecedor.nome) : 'N/A';

        return [
            { text: `${tierACount} fornecedores Tier A (${tierAPercent}%) geram ${tierAReceitaPercent}% da receita`, type: 'star' },
            { text: `${freqMedia >= 10 ? 'Alta' : freqMedia >= 4 ? 'Média' : 'Baixa'} frequência: ${freqMedia.toFixed(1)} vendas/mês`, type: freqMedia >= 4 ? 'positive' : 'warning' },
            { text: `Top fornecedor: ${topNome}`, type: 'star' },
            { text: `Ticket médio: ${ticketFormatado}`, type: 'neutral' },
        ];
    },

    carouselGraphsBuilder: (data) => {
        if (!data) return undefined;
        const tierACount = data.scorecard_tier_a_count || 0;
        const tierBCount = data.scorecard_tier_b_count || 0;
        const tierCCount = data.scorecard_tier_c_count || 0;
        const tierDCount = data.scorecard_tier_d_count || 0;
        const tierATicketMedio = data.scorecard_tier_a_ticket_medio || 0;
        const tierBTicketMedio = data.scorecard_tier_b_ticket_medio || 0;
        const tierCTicketMedio = data.scorecard_tier_c_ticket_medio || 0;
        const tierDTicketMedio = data.scorecard_tier_d_ticket_medio || 0;
        const tierAReceita = data.scorecard_tier_a_receita || 0;
        const tierBReceita = data.scorecard_tier_b_receita || 0;
        const tierCReceita = data.scorecard_tier_c_receita || 0;
        const tierDReceita = data.scorecard_tier_d_receita || 0;
        const barColors = ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'];
        return [
            { data: [{ name: 'Tier A', value: tierACount, color: '#4CAF50' }, { name: 'Tier B', value: tierBCount, color: '#FFC107' }, { name: 'Tier C', value: tierCCount, color: '#FF5722' }, { name: 'Tier D', value: tierDCount, color: '#9E9E9E' }], dataKey: 'value', title: 'Distribuição de Fornecedores por Tier', description: 'Quantidade de fornecedores em cada tier de performance.', chartType: 'bar' as const, barColors, valueLabel: 'Fornecedores' },
            { data: [{ name: 'Tier A', value: Math.round(tierATicketMedio), color: '#4CAF50' }, { name: 'Tier B', value: Math.round(tierBTicketMedio), color: '#FFC107' }, { name: 'Tier C', value: Math.round(tierCTicketMedio), color: '#FF5722' }, { name: 'Tier D', value: Math.round(tierDTicketMedio), color: '#9E9E9E' }], dataKey: 'value', title: 'Ticket Médio por Tier (R$)', description: 'Receita média por fornecedor em cada tier.', chartType: 'bar' as const, barColors, valueLabel: 'Ticket Médio (R$)' },
            { data: [{ name: 'Tier A', value: Math.round(tierAReceita), color: '#4CAF50' }, { name: 'Tier B', value: Math.round(tierBReceita), color: '#FFC107' }, { name: 'Tier C', value: Math.round(tierCReceita), color: '#FF5722' }, { name: 'Tier D', value: Math.round(tierDReceita), color: '#9E9E9E' }], dataKey: 'value', title: 'Receita por Tier (R$)', description: 'Comparativo da receita gerada por cada tier.', chartType: 'bar' as const, barColors, valueLabel: 'Receita (R$)' },
        ];
    },

    // Overview — List Card
    listCard: {
        rankingKeyMap: {
            receita: 'ranking_por_receita',
            quantidade: 'ranking_por_qtd_media',
            ticket_medio: 'ranking_por_ticket_medio',
            fornecedores: 'ranking_por_frequencia',
        },
        descriptionFormatter: (item: Record<string, unknown>, metric: string) => {
            if (metric === 'receita')
                return `Receita: R$ ${((item.receita_total as number) ?? 0).toLocaleString('pt-BR')}`;
            if (metric === 'quantidade')
                return `Qtd Média: ${((item.qtd_media_por_pedido as number) ?? 0).toLocaleString('pt-BR')}`;
            if (metric === 'ticket_medio')
                return `Ticket Médio: R$ ${((item.ticket_medio as number) ?? 0).toLocaleString('pt-BR')}`;
            if (metric === 'fornecedores')
                return `Frequência: ${((item.frequencia_pedidos_mes as number) ?? 0).toFixed(1)} vendas/mês`;
            return '';
        },
        titleFormatter: (metric: string) => {
            switch (metric) {
                case 'receita': return 'Fornecedores com Maior Receita';
                case 'quantidade': return 'Fornecedores com Maior Qtd Média';
                case 'ticket_medio': return 'Fornecedores com Maior Ticket Médio';
                case 'fornecedores': return 'Fornecedores com Maior Frequência';
                default: return 'Fornecedores com Maior Receita';
            }
        },
    },

    // Overview — Map
    mapCardTitle: 'Distribuição Geográfica de Fornecedores',
    mapCardMainText: 'Principais regiões de atuação dos fornecedores.',

    // Services
    services: {
        getDetail: getFornecedor,
        getByProduct: getSuppliersByProduct,
        getBySupplier: getProductsBySupplier,
        getByCustomer: getCustomersBySupplier,
    },

    // List Page
    listViewModes: ['all', 'by-product'],
    defaultRankingKey: 'ranking_por_receita',
    hasProductFilter: false,

    tableColumns: {
        all: [
            { key: 'nome', label: 'Nome' },
            { key: 'receita_total', label: 'Receita Total', render: (item) => `R$ ${((item.receita_total as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'ticket_medio', label: 'Ticket Médio', render: (item) => `R$ ${((item.ticket_medio as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'frequencia_pedidos_mes', label: 'Frequência de Pedidos', render: (item) => `${((item.frequencia_pedidos_mes as number) ?? 0).toFixed(2)} / mês` },
            { key: 'cluster_tier', label: 'Tier' },
        ],
        'by-product': [
            { key: 'supplier_name', label: 'Nome' },
            { key: 'total_revenue', label: 'Receita do Produto', render: (item) => `R$ ${((item.total_revenue as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'quantity_sold', label: 'Quantidade Vendida', render: (item) => ((item.quantity_sold as number) ?? 0).toLocaleString('pt-BR') },
            { key: 'order_count', label: 'Nº Pedidos' },
            { key: 'avg_unit_price', label: 'Preço Unit. Médio', render: (item) => `R$ ${((item.avg_unit_price as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
            { key: 'location', label: 'Cidade/UF', render: (item) => `${(item.endereco_cidade as string) || '-'} / ${(item.endereco_uf as string) || '-'}` },
        ],
    },

    listLabels: {
        pageTitle: 'Fornecedores por Receita',
        newButtonLabel: 'Cadastrar Novo Fornecedor',
        filteredTitleBuilder: (viewMode: ViewMode, params: Record<string, string | null>) => {
            if (viewMode === 'by-product' && params.productName) {
                return `Fornecedores do Produto: ${decodeURIComponent(params.productName).substring(0, 40)}${params.productName.length > 40 ? '...' : ''}`;
            }
            return 'Fornecedores por Receita';
        },
    },

    // Detail Modal
    detailModal: {
        colors: { leftBg: '#B2E7FF', rightBg: '#92DAFF', scorecardBg: '#B2E7FF' },
        showLoadingWhenNull: false,
        headerBuilder: (f) => ({
            subtitle: f.dados_cadastrais.emitter_nome || 'N/A',
            title: `Fornecedor: ${f.dados_cadastrais.emitter_nome || 'N/A'}`,
        }),
        leftPanelFields: [
            { label: 'CNPJ', valueExtractor: (f) => f.dados_cadastrais.emitter_cnpj || 'N/A' },
            { label: 'TELEFONE', valueExtractor: (f) => f.dados_cadastrais.emitter_telefone || 'N/A' },
            {
                label: 'ENDEREÇO', valueExtractor: (f) => {
                    const city = f.dados_cadastrais.emitter_cidade || '';
                    const state = f.dados_cadastrais.emitter_estado ? `, ${f.dados_cadastrais.emitter_estado}` : '';
                    return `${city}${state}`.trim() || 'N/A';
                }
            },
            // Extra left panel field: TOP CLIENTE
            {
                label: 'TOP CLIENTE (Receita)', valueExtractor: (f) => {
                    const top = f.rankings_internos?.clientes_por_receita?.[0];
                    return top ? `${top.nome} (R$ ${top.receita_total.toLocaleString('pt-BR')})` : 'N/A';
                }
            },
        ],
        rightPanelCards: [
            {
                titleExtractor: () => 'Produto Mais Vendido',
                valueExtractor: (f) => {
                    const top = f.rankings_internos?.produtos_por_receita?.[0];
                    return top ? `${top.nome.substring(0, 30)}${top.nome.length > 30 ? '...' : ''}` : 'N/A';
                },
                subtitleExtractor: (f) => {
                    const top = f.rankings_internos?.produtos_por_receita?.[0];
                    return top ? `R$ ${top.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : undefined;
                },
                bgColor: '#B2E7FF',
                getNavigateTo: (f) => {
                    const cnpj = f.dados_cadastrais.emitter_cnpj;
                    const name = f.dados_cadastrais.emitter_nome;
                    if (!cnpj || cnpj === 'N/A' || !name) return undefined;
                    return `/dashboard/produtos/lista?view=by-supplier&supplier=${encodeURIComponent(cnpj)}&supplierName=${encodeURIComponent(name)}`;
                },
            },
            {
                titleExtractor: () => 'Cliente Principal',
                valueExtractor: (f) => {
                    const top = f.rankings_internos?.clientes_por_receita?.[0];
                    return top ? `${top.nome.substring(0, 30)}${top.nome.length > 30 ? '...' : ''}` : 'N/A';
                },
                subtitleExtractor: (f) => {
                    const top = f.rankings_internos?.clientes_por_receita?.[0];
                    return top ? `R$ ${top.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : undefined;
                },
                bgColor: '#B2E7FF',
                getNavigateTo: (f) => {
                    const cnpj = f.dados_cadastrais.emitter_cnpj;
                    const name = f.dados_cadastrais.emitter_nome;
                    if (!cnpj || cnpj === 'N/A' || !name) return undefined;
                    return `/dashboard/clientes/lista?view=by-supplier&supplier=${encodeURIComponent(cnpj)}&supplierName=${encodeURIComponent(name)}`;
                },
            },
            {
                titleExtractor: () => 'Região de Atuação',
                valueExtractor: (f) => f.dados_cadastrais.emitter_estado || 'N/A',
                subtitleExtractor: (f) => {
                    const city = f.dados_cadastrais.emitter_cidade || '';
                    const state = f.dados_cadastrais.emitter_estado ? `, ${f.dados_cadastrais.emitter_estado}` : '';
                    return `${city}${state}`.trim() || 'N/A';
                },
                bgColor: '#B2E7FF',
            },
        ],
        graphCarousel: {
            slidesBuilder: (entity) => {
                if (!entity?.charts?.receita_no_tempo?.length) return [];
                return [
                    {
                        data: entity.charts.receita_no_tempo.map((d: { name: string; total?: number; receita?: number }) => ({
                            name: d.name,
                            receita: d.total || (d as Record<string, unknown>).receita || 0,
                        })) as ChartDataPoint[],
                        dataKey: 'receita',
                        lineColor: '#353A5A',
                        title: 'Receita Mensal do Fornecedor',
                    },
                ];
            },
        },
    },
};
