# Missing Columns - Root Cause Analysis

## Executive Summary

**Problem**: Charts are empty (`chart_clientes_por_regiao: Array(0)`, `chart_cohort_clientes: Array(0)`)

**Root Cause**: Source data is missing STATE/REGION columns entirely. These columns are required for generating regional distribution charts.

**Impact**:
- ✅ Rankings work (data from `analytics_gold_customers` table)
- ✅ Scorecards work (aggregated metrics)
- ❌ Regional charts empty (no state data)
- ❌ Cohort charts empty (reading from wrong source - should use in-memory calculation, not database)

---

## Data Quality Analysis

### What We Have ✅

From the logs:
```
Column names (10):
[
  'emitter_cnpj',           ✅ Supplier CNPJ
  'emitter_nome',           ✅ Supplier name
  'receiver_cpf_cnpj',      ✅ Customer CNPJ (100% populated)
  'data_transacao',         ✅ Transaction date
  'receiver_nome',          ✅ Customer name (98.2% populated)
  'valor_unitario',         ✅ Unit price
  'order_id',               ✅ Order ID
  'valor_total_emitter',    ✅ Total revenue
  'raw_product_description',✅ Product description
  'quantidade'              ✅ Quantity
]
```

**Data Quality**:
- Total rows: 72,952
- All columns > 98% populated
- Good coverage for core metrics

### What We're Missing ❌

**For Regional Charts**:
- `receiverstateuf` OR `receiver_estado` OR `receiver_state`
- `emitterstateuf` OR `emitter_estado` OR `emitter_state`

**Impact**: Cannot generate:
- `chart_clientes_por_regiao` (customer regional distribution)
- `chart_fornecedores_por_regiao` (supplier regional distribution)

---

## Why Charts Are Empty

### 1. chart_clientes_por_regiao (Regional Map)

**Code** (metric_service.py:414-432):
```python
state_col = None
for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:
    if col in self.df.columns:
        state_col = col
        break

if state_col and 'receiver_nome' in self.df.columns:
    # Generate regional chart
    df_clientes_regiao = self.df.groupby(state_col)['receiver_nome'].nunique()
    # ...
else:
    logger.warning("Missing state column for clientes_regiao; skipping")
    # df_clientes_regiao stays empty DataFrame
```

**Result**: `state_col = None` → Chart skipped → Empty array returned

### 2. chart_cohort_clientes (Tier Distribution)

**Expected behavior**: Should work because `cluster_tier` is calculated in aggregation

**Code** (metric_service.py:435-445):
```python
if 'cluster_tier' in df_clientes_agg.columns:
    df_cohort = df_clientes_agg.groupby('cluster_tier').size().reset_index(name='contagem')
    # ...
else:
    df_cohort = pd.DataFrame()
    logger.warning("Missing cluster_tier column; cohort chart will be empty")
```

**Issue**: The code checks for `cluster_tier` but we can see from logs:
```
Sample customer: ['nome', 'receita_total', ..., 'cluster_tier']  ✅ cluster_tier EXISTS
```

So `cluster_tier` **should** be available. This suggests the endpoint might be reading from the database instead of calculating in-memory.

---

## Architecture Issue: Database vs. In-Memory

### Current Behavior (Suspect)

Looking at the console output:
```javascript
ranking_por_cluster_vizu: [{
  id: 'af904530-af50-4d7e-b653-df5c7f7e1c77',          // ← Database UUID
  client_id: 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723',  // ← Database field
  customer_name: 'VISCOTECH...',                       // ← Database field
  customer_cpf_cnpj: null,
  total_orders: 72,
  // ...
}]
```

**The rankings have database fields (`id`, `client_id`, `customer_name`)** which don't exist in the in-memory dataframe aggregation.

### Hypothesis

There might be **TWO CODE PATHS**:

1. **Write path** (ingestion): metric_service calculates and writes to `analytics_gold_*` tables
2. **Read path** (API endpoint): Reads from `analytics_gold_*` tables instead of calculating

**If this is true**:
- Rankings come from database → Include all database fields
- Charts come from in-memory calculation → Empty because missing columns
- This creates inconsistency

### Need to Verify

Check if there's a separate endpoint or service that reads from `analytics_gold_customers` instead of using `metric_service.get_clientes_overview()`.

---

## Solutions

### Solution 1: Add State Columns to Source Data (Recommended)

**If BigQuery source has state data**, ensure column mapping captures it:

1. Check BigQuery table for state columns:
```sql
SELECT column_name
FROM `project.dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'invoices'
  AND column_name LIKE '%state%' OR column_name LIKE '%uf%' OR column_name LIKE '%estado%';
```

2. If found, add to canonical schema in `schema_matcher_service.py`:
```python
CANONICAL_SCHEMA = {
    # ... existing mappings
    "receiver_state": {
        "aliases": ["receiverstateuf", "receiver_estado", "receiver_uf", "cliente_estado", "customer_state"],
        "type": "string",
        "description": "Customer state/region (UF)"
    },
    "emitter_state": {
        "aliases": ["emitterstateuf", "emitter_estado", "emitter_uf", "fornecedor_estado", "supplier_state"],
        "type": "string",
        "description": "Supplier state/region (UF)"
    }
}
```

3. Re-run ingestion to capture state columns

### Solution 2: Fallback to Database Query for Charts

**If source data will never have state info**, modify metric_service to query a separate state mapping table or use external geocoding service.

### Solution 3: Remove Chart Components (Temporary)

If state data is not available and won't be added:
- Remove regional map cards from frontend
- Keep only rankings and cohort charts

---

## Additional Issue: customer_cpf_cnpj NULL in Database

**Observation**:
- Silver table: `receiver_cpf_cnpj: 100% populated, 1,680 unique values` ✅
- Gold table: `customer_cpf_cnpj: null` for all records ❌

**Root Cause**: The field name mismatch in postgres_repository.py

**File**: postgres_repository.py:496

**Current code**:
```python
"customer_cpf_cnpj": customer.get("receiver_cpf_cnpj"),
```

**Issue**: The aggregated dataframe uses `nome` as the grouping key, and `receiver_cpf_cnpj` is in the raw dataframe (`self.df`), not in the aggregated dataframe (`df_clientes_agg`).

**Fix needed**: Join or lookup `receiver_cpf_cnpj` from `self.df` based on customer name, or include it in the aggregation.

---

## Immediate Actions Required

### 1. Restart Analytics API (to see debug logs)

```bash
docker-compose restart analytics_api
```

### 2. Check Debug Logs

```bash
docker-compose logs -f analytics_api | grep -E "\[DEBUG\]|⚠️"
```

**Expected output**:
```
[DEBUG] State column search result: state_col=None, receiver_nome in columns: True
⚠️  Missing state column for clientes_regiao; skipping
[DEBUG] chart_clientes_por_regiao generated: 0 regions
```

### 3. Check BigQuery Source for State Columns

```sql
-- Run this in BigQuery console
SELECT
  column_name,
  data_type
FROM `your-project.your-dataset.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'invoices'
  AND (
    column_name LIKE '%state%'
    OR column_name LIKE '%uf%'
    OR column_name LIKE '%estado%'
    OR column_name LIKE '%region%'
  );
```

### 4. If State Columns Exist in BigQuery

Add them to the canonical schema and re-run ingestion.

### 5. If State Columns Don't Exist

**Options**:
A. Add state data to BigQuery from another source
B. Remove regional charts from UI
C. Use geocoding service to derive state from customer address (if available)

---

## Expected Behavior After Fix

### If State Columns Are Added

```javascript
{
  chart_clientes_por_regiao: [
    {name: 'SP', contagem: 450, percentual: 28.4},
    {name: 'RJ', contagem: 320, percentual: 20.2},
    {name: 'MG', contagem: 280, percentual: 17.7},
    // ...
  ],
  chart_cohort_clientes: [
    {name: 'A (Melhores)', contagem: 395, percentual: 25.0},
    {name: 'B', contagem: 474, percentual: 30.0},
    {name: 'C', contagem: 395, percentual: 25.0},
    {name: 'D (Piores)', contagem: 322, percentual: 20.0}
  ]
}
```

### If State Columns Cannot Be Added

Update frontend to hide regional map cards:
```typescript
{overviewData.chart_clientes_por_regiao?.length > 0 && (
  <DashboardCard
    title="Distribuição Geográfica de Clientes"
    // ... map component
  />
)}
```

---

## Data Quality Scorecard

| Metric | Status | Notes |
|--------|--------|-------|
| Core transaction data | ✅ Excellent | 72k rows, < 2% NULL |
| Customer identification | ✅ Good | receiver_nome 98.2% populated |
| Supplier identification | ✅ Excellent | emitter_nome 100% populated |
| CPF/CNPJ data | ✅ Good | receiver_cpf_cnpj 100% in silver |
| Regional data | ❌ Missing | No state columns mapped |
| Cluster/Tier data | ✅ Good | cluster_tier calculated correctly |

---

## Summary

✅ **Working**:
- Data ingestion and quality (72k rows)
- Aggregations (1,586 customers, 433 suppliers, 5,972 products)
- RFM clustering (cluster_tier calculated)
- Database writes (gold tables populated)
- Rankings (reading from gold tables)
- Core scorecards (ticket medio, frequencia)

❌ **Not Working**:
- Regional charts (missing state columns in source)
- customer_cpf_cnpj in gold table (lookup issue)
- Cohort chart (possible architecture issue - reading from DB instead of in-memory)

**Next Step**: Verify if BigQuery source has state columns, then either add mapping or remove chart components from UI.
