import { Box, Flex, Text, Alert, AlertIcon, Spinner, useDisclosure, Icon, SimpleGrid, VStack, HStack, Badge, Link as ChakraLink } from '@chakra-ui/react';
import { DomainExpansionModal } from '../components/DomainExpansionModal';
import { MainLayout } from '../components/layouts/MainLayout';
import { OnboardingBanner } from '../components/OnboardingBanner';
import { MappingReviewBanner } from '../components/MappingReviewBanner';
import { InsightsCard } from '../components/InsightsCard';
import { useMemo, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useHomeMetrics } from '../hooks/useHomeMetrics';
import { useAgentRunsToday } from '../hooks/useAgentRunsToday';
import { useRecentActivity } from '../hooks/useRecentActivity';
import { useAgenda } from '../hooks/useAgenda';
import { usePendencias } from '../hooks/usePendencias';
import { useNps } from '../hooks/useNps';
import { getClientes, getFornecedores, getProdutosOverview } from '../services/analyticsService';
import { FiDollarSign, FiCheckCircle, FiPackage, FiUsers, FiFileText, FiTrendingUp, FiZap, FiCalendar, FiClock, FiActivity, FiChevronRight, FiMail, FiPhone, FiTarget, FiSend, FiPlusCircle, FiBarChart2 } from 'react-icons/fi';

function HomePage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { isOpen: isModalOpen, onOpen: onModalOpen, onClose: onModalClose } = useDisclosure();
  const [selectedDomain, setSelectedDomain] = useState<'orders' | 'customers' | 'suppliers' | 'products'>('orders');

  const handleDomainClick = (domain: 'orders' | 'customers' | 'suppliers' | 'products') => {
    setSelectedDomain(domain);
    onModalOpen();
  };

  // Prefetch list page data when HomePage loads (improves navigation speed)
  useEffect(() => {
    // Prefetch in background - won't show loading, just warms the cache
    queryClient.prefetchQuery({
      queryKey: ['clientes', 'all'],
      queryFn: () => getClientes('all'),
      staleTime: 5 * 60 * 1000,
    });
    queryClient.prefetchQuery({
      queryKey: ['fornecedores', 'all'],
      queryFn: () => getFornecedores('all'),
      staleTime: 5 * 60 * 1000,
    });
    queryClient.prefetchQuery({
      queryKey: ['produtos', 'all'],
      queryFn: () => getProdutosOverview('all'),
      staleTime: 5 * 60 * 1000,
    });
  }, [queryClient]);

  // Single consolidated hook — v_resumo_dashboard now provides all HomePage data
  const { data: metricsData, loading: metricsLoading, error: metricsError } = useHomeMetrics();

  // Live data hooks (Phase 4: dashboard mocks → live data)
  const { data: agentRunsData } = useAgentRunsToday();
  const { data: recentActivityData } = useRecentActivity(4);
  const { data: agendaData } = useAgenda(7);
  const { data: pendenciasData } = usePendencias();
  const { data: npsData } = useNps(90);

  // Relative-time formatter (PT-BR) — used by Recent Activity & Pendências.
  const relativeTimeFormatter = useMemo(
    () => new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' }),
    []
  );

  const formatRelativeTime = (iso: string | null): string => {
    if (!iso) return '';
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return '';
    const diffSec = Math.round((then - Date.now()) / 1000);
    const abs = Math.abs(diffSec);
    if (abs < 60) return relativeTimeFormatter.format(diffSec, 'second');
    if (abs < 3600) return relativeTimeFormatter.format(Math.round(diffSec / 60), 'minute');
    if (abs < 86400) return relativeTimeFormatter.format(Math.round(diffSec / 3600), 'hour');
    if (abs < 604800) return relativeTimeFormatter.format(Math.round(diffSec / 86400), 'day');
    return relativeTimeFormatter.format(Math.round(diffSec / 604800), 'week');
  };

  // Derive revenue data — current calendar month from v_resumo_dashboard.
  const revenueData = useMemo(() => {
    const currentMonth = new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date());
    if (!metricsData) {
      return { value: 0, month: currentMonth };
    }
    const monthlyRevenue = metricsData.scorecards.receita_mes_atual || metricsData.scorecards.receita_total;
    return { value: monthlyRevenue, month: currentMonth };
  }, [metricsData]);

  const loading = metricsLoading;
  const error = metricsError;

  // Early return for loading state
  if (loading) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Spinner size="xl" color="white" />
        </Flex>
      </MainLayout>
    );
  }

  // Early return for error state
  if (error) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error" bg="#1a1b2e" color="white" borderRadius="10px" border="1px solid" borderColor="red.600">
            <AlertIcon color="red.400" />
            {error}
          </Alert>
        </Flex>
      </MainLayout>
    );
  }

  // Extract Fornecedores data from metricsData (correct source)
  const fornecedoresTotal = metricsData?.scorecards.total_fornecedores || 0;

  // Extract Produtos data — from consolidated v_resumo_dashboard
  const productsTotal = metricsData?.scorecards.total_produtos || 0;

  // Extract Clientes data — from consolidated v_resumo_dashboard
  const customersTotal = metricsData?.scorecards.clientes_ativos || metricsData?.scorecards.total_clientes || 0;

  // Revenue growth — calendar-month value vs prior month.
  const revenueGrowth = metricsData?.scorecards.crescimento_receita;

  // Pedidos this calendar month — from v_resumo_dashboard.pedidos_mes_atual.
  const pedidosMesAtual = metricsData?.scorecards.pedidos_mes_atual || 0;

  const revenueLabel = 'Revenue this month';
  const growthLabel = 'vs last month';
  const pedidosCardLabel = 'pedidos este mês';

  // Format revenue as compact number (ex: R$ 91,7 mi)
  const formatCompactCurrency = (value: number): string => {
    if (value >= 1_000_000_000) {
      return `R$ ${(value / 1_000_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} bi`;
    } else if (value >= 1_000_000) {
      return `R$ ${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`;
    } else if (value >= 1_000) {
      return `R$ ${(value / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`;
    }
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  };

  const formattedRevenue = formatCompactCurrency(revenueData.value);

  // Domain cards config (matching Figma design)
  const domainCards: Array<{
    domain: 'orders' | 'customers' | 'suppliers' | 'products';
    label: string;
    sublabel: string;
    icon: React.ElementType;
    color: string;
    stat: number;
  }> = [
    { domain: 'orders', label: 'Pedidos', sublabel: 'Pedidos processados este mês', icon: FiPackage, color: '#3b82f6', stat: pedidosMesAtual },
    { domain: 'customers', label: 'Clientes', sublabel: 'Base total de clientes', icon: FiUsers, color: '#a855f7', stat: customersTotal },
    { domain: 'suppliers', label: 'Fornecedores', sublabel: 'Parceiros ativos fornecendo produtos', icon: FiFileText, color: '#ec4899', stat: fornecedoresTotal },
    { domain: 'products', label: 'Produtos', sublabel: 'Catálogo de produtos', icon: FiPackage, color: '#10b981', stat: productsTotal },
  ];

  return (
    <MainLayout>
      <OnboardingBanner />
      <MappingReviewBanner />
      <Box p={6} maxW="1800px" mx="auto">
        {/* Welcome Header — Playfair Display title with gradient accent */}
        <Box mb={8}>
          <Flex justify="space-between" align={{ base: 'flex-start', md: 'flex-end' }} direction={{ base: 'column', md: 'row' }} gap={4}>
            <Box>
              <Text
                as="h1"
                fontSize="2.5rem"
                fontWeight="normal"
                fontFamily="'Playfair Display', serif"
                mb={2}
              >
                <Box as="span" color="white">Dashboard </Box>
                <Box
                  as="span"
                  bgGradient="linear(to-r, #ff6b35, #ff006e)"
                  bgClip="text"
                >
                  Analytics
                </Box>
              </Text>
              <Text color="whiteAlpha.600" fontSize="lg" fontWeight="medium">
                Visão completa do seu negócio em tempo real
              </Text>
            </Box>
          </Flex>
        </Box>

        {/* Main Layout Grid — 3 + 1 columns like Figma */}
        <SimpleGrid columns={{ base: 1, lg: 4 }} spacing={4}>
          {/* Left Section — Main Content (3 columns) */}
          <Box gridColumn={{ lg: 'span 3' }}>
            {/* Top Info Cards — Revenue (2 cols) + Active Tasks (1 col) */}
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={4}>
              {/* Revenue Card — Larger, spans 2 columns */}
              <Box
                gridColumn={{ md: 'span 2' }}
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={6}
                position="relative"
                overflow="hidden"
              >
                {/* Left accent bar */}
                <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#10b981" />
                <Flex justify="space-between" align="start" mb={4}>
                  <Box>
                    <Text
                      color="whiteAlpha.500"
                      fontSize="xs"
                      fontWeight="semibold"
                      textTransform="uppercase"
                      letterSpacing="wider"
                      mb={1}
                    >
                      {revenueLabel}
                    </Text>
                    <Text fontSize="2.5rem" fontWeight="bold" color="white">
                      {formattedRevenue}
                    </Text>
                  </Box>
                  <Flex
                    w={12} h={12}
                    borderRadius="1rem"
                    align="center" justify="center"
                    bgGradient="linear(to-br, #10b981, #10b981dd)"
                    boxShadow="0 4px 12px rgba(16,185,129,0.6)"
                  >
                    <Icon as={FiDollarSign} boxSize={6} color="white" />
                  </Flex>
                </Flex>
                <Flex align="center" gap={2}>
                  <Flex
                    align="center"
                    gap={1}
                    color={
                      revenueGrowth !== undefined && revenueGrowth !== null && revenueGrowth < 0
                        ? 'red.400'
                        : 'green.400'
                    }
                  >
                    <Icon as={FiTrendingUp} boxSize={4} />
                    <Text fontSize="sm" fontWeight="medium">
                      {revenueGrowth !== undefined && revenueGrowth !== null
                        ? `${revenueGrowth > 0 ? '+' : ''}${revenueGrowth.toFixed(1)}%`
                        : '+0%'}
                    </Text>
                  </Flex>
                  <Text fontSize="sm" color="whiteAlpha.500">{growthLabel}</Text>
                </Flex>
              </Box>

              {/* Active Tasks Card */}
              <Box
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={6}
                position="relative"
                overflow="hidden"
              >
                <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#3b82f6" />
                <Flex align="center" gap={3} mb={3}>
                  <Flex
                    w={10} h={10}
                    borderRadius="1rem"
                    align="center" justify="center"
                    bgGradient="linear(to-br, #3b82f6, #3b82f6dd)"
                    boxShadow="0 4px 12px rgba(59,130,246,0.6)"
                  >
                    <Icon as={FiCheckCircle} boxSize={5} color="white" />
                  </Flex>
                  <Box>
                    <Text fontSize="xs" color="whiteAlpha.500" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider">
                      Active
                    </Text>
                    <Text fontSize="2xl" fontWeight="bold" color="white">
                      {pedidosMesAtual.toLocaleString('pt-BR')}
                    </Text>
                  </Box>
                </Flex>
                <Text fontSize="xs" color="whiteAlpha.600">{pedidosCardLabel}</Text>
              </Box>
            </SimpleGrid>

            {/* Business Insights — Domain Cards with Figma aesthetic */}
            <Box mb={6}>
              <Text
                fontSize="1.5rem"
                fontWeight="normal"
                fontFamily="'Playfair Display', serif"
                mb={6}
                color="white"
              >
                Áreas de Negócio
              </Text>
              <SimpleGrid columns={{ base: 2, md: 4 }} spacing={6}>
                {domainCards.map((card) => (
                  <Box
                    key={card.domain}
                    bg="#1a1b2e"
                    borderRadius="0.625rem"
                    border="1px solid"
                    borderColor="rgba(255,255,255,0.08)"
                    boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                    p={8}
                    position="relative"
                    overflow="hidden"
                    cursor="pointer"
                    transition="all 0.2s"
                    _hover={{
                      borderColor: 'rgba(255,255,255,0.12)',
                      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                      transform: 'translateY(-4px)',
                    }}
                    onClick={() => handleDomainClick(card.domain)}
                  >
                    {/* Left accent bar */}
                    <Box position="absolute" top={0} left={0} w="3px" h="100%" bg={card.color} />
                    <Flex align="start" gap={4} mb={5}>
                      {/* Icon container with colored glow */}
                      <Flex
                        w={16} h={16}
                        borderRadius="1rem"
                        align="center" justify="center"
                        bgGradient={`linear(to-br, ${card.color}, ${card.color}dd)`}
                        boxShadow={`0 8px 24px ${card.color}60, 0 0 0 1px ${card.color}20`}
                        flexShrink={0}
                        position="relative"
                        overflow="hidden"
                      >
                        <Box position="absolute" inset={0} bgGradient="linear(to-br, whiteAlpha.200, transparent)" />
                        <Icon as={card.icon} boxSize={7} color="white" position="relative" zIndex={1} />
                      </Flex>
                      <Box flex={1}>
                        <Text
                          fontSize="xs"
                          color="whiteAlpha.500"
                          fontWeight="semibold"
                          textTransform="uppercase"
                          letterSpacing="wider"
                          mb={1}
                        >
                          {card.label}
                        </Text>
                        <Text fontSize="2.5rem" fontWeight="bold" color="white" lineHeight="1">
                          {card.stat.toLocaleString('pt-BR')}
                        </Text>
                      </Box>
                    </Flex>
                    <Text fontSize="sm" color="whiteAlpha.600" lineHeight="relaxed">
                      {card.sublabel}
                    </Text>
                  </Box>
                ))}
              </SimpleGrid>
            </Box>

            {/* Bottom row — AI Tasks + Quick Insight */}
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
              <Box
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={5}
                position="relative"
                overflow="hidden"
                cursor="pointer"
                _hover={{ boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}
                transition="box-shadow 0.2s"
              >
                <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#fbbf24" />
                <Flex justify="space-between" align="center">
                  <Box>
                    <Text fontSize="xs" color="whiteAlpha.500" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" mb={1}>
                      AI Tasks Today
                    </Text>
                    <Text fontSize="2xl" fontWeight="bold" color="white">
                      {(agentRunsData?.total ?? 0).toLocaleString('pt-BR')}
                    </Text>
                  </Box>
                  <Flex
                    w={10} h={10}
                    borderRadius="1rem"
                    align="center" justify="center"
                    bgGradient="linear(to-br, #fbbf24, #fbbf24dd)"
                    boxShadow="0 4px 12px rgba(251,191,36,0.6)"
                  >
                    <Icon as={FiZap} boxSize={5} color="white" />
                  </Flex>
                </Flex>
              </Box>

              <Box
                gridColumn={{ md: 'span 2' }}
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={5}
                position="relative"
                overflow="hidden"
              >
                <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#10b981" />
                <Flex justify="space-between" align="start">
                  <Box flex={1}>
                    <Text fontSize="xs" color="whiteAlpha.500" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" mb={2}>
                      Quick Insight
                    </Text>
                    <Text fontSize="sm" color="whiteAlpha.800">
                      {(() => {
                        const sc = metricsData?.scorecards;
                        if (sc?.crescimento_receita !== undefined && sc.crescimento_receita !== null && sc.crescimento_receita > 0) {
                          return `Receita cresceu ${sc.crescimento_receita.toFixed(1)}% vs. mês anterior.`;
                        }
                        if (sc?.crescimento_clientes !== undefined && sc.crescimento_clientes !== null && sc.crescimento_clientes > 0) {
                          return `Sua base de clientes cresceu ${sc.crescimento_clientes.toFixed(1)}% vs. mês anterior.`;
                        }
                        if (sc?.crescimento_produtos !== undefined && sc.crescimento_produtos !== null && sc.crescimento_produtos > 0) {
                          return `Catálogo de produtos cresceu ${sc.crescimento_produtos.toFixed(1)}% vs. mês anterior.`;
                        }
                        return 'Acompanhe os indicadores principais para identificar oportunidades.';
                      })()}
                    </Text>
                  </Box>
                  <Flex
                    w={8} h={8}
                    borderRadius="0.75rem"
                    align="center" justify="center"
                    bgGradient="linear(to-br, #10b981, #10b981dd)"
                    boxShadow="0 4px 12px rgba(16,185,129,0.6)"
                    flexShrink={0}
                    ml={4}
                  >
                    <Icon as={FiTrendingUp} boxSize={4} color="white" />
                  </Flex>
                </Flex>
              </Box>
            </SimpleGrid>

            {/* Horizontal Row — Quick Actions, Pendências, KPIs */}
            <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} mb={6}>
              {/* Quick Actions Card */}
              <Box
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={5}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <HStack spacing={2}>
                    <Icon as={FiZap} boxSize={4} color="#fbbf24" />
                    <Text fontSize="sm" fontWeight="semibold" color="white">Ações Rápidas</Text>
                  </HStack>
                </Flex>
                <SimpleGrid columns={2} spacing={2}>
                  {[
                    { icon: FiPlusCircle, label: 'Novo Pedido', color: '#3b82f6', route: '/dashboard/orders/new' },
                    { icon: FiSend, label: 'Enviar Relatório', color: '#10b981', route: '/dashboard/orders' },
                    { icon: FiMail, label: 'Email Cliente', color: '#a855f7', route: '/dashboard/suppliers' },
                    { icon: FiTarget, label: 'Definir Meta', color: '#f97316', route: '/dashboard/goals/new' },
                  ].map((action) => (
                    <Flex
                      key={action.label}
                      direction="column"
                      align="center"
                      gap={2}
                      py={3}
                      borderRadius="lg"
                      cursor="pointer"
                      transition="all 0.2s"
                      _hover={{ bg: 'whiteAlpha.100' }}
                      onClick={() => navigate(action.route)}
                    >
                      <Flex w={9} h={9} borderRadius="lg" align="center" justify="center" bg={`${action.color}20`}>
                        <Icon as={action.icon} boxSize={4} color={action.color} />
                      </Flex>
                      <Text fontSize="2xs" color="whiteAlpha.700" textAlign="center">{action.label}</Text>
                    </Flex>
                  ))}
                </SimpleGrid>
              </Box>

              {/* Recent Activity Card (moved from right column) */}
              <Box
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={5}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <HStack spacing={2}>
                    <Icon as={FiActivity} boxSize={4} color="#10b981" />
                    <Text fontSize="sm" fontWeight="semibold" color="white">Atividade Recente</Text>
                  </HStack>
                </Flex>
                <VStack spacing={3} align="stretch">
                  {(() => {
                    const items = recentActivityData ?? [];
                    if (items.length === 0) {
                      return (
                        <Text fontSize="xs" color="whiteAlpha.500">
                          Nenhuma atividade recente.
                        </Text>
                      );
                    }
                    const colorByKind: Record<string, string> = {
                      ingestion: '#3b82f6',
                      agent_session: '#10b981',
                      rfq: '#f97316',
                      upload: '#a855f7',
                    };
                    return items.map((activity, idx) => {
                      const color = colorByKind[activity.kind] ?? '#94a3b8';
                      return (
                        <Flex
                          key={`${activity.kind}-${activity.occurredAt}-${idx}`}
                          align="start"
                          gap={3}
                          py={2}
                          borderBottom={idx < items.length - 1 ? '1px solid' : 'none'}
                          borderColor="whiteAlpha.100"
                        >
                          <Box w={1.5} h={1.5} borderRadius="full" bg={color} mt={1.5} flexShrink={0} />
                          <Box flex={1} minW={0}>
                            <Text fontSize="xs" fontWeight="medium" color="white" noOfLines={1}>{activity.title}</Text>
                            <Flex gap={2}>
                              {activity.subtitle && (
                                <Text fontSize="2xs" color={color} noOfLines={1}>{activity.subtitle}</Text>
                              )}
                              <Text fontSize="2xs" color="whiteAlpha.400">{formatRelativeTime(activity.occurredAt)}</Text>
                            </Flex>
                          </Box>
                        </Flex>
                      );
                    });
                  })()}
                </VStack>
              </Box>

              {/* KPIs Card */}
              <Box
                bg="#1a1b2e"
                borderRadius="0.625rem"
                border="1px solid"
                borderColor="rgba(255,255,255,0.08)"
                boxShadow="0 4px 24px rgba(0,0,0,0.4)"
                p={5}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <HStack spacing={2}>
                    <Icon as={FiBarChart2} boxSize={4} color="#a855f7" />
                    <Text fontSize="sm" fontWeight="semibold" color="white">KPIs</Text>
                  </HStack>
                </Flex>
                <VStack spacing={3} align="stretch">
                  {[
                    {
                      label: 'Ticket Médio',
                      value: formatCompactCurrency(metricsData?.scorecards.ticket_medio || 0),
                      sub: undefined as string | undefined,
                      color: '#10b981',
                    },
                    {
                      label: 'NPS Score',
                      value: npsData ? `${Math.round(npsData.score)}` : '—',
                      sub: npsData ? `${npsData.totalResponses} respostas` : undefined,
                      color: '#f97316',
                    },
                  ].map((kpi) => (
                    <Flex key={kpi.label} justify="space-between" align="center" py={2} borderBottom="1px solid" borderColor="whiteAlpha.100">
                      <Box>
                        <Text fontSize="xs" color="whiteAlpha.600">{kpi.label}</Text>
                        {kpi.sub && (
                          <Text fontSize="2xs" color="whiteAlpha.400">{kpi.sub}</Text>
                        )}
                      </Box>
                      <Text fontSize="sm" fontWeight="bold" color={kpi.color}>{kpi.value}</Text>
                    </Flex>
                  ))}
                </VStack>
              </Box>
            </SimpleGrid>
          </Box>

          {/* Right Section — Insights + Agenda + Pendências (1 column, scrolls together) */}
          <Box>
            {/* Phase 2 (I2.2): nightly insights feed */}
            <Box mb={4}>
              <InsightsCard limit={5} />
            </Box>
            <Box
              bg="#1a1b2e"
              borderRadius="0.625rem"
              border="1px solid"
              borderColor="rgba(255,255,255,0.08)"
              boxShadow="0 4px 24px rgba(0,0,0,0.4)"
              p={5}
            >
              <Flex justify="space-between" align="center" mb={4}>
                <HStack spacing={2}>
                  <Icon as={FiCalendar} boxSize={4} color="#3b82f6" />
                  <Text fontSize="sm" fontWeight="semibold" color="white">Agenda</Text>
                </HStack>
                <Icon as={FiChevronRight} boxSize={4} color="whiteAlpha.400" cursor="pointer" _hover={{ color: 'white' }} />
              </Flex>
              <VStack spacing={3} align="stretch">
                {(() => {
                  if (agendaData?.disabled) {
                    return (
                      <Box py={2}>
                        <Text fontSize="xs" color="whiteAlpha.600" mb={2}>
                          Conecte sua agenda para ver eventos.
                        </Text>
                        <ChakraLink
                          fontSize="xs"
                          color="#3b82f6"
                          fontWeight="semibold"
                          onClick={() => navigate('/dashboard/admin/fontes')}
                          _hover={{ textDecoration: 'underline', cursor: 'pointer' }}
                        >
                          Conectar Google Calendar →
                        </ChakraLink>
                      </Box>
                    );
                  }
                  const events = agendaData?.events ?? [];
                  if (events.length === 0) {
                    return (
                      <Text fontSize="xs" color="whiteAlpha.500">
                        Sem eventos nos próximos dias.
                      </Text>
                    );
                  }
                  const colorByType: Record<string, string> = {
                    meeting: '#3b82f6',
                    call: '#10b981',
                    deadline: '#ec4899',
                  };
                  return events.map((event, idx) => {
                    const color = colorByType[event.type] ?? '#a855f7';
                    const iconForType = event.type === 'call' ? FiPhone : event.type === 'deadline' ? FiClock : FiCalendar;
                    let timeLabel = '';
                    try {
                      timeLabel = new Intl.DateTimeFormat('pt-BR', {
                        hour: '2-digit',
                        minute: '2-digit',
                      }).format(new Date(event.startsAt));
                    } catch {
                      timeLabel = '';
                    }
                    return (
                      <Flex
                        key={event.id}
                        align="center"
                        gap={3}
                        py={2}
                        borderBottom={idx < events.length - 1 ? '1px solid' : 'none'}
                        borderColor="rgba(255,255,255,0.06)"
                      >
                        <Flex
                          w={8} h={8}
                          borderRadius="lg"
                          align="center" justify="center"
                          bg={`${color}20`}
                          flexShrink={0}
                        >
                          <Icon as={iconForType} boxSize={3.5} color={color} />
                        </Flex>
                        <Box flex={1} minW={0}>
                          <Text fontSize="xs" fontWeight="medium" color="white" noOfLines={1}>{event.title}</Text>
                          <Text fontSize="2xs" color="whiteAlpha.500">{timeLabel}</Text>
                        </Box>
                      </Flex>
                    );
                  });
                })()}
              </VStack>
            </Box>

            {/* Pendências Card (moved from horizontal row) */}
            <Box
              bg="#1a1b2e"
              borderRadius="0.625rem"
              border="1px solid"
              borderColor="rgba(255,255,255,0.08)"
              boxShadow="0 4px 24px rgba(0,0,0,0.4)"
              p={5}
              mt={4}
            >
              <Flex justify="space-between" align="center" mb={4}>
                <HStack spacing={2}>
                  <Icon as={FiClock} boxSize={4} color="#f97316" />
                  <Text fontSize="sm" fontWeight="semibold" color="white">Pendências</Text>
                </HStack>
                <Badge bg="#f9731620" color="#f97316" fontSize="2xs" borderRadius="full" px={2}>
                  {pendenciasData?.length ?? 0}
                </Badge>
              </Flex>
              <VStack spacing={3} align="stretch">
                {(() => {
                  const items = pendenciasData ?? [];
                  if (items.length === 0) {
                    return (
                      <Text fontSize="xs" color="whiteAlpha.500">
                        Nenhuma pendência no momento.
                      </Text>
                    );
                  }
                  return items.map((item, idx) => {
                    const isHigh = item.severity === 'error';
                    const isMed = item.severity === 'warning';
                    const badgeBg = isHigh ? '#ef444420' : isMed ? '#f9731620' : '#3b82f620';
                    const badgeColor = isHigh ? '#ef4444' : isMed ? '#f97316' : '#3b82f6';
                    const badgeLabel = isHigh ? 'Alta' : isMed ? 'Média' : 'Baixa';
                    return (
                      <Flex
                        key={`${item.kind}-${idx}`}
                        align="center"
                        gap={3}
                        py={2}
                        borderBottom={idx < items.length - 1 ? '1px solid' : 'none'}
                        borderColor="whiteAlpha.100"
                        cursor="pointer"
                        onClick={() => item.targetRoute && navigate(item.targetRoute)}
                        _hover={{ bg: 'whiteAlpha.50' }}
                        borderRadius="sm"
                      >
                        <Box flex={1} minW={0}>
                          <Flex align="center" gap={2} mb={0.5}>
                            <Text fontSize="xs" fontWeight="medium" color="white" noOfLines={1}>{item.title}</Text>
                            <Badge
                              fontSize="2xs"
                              borderRadius="full"
                              px={1.5}
                              bg={badgeBg}
                              color={badgeColor}
                            >
                              {badgeLabel}
                            </Badge>
                          </Flex>
                          <Text fontSize="2xs" color="whiteAlpha.500">{formatRelativeTime(item.occurredAt)}</Text>
                        </Box>
                        <Icon as={FiChevronRight} boxSize={3.5} color="whiteAlpha.400" />
                      </Flex>
                    );
                  });
                })()}
              </VStack>
            </Box>
          </Box>
        </SimpleGrid>
      </Box>

      <DomainExpansionModal
        isOpen={isModalOpen}
        onClose={onModalClose}
        domain={selectedDomain}
      />
    </MainLayout>
  )
}

export default HomePage
