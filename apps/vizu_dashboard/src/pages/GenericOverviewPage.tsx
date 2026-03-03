/**
 * Generic Overview Page
 *
 * Config-driven replacement for ClientesPage, FornecedoresPage, ProdutosPage.
 * Renders: Header → Stat → 4-card layout (Performance, Insights, ListCard, Map).
 */
import {
    Box, Flex, Text, HStack, useDisclosure,
    Spinner, Alert, AlertIcon, IconButton,
} from '@chakra-ui/react';
import { RepeatIcon } from '@chakra-ui/icons';
import { MainLayout } from '../components/layouts/MainLayout';
import { DashboardCard } from '../components/DashboardCard';
import { PerformanceCard } from '../components/PerformanceCard';
import { ListCard } from '../components/ListCard';
import { GenericDetailsModal } from '../components/GenericDetailsModal';
import { useGeoClusters } from '../hooks/useGeoClusters';
import { useUserProfile } from '../hooks/useUserProfile';
import React, { useState, useMemo, useCallback } from 'react';
import type { DimensionConfig } from '../types/dimensionConfig';
import type { MapData } from '../types';

/* eslint-disable @typescript-eslint/no-explicit-any */

interface GenericOverviewPageProps {
    config: DimensionConfig<any, any>;
}

export default function GenericOverviewPage({ config }: GenericOverviewPageProps) {
    const { isOpen, onOpen, onClose } = useDisclosure();
    const [selectedItem, setSelectedItem] = useState<any>(null);
    const [localError, setLocalError] = useState<string | null>(null);
    const [selectedMetric, setSelectedMetric] = useState<string>(
        // Pick the first slide id as default
        'receita',
    );
    const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
    const profile = useUserProfile();
    const userName = profile?.full_name.split(' ')[0] || 'Usuário';

    // Data hooks from config
    const { data: overviewData, isLoading: loading, error: queryError, refetch } = config.hooks.useOverview({
        period: config.defaultPeriod,
    });
    const error = queryError?.message || localError;

    // Geo clusters for map
    const { data: geoClusters } = useGeoClusters('state');

    // Refresh
    const handleRefresh = useCallback(async () => {
        await refetch();
        setLastUpdate(new Date());
    }, [refetch]);

    const handleSlideChange = useCallback((_index: number, slideId: string) => {
        setSelectedMetric(slideId);
    }, []);

    // Detail modal click
    const handleMiniCardClick = async (clickedItem: { id: string }) => {
        try {
            if (!clickedItem?.id || clickedItem.id.trim() === '') {
                setLocalError(`Nome de ${config.dimensionName} inválido.`);
                return;
            }
            setSelectedItem(null);
            const details = await config.services.getDetail(clickedItem.id);
            setSelectedItem(details);
            onOpen();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : `Erro ao carregar detalhes.`;
            console.error(`Erro ao carregar detalhes do ${config.dimensionName}:`, err);
            setLocalError(msg);
        }
    };

    // ─── Memoized builders ─────────────────────────────────────
    const performanceSlides = useMemo(
        () => (overviewData ? config.performanceSlidesBuilder(overviewData) : []),
        [overviewData, config],
    );

    const kpiItems = useMemo(
        () => (overviewData ? config.kpiItemsBuilder(overviewData) : []),
        [overviewData, config],
    );

    const insightScorecard = useMemo(
        () => (overviewData ? config.insightsScorecardBuilder(overviewData) : { value: '0', label: '' }),
        [overviewData, config],
    );

    const insightBullets = useMemo(
        () => (overviewData ? config.insightBulletsBuilder(overviewData) : []),
        [overviewData, config],
    );

    const carouselGraphs = useMemo(
        () => (overviewData && config.carouselGraphsBuilder ? config.carouselGraphsBuilder(overviewData) : undefined),
        [overviewData, config],
    );

    const growthMessage = useMemo(
        () => (overviewData ? config.growthMessageBuilder(overviewData, userName) : ''),
        [overviewData, userName, config],
    );

    // ─── List card items (driven by selectedMetric) ────────────
    const listCardItems = useMemo(() => {
        if (!overviewData) return [];
        const rankingKey = config.listCard.rankingKeyMap[selectedMetric] || config.defaultRankingKey;
        const ranking = (overviewData as any)[rankingKey] || [];
        return ranking.map((item: any) => ({
            id: item.nome,
            title: item.nome,
            description: config.listCard.descriptionFormatter(item, selectedMetric),
            status: item.cluster_tier,
        }));
    }, [overviewData, selectedMetric, config]);

    const listCardTitle = useMemo(
        () => config.listCard.titleFormatter(selectedMetric),
        [selectedMetric, config],
    );

    // ─── Map data ──────────────────────────────────────────────
    const mapData = useMemo((): MapData => {
        if (config.mapDataBuilder && geoClusters) {
            return config.mapDataBuilder(geoClusters);
        }
        return {
            center: geoClusters?.center || [-14.235, -51.9253],
            zoom: 4.5,
            clusters: geoClusters?.clusters || [],
            maxCount: geoClusters?.max_count || 1,
        } as MapData;
    }, [geoClusters, config]);

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
                {/* ===== HEADER ===== */}
                <Flex justify="space-between" align="flex-start" mb="8px">
                    <Text as="h1" textStyle="pageSubtitle">
                        {growthMessage}
                    </Text>
                    <HStack spacing={2}>
                        <Text fontSize="sm" color="gray.600">
                            Atualizado: {lastUpdate.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                        </Text>
                        <IconButton
                            icon={<RepeatIcon />}
                            aria-label="Atualizar dados"
                            size="sm"
                            onClick={handleRefresh}
                            isLoading={loading}
                        />
                    </HStack>
                </Flex>

                {/* ===== STAT ===== */}
                <Box mb="36px">
                    <Text textStyle="homeCardStatLabel">{config.totalStat.label}</Text>
                    <Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
                        {config.totalStat.valueExtractor(overviewData)}
                    </Text>
                </Box>

                {/* ===== 4 CARDS ===== */}
                <Flex wrap="wrap" justify="center" gap="16px">
                    {/* CARD 1: Performance */}
                    <PerformanceCard
                        title={config.performanceCardTitle}
                        bgColor={config.colors.cardBg}
                        slides={performanceSlides}
                        onSlideChange={handleSlideChange}
                        modalLeftBgColor={config.colors.modalLeftBg}
                        modalRightBgColor={config.colors.modalRightBg}
                        mainText={`Análise de performance dos seus ${config.dimensionNamePlural} ao longo do tempo.`}
                        kpiItems={kpiItems}
                    />

                    {/* CARD 2: Insights */}
                    <DashboardCard
                        title={config.insightsCardTitle}
                        size="small"
                        bgGradient="linear-gradient(to-br, #353A5A, #1F2138)"
                        textColor="white"
                        scorecardValue={insightScorecard.value}
                        scorecardLabel={insightScorecard.label}
                        insightBullets={insightBullets}
                        modalLeftBgColor="#353A5A"
                        modalRightBgColor="#1F2138"
                        kpiItems={kpiItems}
                        carouselGraphs={carouselGraphs}
                    />

                    {/* CARD 3: Rankings */}
                    <ListCard
                        title={listCardTitle}
                        items={listCardItems}
                        onMiniCardClick={handleMiniCardClick}
                        viewAllLink={config.listPath}
                        cardBgColor={config.colors.cardBg}
                    />

                    {/* CARD 4: Map */}
                    <DashboardCard
                        title={config.mapCardTitle}
                        size="large"
                        bgColor="white"
                        mapData={mapData}
                        mainText={config.mapCardMainText}
                        modalLeftBgColor={config.colors.modalLeftBg}
                        modalRightBgColor={config.colors.modalRightBg}
                    />
                </Flex>
            </Flex>

            {/* Detail Modal */}
            <GenericDetailsModal
                isOpen={isOpen}
                onClose={onClose}
                entity={selectedItem}
                overviewData={overviewData}
                config={config.detailModal}
            />
        </MainLayout>
    );
}
