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
        // Use receita_mes_atual if available, otherwise fallback to receita_total
        const monthlyRevenue = data.scorecards.receita_mes_atual || data.scorecards.receita_total;
        setRevenueData({
          value: monthlyRevenue,
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

  // Extract Produtos data
  const productsTotal = indicators?.products?.unique_products || metricsData?.scorecards.total_produtos || 0;
  // Convert to tons (divide by 1000) then format compactly
  const productsSoldRaw = indicators?.products?.total_sold || 0;
  const productsSoldInTons = productsSoldRaw / 1000; // Convert kg to tons
  const productsSoldFormatted = formatCompactNumber(productsSoldInTons, 'ton');
  const produtosCrescimento = formatGrowth(metricsData?.scorecards.crescimento_produtos);

  // Extract Clientes data
  const customersTotal = indicators?.customers?.total_active || metricsData?.scorecards.total_clientes || 0;
  const customersNew = indicators?.customers?.new_customers || 0;
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
