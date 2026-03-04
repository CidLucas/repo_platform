/**
 * Generic Details Modal
 *
 * Renders a full-screen modal for any entity dimension using
 * DetailModalConfig from DimensionConfig.
 */
import {
    Modal, ModalOverlay, ModalContent, ModalBody,
    ModalCloseButton, Flex, Text, Box,
} from '@chakra-ui/react';
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ModalContentLayout } from './ModalContentLayout';
import { ScorecardCard } from './ScorecardCard';
import { ExpandableScorecardCard } from './ExpandableScorecardCard';
import { GraphCarousel } from './GraphCarousel';
import type { DetailModalConfig } from '../types/dimensionConfig';
import type { ChartDataPoint } from '../types';

/* eslint-disable @typescript-eslint/no-explicit-any */

interface GenericDetailsModalProps<TDetail = any, TOverview = any> {
    isOpen: boolean;
    onClose: () => void;
    entity: TDetail | null;
    overviewData?: TOverview | null;
    config: DetailModalConfig<TDetail, TOverview>;
}

export function GenericDetailsModal<TDetail, TOverview>({
    isOpen, onClose, entity, overviewData, config,
}: GenericDetailsModalProps<TDetail, TOverview>) {
    const navigate = useNavigate();

    // State for expandable card chart data
    const [expandableChartData, setExpandableChartData] = useState<ChartDataPoint[]>([]);
    const [expandableLoading, setExpandableLoading] = useState(false);

    // Fetch expandable card data when entity changes
    useEffect(() => {
        if (!config.expandableCard || !entity || !isOpen) return;
        let cancelled = false;
        const fetch = async () => {
            setExpandableLoading(true);
            try {
                const data = await config.expandableCard!.fetchChartData(entity);
                if (!cancelled) setExpandableChartData(data);
            } catch {
                if (!cancelled) setExpandableChartData([]);
            } finally {
                if (!cancelled) setExpandableLoading(false);
            }
        };
        fetch();
        return () => { cancelled = true; };
    }, [entity, isOpen, config.expandableCard]);

    // Loading / null state
    if (!entity) {
        if (config.showLoadingWhenNull) {
            return (
                <Modal isOpen={isOpen} onClose={onClose} size="full">
                    <ModalOverlay />
                    <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
                        <ModalBody p={0}>
                            <Flex justify="center" align="center" height="100%" bg="white">
                                <Text>Carregando dados...</Text>
                                <ModalCloseButton />
                            </Flex>
                        </ModalBody>
                    </ModalContent>
                </Modal>
            );
        }
        return null;
    }

    const header = config.headerBuilder(entity);

    // --- Left Panel ---
    const leftContent = (
        <Flex direction="column" height="100%">
            <Text textStyle="modalFinancialInfo" textTransform="uppercase" mb={0}>
                {header.subtitle}
            </Text>
            <Flex justify="space-between" align="center" mb={4}>
                <Text textStyle="modalTitle" fontSize="24px" fontWeight="semibold">
                    {header.title}
                </Text>
            </Flex>
            <Flex flex="1" alignItems="center" justifyContent="center">
                <Flex direction="column" width="100%">
                    {config.leftPanelFields.map((field, idx) => (
                        <React.Fragment key={idx}>
                            <Flex justify="space-between" align="center" py={3}>
                                <Text textStyle="modalFinancialInfo" fontWeight="semibold">{field.label}</Text>
                                <Text textStyle="modalFinancialInfo">{field.valueExtractor(entity)}</Text>
                            </Flex>
                            <Box borderBottom="1px solid black" width="100%" />
                        </React.Fragment>
                    ))}
                </Flex>
            </Flex>
        </Flex>
    );

    // --- Right Panel ---
    const rightContent = (
        <Flex direction="column" height="100%" p={8}>
            <Flex justify="space-between" align="center" mb={6}>
                <Text textStyle="modalTitle" textTransform="uppercase" fontWeight="semibold">
                    INSIGHTS
                </Text>
                <ModalCloseButton position="static" onClick={onClose} />
            </Flex>

            <Flex direction="column" gap={4} mb={6}>
                {config.rightPanelCards.map((card, idx) => {
                    const navigateTo = card.getNavigateTo?.(entity);
                    const handleClick = navigateTo
                        ? () => { onClose(); navigate(navigateTo); }
                        : undefined;
                    return (
                        <ScorecardCard
                            key={idx}
                            title={card.titleExtractor(entity)}
                            value={card.valueExtractor(entity)}
                            subtitle={card.subtitleExtractor(entity)}
                            bgColor={card.bgColor}
                            onClick={handleClick}
                        />
                    );
                })}

                {config.expandableCard && (
                    <ExpandableScorecardCard
                        title={config.expandableCard.labelExtractor(entity)}
                        value={config.expandableCard.valueExtractor(entity)}
                        subtitle={config.expandableCard.subtitleExtractor(entity)}
                        bgColor={config.expandableCard.bgColor}
                        graphData={expandableChartData}
                        graphDataKey={config.expandableCard.graphDataKey}
                        graphLineColor={config.expandableCard.graphLineColor}
                        isLoading={expandableLoading}
                    />
                )}
            </Flex>

            {/* Graph Carousel (optional) */}
            {config.graphCarousel && (() => {
                const slides = config.graphCarousel!.slidesBuilder(entity, overviewData);
                if (!slides || slides.length === 0) return null;
                return (
                    <Box flex="1">
                        <Text textStyle="modalTitle" mb={4}>Análise de Performance no Tempo</Text>
                        <GraphCarousel graphs={slides} />
                    </Box>
                );
            })()}
        </Flex>
    );

    return (
        <Modal isOpen={isOpen} onClose={onClose} size="full">
            <ModalOverlay />
            <ModalContent bg="transparent" boxShadow="none" overflow="hidden" height="100vh">
                <ModalBody p={0}>
                    <ModalContentLayout
                        leftBgColor={config.colors.leftBg}
                        rightBgColor={config.colors.rightBg}
                        isMapModal={false}
                        mapData={undefined}
                        leftContent={leftContent}
                        rightContent={rightContent}
                    />
                </ModalBody>
            </ModalContent>
        </Modal>
    );
}
