import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

// Types matching backend IndicatorsResponse
export interface OrderMetrics {
    total: number;
    revenue: number;
    avg_order_value: number;
    growth_rate: number | null;
    by_status: Record<string, number>;
    period: string;
    comparisons?: ComparisonData;
}

export interface ProductMetrics {
    total_sold: number;
    unique_products: number;
    top_sellers: Array<{ name: string; quantity: number; revenue: number }>;
    low_stock_alerts: number;
    avg_price: number;
    period: string;
    comparisons?: ComparisonData;
}

export interface CustomerMetrics {
    total_active: number;
    new_customers: number;
    returning_customers: number;
    avg_lifetime_value: number;
    period: string;
    comparisons?: ComparisonData;
}

export interface ComparisonData {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: 'up' | 'down' | 'stable' | null;
}

export interface IndicatorsResponse {
    orders: OrderMetrics | null;
    products: ProductMetrics | null;
    customers: CustomerMetrics | null;
    cached: boolean;
    generated_at: string;
    ttl: number | null;
}

type PeriodType = 'today' | 'yesterday' | 'week' | 'month' | 'quarter' | 'year';

interface UseIndicatorsOptions {
    period?: PeriodType;
    metrics?: Array<'orders' | 'products' | 'customers'>;
    includeComparisons?: boolean;
    autoFetch?: boolean;
}

interface UseIndicatorsReturn {
    data: IndicatorsResponse | null;
    loading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

// API fetch function extracted for React Query - now uses Supabase directly
const fetchIndicators = async (
    period: PeriodType,
    metrics: Array<'orders' | 'products' | 'customers'>,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for future comparison feature
    _includeComparisons: boolean
): Promise<IndicatorsResponse> => {
    const ANALYTICS_SCHEMA = 'analytics_v2';
    const generatedAt = new Date().toISOString();

    let orders: OrderMetrics | null = null;
    let products: ProductMetrics | null = null;
    let customers: CustomerMetrics | null = null;

    // Calculate period filter
    const getPeriodDays = (): number | null => {
        switch (period) {
            case 'today': return 1;
            case 'yesterday': return 2;
            case 'week': return 7;
            case 'month': return 30;
            case 'quarter': return 90;
            case 'year': return 365;
            default: return null;
        }
    };

    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- reserved for period-based filtering
    const _periodDays = getPeriodDays();

    // Fetch orders metrics
    if (metrics.includes('orders')) {
        const { data: resumo, error } = await supabase
            .schema(ANALYTICS_SCHEMA)
            .from('v_resumo_dashboard')
            .select('total_pedidos, receita_total, ticket_medio')
            .single();

        if (error) {
            console.error('[Indicators] v_resumo_dashboard FAILED:', error.code, error.message, error.details, error.hint);
        }

        if (!error && resumo) {
            orders = {
                total: Number(resumo.total_pedidos) || 0,
                revenue: Number(resumo.receita_total) || 0,
                avg_order_value: Number(resumo.ticket_medio) || 0,
                growth_rate: null,
                by_status: { completed: Number(resumo.total_pedidos) || 0 },
                period,
            };
        }
    }

    // Fetch product metrics
    if (metrics.includes('products')) {
        const { data: produtos, error } = await supabase
            .schema(ANALYTICS_SCHEMA)
            .from('dim_inventory')
            .select('quantidade_total_vendida, total_pedidos, preco_medio');

        if (error) {
            console.error('[Indicators] dim_inventory FAILED:', error.code, error.message, error.details, error.hint);
        }

        if (!error && produtos) {
            const totalSold = produtos.reduce((sum, p) => sum + Number(p.quantidade_total_vendida || 0), 0);
            const avgPrice = produtos.length > 0
                ? produtos.reduce((sum, p) => sum + Number(p.preco_medio || 0), 0) / produtos.length
                : 0;

            products = {
                total_sold: totalSold,
                unique_products: produtos.length,
                top_sellers: [],
                low_stock_alerts: 0,
                avg_price: avgPrice,
                period,
            };
        }
    }

    // Fetch customer metrics
    if (metrics.includes('customers')) {
        const { data: clientes, error } = await supabase
            .schema(ANALYTICS_SCHEMA)
            .from('dim_clientes')
            .select('total_pedidos, receita_total, dias_recencia');

        if (error) {
            console.error('[Indicators] dim_clientes FAILED:', error.code, error.message, error.details, error.hint);
        }

        if (!error && clientes) {
            const totalActive = clientes.filter(c => Number(c.dias_recencia) <= 90).length;
            const newCustomers = clientes.filter(c => Number(c.total_pedidos) === 1).length;
            const avgLifetimeValue = clientes.length > 0
                ? clientes.reduce((sum, c) => sum + Number(c.receita_total || 0), 0) / clientes.length
                : 0;

            customers = {
                total_active: totalActive,
                new_customers: newCustomers,
                returning_customers: totalActive - newCustomers,
                avg_lifetime_value: avgLifetimeValue,
                period,
            };
        }
    }

    return {
        orders,
        products,
        customers,
        cached: false,
        generated_at: generatedAt,
        ttl: null,
    };
};

/**
 * Hook to fetch indicator metrics from Analytics API
 * Uses React Query for automatic caching and background refetching
 *
 * @example
 * const { data, loading, error } = useIndicators({
 *   period: 'today',
 *   metrics: ['orders', 'products']
 * });
 */
export const useIndicators = ({
    period = 'today',
    metrics = ['orders', 'products', 'customers'],
    includeComparisons = true,
    autoFetch = true,
}: UseIndicatorsOptions = {}): UseIndicatorsReturn => {
    const metricsKey = metrics.slice().sort().join(',');

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['indicators', period, metricsKey, includeComparisons],
        queryFn: () => fetchIndicators(period, metrics, includeComparisons),
        enabled: autoFetch,
        staleTime: 5 * 60 * 1000,  // 5 minutes - indicators don't change frequently
    });

    return {
        data: data ?? null,
        loading: isLoading,
        error: error instanceof Error ? error.message : error ? String(error) : null,
        refetch: async () => { await refetch(); },
    };
};

/**
 * Helper function to format KPI items for DashboardCard from indicators
 * Dynamically generates KPIs based on available data in the metrics object
 * Labels are derived from the object property names
 */
export const formatOrderKPIs = (orders: OrderMetrics | null) => {
    if (!orders) return [];

    const kpis: Array<{ label: string; content: React.ReactNode }> = [];

    // Map of field keys to display formatters
    const fieldMap: Record<string, { label: string; format: (value: any) => React.ReactNode }> = {
        total: {
            label: 'Total',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                    {orders.growth_rate !== null && (
                        <p style={{ fontSize: '14px', color: orders.growth_rate >= 0 ? 'green' : 'red' }}>
                            {orders.growth_rate >= 0 ? '+' : ''}{orders.growth_rate.toFixed(1)}% vs período anterior
                        </p>
                    )}
                </div>
            ),
        },
        revenue: {
            label: 'Receita',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>
                        R$ {value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                    {orders.comparisons?.vs_30_days !== null && orders.comparisons?.vs_30_days !== undefined && (
                        <p style={{ fontSize: '14px', color: orders.comparisons.vs_30_days >= 0 ? 'green' : 'red' }}>
                            {orders.comparisons.vs_30_days >= 0 ? '+' : ''}{orders.comparisons.vs_30_days.toFixed(1)}% vs 30 dias
                        </p>
                    )}
                </div>
            ),
        },
        avg_order_value: {
            label: 'Ticket Médio',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>
                        R$ {value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                </div>
            ),
        },
            by_status: {
            label: 'Por Status',
            format: (value) => {
                // value may be a number when data is malformed; guard against it
                if (typeof value !== 'object' || value === null) {
                    return <div>{String(value)}</div>;
                }
                return (
                    <div>
                        {Object.entries(value as Record<string, number>).map(([status, count]) => (
                            <p key={status} style={{ marginBottom: '4px' }}>
                                <strong>{status}:</strong> {count}
                            </p>
                        ))}
                    </div>
                );
            },
        },
    };

    // Iterate over orders object and create KPIs for mapped fields
    Object.entries(orders).forEach(([key, value]) => {
        if (fieldMap[key] && value !== null && value !== undefined) {
            // Skip empty objects/arrays
            if (typeof value === 'object' && Object.keys(value).length === 0) return;

            kpis.push({
                label: fieldMap[key].label,
                content: fieldMap[key].format(value),
            });
        }
    });

    return kpis;
};

export const formatProductKPIs = (products: ProductMetrics | null) => {
    if (!products) return [];

    const kpis: Array<{ label: string; content: React.ReactNode }> = [];

    type ProductValue = number | Array<{ name: string; quantity: number; revenue: number }>;
    // Map of field keys to display formatters
    const fieldMap: Record<string, { label: string; format: (value: any) => React.ReactNode }> = {
        total_sold: {
            label: 'Vendidos',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                </div>
            ),
        },
        unique_products: {
            label: 'Únicos',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                </div>
            ),
        },
        avg_price: {
            label: 'Preço Médio',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>
                        R$ {value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                </div>
            ),
        },
        top_sellers: {
            label: 'Top Sellers',
            format: (value) => (
                <div>
                    {(value as Array<{ name: string; quantity: number; revenue: number }>).slice(0, 5).map((product, idx) => (
                        <p key={idx} style={{ marginBottom: '8px' }}>
                            <strong>{product.name}:</strong> {product.quantity} unidades
                        </p>
                    ))}
                </div>
            ),
        },
        low_stock_alerts: {
            label: 'Alertas Estoque',
            format: (value) => {
                const num = Number(value) || 0;
                return (
                    <div>
                        <p style={{ fontSize: '24px', fontWeight: 'bold', color: num > 0 ? 'red' : 'green' }}>
                            {num}
                        </p>
                    </div>
                );
            },
        },
    };

    // Iterate over products object and create KPIs for mapped fields
    Object.entries(products).forEach(([key, value]) => {
        if (fieldMap[key] && value !== null && value !== undefined) {
            // Skip empty objects/arrays
            if (Array.isArray(value) && value.length === 0) return;
            if (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0) return;

            kpis.push({
                label: fieldMap[key].label,
                content: fieldMap[key].format(value),
            });
        }
    });

    return kpis;
};

export const formatCustomerKPIs = (customers: CustomerMetrics | null) => {
    if (!customers) return [];

    const kpis: Array<{ label: string; content: React.ReactNode }> = [];

    // Map of field keys to display formatters
    const fieldMap: Record<string, { label: string; format: (value: any) => React.ReactNode }> = {
        total_active: {
            label: 'Ativos',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                </div>
            ),
        },
        new_customers: {
            label: 'Novos',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                </div>
            ),
        },
        returning_customers: {
            label: 'Recorrentes',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>{value.toLocaleString()}</p>
                </div>
            ),
        },
        avg_lifetime_value: {
            label: 'LTV Médio',
            format: (value) => (
                <div>
                    <p style={{ fontSize: '24px', fontWeight: 'bold' }}>
                        R$ {value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </p>
                </div>
            ),
        },
    };

    // Iterate over customers object and create KPIs for mapped fields
    Object.entries(customers).forEach(([key, value]) => {
        if (fieldMap[key] && value !== null && value !== undefined) {
            // Skip empty objects/arrays
            if (typeof value === 'object' && Object.keys(value).length === 0) return;

            kpis.push({
                label: fieldMap[key].label,
                content: fieldMap[key].format(value),
            });
        }
    });

    return kpis;
};
