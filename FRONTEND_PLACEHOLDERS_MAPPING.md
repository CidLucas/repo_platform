# Frontend Placeholders & Hardcoded Data - Mapping for Dynamic Implementation

**Date**: January 14, 2026
**Target**: `apps/vizu_dashboard/src`

---

## 🔴 CRITICAL: Hardcoded Numbers (Must Replace)

### 1. **PedidosPage.tsx** - Lines 104, 108, 112
**Status**: ❌ Hardcoded
**Location**: Header stats section
**Current Code**:
```tsx
<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">250</Text>  // Total Pedidos
<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">200</Text>  // Pedidos Concluídos
<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">50</Text>   // Pedidos Pendentes
```

**Should Use**:
```tsx
// Replace with data from orderMetrics or overviewData
<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
  {orderMetrics?.total || 0}
</Text>

// For completed/pending, use by_status field
<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
  {orderMetrics?.by_status?.completed || 0}
</Text>

<Text as="h2" textStyle="pageBigNumberSmall" mt="4px">
  {orderMetrics?.by_status?.pending || 0}
</Text>
```

**API Field**: `orderMetrics.total`, `orderMetrics.by_status`

---

## 🟡 NON-FUNCTIONAL: Select Dropdowns (No onChange handlers)

### 2. **Period & Metrics Selects** - Multiple Pages
**Status**: ⚠️ UI Only (Not connected to functionality)
**Affected Pages**:
- PedidosPage.tsx (lines 115-125)
- ClientesPage.tsx (lines 153-165)
- FornecedoresPage.tsx (lines 134-145)
- ProdutosPage.tsx (lines 95-106)

**Current Code**:
```tsx
<Select placeholder="Período" width="150px" bg="white" color="gray.800">
  <option value="semana">Última semana</option>
  <option value="mes">Último mês</option>
  <option value="tri">Último tri</option>
  <option value="total">Total</option>
</Select>

<Select placeholder="Métricas" width="150px" bg="white" color="gray.800">
  <option value="receita">Receita</option>
  <option value="quantidade">Quantidade</option>
  <option value="ticket_medio">Ticket Médio</option>
</Select>
```

**Needs**:
1. **State management** for selected period/metric
2. **onChange handlers** to update data
3. **API integration** to fetch filtered data
4. **Loading states** during data refresh

**Recommended Implementation**:
```tsx
const [selectedPeriod, setSelectedPeriod] = useState<PeriodType>('month');
const [selectedMetric, setSelectedMetric] = useState('receita');

const handlePeriodChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
  const period = e.target.value as PeriodType;
  setSelectedPeriod(period);
  // Refetch indicators with new period
  await refetchIndicators({ period });
};

<Select
  value={selectedPeriod}
  onChange={handlePeriodChange}
  placeholder="Período"
  width="150px"
  bg="white"
  color="gray.800"
>
  <option value="week">Última semana</option>
  <option value="month">Último mês</option>
  <option value="quarter">Último tri</option>
  <option value="year">Total</option>
</Select>
```

**Note**: Period values should match API's PeriodType: `"today" | "yesterday" | "week" | "month" | "quarter" | "year"`

---

## 🟢 PLACEHOLDER ROUTES (Redirect to HomePage)

### 3. **Dashboard Routes** - dashboardRoutes.tsx (lines 70-85)
**Status**: ⚠️ Temporary redirects
**Location**: `src/routes/dashboardRoutes.tsx`

**Current Placeholder Routes**:
```tsx
// Lines 70-85
{
  path: "/dashboard/orders",
  element: <HomePage />, // Placeholder - redirect to home for now
},
{
  path: "/dashboard/orders/new",
  element: <HomePage />, // Placeholder - redirect to home for now
},
{
  path: "/dashboard/goals",
  element: <HomePage />, // Placeholder - redirect to home for now
},
{
  path: "/dashboard/goals/new",
  element: <HomePage />, // Placeholder - redirect to home for now
},
{
  path: "/dashboard/financial",
  element: <HomePage />, // Placeholder - redirect to home for now
},
```

**Needed Pages**:
1. **OrdersListPage** - Full orders management (similar to PedidosPage but with more CRUD)
2. **OrderFormPage** - Create/edit orders
3. **GoalsPage** - Goals/targets management
4. **GoalFormPage** - Create/edit goals
5. **FinancialPage** - Financial analytics dashboard

**Priority**: Medium (these are menu items that currently don't work)

---

## 📍 GEOGRAPHIC FALLBACKS

### 4. **Map Center Coordinates** - Multiple Pages
**Status**: ✅ Has fallback, but could be smarter
**Affected Pages**:
- ClientesPage.tsx (line 128)
- FornecedoresPage.tsx (line 99)
- PedidosPage.tsx (line 274)

**Current Code**:
```tsx
const mapCenter = mapMarkers.length > 0
  ? mapMarkers[0].position
  : [-23.55052, -46.633308] as [number, number]; // São Paulo fallback
```

**Enhancement Suggestion**:
```tsx
// Use user's business location from profile or most common region
const mapCenter = mapMarkers.length > 0
  ? mapMarkers[0].position
  : profile?.business_location || DEFAULT_BRAZIL_CENTER;
```

---

## 📊 MODAL CONTENT PLACEHOLDERS

### 5. **DashboardCard Modal Content** - Multiple Pages
**Status**: ⚠️ Generic placeholder text
**Affected**: All pages with DashboardCard components

**Current Pattern**:
```tsx
modalContent={<Text>Detalhes do gráfico de vendas</Text>}
modalContent={<Text>Detalhes dos novos clientes</Text>}
modalContent={<Text>Métricas detalhadas de clientes no período de {customerMetrics?.period || 'mês'}</Text>}
```

**Enhancement Needed**:
- Add more detailed information in modals
- Show data tables or additional charts
- Add download/export functionality
- Add period comparison visuals

**Example Enhanced Modal**:
```tsx
modalContent={
  <Box>
    <VStack align="stretch" spacing={4}>
      <Text fontSize="lg" fontWeight="bold">
        Análise Detalhada - {customerMetrics?.period}
      </Text>

      {/* Data table */}
      <Table>
        <Thead>
          <Tr>
            <Th>Métrica</Th>
            <Th>Valor</Th>
            <Th>Variação</Th>
          </Tr>
        </Thead>
        <Tbody>
          {/* Dynamic rows */}
        </Tbody>
      </Table>

      {/* Export button */}
      <Button leftIcon={<DownloadIcon />}>
        Exportar Dados
      </Button>
    </VStack>
  </Box>
}
```

---

## 🎨 UI TEXT PLACEHOLDERS

### 6. **Static Description Text** - PedidosPage.tsx (line 257)
**Status**: ⚠️ Generic text
**Location**: Histórico de Pedidos card

**Current**:
```tsx
mainText="Histórico completo de todos os pedidos."
```

**Should Be Dynamic**:
```tsx
mainText={`${overviewData?.ultimos_pedidos?.length || 0} pedidos recentes disponíveis para consulta.`}
```

---

## 🔄 DATA REFRESH INDICATORS

### 7. **Missing Data Refresh Timestamps**
**Status**: ❌ Not implemented
**All pages should show**:
- Last update timestamp
- Auto-refresh interval
- Manual refresh button

**Implementation Needed**:
```tsx
// In each page component
const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

// In data fetch success
setLastUpdate(new Date());

// In UI
<Flex justify="space-between" align="center" mb={4}>
  <Text fontSize="sm" color="gray.600">
    Última atualização: {lastUpdate.toLocaleTimeString('pt-BR')}
  </Text>
  <IconButton
    icon={<RepeatIcon />}
    aria-label="Atualizar dados"
    size="sm"
    onClick={refetchData}
    isLoading={loading}
  />
</Flex>
```

---

## 📈 COMPARISON DATA (Not Displayed)

### 8. **Comparison Data from API** - All Indicator Pages
**Status**: ❌ Fetched but not displayed
**API Returns**: `comparisons: { vs_7_days, vs_30_days, vs_90_days, trend }`

**Current**: Indicators are fetched with `include_comparisons: false`

**Enhancement**:
```tsx
// In API calls, enable comparisons
const metricsResponse = await getCustomerIndicators('month', true); // include_comparisons

// Display in KPI cards
{customerMetrics.comparisons && (
  <HStack spacing={2} mt={2}>
    <Badge colorScheme={customerMetrics.comparisons.trend === 'up' ? 'green' : 'red'}>
      {customerMetrics.comparisons.vs_30_days > 0 ? '↑' : '↓'}
      {Math.abs(customerMetrics.comparisons.vs_30_days)}% vs 30 dias
    </Badge>
    <Text fontSize="xs" color="gray.500">
      Tendência: {customerMetrics.comparisons.trend}
    </Text>
  </HStack>
)}
```

---

## 🔍 SEARCH & FILTER FUNCTIONALITY

### 9. **List Pages Missing Filters** - All ListPage components
**Status**: ❌ Not implemented
**Affected**:
- ClientesListPage.tsx
- FornecedoresListPage.tsx
- ProdutosListPage.tsx

**Needed Features**:
1. Search bar to filter by name
2. Column sorting (by revenue, date, etc.)
3. Pagination controls
4. Export to CSV functionality

**Example Implementation**:
```tsx
const [searchTerm, setSearchTerm] = useState('');
const [sortBy, setSortBy] = useState<'receita_total' | 'nome'>('receita_total');
const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

const filteredData = useMemo(() => {
  return data
    .filter(item =>
      item.nome.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      const multiplier = sortOrder === 'asc' ? 1 : -1;
      return (a[sortBy] > b[sortBy] ? 1 : -1) * multiplier;
    });
}, [data, searchTerm, sortBy, sortOrder]);

// In UI
<InputGroup mb={4}>
  <InputLeftElement>
    <SearchIcon />
  </InputLeftElement>
  <Input
    placeholder="Buscar..."
    value={searchTerm}
    onChange={(e) => setSearchTerm(e.target.value)}
  />
</InputGroup>
```

---

## 📱 RESPONSIVE IMPROVEMENTS

### 10. **Mobile View Optimizations**
**Status**: ⚠️ Partially responsive
**Issues**:
- Select dropdowns might overflow on small screens
- Table columns not optimized for mobile
- Dashboard cards could stack better

**Enhancements Needed**:
```tsx
// Use responsive values more extensively
<Select
  width={{ base: "100%", md: "150px" }}
  mb={{ base: 2, md: 0 }}
>
  {/* options */}
</Select>

// Hide certain columns on mobile
<Td display={{ base: "none", md: "table-cell" }}>
  {/* Less critical data */}
</Td>

// Horizontal scroll for tables on mobile
<Box overflowX="auto">
  <Table minW="600px">
    {/* table content */}
  </Table>
</Box>
```

---

## 🎯 PRIORITY SUMMARY

### High Priority (Must Fix):
1. ✅ **PedidosPage hardcoded numbers** (lines 104, 108, 112)
2. ✅ **Period/Metrics Select onChange handlers** (all pages)
3. ✅ **Comparison data display** (enable and show)

### Medium Priority (Should Add):
4. 🔄 **Data refresh indicators** (timestamps + buttons)
5. 🔄 **Placeholder routes implementation** (orders, goals, financial pages)
6. 🔄 **Search & filter on list pages**

### Low Priority (Nice to Have):
7. 📈 **Enhanced modal content** (more details, tables, charts)
8. 📱 **Mobile optimizations**
9. 🗺️ **Smarter map center based on user location**

---

## 📝 IMPLEMENTATION CHECKLIST

### Phase 1: Fix Hardcoded Data ✅
- [ ] Replace hardcoded numbers in PedidosPage with orderMetrics data
- [ ] Add state management for period/metrics selects
- [ ] Implement onChange handlers for filters
- [ ] Connect selects to API refetch logic

### Phase 2: Enable Comparisons 📊
- [ ] Set `include_comparisons: true` in all indicator API calls
- [ ] Display comparison badges in KPI cards
- [ ] Add trend indicators (↑↓) with colors

### Phase 3: Add Interactivity 🎮
- [ ] Add refresh buttons with loading states
- [ ] Add last update timestamps
- [ ] Implement search on list pages
- [ ] Add column sorting on tables
- [ ] Add pagination controls

### Phase 4: New Pages 🆕
- [ ] Create OrdersListPage (full CRUD)
- [ ] Create GoalsPage
- [ ] Create FinancialPage
- [ ] Update routes to point to new pages

### Phase 5: Enhanced UX ✨
- [ ] Improve modal content (detailed tables)
- [ ] Add export functionality
- [ ] Optimize mobile responsiveness
- [ ] Add loading skeletons
- [ ] Add error boundaries

---

## 🔗 API Integration Notes

### Available Indicators Endpoints:
```typescript
// Individual metric endpoints
GET /api/indicators/customers?period={period}&include_comparisons=true
GET /api/indicators/products?period={period}&include_comparisons=true
GET /api/indicators/orders?period={period}&include_comparisons=true

// Combined endpoint
POST /api/indicators
{
  "period": "month",
  "metrics": ["orders", "products", "customers"],
  "include_comparisons": true
}
```

### Period Types (use these values):
- `"today"` - Current day
- `"yesterday"` - Previous day
- `"week"` - Last 7 days
- `"month"` - Last 30 days
- `"quarter"` - Last 90 days
- `"year"` - Last 365 days

---

## ⚡ Quick Wins (Can implement now):

1. **Fix PedidosPage hardcoded numbers** (5 min)
2. **Enable comparisons in API calls** (10 min)
3. **Add refresh timestamps** (15 min)
4. **Add loading states on refresh** (10 min)

**Total**: ~40 minutes for immediate improvements! 🚀
