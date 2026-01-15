import { Box, Flex, Text, Alert, AlertIcon, Spinner } from '@chakra-ui/react';
import { StatCard } from '../components/StatCard';
import { MainLayout } from '../components/layouts/MainLayout';
import { Link } from 'react-router-dom';
import { useUserProfile } from '../hooks/useUserProfile';
import { useState, useEffect } from 'react';
import { getHomeMetrics, HomeMetricsResponse } from '../services/analyticsService';
import { useIndicators } from '../hooks/useIndicators';

function HomePage() {
  const profile = useUserProfile();
  const [revenueData, setRevenueData] = useState({ value: 0, month: '' });
  const [metricsData, setMetricsData] = useState<HomeMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch indicators from IndicatorService
  const { data: indicators, loading: indicatorsLoading, error: indicatorsError } = useIndicators({
    period: 'today',
    metrics: ['orders', 'products', 'customers'],
    includeComparisons: true,
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const data = await getHomeMetrics();
        setMetricsData(data);

        const currentMonth = new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date());
        setRevenueData({
          value: data.scorecards.receita_total,
          month: currentMonth
        });
        setError(null);
      } catch (err) {
        console.error('Error fetching home metrics:', err);
        setError('Erro ao carregar métricas');
        // Fallback to placeholder data on error
        const currentMonth = new Intl.DateTimeFormat('pt-BR', { month: 'long' }).format(new Date());
        setRevenueData({
          value: 0,
          month: currentMonth
        });
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, []);

  // Early return for loading state
  if (loading || indicatorsLoading) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Spinner size="xl" />
        </Flex>
      </MainLayout>
    );
  }

  // Early return for error state
  if (error || indicatorsError) {
    return (
      <MainLayout>
        <Flex justify="center" align="center" height="100vh">
          <Alert status="error">
            <AlertIcon />
            {error || indicatorsError}
          </Alert>
        </Flex>
      </MainLayout>
    );
  }

  const userName = profile?.full_name.split(' ')[0] || 'Usuário';
  const formattedRevenue = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(revenueData.value);

  // Extract indicator values with fallbacks
  const ordersTotal = indicators?.orders?.total || metricsData?.scorecards.total_produtos || 0;
  const ordersRevenue = indicators?.orders?.revenue || 0;
  const ordersGrowth = indicators?.orders?.growth_rate
    ? `${indicators.orders.growth_rate >= 0 ? '+' : ''}${indicators.orders.growth_rate.toFixed(1)}%`
    : '';

  const productsTotal = indicators?.products?.unique_products || metricsData?.scorecards.total_produtos || 0;
  const productsSold = indicators?.products?.total_sold || 0;
  const productsAvgPrice = indicators?.products?.avg_price || 0;

  const customersTotal = indicators?.customers?.total_active || metricsData?.scorecards.total_clientes || 0;
  const customersNew = indicators?.customers?.new_customers || 0;
  const customersLTV = indicators?.customers?.avg_lifetime_value || 0;

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
                percentage={ordersGrowth.toLocaleString()}
                total={ordersTotal.toLocaleString()}
                totalLabel="TOTAL"
                frequency={`R$ ${ordersRevenue.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                frequencyLabel="FREQUÊNCIA"
                color="#F9BBCB"
              />
            </Link>
            <Link to="/dashboard/produtos">
              <StatCard
                title="PRODUTOS"
                percentage=""
                total={productsTotal.toLocaleString()}
                totalLabel="ÚNICOS"
                frequency={productsSold.toLocaleString()}
                frequencyLabel="VENDIDOS"
                color="#FFF856"
              />
            </Link>
            <Link to="/dashboard/clientes">
              <StatCard
                title="CLIENTES"
                percentage=""
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
