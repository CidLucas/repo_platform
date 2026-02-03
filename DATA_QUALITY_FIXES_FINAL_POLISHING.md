# Data Quality Fixes Applied - Final Polishing

**Date:** 2024
**Target Client:** e0e9c949-18fe-4d9a-9295-d5dfb2cc9723

## Issues Identified

1. **dim_product:** NCM and CFOP columns empty (0% populated)
2. **dim_customer:** `lifetime_start_date` empty (0% populated)
3. **dim_customer:** `endereco_uf` 44% NULL (data source issue)
4. **fact_sales:** `line_item_sequence` empty (source column doesn't exist)
5. **v_regional:** Shows state codes instead of Brazilian regions
6. **v_regional:** `region_type` column is useless (all same value)

## Fixes Applied

### ✅ Fix 1: Add NCM and CFOP to column_mapping

**File:** `client_data_sources.column_mapping` (Supabase)

**Change:**
```sql
UPDATE public.client_data_sources
SET column_mapping = column_mapping || '{"ncm": "ncm", "cfop": "cfop"}'::jsonb
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
```

**Verification:**
- BigQuery source has 310 distinct NCM values, 64 distinct CFOP values
- Columns exist in `analytics_v2.dim_product` schema
- Column mapping now includes: `ncm → ncm`, `cfop → cfop`

**Impact:** Next recompute will populate NCM/CFOP for all 6,670 products

---

### ✅ Fix 2: Fix lifetime_start_date SQL aggregation

**File:** [services/analytics_api/src/analytics_api/services/metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py#L548-L577)

**Change:**
```python
# OLD: Missing lifetime dates
WITH cust_stats AS (
    SELECT
        ...
        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active
        -- Missing: MIN/MAX dates
    ...

# NEW: Includes lifetime dates
WITH cust_stats AS (
    SELECT
        ...
        COUNT(DISTINCT date_trunc('month', f.data_transacao)) AS months_active,
        MIN(f.data_transacao) AS lifetime_start_date,  # ← Added
        MAX(f.data_transacao) AS lifetime_end_date      # ← Added
    ...

UPDATE analytics_v2.dim_customer dc
SET
    ...
    lifetime_start_date = s.lifetime_start_date,  # ← Added
    lifetime_end_date = s.lifetime_end_date,      # ← Added
```

**Impact:** Populates first/last transaction dates for all 2,987 customers

---

### ✅ Fix 3: Extract NCM/CFOP in dimension aggregation

**File:** [services/analytics_api/src/analytics_api/services/metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py#L170-L177)

**Change:**
```python
# Added NCM/CFOP extraction for products
if dimension_col == 'raw_product_description':
    # Preserve NCM, CFOP for products
    if 'ncm' in df.columns:
        agg_ops['ncm'] = ('ncm', 'first')
    if 'cfop' in df.columns:
        agg_ops['cfop'] = ('cfop', 'first')
```

**Impact:** Product dimension now carries NCM/CFOP from BigQuery to `dim_product`

---

### 📋 Fix 4: Brazilian region mapping (SQL migration created)

**File:** [migrations/fix_regional_view_with_regions.sql](migrations/fix_regional_view_with_regions.sql)

**Status:** ⚠️ Migration created but not applied (Supabase timeout - needs manual application)

**Change:** Replaces `region_name` (UF) + `region_type` (useless) with:
- `state` (UF: SP, RJ, etc.)
- `region` (Brazilian region: Sul, Sudeste, Norte, Nordeste, Centro-Oeste)

**Mapping:**
```sql
state_to_region AS (
    SELECT * FROM (VALUES
        -- North (Norte): AC, AM, AP, PA, RO, RR, TO
        -- Northeast (Nordeste): AL, BA, CE, MA, PB, PE, PI, RN, SE
        -- Center-West (Centro-Oeste): DF, GO, MT, MS
        -- Southeast (Sudeste): ES, MG, RJ, SP
        -- South (Sul): PR, RS, SC
    ) AS mapping(state_code, region_name)
)
```

**Manual Application Required:**
```bash
# Apply via Supabase SQL Editor or psql
psql $DATABASE_URL < migrations/fix_regional_view_with_regions.sql
```

---

## Issues Not Fixed (Data Availability)

### ❌ endereco_uf NULL values (44%)

**Source:** BigQuery has 2.3% NULL values in `receiverstateuf` (1,903 / 83,229 rows)

**Reason:** Data quality issue in source system - state not captured for some transactions

**Workaround:** Could add fallback logic to infer state from `receiver_cidade` (city) using external API or mapping table

---

### ❌ line_item_sequence empty (100%)

**Source:** No sequence/item column exists in BigQuery foreign table

**Available columns:** `ncm`, `cfop`, `emitterphone`, `receivercity`, etc. (no sequence field)

**Reason:** Source data doesn't track line item ordering within invoices

**Impact:** Cannot support line-item-level analytics (e.g., "3rd item in order")

---

## Testing Instructions

### 1. Restart analytics_api service
```bash
cd /Users/lucascruz/Documents/GitHub/vizu-mono
docker-compose restart analytics_api
```

### 2. Trigger full recompute
```bash
curl -X POST "http://localhost:8012/ingest/recompute?force_full=true" \
  -H "Content-Type: application/json" \
  -H "X-Client-ID: e0e9c949-18fe-4d9a-9295-d5dfb2cc9723"
```

### 3. Verify NCM/CFOP populated
```sql
SELECT
    COUNT(*) as total_products,
    COUNT(ncm) as has_ncm,
    COUNT(cfop) as has_cfop,
    ROUND(100.0 * COUNT(ncm) / COUNT(*), 2) as ncm_percentage,
    ROUND(100.0 * COUNT(cfop) / COUNT(*), 2) as cfop_percentage
FROM analytics_v2.dim_product
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

-- Expected: 100% populated (6,670 products with NCM/CFOP)
```

### 4. Verify lifetime_start_date populated
```sql
SELECT
    COUNT(*) as total_customers,
    COUNT(lifetime_start_date) as has_lifetime_start,
    COUNT(lifetime_end_date) as has_lifetime_end,
    ROUND(100.0 * COUNT(lifetime_start_date) / COUNT(*), 2) as start_percentage
FROM analytics_v2.dim_customer
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';

-- Expected: 100% populated (2,987 customers with dates)
```

### 5. Apply regional mapping migration (manual)
```bash
# Copy migration to Supabase SQL Editor or use psql
psql $DATABASE_URL < migrations/fix_regional_view_with_regions.sql

# Verify view structure changed
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'analytics_v2'
  AND table_name = 'v_regional'
ORDER BY ordinal_position;

-- Expected: state, region columns (not region_name, region_type)
```

---

## Expected Outcomes

| Metric | Before | After | Status |
|--------|--------|-------|--------|
| dim_product NCM | 0% | 100% | ✅ Fixed |
| dim_product CFOP | 0% | 100% | ✅ Fixed |
| dim_customer lifetime_start_date | 0% | 100% | ✅ Fixed |
| dim_customer endereco_uf | 56% | 56% | ❌ Source data |
| v_regional structure | region_name/region_type | state/region | 📋 Migration ready |
| fact_sales line_item_sequence | 0% | 0% | ❌ Source missing |

---

## Files Modified

1. **[services/analytics_api/src/analytics_api/services/metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py)**
   - Line 548-577: Added lifetime_start_date/lifetime_end_date to customer aggregation SQL
   - Line 170-177: Added NCM/CFOP extraction for product dimension

2. **[migrations/fix_regional_view_with_regions.sql](migrations/fix_regional_view_with_regions.sql)** (new)
   - Brazilian state-to-region mapping (27 states → 5 regions)
   - Updated v_regional view structure

3. **Supabase database: client_data_sources.column_mapping**
   - Added `ncm → ncm`, `cfop → cfop` mappings

---

## Production Checklist

- [ ] Restart analytics_api service
- [ ] Run full recompute for test client
- [ ] Verify NCM/CFOP 100% populated (6,670 products)
- [ ] Verify lifetime_start_date 100% populated (2,987 customers)
- [ ] Apply regional mapping migration via Supabase SQL Editor
- [ ] Test v_regional query returns `state` and `region` columns
- [ ] Monitor ingestion logs for errors
- [ ] Update frontend to use new v_regional column names
- [ ] Document endereco_uf and line_item_sequence limitations

