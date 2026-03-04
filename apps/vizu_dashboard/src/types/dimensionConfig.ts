/**
 * Dimension Configuration Types
 *
 * These types define the configuration interface for generic entity pages
 * (OverviewPage, ListPage, DetailsModal). Each "dimension" (clientes,
 * fornecedores, produtos) provides its own config implementing these types.
 */
import React from 'react';
import type { ChartDataPoint, InsightBullet, KpiItem, MapData } from './index';
import type { MetricSlide } from '../components/PerformanceCard';

// =============================================================================
// Detail Modal Config
// =============================================================================

export interface ModalFieldConfig<TDetail> {
    label: string;
    valueExtractor: (entity: TDetail) => React.ReactNode;
}

export interface ModalScorecardConfig<TDetail> {
    titleExtractor: (entity: TDetail) => string;
    valueExtractor: (entity: TDetail) => string;
    subtitleExtractor: (entity: TDetail) => string | undefined;
    bgColor: string;
    /** Return a path to navigate to, or undefined to disable click */
    getNavigateTo?: (entity: TDetail) => string | undefined;
}

export interface ExpandableCardConfig<TDetail> {
    labelExtractor: (entity: TDetail) => string;
    valueExtractor: (entity: TDetail) => string;
    subtitleExtractor: (entity: TDetail) => string;
    bgColor: string;
    fetchChartData: (entity: TDetail) => Promise<ChartDataPoint[]>;
    graphDataKey: string;
    graphLineColor: string;
}

export interface ModalGraphCarouselConfig<TDetail, TOverview> {
    slidesBuilder: (entity: TDetail, overviewData?: TOverview | null) => {
        data: ChartDataPoint[];
        dataKey: string;
        lineColor?: string;
        title: string;
        description?: string;
    }[];
}

export interface DetailModalConfig<TDetail, TOverview> {
    colors: {
        leftBg: string;
        rightBg: string;
        scorecardBg: string;
    };
    headerBuilder: (entity: TDetail) => { subtitle: string; title: string };
    leftPanelFields: ModalFieldConfig<TDetail>[];
    rightPanelCards: ModalScorecardConfig<TDetail>[];
    expandableCard?: ExpandableCardConfig<TDetail>;
    graphCarousel?: ModalGraphCarouselConfig<TDetail, TOverview>;
    /** If true, shows a loading state instead of returning null when entity is null */
    showLoadingWhenNull?: boolean;
}

// =============================================================================
// Table Column Config
// =============================================================================

export interface TableColumnConfig {
    key: string;
    label: string;
    isNumeric?: boolean;
    render?: (item: Record<string, unknown>) => React.ReactNode;
}

// =============================================================================
// List Card Config
// =============================================================================

export interface ListCardConfig {
    /** Maps selectedMetric id to the ranking array key in overview data */
    rankingKeyMap: Record<string, string>;
    /** Formats the description for each ranking item */
    descriptionFormatter: (item: Record<string, unknown>, selectedMetric: string) => string;
    /** Formats the list card title based on selected metric */
    titleFormatter: (selectedMetric: string) => string;
}

// =============================================================================
// View Mode Types
// =============================================================================

export type ViewMode = 'all' | 'by-product' | 'by-customer' | 'by-supplier';

// =============================================================================
// Dimension Config — Main Interface
// =============================================================================

/* eslint-disable @typescript-eslint/no-explicit-any */
export interface DimensionConfig<TOverview = any, TDetail = any> {
    // ─── Identity ─────────────────────────────────────────────
    dimensionName: string;          // singular: "cliente", "fornecedor", "produto"
    dimensionNamePlural: string;    // "clientes", "fornecedores", "produtos"
    basePath: string;               // "/dashboard/clientes"
    listPath: string;               // "/dashboard/clientes/lista"

    // ─── Colors ───────────────────────────────────────────────
    colors: {
        pageBg: string;
        cardBg: string;
        modalLeftBg: string;
        modalRightBg: string;
        hoverBg: string;              // table row hover color
    };

    // ─── Data Hooks ───────────────────────────────────────────
    defaultPeriod: string;
    hooks: {
        useOverview: (opts?: { period?: string; enabled?: boolean }) => {
            data: TOverview | undefined;
            isLoading: boolean;
            error: Error | null;
            refetch: () => Promise<any>;
        };
        useListData: (period?: string) => {
            data: TOverview | null;
            loading: boolean;
            error: string | null;
            refetch: () => Promise<any>;
            /** Extra data from combined hooks (e.g. productsFilter for clientes) */
            extra?: Record<string, any>;
        };
    };

    // ─── Overview Page: Performance Card ──────────────────────
    /** Builder for the growth/subtitle message at top of page */
    growthMessageBuilder: (overviewData: TOverview, userName: string) => string;

    /** Label + value for the big stat shown below the header ("TOTAL DE CLIENTES" / "324") */
    totalStat: {
        label: string;
        valueExtractor: (overviewData: TOverview) => string | number;
    };

    /** Builds performance card slides from overview data */
    performanceSlidesBuilder: (overviewData: TOverview) => MetricSlide[];

    /** Title for the PerformanceCard */
    performanceCardTitle: string;

    /** KPI items shown in PerformanceCard modal */
    kpiItemsBuilder: (overviewData: TOverview) => KpiItem[];

    // ─── Overview Page: Insights Card ─────────────────────────
    insightsCardTitle: string;

    /** Builds the scorecard value/label shown at the bottom of the insights card */
    insightsScorecardBuilder: (overviewData: TOverview) => {
        value: string;
        label: string;
    };

    /** Builds insight bullets (max 4) */
    insightBulletsBuilder: (overviewData: TOverview) => InsightBullet[];

    /** Builds carousel graphs for the insights card modal. Optional — not all dimensions have them */
    carouselGraphsBuilder?: (overviewData: TOverview) => {
        data: ChartDataPoint[];
        dataKey: string;
        lineColor?: string;
        title: string;
        description?: string;
        chartType?: 'line' | 'bar';
        barColors?: string[];
        valueLabel?: string;
    }[] | undefined;

    // ─── Overview Page: List Card ─────────────────────────────
    listCard: ListCardConfig;

    // ─── Overview Page: Map Card ──────────────────────────────
    mapCardTitle: string;
    mapCardMainText: string;
    /** Builds map data; if undefined, uses default Brazil center */
    mapDataBuilder?: (geoClusters: any) => MapData;

    // ─── Services ─────────────────────────────────────────────
    services: {
        getDetail: (name: string) => Promise<TDetail>;
        getByProduct?: (productName: string) => Promise<any[]>;
        getByCustomer?: (cpfCnpj: string) => Promise<any[]>;
        getBySupplier?: (cnpj: string) => Promise<any[]>;
    };

    // ─── List Page ────────────────────────────────────────────
    listViewModes: ViewMode[];

    /** Table columns keyed by view mode */
    tableColumns: Partial<Record<ViewMode, TableColumnConfig[]>>;

    /** Optional product filter (only clientes has this toggle + select) */
    hasProductFilter?: boolean;

    /** Labels used in the list page */
    listLabels: {
        pageTitle: string;
        newButtonLabel: string;
        /** Builds a title for filtered views (e.g. "Clientes que compraram: Arroz") */
        filteredTitleBuilder?: (viewMode: ViewMode, params: Record<string, string | null>) => string;
    };

    /** The ranking array key in overview data used for the default "all" table */
    defaultRankingKey: string;

    // ─── Detail Modal ─────────────────────────────────────────
    detailModal: DetailModalConfig<TDetail, TOverview>;
}
/* eslint-enable @typescript-eslint/no-explicit-any */
