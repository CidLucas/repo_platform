import { Box, Flex, Text, Alert, AlertIcon, useDisclosure, Icon, SimpleGrid, VStack, HStack, Badge, Link as ChakraLink, usePrefersReducedMotion, useToast } from '@chakra-ui/react';
import { DomainExpansionModal } from '../components/DomainExpansionModal';
import { MainLayout } from '../components/layouts/MainLayout';
import { OnboardingBanner } from '../components/OnboardingBanner';
import { MappingReviewBanner } from '../components/MappingReviewBanner';
import { InsightsCard } from '../components/InsightsCard';
import { KpiCard } from '../components/KpiCard';
import { KpisSection } from '../components/KpisSection';
import { GeneralKpisCard } from '../components/GeneralKpisCard';
import { SampleBadge } from '../components/SampleBadge';
import { useMemo, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useHomeMetrics } from '../hooks/useHomeMetrics';
import { useAgentRunsToday } from '../hooks/useAgentRunsToday';
import { useRecentActivity } from '../hooks/useRecentActivity';
import { useAgenda } from '../hooks/useAgenda';
import { usePendencias } from '../hooks/usePendencias';
import { useNps } from '../hooks/useNps';
import { useDashboardKpis } from '../hooks/useDashboardKpis';
import { getActivationStatusSnapshot } from '../services/analyticsService';
import { useAuth } from '../hooks/useAuth';
import { useTracking } from '../hooks/useTracking';
import { FiDollarSign, FiCheckCircle, FiPackage, FiUsers, FiFileText, FiTrendingUp, FiZap, FiCalendar, FiClock, FiActivity, FiChevronRight, FiMail, FiPhone, FiTarget, FiSend, FiPlusCircle } from 'react-icons/fi';

function HomePage() {
  const { user } = useAuth();
  const toast = useToast();
  const { track } = useTracking();
  const navigate = useNavigate();
  const { isOpen: isModalOpen, onOpen: onModalOpen, onClose: onModalClose } = useDisclosure();
  const prefersReducedMotion = usePrefersReducedMotion();
  const [selectedDomain, setSelectedDomain] = useState<'orders' | 'customers' | 'suppliers' | 'products'>('orders');

  const handleDomainClick = (domain: 'orders' | 'customers' | 'suppliers' | 'products') => {
    setSelectedDomain(domain);
    onModalOpen();
  };

  useEffect(() => {
    let mounted = true;

    const maybeCelebrateFirstConnector = async () => {
      try {
        const snapshot = await getActivationStatusSnapshot();
        if (!mounted || !snapshot.has_synced_connector) return;

        const storageKey = `blu.activation.first_connector_toast.${snapshot.client_id}`;
        if (window.localStorage.getItem(storageKey) === '1') return;

        const suggestions = [
          '"Vendas dessa semana"',
          '"Ticket médio"',
          '"Top produtos"',
        ];
        const extra = snapshot.pending_approvals > 0
          ? ` Você também tem ${snapshot.pending_approvals} aprovação(ões) pendente(s).`
          : '';

        toast({
          title: 'Primeiro conector sincronizado com sucesso!',
          description: `Próximos prompts sugeridos: ${suggestions.join(' · ')}.${extra}`,
          status: 'success',
          duration: 9000,
          isClosable: true,
          position: 'top-right',
        });

        window.localStorage.setItem(storageKey, '1');
      } catch {
        // Non-blocking UX enhancement.
      }
    };

    void maybeCelebrateFirstConnector();
    return () => {
      mounted = false;
    };
  }, [toast, user?.id]);

  // Single consolidated hook — v_resumo_dashboard now provides all HomePage data
  const { data: metricsData, loading: metricsLoading, error: metricsError } = useHomeMetrics();

  // Live data hooks (Phase 4: dashboard mocks → live data)
  const { data: agentRunsData } = useAgentRunsToday();
  const { data: recentActivityData } = useRecentActivity(4);
  const { data: agendaData } = useAgenda(7);
  const { data: pendenciasData } = usePendencias();
  const { data: npsData } = useNps(90);
  const { data: dashboardKpisData, loading: dashboardKpisLoading } = useDashboardKpis();

  // Relative-time formatter (PT-BR) — used by Recent Activity & Pendências.
  const relativeTimeFormatter = useMemo(
    () => new Intl.RelativeTimeFormat('pt-BR', { numeric: 'auto' }),
    []
  );

  const formatRelativeTime = (isoDate?: string | null): string => {
    if (!isoDate) {
      return 'agora';
    }
    const now = Date.now();
    const then = new Date(isoDate).getTime();
    if (!Number.isFinite(then)) {
      return 'agora';
    }

    const diffMs = then - now;
    const minute = 60 * 1000;
    const hour = 60 * minute;
    const day = 24 * hour;

    if (Math.abs(diffMs) < hour) {
      return relativeTimeFormatter.format(Math.round(diffMs / minute), 'minute');
    }
    if (Math.abs(diffMs) < day) {
      return relativeTimeFormatter.format(Math.round(diffMs / hour), 'hour');
    }
    return relativeTimeFormatter.format(Math.round(diffMs / day), 'day');
  };

  if (metricsError) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error" bg="#1a1b2e" color="white" borderRadius="10px" border="1px solid" borderColor="red.600">
            <AlertIcon color="red.400" />
            {metricsError}
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

  const revenueLabel = 'Receita deste mês';
  const growthLabel = 'vs. mês anterior';
  const pedidosCardLabel = 'pedidos este mês';
  const scorecardsAny = metricsData?.scorecards as unknown as Record<string, unknown> | undefined;
  const isSampleData = Boolean(scorecardsAny?.is_sample || scorecardsAny?.sample);

  const capDisplayNumber = (value: number): number => {
    if (!Number.isFinite(value)) return 0;
    if (!isSampleData) return value;
    return Math.min(value, 99_999);
  };

  const formatCountWithCap = (value: number): string => {
    const capped = capDisplayNumber(value);
    const suffix = isSampleData && value > capped ? '+' : '';
    return `${capped.toLocaleString('pt-BR')}${suffix}`;
  };

  const buildActionableInsight = () => {
    const sc = metricsData?.scorecards;
    if (!sc) {
      return 'Receita atual: R$ 0,0. Investigar origem de dados para iniciar o painel.';
    }

    if (revenueGrowth !== undefined && revenueGrowth !== null) {
      const trend = revenueGrowth > 0 ? 'subiu' : revenueGrowth < 0 ? 'caiu' : 'ficou estável';
      return `Receita do mês ${trend} ${Math.abs(revenueGrowth).toFixed(1)}%. Investigar drivers por canal.`;
    }

    if (sc.ticket_medio !== undefined && sc.ticket_medio !== null) {
      return `Ticket médio atual: ${formatCompactCurrency(sc.ticket_medio)}. Investigar oportunidades de upsell.`;
    }

    return `Pedidos no mês: ${formatCountWithCap(pedidosMesAtual)}. Priorizar clientes sem recompra nos últimos 30 dias.`;
  };

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

  const formattedRevenue = formatCompactCurrency(metricsData?.scorecards.receita_mes_atual || 0);

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
      {isSampleData && (
        <Box
          mx={6}
          mt={4}
          px={4}
          py={3}
          borderRadius="10px"
          bg="rgba(251,191,36,0.08)"
          border="1px solid"
          borderColor="rgba(251,191,36,0.35)"
        >
          <HStack justify="space-between" flexWrap="wrap" spacing={3}>
            <HStack spacing={2}>
              <Text fontSize="14px">🧪</Text>
              <Text fontSize="14px" color="white">
                Você está vendo dados de exemplo.
              </Text>
            </HStack>
            <ChakraLink
              href="/dashboard/configurar/connectors"
              color="#fbbf24"
              fontSize="14px"
              fontWeight={600}
              _hover={{ color: '#fcd34d', textDecoration: 'none' }}
              onClick={() => {
                track('dashboard.demo_live.switch', { source: 'demo_banner' });
                track('tenant.sample_data.disabled', { source: 'demo_banner' });
              }}
            >
              <HStack as="span" spacing={1}>
                <Text>Conectar minha loja →</Text>
              </HStack>
            </ChakraLink>
          </HStack>
        </Box>
      )}
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
                <Box as="span" color="white">Painel </Box>
                <Box
                  as="span"
                  bgGradient="linear(to-r, #ff6b35, #ff006e)"
                  bgClip="text"
                >
                  Analítico
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
              >
                <KpiCard
                  title={revenueLabel}
                  value={formattedRevenue}
                  icon={FiDollarSign}
                  accentColor="#10b981"
                  delta={revenueGrowth}
                  deltaContext={growthLabel}
                  isSample={isSampleData}
                />
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
                    <HStack spacing={2} mb={1}>
                      <Text fontSize="xs" color="whiteAlpha.500" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider">
                        Pedidos ativos
                      </Text>
                      {isSampleData && <SampleBadge />}
                    </HStack>
                    <Text fontSize="2xl" fontWeight="bold" color="white">
                      {formatCountWithCap(pedidosMesAtual)}
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
                    transition={prefersReducedMotion ? 'none' : 'all 0.2s'}
                    _hover={{
                      borderColor: 'rgba(255,255,255,0.12)',
                      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
                      transform: prefersReducedMotion ? 'none' : 'translateY(-4px)',
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
                          {formatCountWithCap(card.stat)}
                        </Text>
                      </Box>
                    </Flex>
                    <Text fontSize="sm" color="whiteAlpha.600" lineHeight="relaxed">
                      {card.sublabel}
                    </Text>
                    {isSampleData && (
                      <Box mt={3}>
                        <SampleBadge />
                      </Box>
                    )}
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
                transition={prefersReducedMotion ? 'none' : 'box-shadow 0.2s'}
              >
                <Box position="absolute" top={0} left={0} w="3px" h="100%" bg="#fbbf24" />
                <Flex justify="space-between" align="center">
                  <Box>
                    <Text fontSize="xs" color="whiteAlpha.500" fontWeight="semibold" textTransform="uppercase" letterSpacing="wider" mb={1}>
                      Tarefas de IA hoje
                    </Text>
                    <Text fontSize="2xl" fontWeight="bold" color="white">
                      {formatCountWithCap(agentRunsData?.total ?? 0)}
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
                      Insight acionável
                    </Text>
                    <Text fontSize="sm" color="whiteAlpha.800">
                      {buildActionableInsight()}
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

            {/* Full-width KPIs Section */}
            <Box mb={6} id="section-kpis" data-insight-target="kpis">
              <KpisSection
                kpis={dashboardKpisData}
                loading={dashboardKpisLoading}
                isSampleData={isSampleData}
                demoStateShowsOnlyPrimary={true}
              />
            </Box>

            {/* C2: insights as actionable section in Mission Control main flow */}
            <Box mb={6}>
              <InsightsCard limit={5} title="Insights acionáveis" />
            </Box>

            {/* Horizontal Row — Quick Actions, Recent Activity, Pendências */}
              <SimpleGrid columns={{ base: 1, md: 4 }} spacing={4} mb={6}>
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
                    { icon: FiPlusCircle, label: 'Nova Aprovação', color: '#3b82f6', route: '/dashboard/inbox' },
                    { icon: FiSend, label: 'Enviar Relatório', color: '#10b981', route: '/dashboard/reports' },
                    { icon: FiMail, label: 'E-mail cliente', color: '#a855f7', route: '/dashboard/inbox' },
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
                      transition={prefersReducedMotion ? 'none' : 'all 0.2s'}
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

              {/* General KPIs Card */}
              <GeneralKpisCard
                kpis={[
                  {
                    label: 'Ticket Médio',
                    value: formatCompactCurrency(metricsData?.scorecards.ticket_medio || 0),
                    color: '#10b981',
                  },
                  {
                    label: 'NPS Score',
                    value: npsData ? `${Math.round(npsData.score)}` : '—',
                    unit: npsData ? `${npsData.totalResponses} respostas` : undefined,
                    color: '#f97316',
                  },
                ]}
                loading={metricsLoading}
              />
            </SimpleGrid>
          </Box>

          {/* Right Section — Hoje + Pendências (1 column, scrolls together) */}
          <Box>
            <Box
              id="section-hoje"
              data-insight-target="operations"
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
                          onClick={() => navigate('/dashboard/configurar/fontes')}
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
