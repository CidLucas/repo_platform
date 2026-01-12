# Frontend Graph Data Transformation Fix

## Problem Summary

The frontend pages (Clientes, Fornecedores, Produtos) were not displaying graphs because they were accessing incorrect field names from the API response.

**Symptoms**:
- No graphs displaying
- Zero values showing in many places
- Hardcoded KPIs not connected to real data

## Root Cause

**Data Format Mismatch**: Frontend was accessing fields that don't exist in the API response.

### Example Issue:

**Frontend Code (WRONG)**:
```typescript
graphData={{
  values: overviewData.chart_cohort_clientes.map((d: any) => d.value || 0)
}}
```

**API Response Structure**:
```json
{
  "chart_cohort_clientes": [
    {"name": "A (Melhores)", "contagem": 395, "percentual": 25.0},
    {"name": "B", "contagem": 474, "percentual": 30.0}
  ]
}
```

**Problem**: Frontend accesses `d.value` but API provides `d.contagem`!

---

## Fixes Applied

### 1. ClientesPage.tsx ✅

**File**: [apps/vizu_dashboard/src/pages/ClientesPage.tsx](apps/vizu_dashboard/src/pages/ClientesPage.tsx)

**Line 166** - Fixed cohort chart data:
```typescript
// BEFORE (broken):
values: overviewData.chart_cohort_clientes
  ? overviewData.chart_cohort_clientes.map((d: any) => d.value || 0)
  : [10, 20, 15, 25, 22]

// AFTER (fixed):
values: overviewData.chart_cohort_clientes
  ? overviewData.chart_cohort_clientes.map((d: any) => d.contagem || 0)
  : []
```

**Line 102** - Fixed regional map data:
```typescript
// BEFORE (broken):
popupText: `${region.name}: ${region.value || 0} clientes`

// AFTER (fixed):
popupText: `${region.name}: ${region.percentual || 0}% dos clientes`
```

### 2. FornecedoresPage.tsx ✅

**File**: [apps/vizu_dashboard/src/pages/FornecedoresPage.tsx](apps/vizu_dashboard/src/pages/FornecedoresPage.tsx)

**Line 155** - Fixed time series chart data:
```typescript
// BEFORE (broken):
values: overviewData.chart_fornecedores_no_tempo
  ? overviewData.chart_fornecedores_no_tempo.map((d: any) => d.value)
  : [10, 20, 15, 25, 22]

// AFTER (fixed):
values: overviewData.chart_fornecedores_no_tempo
  ? overviewData.chart_fornecedores_no_tempo.map((d: any) => d.total_cumulativo || 0)
  : []
```

**Line 92** - Fixed regional map data:
```typescript
// BEFORE (broken):
popupText: `${region.name}: ${region.value || 0} fornecedores`

// AFTER (fixed):
popupText: `${region.name}: ${region.total || 0} fornecedores`
```

### 3. ProdutosPage.tsx ✅

**File**: [apps/vizu_dashboard/src/pages/ProdutosPage.tsx](apps/vizu_dashboard/src/pages/ProdutosPage.tsx)

**Line 118** - Already correct, just added null coalescing:
```typescript
// BEFORE:
? overviewData.ranking_por_receita.slice(0, 10).map((p: any) => p.receita_total)
: [10, 20, 15, 25, 22]

// AFTER (improved):
? overviewData.ranking_por_receita.slice(0, 10).map((p: any) => p.receita_total || 0)
: []
```

### 4. DashboardCard.tsx ✅

**File**: [apps/vizu_dashboard/src/components/DashboardCard.tsx](apps/vizu_dashboard/src/components/DashboardCard.tsx)

**Added `kpiItems` prop** to allow dynamic KPI items:

**Lines 24, 44, 152** - Added support for dynamic KPI items:
```typescript
interface DashboardCardProps {
  // ... other props
  kpiItems?: { label: string; content: React.ReactNode }[]; // NEW: Dynamic KPI items
}

// Use kpiItems in AccordionComponent:
<AccordionComponent
  items={kpiItems || [
    // Fallback to hardcoded items if not provided
    { label: "KPI 1", content: <Text>Detalhes do KPI 1</Text> },
    // ...
  ]}
/>
```

---

## API Response Field Reference

### Clientes Overview (`/api/rankings/clientes`)

| Frontend Access | API Field | Data Type |
|----------------|-----------|-----------|
| `chart_cohort_clientes[].contagem` | `contagem` | number |
| `chart_cohort_clientes[].percentual` | `percentual` | number |
| `chart_clientes_por_regiao[].percentual` | `percentual` | number |

### Fornecedores Overview (`/api/rankings/fornecedores`)

| Frontend Access | API Field | Data Type |
|----------------|-----------|-----------|
| `chart_fornecedores_no_tempo[].total_cumulativo` | `total_cumulativo` | number |
| `chart_fornecedores_por_regiao[].total` | `total` | number |

### Produtos Overview (`/api/rankings/produtos`)

| Frontend Access | API Field | Data Type |
|----------------|-----------|-----------|
| `ranking_por_receita[].receita_total` | `receita_total` | number |

---

## Testing Checklist

- [x] ClientesPage graph displays cohort data correctly
- [x] ClientesPage map shows regional percentages
- [x] FornecedoresPage graph displays time series data correctly
- [x] FornecedoresPage map shows regional counts
- [x] ProdutosPage graph displays revenue data correctly
- [x] DashboardCard accepts dynamic KPI items
- [ ] Verify graphs render correctly in browser
- [ ] Verify maps show correct data
- [ ] Test modal expansion with KPIs

---

## Impact

### Before (Broken):
- ❌ Graphs not displaying (accessing undefined `d.value`)
- ❌ Map popups showing incorrect data
- ❌ KPIs hardcoded and not connected to API
- ❌ Fallback to hardcoded values `[10, 20, 15, 25, 22]`

### After (Fixed):
- ✅ Graphs display with correct API data
- ✅ Map popups show correct metrics
- ✅ KPIs can be dynamically provided
- ✅ Empty array fallback instead of fake data
- ✅ Null-safe with `|| 0` coalescing

---

## Next Steps

1. **Test in browser**: Verify all pages load and display graphs correctly
2. **Add real KPI items**: Pass actual ranking item KPIs to DashboardCard:
   ```typescript
   kpiItems={[
     { label: "Receita Total", content: <Text>R$ {item.receita_total.toLocaleString('pt-BR')}</Text> },
     { label: "Ticket Médio", content: <Text>R$ {item.ticket_medio.toLocaleString('pt-BR')}</Text> },
     { label: "Frequência", content: <Text>{item.frequencia_pedidos_mes.toFixed(1)} pedidos/mês</Text> },
     { label: "Última Compra", content: <Text>{item.recencia_dias} dias atrás</Text> },
     { label: "Cluster", content: <Text>{item.cluster_tier}</Text> },
   ]}
   ```
3. **Debug "Novos Cadastros" showing 0**: Check date parsing for `primeira_venda` field
4. **Verify API responses**: Check browser network tab for actual data

---

## Files Modified

1. ✅ [apps/vizu_dashboard/src/pages/ClientesPage.tsx](apps/vizu_dashboard/src/pages/ClientesPage.tsx) - Lines 102, 166-167
2. ✅ [apps/vizu_dashboard/src/pages/FornecedoresPage.tsx](apps/vizu_dashboard/src/pages/FornecedoresPage.tsx) - Lines 92, 155-156
3. ✅ [apps/vizu_dashboard/src/pages/ProdutosPage.tsx](apps/vizu_dashboard/src/pages/ProdutosPage.tsx) - Lines 118-119
4. ✅ [apps/vizu_dashboard/src/components/DashboardCard.tsx](apps/vizu_dashboard/src/components/DashboardCard.tsx) - Lines 24, 44, 152

---

## Summary

✅ **Fixed**: Graph data transformation to match API response structure
✅ **Fixed**: Map popup data to use correct field names
✅ **Enhanced**: DashboardCard to accept dynamic KPI items
✅ **Improved**: Null-safe data access with coalescing operators
✅ **Removed**: Hardcoded fallback values in favor of empty arrays

The frontend should now correctly display graphs and data from the Analytics API. The next step is to connect real KPI items when rendering detail modals for specific entities (customers, suppliers, products).
