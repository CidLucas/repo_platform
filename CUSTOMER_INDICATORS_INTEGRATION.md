# Customer Indicators Integration - IndicatorService to Frontend

## Problem Statement

User wanted to display customer KPI metrics from `IndicatorService` in the ClientesPage, specifically:
- Show metrics in the graph area (GraphComponent)
- Display KPI names and values in AccordionComponent

## Solution Implemented

### Backend - Indicators Endpoint

The indicators endpoint already existed at `/api/indicators/customers` returning:

```python
class CustomerMetricsResponse(BaseModel):
    total_active: int          # Total active customers in period
    new_customers: int         # New customers in period
    returning_customers: int   # Returning customers in period
    avg_lifetime_value: float  # Average customer lifetime value
    period: str                # Period type (today, week, month, etc.)
    comparisons: ComparisonData | None  # Optional comparisons vs 7/30/90 days
```

**File:** [indicators.py:195-211](services/analytics_api/src/analytics_api/api/endpoints/indicators.py)

### Frontend Integration

#### 1. Added Type Definition

**File:** [analyticsService.ts:65-77](apps/vizu_dashboard/src/services/analyticsService.ts)

```typescript
export interface CustomerMetricsResponse {
  total_active: number;
  new_customers: number;
  returning_customers: number;
  avg_lifetime_value: number;
  period: string;
  comparisons?: {
    vs_7_days: number | null;
    vs_30_days: number | null;
    vs_90_days: number | null;
    trend: string | null;
  };
}
```

#### 2. Added API Function

**File:** [analyticsService.ts:332-337](apps/vizu_dashboard/src/services/analyticsService.ts)

```typescript
export const getCustomerIndicators = async (period: string = 'month'): Promise<CustomerMetricsResponse> => {
  const response = await axiosInstance.get<CustomerMetricsResponse>(`/indicators/customers`, {
    params: { period, include_comparisons: false }
  });
  return response.data;
};
```

**Parameters:**
- `period`: One of "today", "yesterday", "week", "month", "quarter", "year" (default: "month")
- `include_comparisons`: Boolean to include comparison data (default: false for simplicity)

#### 3. Updated ClientesPage

**File:** [ClientesPage.tsx](apps/vizu_dashboard/src/pages/ClientesPage.tsx)

**Added State:**
```typescript
const [customerMetrics, setCustomerMetrics] = useState<CustomerMetricsResponse | null>(null);
```

**Fetch Data in Parallel:**
```typescript
const [overviewResponse, metricsResponse] = await Promise.all([
  getClientes(),
  getCustomerIndicators('month')
]);
```

**Transform for GraphComponent:**
```typescript
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
```

**Transform for KPI Accordion:**
```typescript
kpiItems={
  customerMetrics
    ? [
        {
          label: `Clientes Ativos: ${customerMetrics.total_active}`,
          content: <Text>Total de clientes ativos no período de {customerMetrics.period}</Text>
        },
        {
          label: `Novos Clientes: ${customerMetrics.new_customers}`,
          content: <Text>Clientes que fizeram sua primeira compra...</Text>
        },
        {
          label: `Clientes Recorrentes: ${customerMetrics.returning_customers}`,
          content: <Text>Clientes que retornaram para fazer novas compras...</Text>
        },
        {
          label: `Valor Médio de Vida (LTV): R$ ${customerMetrics.avg_lifetime_value.toLocaleString('pt-BR')}`,
          content: <Text>Valor médio total que um cliente gasta...</Text>
        }
      ]
    : undefined
}
```

---

## Data Flow

```
1. IndicatorService.get_customer_metrics('month')
   ↓ Reads from analytics_gold_customers table
   ↓ Calculates: total_active, new_customers, returning_customers, avg_lifetime_value

2. /api/indicators/customers?period=month
   ↓ Returns CustomerMetricsResponse

3. Frontend: getCustomerIndicators('month')
   ↓ Fetches from API

4. ClientesPage
   ↓ Transforms data into two formats:

   A) GraphComponent format:
      [
        { name: 'Ativos', value: 150 },
        { name: 'Novos', value: 25 },
        ...
      ]

   B) AccordionComponent format:
      [
        {
          label: 'Clientes Ativos: 150',
          content: <Text>Description...</Text>
        },
        ...
      ]
```

---

## Component Rendering

### GraphComponent (Card Display)
- X-axis shows metric names: "ATIVOS", "NOVOS", "RECORRENTES", "LTV MÉDIO"
- Y-axis shows values: 150, 25, 100, 5000
- Line chart visualization of customer metrics

### AccordionComponent (Modal Display)
When user clicks info icon on card, modal opens showing:
- **Left side:** Accordion with expandable KPI items
  - Each item shows: "Metric Name: Value"
  - Expandable content explains what the metric means
- **Right side:** GraphCarousel with the same data

---

## Example API Response

```json
GET /api/indicators/customers?period=month

{
  "total_active": 150,
  "new_customers": 25,
  "returning_customers": 125,
  "avg_lifetime_value": 5432.67,
  "period": "month"
}
```

## Example Graph Data Transformation

```typescript
// API Response
{
  total_active: 150,
  new_customers: 25,
  returning_customers: 125,
  avg_lifetime_value: 5432.67
}

// Transformed for GraphComponent
[
  { name: 'Ativos', value: 150 },
  { name: 'Novos', value: 25 },
  { name: 'Recorrentes', value: 125 },
  { name: 'LTV Médio', value: 5433 }  // Rounded
]

// Rendered X-axis labels (uppercased by GraphComponent)
"ATIVOS", "NOVOS", "RECORRENTES", "LTV MÉDIO"
```

---

## KPI Definitions

| Metric | Field | Definition |
|--------|-------|------------|
| **Clientes Ativos** | `total_active` | Total customers who made at least one purchase in the period |
| **Novos Clientes** | `new_customers` | Customers who made their first purchase in the period |
| **Clientes Recorrentes** | `returning_customers` | Customers who made repeat purchases in the period |
| **LTV Médio** | `avg_lifetime_value` | Average total revenue per customer across their entire relationship |

---

## Period Options

User can potentially change the period by updating the `getCustomerIndicators()` parameter:

| Period | Description | Days |
|--------|-------------|------|
| `today` | Current day | 1 |
| `yesterday` | Previous day | 1 |
| `week` | Last 7 days | 7 |
| `month` | Last 30 days | 30 (default) |
| `quarter` | Last 90 days | 90 |
| `year` | Last 365 days | 365 |

**Current Implementation:** Hardcoded to `'month'`

**Future Enhancement:** Add a dropdown/selector to let users choose the period dynamically.

---

## Styling Details

### DashboardCard Configuration
- **Title:** "Performance de Clientes"
- **Size:** Large (824px × 524px)
- **Background Color:** #FFD1DC (light pink)
- **Modal Colors:**
  - Left side: #FFD1DC
  - Right side: #FFB6C1

### GraphComponent
- **Line Color:** Inherited from bgColor (dark gray by default)
- **Line Width:** 8px
- **X-axis:** Black, 3px thick, uppercase labels
- **Tooltip:** Dark background with white text

---

## Files Modified

1. **[analyticsService.ts](apps/vizu_dashboard/src/services/analyticsService.ts)**
   - Added `CustomerMetricsResponse` interface (lines 65-77)
   - Added `getCustomerIndicators()` function (lines 332-337)

2. **[ClientesPage.tsx](apps/vizu_dashboard/src/pages/ClientesPage.tsx)**
   - Added import for `getCustomerIndicators` and `CustomerMetricsResponse`
   - Added `customerMetrics` state
   - Updated `useEffect` to fetch indicators in parallel
   - Transformed metrics for `graphData` prop
   - Added `kpiItems` prop with accordion content

---

## Testing Checklist

- [ ] API call to `/api/indicators/customers` succeeds
- [ ] CustomerMetrics data populates in ClientesPage state
- [ ] GraphComponent displays 4 data points with correct names
- [ ] X-axis shows: "ATIVOS", "NOVOS", "RECORRENTES", "LTV MÉDIO"
- [ ] Y-axis values match the API response
- [ ] Modal opens when clicking info icon
- [ ] Accordion shows 4 KPI items with correct labels
- [ ] Each accordion item expands to show description
- [ ] GraphCarousel in modal displays the same data
- [ ] No console errors
- [ ] Loading state works correctly
- [ ] Error handling works if API fails

---

## Future Enhancements

1. **Period Selector**: Add dropdown to switch between day/week/month/quarter/year
2. **Comparisons**: Enable `include_comparisons: true` to show trends (vs 7/30/90 days)
3. **Trend Indicators**: Display up/down/stable arrows based on comparison data
4. **Drill-down**: Click on a KPI to see detailed breakdown
5. **Export**: Add button to export metrics as CSV/PDF

---

## Comparison with Other Integrations

| Integration | Data Source | Display Location | Component |
|-------------|-------------|------------------|-----------|
| **Fornecedores Time Series** | `gold_time_series` | GraphComponent | Line chart (time series) |
| **Customer Indicators** | `IndicatorService` | GraphComponent + Accordion | Bar chart (KPI values) |
| **Cohort Clientes** | `gold_customers` | PieChart | Segmentation |

---

## Notes

- **Why month period?** Most business metrics are reviewed monthly. Week/quarter can be added via selector.
- **Why round LTV?** Graph looks cleaner with integers. Full precision shown in accordion.
- **Why no comparisons?** Simplifies initial implementation. Can add later with trend arrows.
- **Why parallel fetch?** Faster page load (both API calls happen simultaneously).

---

## Deployment

- [x] Add CustomerMetricsResponse type to analyticsService
- [x] Add getCustomerIndicators() API function
- [x] Update ClientesPage to fetch and display metrics
- [x] Transform data for GraphComponent
- [x] Transform data for AccordionComponent
- [ ] **Test in browser with real data**
- [ ] **Deploy to production**
- [ ] **Monitor API response times**
- [ ] **Verify indicators endpoint is performant**
