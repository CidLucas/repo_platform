import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Box,
  Flex,
  Text,
  Spinner,
  ButtonGroup,
  Button,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
} from '@chakra-ui/react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { getDomainAnalytics, DomainAnalytics } from '../services/analyticsService';

type DomainType = 'orders' | 'customers' | 'suppliers' | 'products';

interface DomainExpansionModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain: DomainType;
}

const DOMAIN_CONFIG: Record<
  DomainType,
  {
    title: string;
    color: string;
    chartType: 'bar';
    dataKeys: string[];
    kpiLabels: Record<string, string>;
  }
> = {
  orders: {
    title: 'Pedidos',
    color: '#8884d8',
    chartType: 'bar',
    dataKeys: ['revenue'],
    kpiLabels: {
      total_orders: 'Total de Pedidos',
      avg_ticket: 'Ticket Médio',
      growth: 'Crescimento',
      conversion_rate: 'Taxa de Conversão',
      revenue_growth: 'Cresc. Receita',
    },
  },
  customers: {
    title: 'Clientes',
    color: '#FFB6C1',
    chartType: 'bar',
    dataKeys: ['new'],
    kpiLabels: {
      active_customers: 'Clientes Ativos',
      total_customers: 'Total Clientes',
      avg_ltv: 'LTV Médio',
      churn_rate: 'Taxa de Churn',
      growth: 'Crescimento',
    },
  },
  suppliers: {
    title: 'Fornecedores',
    color: '#92DAFF',
    chartType: 'bar',
    dataKeys: ['active'],
    kpiLabels: {
      total_suppliers: 'Total Fornecedores',
      active_suppliers: 'Fornecedores Ativos',
      total_revenue: 'Receita Total',
      avg_delivery_time: 'Tempo Médio Entrega',
      compliance_rate: 'Conformidade',
    },
  },
  products: {
    title: 'Produtos',
    color: '#FFF856',
    chartType: 'bar',
    dataKeys: ['sold'],
    kpiLabels: {
      total_products: 'Total Produtos',
      total_sold: 'Total Vendido',
      total_revenue: 'Receita Total',
      avg_margin: 'Margem Média',
      turnover_rate: 'Giro',
    },
  },
};

export function DomainExpansionModal({
  isOpen,
  onClose,
  domain,
}: DomainExpansionModalProps) {
  const [data, setData] = useState<DomainAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  // Chart range in months — default 12, options 6 / 12 / 24 / all.
  const [rangeMonths, setRangeMonths] = useState<number | 'all'>(12);

  const config = DOMAIN_CONFIG[domain];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getDomainAnalytics(domain);
      setData(result);
    } catch (err) {
      console.error(`Failed to fetch ${domain} analytics:`, err);
    } finally {
      setLoading(false);
    }
  }, [domain]);

  useEffect(() => {
    if (isOpen) {
      setRangeMonths(12);
      fetchData();
    }
  }, [isOpen, fetchData]);

  // Slice the most recent N months client-side — switching the toggle is
  // instant because the full series is already cached.
  const currentChartData = useMemo(() => {
    const series = data?.monthlyData ?? [];
    if (rangeMonths === 'all') return series;
    return series.slice(Math.max(0, series.length - rangeMonths));
  }, [data, rangeMonths]);

  const rangeOptions: Array<{ label: string; value: number | 'all' }> = [
    { label: '6m', value: 6 },
    { label: '12m', value: 12 },
    { label: '24m', value: 24 },
    { label: 'Tudo', value: 'all' },
  ];

  const formatKpiValue = (key: string, value: number): string => {
    if (key.includes('rate') || key === 'growth') {
      return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
    }
    if (key.includes('revenue') || key.includes('ticket') || key.includes('ltv')) {
      if (value >= 1_000_000) {
        return `R$ ${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`;
      }
      if (value >= 1_000) {
        return `R$ ${(value / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`;
      }
      return `R$ ${value.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;
    }
    if (value >= 1_000_000) {
      return `${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`;
    }
    if (value >= 1_000) {
      return `${(value / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mil`;
    }
    return value.toLocaleString('pt-BR');
  };

  const renderChart = () => {
    if (!currentChartData.length) {
      return (
        <Flex justify="center" align="center" h="200px">
          <Text color="gray.400">Sem dados disponíveis</Text>
        </Flex>
      );
    }

    return (
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={currentChartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#333" />
          <XAxis dataKey="name" stroke="#999" fontSize={12} />
          <YAxis stroke="#999" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid #333',
              borderRadius: '8px',
              color: '#fff',
            }}
          />
          {config.dataKeys.map(key => (
            <Bar
              key={key}
              dataKey={key}
              fill={config.color}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" isCentered>
      <ModalOverlay bg="blackAlpha.700" />
      <ModalContent bg="#1a1a2e" color="white" borderRadius="16px" maxW="700px">
        <ModalHeader
          borderBottom="1px solid"
          borderColor="whiteAlpha.200"
          fontSize="xl"
          fontWeight="bold"
        >
          {config.title}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody py={6}>
          {loading ? (
            <Flex justify="center" align="center" h="300px">
              <Spinner size="lg" color={config.color} />
            </Flex>
          ) : (
            <>
              {/* Chart with range toggle */}
              <Box mb={6}>
                <Flex justify="space-between" align="center" mb={3} gap={3} flexWrap="wrap">
                  <Text fontSize="sm" color="gray.400" fontWeight="medium">
                    Tendência Mensal
                  </Text>
                  <ButtonGroup size="xs" isAttached variant="outline">
                    {rangeOptions.map((opt) => {
                      const active = rangeMonths === opt.value;
                      return (
                        <Button
                          key={String(opt.value)}
                          onClick={() => setRangeMonths(opt.value)}
                          bg={active ? 'whiteAlpha.200' : 'transparent'}
                          color={active ? 'white' : 'gray.400'}
                          borderColor="whiteAlpha.300"
                          _hover={{ bg: 'whiteAlpha.100' }}
                          aria-pressed={active}
                        >
                          {opt.label}
                        </Button>
                      );
                    })}
                  </ButtonGroup>
                </Flex>
                {renderChart()}
              </Box>

              {/* KPIs Grid */}
              {data?.kpis && (
                <SimpleGrid columns={{ base: 2, md: 3 }} spacing={4}>
                  {Object.entries(data.kpis).map(([key, value]) => {
                    const label = config.kpiLabels[key] || key;
                    const isPercentage = key.includes('rate') || key === 'growth';
                    return (
                      <Stat
                        key={key}
                        bg="whiteAlpha.100"
                        p={4}
                        borderRadius="12px"
                      >
                        <StatLabel color="gray.400" fontSize="xs">
                          {label}
                        </StatLabel>
                        <StatNumber fontSize="lg">
                          {formatKpiValue(key, value)}
                        </StatNumber>
                        {isPercentage && value !== 0 && (
                          <StatHelpText>
                            <StatArrow
                              type={value >= 0 ? 'increase' : 'decrease'}
                            />
                            vs mês anterior
                          </StatHelpText>
                        )}
                      </Stat>
                    );
                  })}
                </SimpleGrid>
              )}
            </>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
}
