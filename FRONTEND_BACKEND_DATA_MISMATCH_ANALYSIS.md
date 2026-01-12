# Frontend-Backend Data Mismatch Analysis

## Problem Summary

You're seeing:
1. **Zero values** in Fornecedores and Clientes pages
2. **No graphs** displaying
3. **Hardcoded KPIs** in DashboardCard component
4. **Produtos page shows some values** but still has issues

---

## Root Causes

### 1. Data Format Mismatch

**Frontend Expects** (DashboardCard.tsx):
```typescript
graphData?: {
  values: number[];  // Simple array of numbers
}
```

**Backend Returns** (metric_service.py):
```python
"chart_cohort_clientes": [
  {"name": "A (Melhores)", "contagem": 150, "percentual": 25.0},
  {"name": "B", "contagem": 200, "percentual": 33.3},
  {"name": "C", "contagem": 180, "percentual": 30.0},
  {"name": "D (Piores)", "contagem": 70, "percentual": 11.7}
]
```

**The Issue**: Frontend is trying to use `graphData.values` which doesn't exist in the API response!

---

### 2. Hardcoded KPIs Not Connected to API

**Current State** (DashboardCard.tsx lines 150-157):
```typescript
items={[
  { label: "KPI 1", content: <Text>Detalhes do KPI 1</Text> },
  { label: "KPI 2", content: <Text>Detalhes do KPI 2</Text> },
  { label: "KPI 3", content: <Text>Detalhes do KPI 3</Text> },
  { label: "KPI 4", content: <Text>Detalhes do KPI 4</Text> },
  { label: "KPI 5", content: <Text>Detalhes do KPI 5</Text> },
]}
```

**What It Should Be**: Dynamic KPIs from API data for each entity (customer/supplier/product).

---

## Available Metrics from Analytics API

### **Fornecedores Overview API** (`GET /api/rankings/fornecedores`)

**Response Structure**:
```json
{
  "scorecard_total_fornecedores": 432,
  "scorecard_crescimento_percentual": 5.2,

  "chart_fornecedores_no_tempo": [
    {"name": "2024-01", "total_cumulativo": 50},
    {"name": "2024-02", "total_cumulativo": 78},
    ...
  ],

  "chart_fornecedores_por_regiao": [
    {"name": "SP", "total": 150},
    {"name": "RJ", "total": 89},
    ...
  ],

  "chart_cohort_fornecedores": [
    {"name": "A (Melhores)", "contagem": 100, "percentual": 23.1},
    {"name": "B", "contagem": 150, "percentual": 34.7},
    {"name": "C", "contagem": 120, "percentual": 27.8},
    {"name": "D (Piores)", "contagem": 62, "percentual": 14.4}
  ],

  "ranking_por_receita": [
    {
      "nome": "Supplier A",
      "receita_total": 1500000.50,
      "quantidade_total": 5000.0,
      "num_pedidos_unicos": 120,
      "primeira_venda": "2023-01-15T00:00:00Z",
      "ultima_venda": "2024-12-20T00:00:00Z",
      "ticket_medio": 12500.00,
      "qtd_media_por_pedido": 41.67,
      "frequencia_pedidos_mes": 5.2,
      "recencia_dias": 18,
      "valor_unitario_medio": 300.00,
      "cluster_score": 85.6,
      "cluster_tier": "A (Melhores)"
    },
    ... // Top 10
  ],

  "ranking_por_ticket_medio": [...],  // Top 10
  "ranking_por_qtd_media": [...],     // Top 10
  "ranking_por_frequencia": [...],    // Top 10

  "ranking_produtos_mais_vendidos": [
    {
      "nome": "Product X",
      "receita_total": 250000.00,
      "valor_unitario_medio": 150.00
    },
    ...
  ]
}
```

### **Clientes Overview API** (`GET /api/rankings/clientes`)

**Response Structure**:
```json
{
  "scorecard_total_clientes": 1579,
  "scorecard_ticket_medio_geral": 15313.83,
  "scorecard_frequencia_media_geral": 2.8,
  "scorecard_crescimento_percentual": 3.5,

  "chart_clientes_por_regiao": [
    {"name": "SP", "percentual": 35.5},
    {"name": "RJ", "percentual": 22.3},
    ...
  ],

  "chart_cohort_clientes": [
    {"name": "A (Melhores)", "contagem": 395, "percentual": 25.0},
    {"name": "B", "contagem": 474, "percentual": 30.0},
    {"name": "C", "contagem": 395, "percentual": 25.0},
    {"name": "D (Piores)", "contagem": 315, "percentual": 20.0}
  ],

  "ranking_por_receita": [...],        // RankingItem[] - Top 10
  "ranking_por_ticket_medio": [...],   // RankingItem[] - Top 10
  "ranking_por_qtd_pedidos": [...],    // RankingItem[] - Top 10
  "ranking_por_cluster_vizu": [...]    // RankingItem[] - Top 10 by RFM score
}
```

### **Produtos Overview API** (`GET /api/rankings/produtos`)

**Response Structure**:
```json
{
  "scorecard_total_itens_unicos": 5964,

  "ranking_por_receita": [
    {
      "nome": "Product A",
      "receita_total": 500000.00,
      "valor_unitario_medio": 250.00
    },
    ... // Top 10
  ],

  "ranking_por_volume": [
    {
      "nome": "Product B",
      "quantidade_total": 8500.0,
      "valor_unitario_medio": 125.00
    },
    ... // Top 10
  ],

  "ranking_por_ticket_medio": [
    {
      "nome": "Product C",
      "ticket_medio": 35000.00,
      "valor_unitario_medio": 400.00
    },
    ... // Top 10
  ]
}
```

---

## What's Missing vs Your Requirements

### Fornecedores

| Requirement | API Has It? | Field Name | Notes |
|------------|-------------|------------|-------|
| Top by receita/frequência/ticket | ✅ YES | `ranking_por_receita`, `ranking_por_frequencia`, `ranking_por_ticket_medio` | |
| Tier distribution | ✅ YES | `chart_cohort_fornecedores` | A/B/C/D segments |
| Growth % | ✅ YES | `scorecard_crescimento_percentual` | Month over month |
| Regional distribution | ✅ YES | `chart_fornecedores_por_regiao` | Count by state |
| Top products sold | ✅ YES | `ranking_produtos_mais_vendidos` | Top 10 products |
| Cross-tab: Suppliers × Top Clients | ❌ NO | - | Would need new calculation |
| Heatmap: Sales by region | ⚠️ PARTIAL | `chart_fornecedores_por_regiao` | Has count, not sales amount |

### Clientes

| Requirement | API Has It? | Field Name | Notes |
|------------|-------------|------------|-------|
| Top by receita/frequência/ticket | ✅ YES | `ranking_por_receita`, `ranking_por_qtd_pedidos`, `ranking_por_ticket_medio` | |
| Bottom customers | ⚠️ PARTIAL | Can reverse any ranking | Not explicitly provided |
| Tier distribution | ✅ YES | `chart_cohort_clientes` | A/B/C/D segments |
| Growth % | ✅ YES | `scorecard_crescimento_percentual` | Month over month |
| Regional distribution | ✅ YES | `chart_clientes_por_regiao` | % by state |
| Avg ticket | ✅ YES | `scorecard_ticket_medio_geral` | |
| Avg frequency | ✅ YES | `scorecard_frequencia_media_geral` | |

### Produtos

| Requirement | API Has It? | Field Name | Notes |
|------------|-------------|------------|-------|
| Top by receita/quantidade | ✅ YES | `ranking_por_receita`, `ranking_por_volume` | |
| Avg price per kg | ✅ YES | `valor_unitario_medio` | In each ranking item |
| By category | ❌ NO | - | No category field exists |
| Regional heatmap | ❌ NO | - | Would need new calculation |

---

## Specific Issues to Fix

### Issue 1: **"Novos Cadastros" showing 0**

**Location**: FornecedoresPage / ClientesPage "Novos Clientes" card

**Root Cause**: The frontend is calculating this CLIENT-SIDE (lines 84-89 in ClientesPage.tsx):
```typescript
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
const newCustomersCount = (overviewData.ranking_por_receita || []).filter((item: any) => {
  const firstSaleDate = new Date(item.primeira_venda);
  return firstSaleDate >= thirtyDaysAgo;
}).length;
```

**Problem**: `item.primeira_venda` is a string like `"2023-01-15T00:00:00Z"` but the date parsing might be failing, OR all customers have `primeira_venda` older than 30 days.

**Fix Options**:
1. **Backend calculation**: Add `scorecard_novos_ultimos_30_dias` to the API response
2. **Frontend fix**: Ensure proper date parsing with timezone handling

### Issue 2: **"Receita is zero" in rankings**

**Root Cause**: The frontend might be accessing the wrong field name, or the data is actually zero.

**Debug Steps**:
1. Check browser console: `console.log('Clientes data:', overviewData)`
2. Check if `ranking_por_receita` array has items with non-zero `receita_total`
3. Verify the field name used in frontend matches API response

### Issue 3: **No Graphs Displaying**

**Root Cause**: Data format mismatch between what DashboardCard expects vs what API provides.

**Frontend expects**:
```typescript
graphData={{
  values: [10, 20, 15, 25, 22]  // Simple array
}}
```

**API provides**:
```json
"chart_cohort_clientes": [
  {"name": "A", "contagem": 395, "percentual": 25.0},
  {"name": "B", "contagem": 474, "percentual": 30.0},
  ...
]
```

**Fix**: Transform API data to match frontend format:
```typescript
graphData={{
  values: overviewData.chart_cohort_clientes
    ? overviewData.chart_cohort_clientes.map((d: any) => d.contagem || 0)
    : []
}}
```

### Issue 4: **Hardcoded KPIs**

**Location**: DashboardCard.tsx modal accordion

**Current**: Shows "KPI 1", "KPI 2", etc. with no real data

**Fix**: Pass actual KPIs from the ranking items:

For a customer in the ranking:
```typescript
items={[
  { label: "Receita Total", content: <Text>R$ {item.receita_total.toLocaleString('pt-BR')}</Text> },
  { label: "Ticket Médio", content: <Text>R$ {item.ticket_medio.toLocaleString('pt-BR')}</Text> },
  { label: "Frequência", content: <Text>{item.frequencia_pedidos_mes.toFixed(1)} pedidos/mês</Text> },
  { label: "Última Compra", content: <Text>{item.recencia_dias} dias atrás</Text> },
  { label: "Cluster", content: <Text>{item.cluster_tier}</Text> },
]}
```

---

## Next Steps

1. **Debug the actual API responses**: Check browser network tab to see what data is being returned
2. **Fix graph data transformation**: Convert API's `ChartDataPoint[]` to frontend's `values: number[]`
3. **Connect hardcoded KPIs to real data**: Use ranking item fields instead of placeholders
4. **Add missing calculations**: Backend should calculate "new customers in last 30 days"
5. **Fix date parsing**: Ensure `primeira_venda` dates are properly parsed in frontend

Would you like me to start fixing these issues? Which one should we tackle first?
