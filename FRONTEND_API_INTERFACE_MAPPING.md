# Frontend-API Interface Mapping

Complete analysis of frontend data requirements and how they map to Analytics API objects.

---

## 1. ClientesPage.tsx (Customers Page)

### Data Requirements

#### Overview Data (from `getClientes()`)
**Type Expected:** `ClientesOverviewResponse`

```typescript
interface ClientesOverviewResponse {
  // Scorecards
  scorecard_total_clientes: number;           // Total customers count
  scorecard_ticket_medio_geral: number;       // Average ticket across all customers
  scorecard_frequencia_media_geral: number;   // Average frequency (not displayed)
  scorecard_crescimento_percentual: number;   // Growth % (e.g., +15.2)

  // Rankings
  ranking_por_receita: Array<{
    nome: string;                             // Customer name
    receita_total: number;                    // Total revenue
    primeira_venda: string;                   // First purchase date (ISO timestamp)
    cluster_tier: string;                     // Tier: "A (Melhores)", "B", "C", "D (Piores)"
  }>;

  // Charts
  chart_cohort_clientes: Array<{
    name: string;                             // Tier name
    contagem: number;                         // Count of customers in tier
  }>;

  chart_clientes_por_regiao: Array<{
    name: string;                             // State/Region name (e.g., "SP", "RJ")
    percentual: number;                       // Percentage of customers in region
  }>;
}
```

**Usage in Component:**
- **Line 92:** `scorecard_total_clientes` → Display total customers
- **Line 132-134:** `scorecard_crescimento_percentual` → Display growth percentage in subtitle
- **Line 141:** `scorecard_total_clientes` → Big number display
- **Line 169:** `scorecard_ticket_medio_geral` → Scorecard value "Ticket Médio Geral"
- **Line 165-167:** `chart_cohort_clientes` → Graph data for Performance card
- **Line 86-89:** `ranking_por_receita` → Calculate new customers (last 30 days)
- **Line 112-117:** `ranking_por_receita` → ListCard items (top customers by revenue)
- **Line 98-104:** `chart_clientes_por_regiao` → Map markers for geographic distribution

#### Detail Data (from `getCliente(id)`)
**Type Expected:** `ClienteDetailResponse`

```typescript
interface ClienteDetailResponse {
  dados_cadastrais: {
    receiver_nome: string;                    // Customer name
    receiver_cpf_cnpj?: string;              // CPF/CNPJ
    receiver_telefone?: string;              // Phone
    receiver_cidade?: string;                // City
    receiver_estado?: string;                // State/UF
  };

  scorecards: {
    cluster_tier: string;                     // Tier (A/B/C/D)
  };

  rankings_internos?: {
    mix_de_produtos_por_receita?: Array<{
      nome: string;                           // Product name
      receita_total: number;                  // Revenue from this product
    }>;
  };
}
```

**Usage in Modal:**
- **Line 17:** `dados_cadastrais.receiver_nome` → Customer name
- **Line 18:** `dados_cadastrais.receiver_telefone` → Contact
- **Line 19:** `dados_cadastrais.receiver_cidade`, `receiver_estado` → Address
- **Line 20:** `dados_cadastrais.receiver_cnpj` → CNPJ
- **Line 64:** `scorecards.cluster_tier` → Display tier
- **Line 82-96:** `rankings_internos.mix_de_produtos_por_receita` → Top product by revenue

---

## 2. FornecedoresPage.tsx (Suppliers Page)

### Data Requirements

#### Overview Data (from `getFornecedores()`)
**Type Expected:** `FornecedoresOverviewResponse`

```typescript
interface FornecedoresOverviewResponse {
  // Scorecards
  scorecard_total_fornecedores: number;       // Total suppliers count
  scorecard_crescimento_percentual: number;   // Growth % (e.g., +8.5)

  // Rankings
  ranking_por_receita: Array<{
    nome: string;                             // Supplier name
    receita_total: number;                    // Total revenue
    primeira_venda: string;                   // First purchase date (ISO timestamp)
    cluster_tier: string;                     // Tier
  }>;

  // Charts
  chart_fornecedores_no_tempo: Array<{
    period: string;                           // Period (e.g., "2025-10")
    total_cumulativo: number;                 // Cumulative total suppliers
  }>;

  chart_fornecedores_por_regiao: Array<{
    name: string;                             // State/Region name
    total: number;                            // Number of suppliers
  }>;
}
```

**Usage in Component:**
- **Line 131:** `scorecard_total_fornecedores` → Display total suppliers
- **Line 122-124:** `scorecard_crescimento_percentual` → Display growth in subtitle
- **Line 74-77:** `ranking_por_receita` → Calculate total revenue
- **Line 82-85:** `ranking_por_receita` → Calculate new suppliers (last 30 days)
- **Line 154-156:** `chart_fornecedores_no_tempo[].total_cumulativo` → Graph data
- **Line 158:** Calculated `totalRevenue` → Scorecard "Total Vendido"
- **Line 102-107:** `ranking_por_receita` → ListCard items
- **Line 88-94:** `chart_fornecedores_por_regiao` → Map markers

#### Detail Data (from `getFornecedor(id)`)
**Type Expected:** `FornecedorDetailResponse`

```typescript
interface FornecedorDetailResponse {
  dados_cadastrais: {
    emitter_nome: string;                     // Supplier name
    emitter_cnpj?: string;                   // CNPJ
    emitter_telefone?: string;               // Phone
    emitter_cidade?: string;                 // City
    emitter_estado?: string;                 // State/UF
  };

  rankings_internos?: {
    clientes_por_receita?: Array<{
      nome: string;                           // Customer name
      receita_total: number;                  // Revenue from customer
    }>;

    produtos_por_receita?: Array<{
      nome: string;                           // Product name
      receita_total: number;                  // Revenue from product
    }>;
  };
}
```

**Usage in Modal:**
- **Line 17:** `dados_cadastrais.emitter_nome` → Supplier name
- **Line 18:** `dados_cadastrais.emitter_telefone` → Contact
- **Line 19:** `dados_cadastrais.emitter_cidade`, `emitter_estado` → Address
- **Line 20:** `dados_cadastrais.emitter_cnpj` → CNPJ
- **Line 66-74:** `rankings_internos.clientes_por_receita` → Top customer
- **Line 88-101:** `rankings_internos.produtos_por_receita` → Top product

---

## 3. GraphComponent.tsx

### Data Requirements

```typescript
interface GraphComponentProps {
  data: Array<{
    name: string;                             // X-axis label (e.g., period name)
    [dataKey: string]: number | string;      // Dynamic key for Y-axis value
  }>;
  dataKey: string;                            // Key to use for line values
  lineColor?: string;                         // Line color (default: #FFA500)
}
```

**Usage:**
- **Line 18:** Renders LineChart with provided data
- **Line 21:** X-axis displays `name` field (uppercased)
- **Line 38:** Line displays values from `dataKey` field

**Expected Data Format:**
```javascript
// Example for time series
[
  { name: "2025-10", total: 45 },
  { name: "2025-11", total: 52 },
  { name: "2025-12", total: 58 }
]
```

---

## 4. GraphCarousel.tsx

### Data Requirements

```typescript
interface GraphCarouselProps {
  graphs: Array<{
    data: Array<{
      name: string;                           // X-axis label
      [key: string]: number | string;        // Y-axis values
    }>;
    dataKey: string;                          // Key for line values
    lineColor?: string;                       // Line color
    title: string;                            // Graph title displayed above chart
  }>;
}
```

**Usage:**
- **Line 16:** Manages current graph index with carousel
- **Line 34:** Displays current graph title
- **Line 36-40:** Renders GraphComponent with current graph data
- **Line 44-54:** Navigation buttons (prev/next)

**Expected Format:**
```javascript
[
  {
    title: "Fornecedores no Tempo",
    data: [{ name: "out", total: 3 }, { name: "nov", total: 3 }],
    dataKey: "total",
    lineColor: "#FFA500"
  },
  {
    title: "Clientes no Tempo",
    data: [{ name: "out", total: 8 }, { name: "nov", total: 10 }],
    dataKey: "total",
    lineColor: "#00FF00"
  }
]
```

---

## 5. ProdutoDetailsModal.tsx

### Data Requirements

**Type Expected:** `ProdutoDetailResponse`

```typescript
interface ProdutoDetailResponse {
  nome_produto: string;                       // Product name

  scorecards: {
    receita_total: number;                    // Total revenue
    quantidade_total: number;                 // Total quantity sold
    ticket_medio: number;                     // Average ticket
  };

  charts?: {
    segmentos_de_clientes?: Array<{
      name: string;                           // Segment name
      percentual: number;                     // Percentage
    }>;
  };

  rankings_internos?: {
    clientes_por_receita?: Array<{
      nome: string;                           // Customer name
      receita_total: number;                  // Revenue
    }>;
  };
}
```

**Usage in Modal:**
- **Line 16:** `nome_produto` → Product name
- **Line 35-37:** `nome_produto` → Title display
- **Line 45:** `scorecards.receita_total` → Revenue display
- **Line 51:** `scorecards.quantidade_total` → Quantity display
- **Line 57:** `scorecards.ticket_medio` → Ticket medio display
- **Line 73-87:** `charts.segmentos_de_clientes` → Customer segments chart
- **Line 91-105:** `rankings_internos.clientes_por_receita` → Top customer

---

## 6. Common Patterns Across All Pages

### Scorecard Pattern
```typescript
{
  scorecardValue: string | number;            // Main value to display
  scorecardLabel: string;                     // Label below value
}
```

### ListCard Items Pattern
```typescript
{
  id: string;                                 // Unique identifier (used for detail fetch)
  title: string;                              // Main title
  description: string;                        // Subtitle (usually revenue)
  status: string;                             // Status badge (cluster_tier)
}
```

### Map Markers Pattern
```typescript
{
  position: [number, number];                 // [latitude, longitude]
  popupText: string;                          // Text shown on marker click
}
```

### Chart Data Pattern
```typescript
{
  name: string;                               // X-axis label or category name
  contagem?: number;                          // Count
  total?: number;                             // Total value
  percentual?: number;                        // Percentage
  total_cumulativo?: number;                  // Cumulative total
}
```

---

## Issues Identified

### 1. Missing Time Series in FornecedoresPage ✅ FIXED
**Location:** Line 154-156
**Issue:** Uses `chart_fornecedores_no_tempo[].total_cumulativo`
**Problem:** API was returning `total` (monthly count), not `total_cumulativo` (cumulative sum)

**Fix Applied:** Updated rankings.py endpoint (lines 67-76) to calculate cumulative sum:
```python
# Calculate cumulative sum for frontend (expects total_cumulativo)
cumulative_sum = 0
chart_fornecedores_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_fornecedores_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

**Result:** API now returns both `total` (monthly) and `total_cumulativo` (cumulative) fields

### 2. New Customers Calculation
**Location:** ClientesPage.tsx lines 86-89
**Issue:** Frontend calculates new customers by filtering `primeira_venda < 30 days ago`
**Problem:** This should be a backend calculation

**Recommendation:** Add to API:
```typescript
scorecard_novos_clientes_30d: number;  // Calculated by API
```

### 3. Total Revenue Calculation
**Location:** FornecedoresPage.tsx lines 74-77
**Issue:** Frontend sums all `receita_total` from ranking
**Problem:** This should be in API scorecards

**Recommendation:** Add to API:
```typescript
scorecard_receita_total: number;  // Total revenue across all suppliers
```

### 4. Growth Calculation
**Location:** ClientesPage.tsx lines 93-95
**Issue:** Frontend calculates growth percentage manually
**Problem:** API already has `scorecard_crescimento_percentual` but frontend recalculates it differently

**Fix:** Use API value directly (already correct in FornecedoresPage)

---

## API Objects Needed (Summary)

### ClientesOverviewResponse ✅
- scorecard_total_clientes ✅
- scorecard_ticket_medio_geral ✅
- scorecard_crescimento_percentual ✅
- ranking_por_receita[] ✅
- chart_cohort_clientes[] ✅
- chart_clientes_por_regiao[] ✅

**Missing:**
- ❌ `chart_clientes_no_tempo` (for GraphCarousel - should exist in time series)

### FornecedoresOverviewResponse ✅
- scorecard_total_fornecedores ✅
- scorecard_crescimento_percentual ✅
- ranking_por_receita[] ✅
- chart_fornecedores_por_regiao[] ✅

**Missing:**
- ⚠️ `chart_fornecedores_no_tempo` exists but frontend expects `total_cumulativo` field (API has `total`)

### ClienteDetailResponse ✅
- dados_cadastrais ✅
- scorecards.cluster_tier ✅
- rankings_internos.mix_de_produtos_por_receita ✅

### FornecedorDetailResponse ✅
- dados_cadastrais ✅
- rankings_internos.clientes_por_receita ✅
- rankings_internos.produtos_por_receita ✅

### ProdutoDetailResponse ✅
- nome_produto ✅
- scorecards ✅
- charts.segmentos_de_clientes ❓ (not sure if API provides this)
- rankings_internos.clientes_por_receita ✅

---

## Next Steps

1. **Verify time series data structure** - Ensure API returns correct field names
2. **Add missing chart data** - clientes_no_tempo for ClientesPage carousel
3. **Fix field name mismatch** - `total` vs `total_cumulativo` in fornecedores_no_tempo
4. **Consider adding backend calculations** - new customers count, total revenue scorecard
5. **Verify segmentos_de_clientes** - Check if this exists in produtos endpoint
