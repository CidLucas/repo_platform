/**
 * Produtos Dimension Configuration
 *
 * Reference implementation — ProdutosPage is the cleanest model.
 */
import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { useProdutos, useProdutosPageData } from '../hooks/useListData';
import {
    getProdutoDetails,
    getProductsByCustomer,
    getProductsBySupplier,
} from '../services/analyticsService';
import type {
    ProdutosOverviewResponse,
    ProdutoDetailResponse,
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
const truncate = (name: string, max = 22) =>
    name.length > max ? name.substring(0, max) + '...' : name;

// ─── Config ─────────────────────────────────────────────────
export const produtosConfig: DimensionConfig<ProdutosOverviewResponse, ProdutoDetailResponse> = {

    // Identity
    dimensionName: 'produto',
    dimensionNamePlural: 'produtos',
    basePath: '/dashboard/produtos',
    listPath: '/dashboard/produtos/lista',

    // Colors
    colors: {
        pageBg: '#FFF856',
        cardBg: '#FFFB97',
        modalLeftBg: '#FFFB97',
        modalRightBg: '#FFF856',
        hoverBg: 'yellow.100',
    },

    // Data
    defaultPeriod: 'month',
    hooks: {
        useOverview: (opts) => {
            const result = useProdutos({ period: opts?.period ?? 'month', enabled: opts?.enabled });
            return { data: result.data, isLoading: result.isLoading, error: result.error, refetch: result.refetch };
        },
        useListData: (period = 'month') => {
            const result = useProdutosPageData(period);
            return { data: result.produtos, loading: result.loading, error: result.error, refetch: result.refetch };
        },
    },

    // Overview — Header
    growthMessageBuilder: (data, userName) => {
        const crescimento = data?.scorecard_crescimento_percentual ?? 0;
        const absValue = Math.abs(crescimento).toFixed(1);
        if (crescimento > 0) return `${userName}, você vendeu mais ${absValue}% em produtos este mês`;
        if (crescimento < 0) return `${userName}, você vendeu menos ${absValue}% em produtos este mês`;
        return `${userName}, suas vendas de produtos estão estáveis este mês`;
    },

    totalStat: {
        label: 'TOTAL DE PRODUTOS',
        valueExtractor: (data) => data?.scorecard_total_itens_unicos ?? 0,
    },

    // Overview — Performance Card
    performanceCardTitle: 'Performance de Produtos',

    performanceSlidesBuilder: (data) => {
        if (!data) return [];

        const totalQuantidade = data.scorecard_quantidade_total || 0;
        const totalReceita = data.scorecard_receita_total || 0;
        const avgTicket = data.scorecard_ticket_medio || 0;

        const chartQuantidade = (data.chart_quantidade_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
            name: d.name, value: d.total ?? d.value ?? 0,
        }));
        const chartReceita = (data.chart_receita_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
            name: d.name, value: d.total ?? d.value ?? 0,
        }));
        const chartProdutos = (data.chart_produtos_no_tempo || []).map((d: { name: string; total?: number; value?: number }) => ({
            name: d.name, value: d.total ?? d.value ?? 0,
        }));
        const quantidadeArr = data.chart_quantidade_no_tempo || [];
        const receitaArr = data.chart_receita_no_tempo || [];
        const chartTicketMedio = receitaArr.map((r: { name: string; total?: number; value?: number }, idx: number) => {
            const qItem = quantidadeArr[idx] as { total?: number; value?: number } | undefined;
            const q = qItem?.total ?? qItem?.value ?? 1;
            const rv = r.total ?? r.value ?? 0;
            return { name: r.name, value: q > 0 ? rv / q : 0 };
        });

        return [
            { id: 'quantidade', title: 'Quantidade no Tempo', data: chartQuantidade, dataKey: 'value', lineColor: '#82ca9d', metricLabel: 'QUANTIDADE KGs MENSAL', metricValue: formatNumber(totalQuantidade), rankingKey: 'ranking_por_volume' },
            { id: 'ticket_medio', title: 'Ticket Médio no Tempo', data: chartTicketMedio, dataKey: 'value', lineColor: '#8884d8', metricLabel: 'TICKET MÉDIO KGs MENSAL', metricValue: formatCurrency(avgTicket), rankingKey: 'ranking_por_ticket_medio' },
            { id: 'receita', title: 'Receita no Tempo', data: chartReceita, dataKey: 'value', lineColor: '#ffc658', metricLabel: 'RECEITA MENSAL', metricValue: formatCurrency(totalReceita), rankingKey: 'ranking_por_receita' },
            { id: 'produtos', title: 'Produtos Únicos no Tempo', data: chartProdutos, dataKey: 'value', lineColor: '#ff7300', metricLabel: 'PRODUTOS ÚNICOS MENSAL', metricValue: formatNumber(data.scorecard_total_itens_unicos || 0), rankingKey: 'ranking_por_receita' },
        ];
    },

    kpiItemsBuilder: (data) => {
        if (!data) return [];
        const totalQuantidade = data.scorecard_quantidade_total || 0;
        const totalReceita = data.scorecard_receita_total || 0;
        const totalProdutos = data.scorecard_total_itens_unicos || 0;
        const avgTicket = data.scorecard_ticket_medio || 0;
        return [
            { label: `Total Vendido: ${totalQuantidade.toLocaleString('pt-BR')} unidades`, content: (<Box><Text>Quantidade total de produtos vendidos no período</Text><Text mt={2} fontSize="sm">Soma de todas as unidades vendidas de todos os produtos</Text></Box>) },
            { label: `Receita Total: R$ ${totalReceita.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, content: (<Box><Text>Receita total gerada por todos os produtos</Text><Text mt={2} fontSize="sm">Soma do faturamento de todos os produtos no período</Text></Box>) },
            { label: `Produtos Únicos Vendidos: ${totalProdutos}`, content: (<Box><Text>Número de produtos únicos com vendas no período</Text><Text mt={2} fontSize="sm">Produtos que tiveram pelo menos uma venda</Text></Box>) },
            { label: `Ticket Médio KG's: R$ ${avgTicket.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`, content: (<Box><Text>Valor médio por unidade vendida</Text><Text mt={2} fontSize="sm">Receita total dividida pela quantidade total vendida</Text></Box>) },
        ];
    },

    // Overview — Insights Card
    insightsCardTitle: 'Insights de Produtos',

    insightsScorecardBuilder: (data) => ({
        value: String(data?.scorecard_total_itens_unicos ?? 0),
        label: 'Produtos Classificados',
    }),

    insightBulletsBuilder: (data): InsightBullet[] => {
        if (!data || !data.scorecard_total_itens_unicos) return [];
        const allProducts = data.ranking_por_receita || [];
        const totalReceita = data.scorecard_receita_total || 0;
        const tierAReceita = data.scorecard_tier_a_receita || 0;
        const tierACount = data.scorecard_tier_a_count || 0;
        const avgTicket = data.scorecard_ticket_medio || 0;

        const bullets: InsightBullet[] = [];

        const topReceita = allProducts[0];
        if (topReceita?.nome) {
            bullets.push({ text: `Líder receita: ${truncate(topReceita.nome)} (${formatCurrencyShort(topReceita.receita_total)})`, type: 'star' });
        }
        const tierAReceitaPercent = totalReceita > 0 ? ((tierAReceita / totalReceita) * 100).toFixed(1) : '0';
        bullets.push({ text: `${tierACount} produtos Tier A geram ${tierAReceitaPercent}% da receita`, type: 'star' });

        const rankingVolume = data.ranking_por_volume || [];
        const topVolume = rankingVolume[0];
        if (topVolume?.nome && topVolume.nome !== topReceita?.nome) {
            bullets.push({ text: `Maior volume: ${truncate(topVolume.nome)} (${formatNumber(topVolume.quantidade_total)} un)`, type: 'neutral' });
        }

        const topVariacaoNome = data.top_variacao_produto_nome;
        const topVariacaoPercent = data.top_variacao_produto_percentual || 0;
        const topVariacaoDirecao = data.top_variacao_produto_direcao || 'stable';
        if (topVariacaoNome && Math.abs(topVariacaoPercent) > 1) {
            const txt = topVariacaoPercent >= 0 ? `+${topVariacaoPercent.toFixed(1)}%` : `${topVariacaoPercent.toFixed(1)}%`;
            const tipo = topVariacaoDirecao === 'up' ? 'negative' : topVariacaoDirecao === 'down' ? 'positive' : 'neutral';
            bullets.push({ text: `Maior variação preço: ${truncate(topVariacaoNome, 18)} (${txt})`, type: tipo as InsightBullet['type'] });
        }

        const rankingTicket = data.ranking_por_ticket_medio || [];
        const topTicket = rankingTicket[0];
        if (topTicket?.nome && topTicket.nome !== topReceita?.nome) {
            bullets.push({ text: `Maior ticket: ${truncate(topTicket.nome)} (${formatCurrencyShort(topTicket.ticket_medio)}/un)`, type: 'neutral' });
        }

        if (bullets.length < 4) {
            bullets.push({ text: `Ticket médio geral: ${formatCurrencyShort(avgTicket)}/unidade`, type: 'neutral' });
        }
        return bullets.slice(0, 4);
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
        const tierAQuantidade = data.scorecard_tier_a_quantidade || 0;
        const tierBQuantidade = data.scorecard_tier_b_quantidade || 0;
        const tierCQuantidade = data.scorecard_tier_c_quantidade || 0;
        const tierDQuantidade = data.scorecard_tier_d_quantidade || 0;
        const barColors = ['#4CAF50', '#FFC107', '#FF5722', '#9E9E9E'];
        return [
            { data: [{ name: 'Tier A', value: tierACount, color: '#4CAF50' }, { name: 'Tier B', value: tierBCount, color: '#FFC107' }, { name: 'Tier C', value: tierCCount, color: '#FF5722' }, { name: 'Tier D', value: tierDCount, color: '#9E9E9E' }], dataKey: 'value', title: 'Distribuição de Produtos por Tier', description: 'Quantidade de produtos em cada tier de performance.', chartType: 'bar' as const, barColors, valueLabel: 'Produtos' },
            { data: [{ name: 'Tier A', value: Math.round(tierATicketMedio), color: '#4CAF50' }, { name: 'Tier B', value: Math.round(tierBTicketMedio), color: '#FFC107' }, { name: 'Tier C', value: Math.round(tierCTicketMedio), color: '#FF5722' }, { name: 'Tier D', value: Math.round(tierDTicketMedio), color: '#9E9E9E' }], dataKey: 'value', title: 'Ticket Médio por Tier (R$)', description: 'Receita total dividida pela quantidade vendida em cada tier.', chartType: 'bar' as const, barColors, valueLabel: 'Ticket Médio (R$)' },
            { data: [{ name: 'Tier A', value: Math.round(tierAReceita), color: '#4CAF50' }, { name: 'Tier B', value: Math.round(tierBReceita), color: '#FFC107' }, { name: 'Tier C', value: Math.round(tierCReceita), color: '#FF5722' }, { name: 'Tier D', value: Math.round(tierDReceita), color: '#9E9E9E' }], dataKey: 'value', title: 'Receita por Tier (R$)', description: 'Comparativo da receita gerada por cada tier.', chartType: 'bar' as const, barColors, valueLabel: 'Receita (R$)' },
            { data: [{ name: 'Tier A', value: Math.round(tierAQuantidade), color: '#4CAF50' }, { name: 'Tier B', value: Math.round(tierBQuantidade), color: '#FFC107' }, { name: 'Tier C', value: Math.round(tierCQuantidade), color: '#FF5722' }, { name: 'Tier D', value: Math.round(tierDQuantidade), color: '#9E9E9E' }], dataKey: 'value', title: 'Quantidade Vendida por Tier', description: 'Comparativo da quantidade total vendida por tier.', chartType: 'bar' as const, barColors, valueLabel: 'Quantidade' },
        ];
    },

    // Overview — List Card
    listCard: {
        rankingKeyMap: {
            receita: 'ranking_por_receita',
            quantidade: 'ranking_por_volume',
            ticket_medio: 'ranking_por_ticket_medio',
            produtos: 'ranking_por_receita',
        },
        descriptionFormatter: (item: Record<string, unknown>, metric: string) => {
            const qtd = (item.quantidade_total as number) ?? 0;
            const ticketMedio = (item.ticket_medio as number) ?? (item.valor_unitario_medio as number) ?? 0;
            const valorUnit = (item.valor_unitario_medio as number) ?? 0;
            const receita = (item.receita_total as number) ?? 0;
            let primary = '';
            if (metric === 'receita' || metric === 'produtos') primary = `Receita: R$ ${receita.toLocaleString('pt-BR')}`;
            else if (metric === 'quantidade') primary = `Quantidade: ${qtd.toLocaleString('pt-BR')}`;
            else if (metric === 'ticket_medio') primary = `Ticket Médio: R$ ${ticketMedio.toLocaleString('pt-BR')}`;
            return `${primary} | Qtd: ${qtd.toLocaleString('pt-BR')} | Unit: R$ ${valorUnit.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        },
        titleFormatter: (metric: string) => {
            switch (metric) {
                case 'receita': return 'Produtos com Maior Receita';
                case 'quantidade': return 'Produtos com Maior Volume';
                case 'ticket_medio': return 'Produtos com Maior Ticket Médio';
                case 'produtos': return 'Produtos com Maior Receita';
                default: return 'Produtos com Maior Receita';
            }
        },
    },

    // Overview — Map
    mapCardTitle: 'Distribuição Geográfica',
    mapCardMainText: 'Principais regiões de venda de produtos.',

    // Services
    services: {
        getDetail: getProdutoDetails,
        getByCustomer: getProductsByCustomer,
        getBySupplier: getProductsBySupplier,
    },

    // List Page
    listViewModes: ['all', 'by-customer', 'by-supplier'],
    defaultRankingKey: 'ranking_por_receita',
    hasProductFilter: false,

    tableColumns: {
        all: [
            { key: 'nome', label: 'Nome' },
            { key: 'receita_total', label: 'Receita Total', render: (item) => `R$ ${((item.receita_total as number) ?? 0).toLocaleString('pt-BR')}` },
            { key: 'valor_unitario_medio', label: 'Valor Unitário Médio', render: (item) => `R$ ${((item.valor_unitario_medio as number) ?? 0).toLocaleString('pt-BR')}` },
        ],
        'by-customer': [
            { key: 'nome', label: 'Produto' },
            { key: 'receita_total', label: 'Receita Total', isNumeric: true, render: (item) => (<Text fontWeight="bold" color="green.700">R$ {((item.receita_total as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>) as React.ReactNode },
            { key: 'quantidade_total', label: 'Quantidade', isNumeric: true, render: (item) => `${((item.quantidade_total as number) ?? 0).toLocaleString('pt-BR')} kg` },
            { key: 'num_pedidos', label: 'Pedidos', isNumeric: true },
            { key: 'valor_unitario_medio', label: 'Preço Médio', isNumeric: true, render: (item) => `R$ ${((item.valor_unitario_medio as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
        ],
        'by-supplier': [
            { key: 'nome', label: 'Produto' },
            { key: 'receita_total', label: 'Receita Total', isNumeric: true, render: (item) => (<Text fontWeight="bold" color="green.700">R$ {((item.receita_total as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</Text>) as React.ReactNode },
            { key: 'quantidade_total', label: 'Quantidade', isNumeric: true, render: (item) => `${((item.quantidade_total as number) ?? 0).toLocaleString('pt-BR')} kg` },
            { key: 'num_pedidos', label: 'Pedidos', isNumeric: true },
            { key: 'valor_unitario_medio', label: 'Preço Médio', isNumeric: true, render: (item) => `R$ ${((item.valor_unitario_medio as number) ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` },
        ],
    },

    listLabels: {
        pageTitle: 'Produtos por Receita',
        newButtonLabel: 'Cadastrar Novo Produto',
        filteredTitleBuilder: (viewMode: ViewMode, params: Record<string, string | null>) => {
            if (viewMode === 'by-customer' && params.customerName) {
                return `Produtos comprados por: ${decodeURIComponent(params.customerName).substring(0, 40)}${params.customerName.length > 40 ? '...' : ''}`;
            }
            if (viewMode === 'by-supplier' && params.supplierName) {
                return `Produtos vendidos por: ${decodeURIComponent(params.supplierName).substring(0, 40)}${params.supplierName.length > 40 ? '...' : ''}`;
            }
            return 'Produtos por Receita';
        },
    },

    // Detail Modal
    detailModal: {
        colors: { leftBg: '#FFFB97', rightBg: '#FFF856', scorecardBg: '#FFFB97' },
        showLoadingWhenNull: false,
        headerBuilder: (p) => ({
            subtitle: p.nome_produto || 'N/A',
            title: `Produto: ${p.nome_produto || 'N/A'}`,
        }),
        leftPanelFields: [
            { label: 'RECEITA TOTAL', valueExtractor: (p) => p.scorecards?.receita_total?.toLocaleString('pt-BR') ?? 'N/A' },
            { label: 'QTD. VENDIDA', valueExtractor: (p) => p.scorecards?.quantidade_total?.toLocaleString('pt-BR') ?? 'N/A' },
            { label: 'TICKET MÉDIO', valueExtractor: (p) => p.scorecards?.ticket_medio?.toLocaleString('pt-BR') ?? 'N/A' },
        ],
        rightPanelCards: [
            {
                titleExtractor: () => 'Top Cliente Comprador',
                valueExtractor: (p) => {
                    const top = p.rankings_internos?.clientes_por_receita?.[0];
                    return top ? `${top.nome.substring(0, 30)}${top.nome.length > 30 ? '...' : ''}` : 'N/A';
                },
                subtitleExtractor: (p) => {
                    const top = p.rankings_internos?.clientes_por_receita?.[0];
                    return top ? `R$ ${top.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })} - Clique para ver todos` : undefined;
                },
                bgColor: '#FFFB97',
                getNavigateTo: (p) => {
                    const top = p.rankings_internos?.clientes_por_receita?.[0];
                    if (!top) return undefined;
                    return `/dashboard/clientes/lista?view=by-product&product=${encodeURIComponent(p.nome_produto)}&productName=${encodeURIComponent(p.nome_produto)}`;
                },
            },
            {
                titleExtractor: () => 'Fornecedores',
                valueExtractor: () => 'Ver Fornecedores',
                subtitleExtractor: () => 'Clique para ver todos os fornecedores deste produto',
                bgColor: '#FFFB97',
                getNavigateTo: (p) => `/dashboard/fornecedores/lista?view=by-product&product=${encodeURIComponent(p.nome_produto)}&productName=${encodeURIComponent(p.nome_produto)}`,
            },
            {
                titleExtractor: () => 'Receita Total',
                valueExtractor: (p) => p.scorecards?.receita_total ? `R$ ${p.scorecards.receita_total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : 'N/A',
                subtitleExtractor: (p) => `Quantidade: ${p.scorecards?.quantidade_total?.toLocaleString('pt-BR') || 'N/A'}`,
                bgColor: '#FFFB97',
            },
            {
                titleExtractor: () => 'Preço Médio',
                valueExtractor: (p) => p.scorecards?.valor_unitario_medio ? `R$ ${p.scorecards.valor_unitario_medio.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : 'N/A',
                subtitleExtractor: () => 'Valor unitário médio',
                bgColor: '#FFFB97',
            },
        ],
        graphCarousel: {
            slidesBuilder: (_entity, overviewData) => {
                if (!overviewData) return [];
                return [
                    {
                        data: (overviewData.chart_receita_no_tempo || []).map((d: { name: string; total?: number; receita?: number }) => ({
                            name: d.name,
                            receita: d.total || (d as Record<string, unknown>).receita || 0,
                        })) as ChartDataPoint[],
                        dataKey: 'receita',
                        lineColor: '#FFF856',
                        title: 'Receita Mensal dos Produtos',
                    },
                    {
                        data: (overviewData.chart_quantidade_no_tempo || []).map((d: { name: string; total?: number; quantidade?: number }) => ({
                            name: d.name,
                            quantidade: d.total || (d as Record<string, unknown>).quantidade || 0,
                        })) as ChartDataPoint[],
                        dataKey: 'quantidade',
                        lineColor: '#FFD700',
                        title: 'Volume Mensal (kg/ton)',
                    },
                ];
            },
        },
    },
};
