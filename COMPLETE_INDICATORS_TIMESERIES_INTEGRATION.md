# Complete Indicators & Time Series Integration Guide

## Summary of Changes

This document describes all changes made to integrate:
1. **IndicatorService metrics** (customers, products, orders) → KPI accordions
2. **Time series data** (fornecedores, clientes, produtos, pedidos) → Graph displays

---

## Backend Changes Completed ✅

### 1. Added Time Series to Endpoints

**File:** [rankings.py](services/analytics_api/src/analytics_api/api/endpoints/rankings.py)

#### Clientes Endpoint (lines 147-156)
```python
# Time series from Gold (precomputed) with cumulative calculation
time_data = repo.get_gold_time_series(client_id, 'clientes_no_tempo')
cumulative_sum = 0
chart_clientes_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_clientes_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

#### Produtos Endpoint (lines 216-224)
```python
# Time series from Gold (precomputed) with cumulative calculation
time_data = repo.get_gold_time_series(client_id, 'produtos_no_tempo')
cumulative_sum = 0
chart_produtos_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_produtos_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

#### Pedidos Endpoint (lines 273-281)
```python
# Time series from Gold (precomputed) with cumulative calculation
time_data = repo.get_gold_time_series(client_id, 'pedidos_no_tempo')
cumulative_sum = 0
chart_pedidos_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_pedidos_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

### 2. Updated Response Schemas

**File:** [metrics.py](services/analytics_api/src/analytics_api/schemas/metrics.py)

```python
class ClientesOverviewResponse(BaseModel):
    # ... existing fields ...
    chart_clientes_no_tempo: list[ChartDataPoint]  # ← ADDED
    # ... rest of fields ...

class ProdutosOverviewResponse(BaseModel):
    scorecard_total_itens_unicos: int
    chart_produtos_no_tempo: list[ChartDataPoint]  # ← ADDED
    ranking_por_receita: list[ProdutoRankingReceita]
    # ... rest of fields ...

class PedidosOverviewResponse(BaseModel):
    # ... existing fields ...
    chart_pedidos_no_tempo: list[ChartDataPoint]  # ← ADDED
    # ... rest of fields ...
```

---

## Frontend Changes Completed ✅

### 1. Added Types to analyticsService.ts

**File:** [analyticsService.ts](apps/vizu_dashboard/src/services/analyticsService.ts)

#### Added Indicator Types (lines 56-104)
```typescript
export interface CustomerMetricsResponse {
  total_active: number;
  new_customers: number;
  returning_customers: number;
  avg_lifetime_value: number;
  period: string;
}

export interface ProductMetricsResponse {
  total_sold: number;
  unique_products: number;
  top_sellers: any[];
  low_stock_alerts: number;
  avg_price: number;
  period: string;
}

export interface OrderMetricsResponse {
  total: number;
  revenue: number;
  avg_order_value: number;
  growth_rate: number | null;
  by_status: Record<string, any>;
  period: string;
}
```

#### Updated Overview Response Types
```typescript
export interface ClientesOverviewResponse {
  // ... existing fields ...
  chart_clientes_no_tempo: ChartDataPoint[];  // ← ADDED
  // ... rest of fields ...
}

export interface ProdutosOverviewResponse {
  scorecard_total_itens_unicos: number;
  chart_produtos_no_tempo: ChartDataPoint[];  // ← ADDED
  ranking_por_receita: ProdutoRankingReceita[];
  // ... rest of fields ...
}

export interface PedidosOverviewResponse {
  // ... existing fields ...
  chart_pedidos_no_tempo: ChartDataPoint[];  // ← ADDED
  // ... rest of fields ...
}
```

#### Added API Functions (lines 332-353)
```typescript
export const getCustomerIndicators = async (period: string = 'month'): Promise<CustomerMetricsResponse> => {
  const response = await axiosInstance.get<CustomerMetricsResponse>(`/indicators/customers`, {
    params: { period, include_comparisons: false }
  });
  return response.data;
};

export const getProductIndicators = async (period: string = 'month'): Promise<ProductMetricsResponse> => {
  const response = await axiosInstance.get<ProductMetricsResponse>(`/indicators/products`, {
    params: { period, include_comparisons: false }
  });
  return response.data;
};

export const getOrderIndicators = async (period: string = 'month'): Promise<OrderMetricsResponse> => {
  const response = await axiosInstance.get<OrderMetricsResponse>(`/indicators/orders`, {
    params: { period, include_comparisons: false }
  });
  return response.data;
};
```

### 2. Updated ClientesPage ✅

**File:** [ClientesPage.tsx](apps/vizu_dashboard/src/pages/ClientesPage.tsx)

**Changes Made:**
1. Added import for `getCustomerIndicators` and `CustomerMetricsResponse`
2. Added state: `const [customerMetrics, setCustomerMetrics] = useState<CustomerMetricsResponse | null>(null)`
3. Fetch indicators in parallel with overview data
4. Transform metrics for GraphComponent (4 data points: Ativos, Novos, Recorrentes, LTV Médio)
5. Create KPI accordion with 4 items showing metric names and values

**Result:** Card shows customer indicators in graph and detailed KPIs in modal accordion.

---

## Frontend Changes Needed 🚧

### 3. ProdutosListPage

**Current State:** Shows table of products, no indicators or time series

**Changes Needed:**

#### Add State
```typescript
const [productMetrics, setProductMetrics] = useState<ProductMetricsResponse | null>(null);
```

#### Fetch Indicators
```typescript
useEffect(() => {
  const fetchData = async () => {
    try {
      setLoading(true);
      const [overviewResponse, metricsResponse] = await Promise.all([
        getProdutosOverview(),
        getProductIndicators('month')
      ]);
      setOverviewData(overviewResponse);
      setProductMetrics(metricsResponse);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar produtos.');
    } finally {
      setLoading(false);
    }
  };
  fetchData();
}, []);
```

#### Add DashboardCard Before Table
```tsx
<DashboardCard
  title="Métricas de Produtos"
  size="large"
  bgColor="#C7E7FF"
  graphData={{
    values: productMetrics
      ? [
          { name: 'Total Vendido', value: productMetrics.total_sold },
          { name: 'Produtos Únicos', value: productMetrics.unique_products },
          { name: 'Preço Médio', value: Math.round(productMetrics.avg_price) },
          { name: 'Alertas Estoque', value: productMetrics.low_stock_alerts }
        ]
      : []
  }}
  scorecardValue={`${overviewData?.scorecard_total_itens_unicos || 0}`}
  scorecardLabel="Produtos Únicos"
  kpiItems={
    productMetrics
      ? [
          {
            label: `Total Vendido: ${productMetrics.total_sold}`,
            content: <Text>Quantidade total de produtos vendidos no período de {productMetrics.period}</Text>
          },
          {
            label: `Produtos Únicos: ${productMetrics.unique_products}`,
            content: <Text>Número de produtos diferentes vendidos no período</Text>
          },
          {
            label: `Preço Médio: R$ ${productMetrics.avg_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
            content: <Text>Valor médio de venda por produto</Text>
          },
          {
            label: `Alertas de Estoque: ${productMetrics.low_stock_alerts}`,
            content: <Text>Produtos com estoque baixo que precisam de reposição</Text>
          }
        ]
      : undefined
  }
  modalContent={<Text>Métricas detalhadas de produtos no período de {productMetrics?.period || 'mês'}</Text>}
/>
```

#### Add Time Series Card (Optional)
```tsx
<DashboardCard
  title="Crescimento do Catálogo"
  size="large"
  bgColor="#E0F7FF"
  graphData={{
    values: overviewData?.chart_produtos_no_tempo
      ? overviewData.chart_produtos_no_tempo.map((d: any) => ({
          name: d.name,
          value: d.total_cumulativo || 0
        }))
      : []
  }}
  scorecardValue={`${overviewData?.scorecard_total_itens_unicos || 0}`}
  scorecardLabel="Total de Produtos"
  modalContent={<Text>Evolução do catálogo de produtos ao longo do tempo</Text>}
/>
```

---

### 4. PedidosPage

**Current State:** Shows hardcoded graph values, no real indicators

**Changes Needed:**

#### Add Imports
```typescript
import { getOrderIndicators, getPedidosOverview } from '../services/analyticsService';
import type { OrderMetricsResponse, PedidosOverviewResponse } from '../services/analyticsService';
```

#### Add State
```typescript
const [orderMetrics, setOrderMetrics] = useState<OrderMetricsResponse | null>(null);
const [overviewData, setOverviewData] = useState<PedidosOverviewResponse | null>(null);
```

#### Fetch Data
```typescript
useEffect(() => {
  const fetchData = async () => {
    try {
      const [overviewResponse, metricsResponse] = await Promise.all([
        getPedidosOverview(),
        getOrderIndicators('month')
      ]);
      setOverviewData(overviewResponse);
      setOrderMetrics(metricsResponse);
    } catch (err: any) {
      console.error('Error fetching pedidos:', err);
    }
  };
  fetchData();
}, []);
```

#### Replace Hardcoded Graph (line 123)
**Before:**
```typescript
graphData={{ values: [10, 20, 15, 25, 22] }}
```

**After:**
```typescript
graphData={{
  values: orderMetrics
    ? [
        { name: 'Total Pedidos', value: orderMetrics.total },
        { name: 'Receita', value: Math.round(orderMetrics.revenue) },
        { name: 'Ticket Médio', value: Math.round(orderMetrics.avg_order_value) },
        { name: 'Crescimento %', value: orderMetrics.growth_rate || 0 }
      ]
    : []
}}
kpiItems={
  orderMetrics
    ? [
        {
          label: `Total de Pedidos: ${orderMetrics.total}`,
          content: <Text>Número total de pedidos no período de {orderMetrics.period}</Text>
        },
        {
          label: `Receita Total: R$ ${orderMetrics.revenue.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          content: <Text>Valor total de receita gerada pelos pedidos</Text>
        },
        {
          label: `Ticket Médio: R$ ${orderMetrics.avg_order_value.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`,
          content: <Text>Valor médio por pedido</Text>
        },
        {
          label: `Taxa de Crescimento: ${orderMetrics.growth_rate?.toFixed(1) || 0}%`,
          content: <Text>Crescimento percentual em relação ao período anterior</Text>
        }
      ]
    : undefined
}
```

#### Add Time Series Card
```tsx
<DashboardCard
  title="Volume de Pedidos"
  size="large"
  bgColor="#FFF4C7"
  graphData={{
    values: overviewData?.chart_pedidos_no_tempo
      ? overviewData.chart_pedidos_no_tempo.map((d: any) => ({
          name: d.name,
          value: d.total_cumulativo || 0
        }))
      : []
  }}
  scorecardValue={orderMetrics ? `${orderMetrics.total}` : '0'}
  scorecardLabel="Total de Pedidos"
  modalContent={<Text>Evolução do volume de pedidos ao longo do tempo</Text>}
/>
```

---

### 5. ClientesPage - Add Time Series to Modal

**Current State:** Modal shows only accordion with KPIs

**Change Needed:** Add time series graph to the modal right side

#### Update DashboardCard (around line 169)
**Add `modalRightContent` prop:**

```typescript
<DashboardCard
  title="Métricas de Clientes"
  size="large"
  bgColor="#FFD1DC"
  graphData={{
    values: customerMetrics
      ? [
          { name: 'Ativos', value: customerMetrics.total_active },
          { name: 'Novos', value: customerMetrics.new_customers },
          { name: 'Recorrentes', value: customerMetrics.returning_customers },
          { name: 'LTV Médio', value: Math.round(customerMetrics.avg_lifetime_value) }
        ]
      : []
  }}
  scorecardValue={`R$ ${(overviewData.scorecard_ticket_medio_geral ?? 0).toLocaleString('pt-BR')}`}
  scorecardLabel="Ticket Médio Geral"
  kpiItems={
    customerMetrics
      ? [
          // ... existing KPI items ...
        ]
      : undefined
  }
  modalLeftBgColor="#FFD1DC"
  modalRightBgColor="#FFB6C1"
  modalContent={
    <GraphCarousel
      graphs={[
        {
          title: "Crescimento de Clientes",
          data: overviewData.chart_clientes_no_tempo.map((d: any) => ({
            name: d.name,
            value: d.total_cumulativo || 0
          })),
          dataKey: "value",
          lineColor: "white"
        }
      ]}
    />
  }
/>
```

**Note:** This would require importing GraphCarousel in ClientesPage or adjusting DashboardCard to accept time series data separately.

---

## Complete Integration Checklist

### Backend ✅
- [x] Add time series to clientes endpoint
- [x] Add time series to produtos endpoint
- [x] Add time series to pedidos endpoint
- [x] Update ClientesOverviewResponse schema
- [x] Update ProdutosOverviewResponse schema
- [x] Update PedidosOverviewResponse schema
- [x] Indicators endpoints already exist (customers, products, orders)

### Frontend Types ✅
- [x] Add CustomerMetricsResponse type
- [x] Add ProductMetricsResponse type
- [x] Add OrderMetricsResponse type
- [x] Update ClientesOverviewResponse to include chart_clientes_no_tempo
- [x] Update ProdutosOverviewResponse to include chart_produtos_no_tempo
- [x] Update PedidosOverviewResponse to include chart_pedidos_no_tempo
- [x] Add getCustomerIndicators() function
- [x] Add getProductIndicators() function
- [x] Add getOrderIndicators() function

### Frontend Pages - Completed ✅
- [x] ClientesPage: Indicators integrated with KPI accordion

### Frontend Pages - To Do 🚧
- [ ] ProdutosListPage: Add product indicators and time series
- [ ] PedidosPage: Replace hardcoded values with real indicators
- [ ] PedidosPage: Add time series graph
- [ ] ClientesPage: Add time series to modal (optional enhancement)
- [ ] FornecedoresPage: Already has time series, consider adding indicators

---

## Testing Guide

### For Each Page

1. **Check API Response**
   ```bash
   curl -H "Authorization: Bearer YOUR_JWT" \
     "http://localhost:8000/api/rankings/clientes?client_id=YOUR_CLIENT_ID"

   # Verify response includes:
   # - chart_clientes_no_tempo (array with name, total, total_cumulativo)
   ```

2. **Check Indicators Response**
   ```bash
   curl -H "Authorization: Bearer YOUR_JWT" \
     "http://localhost:8000/api/indicators/customers?period=month"

   # Verify response includes:
   # - total_active, new_customers, returning_customers, avg_lifetime_value
   ```

3. **Frontend Verification**
   - Graph displays 4 data points with correct metric names
   - X-axis shows uppercased metric names
   - Modal opens and shows accordion with KPI items
   - Each KPI item shows "Metric Name: Value"
   - Clicking KPI item expands to show description
   - No console errors
   - Loading states work correctly

---

## Data Transformation Pattern

This pattern should be used consistently across all pages:

```typescript
// 1. Fetch both overview and indicators
const [overview, indicators] = await Promise.all([
  getOverview(),
  getIndicators('month')
]);

// 2. Transform for GraphComponent (card display)
graphData={{
  values: indicators
    ? [
        { name: 'Metric1', value: indicators.metric1 },
        { name: 'Metric2', value: indicators.metric2 },
        // ... etc
      ]
    : []
}}

// 3. Transform for AccordionComponent (modal display)
kpiItems={
  indicators
    ? [
        {
          label: `Metric Name: ${indicators.metric1}`,
          content: <Text>Description of what this metric means</Text>
        },
        // ... etc
      ]
    : undefined
}

// 4. Transform time series (if available)
// For main graph:
graphData={{
  values: overview.chart_*_no_tempo
    ? overview.chart_*_no_tempo.map(d => ({
        name: d.name,
        value: d.total_cumulativo || 0
      }))
    : []
}}
```

---

## Period Options

Currently hardcoded to `'month'`. Future enhancement: add selector.

Available periods:
- `today` - Current day
- `yesterday` - Previous day
- `week` - Last 7 days
- `month` - Last 30 days (default)
- `quarter` - Last 90 days
- `year` - Last 365 days

---

## Files Reference

### Backend
- `services/analytics_api/src/analytics_api/api/endpoints/rankings.py` - Overview endpoints with time series
- `services/analytics_api/src/analytics_api/api/endpoints/indicators.py` - Indicators endpoints
- `services/analytics_api/src/analytics_api/schemas/metrics.py` - Response schemas
- `services/analytics_api/src/analytics_api/services/indicator_service.py` - Indicator calculation logic

### Frontend
- `apps/vizu_dashboard/src/services/analyticsService.ts` - API types and functions
- `apps/vizu_dashboard/src/pages/ClientesPage.tsx` - Customers page (completed)
- `apps/vizu_dashboard/src/pages/ProdutosListPage.tsx` - Products page (to do)
- `apps/vizu_dashboard/src/pages/PedidosPage.tsx` - Orders page (to do)
- `apps/vizu_dashboard/src/components/DashboardCard.tsx` - Card component with accordion
- `apps/vizu_dashboard/src/components/GraphComponent.tsx` - Line chart component

---

## Next Steps

1. **Complete ProdutosListPage integration** (add indicators + time series)
2. **Complete PedidosPage integration** (replace hardcoded values, add indicators + time series)
3. **Test all pages** with real data
4. **Deploy to production**
5. **Monitor API performance** (indicators endpoints should be fast <100ms)
6. **Consider adding period selector** to let users choose time range
7. **Add comparison trends** (vs 7/30/90 days) using `include_comparisons: true`
