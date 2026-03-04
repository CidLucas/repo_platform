import { Box, Flex, Text, Alert, AlertIcon, Spinner } from '@chakra-ui/react';
import { StatCard } from '../components/StatCard';
import { MainLayout } from '../components/layouts/MainLayout';
import { Link } from 'react-router-dom';
import { useUserProfile } from '../hooks/useUserProfile';
import { useMemo, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useHomeMetrics } from '../hooks/useHomeMetrics';
import { getClientes, getFornecedores, getProdutosOverview } from '../services/analyticsService';

function HomePage() {
  const profile = useUserProfile();
  const queryClient = useQueryClient();

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

  // Derive revenue data from metricsData (memoized to avoid recalculation)
  const revenueData = useMemo(() => {
    if (!metricsData) {
      return { value: 0, month: new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date()) };
    }
    const currentMonth = new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date());
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
          <Spinner size="xl" />
        </Flex>
      </MainLayout>
    );
  }

  // Early return for error state
  if (error) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error">
            <AlertIcon />
            {error}
          </Alert>
        </Flex>
      </MainLayout>
    );
  }

  const userName = profile?.full_name.split(' ')[0] || 'Usuário';

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

  // Format growth percentage helper
  const formatGrowth = (value: number | undefined): string => {
    if (value === undefined || value === null) return '';
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  // Format large numbers as compact (ex: 361M -> "361,9 mil ton")
  const formatCompactNumber = (value: number, unit?: string): string => {
    const suffix = unit ? ` ${unit}` : '';
    if (value >= 1_000_000_000) {
      return `${(value / 1_000_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} bi${suffix}`;
    } else if (value >= 1_000_000) {
      return `${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi${suffix}`;
    } else if (value >= 1_000) {
      return `${(value / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil${suffix}`;
    }
    return `${value.toLocaleString('pt-BR')}${suffix}`;
  };

  // Extract Fornecedores data from metricsData (correct source)
  const fornecedoresTotal = metricsData?.scorecards.total_fornecedores || 0;
  const fornecedoresFrequencia = metricsData?.scorecards.frequencia_media_fornecedores || 0;
  const fornecedoresCrescimento = formatGrowth(metricsData?.scorecards.crescimento_receita);

  // Extract Produtos data — from consolidated v_resumo_dashboard
  const productsTotal = metricsData?.scorecards.total_produtos || 0;
  const productsSoldRaw = metricsData?.scorecards.quantidade_total_vendida || 0;
  const productsSoldInTons = productsSoldRaw / 1000; // Convert kg to tons
  const productsSoldFormatted = formatCompactNumber(productsSoldInTons, 'ton');
  const produtosCrescimento = formatGrowth(metricsData?.scorecards.crescimento_produtos);

  // Extract Clientes data — from consolidated v_resumo_dashboard
  const customersTotal = metricsData?.scorecards.clientes_ativos || metricsData?.scorecards.total_clientes || 0;
  const customersNew = metricsData?.scorecards.clientes_novos || 0;
  const clientesCrescimento = formatGrowth(metricsData?.scorecards.crescimento_clientes);

  return (
    <MainLayout>
      <Flex
        direction="column"
        px={{ base: '20px', md: '40px', lg: '80px' }}
        pt={{ base: '20px', md: '40px', lg: '20px' }}
        pb={{ base: '80px', md: '40px', lg: '20px' }} // Added responsive padding-bottom
        mt="32px"
        bg="#F6F6F6" // Explicitly set background for HomePage
      >
        <Text as="h1" textStyle="pageTitle" mb="36px">
          Olá, {userName}. Sua<br />receita em {revenueData.month}
        </Text>
        <Text as="h2" textStyle="pageBigNumber" mb="36px">{formattedRevenue}</Text>
        <Box mt="36px">
          <Flex wrap="wrap" justify="center" gap="16px">
            <Link to="/dashboard/fornecedores">
              <StatCard
                title="FORNECEDORES"
                percentage={fornecedoresCrescimento}
                total={fornecedoresTotal.toLocaleString()}
                totalLabel="TOTAL"
                frequency={`${fornecedoresFrequencia.toFixed(1)}/mês`}
                frequencyLabel="FREQUÊNCIA"
                color="#92DAFF"
              />
            </Link>
            <Link to="/dashboard/produtos">
              <StatCard
                title="PRODUTOS"
                percentage={produtosCrescimento}
                total={productsTotal.toLocaleString()}
                totalLabel="ÚNICOS"
                frequency={productsSoldFormatted}
                frequencyLabel="VENDIDOS"
                color="#FFF856"
              />
            </Link>
            <Link to="/dashboard/clientes">
              <StatCard
                title="CLIENTES"
                percentage={clientesCrescimento}
                total={customersTotal.toLocaleString()}
                totalLabel="ATIVOS"
                frequency={customersNew.toLocaleString()}
                frequencyLabel="NOVOS"
                color="#FFB6C1"
              />
            </Link>
          </Flex>
        </Box>
      </Flex>
    </MainLayout>
  )
}

export default HomePage
