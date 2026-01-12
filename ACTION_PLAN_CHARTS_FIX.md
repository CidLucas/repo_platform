# Action Plan: Fix Empty Charts

## Problem Statement

Charts showing as empty arrays:
- `chart_clientes_por_regiao: Array(0)` ❌
- `chart_cohort_clientes: Array(0)` ❌
- `chart_fornecedores_por_regiao: Array(0)` ❌
- `chart_fornecedores_no_tempo: ?` (need to check)

## Root Cause

**State/Region columns are NOT mapped** from BigQuery source to the silver layer.

Current mapped columns (only 10):
```
emitter_cnpj, emitter_nome, receiver_cpf_cnpj, data_transacao, receiver_nome,
valor_unitario, order_id, valor_total_emitter, raw_product_description, quantidade
```

**Missing for charts**:
- `receiverstateuf` / `receiver_estado` / `receiver_state`
- `emitterstateuf` / `emitter_estado` / `emitter_state`

Data loss: 88.1% (74 of 84 columns unmapped)

---

## Step-by-Step Action Plan

### Phase 1: Investigate BigQuery Source (5 minutes)

**Objective**: Determine if state columns exist in the source data

**Action**:
```sql
-- Run in BigQuery console
SELECT
  column_name,
  data_type,
  is_nullable
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'maua_materials'
  AND (
    column_name LIKE '%state%'
    OR column_name LIKE '%uf%'
    OR column_name LIKE '%estado%'
    OR column_name LIKE '%region%'
    OR column_name LIKE '%endereco%'
    OR column_name LIKE '%cidade%'
  )
ORDER BY column_name;
```

**Expected outcomes**:

#### A. State columns FOUND ✅
Example result:
```
| column_name                          | data_type | is_nullable |
|--------------------------------------|-----------|-------------|
| receiverstateuf_legaloperator        | STRING    | YES         |
| emitterstateuf_naturaloperator       | STRING    | YES         |
```

**Next**: Go to Phase 2 (Add column mapping)

#### B. State columns NOT FOUND ❌
No columns with state/uf/estado in names.

**Next**: Go to Phase 3 (Alternative solutions)

---

### Phase 2: Add State Column Mapping (15 minutes)

**Only if Phase 1 found state columns in BigQuery**

#### 2A. Add State Columns to Canonical Schema

**File**: `services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py`

**Find the CANONICAL_SCHEMA dictionary** (around line 50-150) and add:

```python
CANONICAL_SCHEMA = {
    # ... existing entries ...

    # Customer/Receiver State
    "receiver_state": {
        "aliases": [
            "receiverstateuf",
            "receiver_estado",
            "receiver_uf",
            "receiver_state",
            "cliente_estado",
            "customer_state",
            "receiverstateuf_legaloperator",  # Add actual BigQuery column name here
        ],
        "type": "string",
        "description": "Customer/Receiver state or region (UF code like SP, RJ, MG)"
    },

    # Supplier/Emitter State
    "emitter_state": {
        "aliases": [
            "emitterstateuf",
            "emitter_estado",
            "emitter_uf",
            "emitter_state",
            "fornecedor_estado",
            "supplier_state",
            "emitterstateuf_naturaloperator",  # Add actual BigQuery column name here
        ],
        "type": "string",
        "description": "Supplier/Emitter state or region (UF code like SP, RJ, MG)"
    },
}
```

**IMPORTANT**: Replace the example BigQuery column names with the actual names found in Phase 1.

#### 2B. Update metric_service.py to Use New Column Names

**File**: `services/analytics_api/src/analytics_api/services/metric_service.py`

**Line 414** - Update search list for clientes:
```python
# BEFORE:
for col in ['receiverstateuf', 'receiver_estado', 'receiver_state']:

# AFTER (add new canonical name):
for col in ['receiver_state', 'receiverstateuf', 'receiver_estado', 'receiver_state']:
```

**Line 357** - Update search list for fornecedores:
```python
# BEFORE:
for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:

# AFTER (add new canonical name):
for col in ['emitter_state', 'emitterstateuf', 'emitter_estado', 'emitter_state']:
```

#### 2C. Re-run Data Ingestion

```bash
# Restart data_ingestion_api to pick up schema changes
docker-compose restart data_ingestion_api

# Trigger new ingestion
curl -X POST http://localhost:8002/etl/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $YOUR_TOKEN"
```

#### 2D. Verify New Columns Are Mapped

Check logs:
```bash
docker-compose logs data_ingestion_api | grep "✓ Matched"
```

Expected output should show **12 columns** instead of 10:
```
✓ Matched: 12 columns
  ✓ receiver_state → receiverstateuf_legaloperator
  ✓ emitter_state → emitterstateuf_naturaloperator
```

#### 2E. Verify Charts Populate

After ingestion completes:
1. Refresh frontend
2. Check console: `chart_clientes_por_regiao` should have data
3. Verify regional map displays

---

### Phase 3: Alternative Solutions (if no state columns)

**Only if Phase 1 found NO state columns in BigQuery**

#### Option A: Derive State from Existing Data

If BigQuery has:
- City names (`receivercity_legaloperator`)
- Full addresses (`receiveraddress_legaloperator`)
- ZIP codes (`receiverzip_legaloperator`)

We can create a lookup table to map these to states.

**Implementation**:
1. Create `state_lookup` table in Supabase
2. Add lookup logic in metric_service.py
3. This requires significant development time

#### Option B: Remove Chart Components from UI

**Fastest solution** if state data will never be available.

**Files to modify**:

1. **ClientesPage.tsx** - Hide regional map card:
```typescript
{/* Only show if data exists */}
{overviewData.chart_clientes_por_regiao && overviewData.chart_clientes_por_regiao.length > 0 && (
  <DashboardCard
    title="Distribuição Geográfica de Clientes"
    // ... existing props
  />
)}
```

2. **FornecedoresPage.tsx** - Hide regional map card:
```typescript
{overviewData.chart_fornecedores_por_regiao && overviewData.chart_fornecedores_por_regiao.length > 0 && (
  <DashboardCard
    title="Distribuição Geográfica"
    // ... existing props
  />
)}
```

**Pros**: Immediate fix, no backend changes needed
**Cons**: Loses regional insights feature

#### Option C: Mock Data for Demo

If this is for demonstration purposes only:

Add fallback mock data in the frontend:
```typescript
const mockRegionalData = [
  {name: 'SP', percentual: 35.5},
  {name: 'RJ', percentual: 22.3},
  {name: 'MG', percentual: 18.2},
  // ...
];

// In component:
chart_clientes_por_regiao: overviewData.chart_clientes_por_regiao?.length > 0
  ? overviewData.chart_clientes_por_regiao
  : mockRegionalData
```

---

### Phase 4: Fix customer_cpf_cnpj NULL Issue (10 minutes)

**Separate issue**: customer_cpf_cnpj is null in gold table even though it's populated in silver.

**Root cause**: Aggregation doesn't include CNPJ lookup.

**File**: `services/analytics_api/src/analytics_api/services/metric_service.py`

**Line ~130** in `_get_aggregated_metrics_by_dimension()`:

**Add CNPJ to aggregation**:
```python
agg_ops = {}

# EXISTING aggregations...
if 'receiver_nome' in df.columns:
    agg_ops['nome'] = ('receiver_nome', 'first')  # Existing

# ADD THIS:
if 'receiver_cpf_cnpj' in df.columns:
    agg_ops['receiver_cpf_cnpj'] = ('receiver_cpf_cnpj', 'first')

# Continue with rest of aggregations...
```

**Also need to update write operation**:

**File**: `services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

**Line 496**:
```python
# BEFORE:
"customer_cpf_cnpj": customer.get("receiver_cpf_cnpj"),

# AFTER:
"customer_cpf_cnpj": customer.get("receiver_cpf_cnpj"),  # This will now work because it's in the aggregated dataframe
```

---

## Testing Checklist

After implementing fixes:

### Backend
- [ ] Schema matcher logs show new state columns mapped
- [ ] Silver table query shows state columns populated
- [ ] Gold tables have state data
- [ ] Analytics API debug logs show chart generation

### Frontend
- [ ] `chart_clientes_por_regiao` array has items
- [ ] `chart_cohort_clientes` array has 4 items (tiers)
- [ ] Regional map displays markers
- [ ] Cohort graph displays bars
- [ ] customer_cpf_cnpj shows values (not null)

---

## Quick Decision Matrix

| Scenario | Action | Time | Outcome |
|----------|--------|------|---------|
| BigQuery HAS state columns | Phase 2 | 15 min | ✅ Full functionality |
| BigQuery DOESN'T have state | Option B (hide) | 5 min | ⚠️ Reduced features |
| BigQuery HAS city/address | Option A (lookup) | 2-4 hours | ✅ Full functionality |
| Just need demo to work | Option C (mock) | 10 min | ✅ Demo looks good |

---

## Priority Order

1. **CRITICAL**: Run Phase 1 (investigate BigQuery) - This determines everything else
2. **HIGH**: Fix customer_cpf_cnpj (Phase 4) - Quick win, improves data quality
3. **DEPENDS**: Either Phase 2 or Phase 3 based on Phase 1 results

---

## Expected Timeline

**Best case** (state columns exist in BigQuery):
- Phase 1: 5 minutes
- Phase 2: 15 minutes
- Phase 4: 10 minutes
- **Total: 30 minutes**

**Worst case** (no state columns available):
- Phase 1: 5 minutes
- Phase 3 Option B: 5 minutes
- Phase 4: 10 minutes
- **Total: 20 minutes**

---

## Next Immediate Step

**RUN THIS SQL QUERY IN BIGQUERY NOW**:

```sql
SELECT column_name, data_type
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'maua_materials'
  AND (
    column_name LIKE '%state%'
    OR column_name LIKE '%uf%'
    OR column_name LIKE '%estado%'
  )
ORDER BY column_name;
```

**Share the results** and we'll proceed with the appropriate phase!
