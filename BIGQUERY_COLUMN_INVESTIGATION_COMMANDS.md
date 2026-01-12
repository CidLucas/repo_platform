# BigQuery Column Investigation Commands

## Objective

Determine if state/region columns exist in the BigQuery source table to understand why charts are empty.

---

## Step 1: Authenticate with Google Cloud

```bash
# Login to gcloud (opens browser for authentication)
gcloud auth login

# Set the project
gcloud config set project pdi-bigquery-434820

# Verify authentication
gcloud auth list
```

---

## Step 2: Query for State/Region Columns

### Option A: Search for State-Related Columns (Recommended First)

```bash
bq query --use_legacy_sql=false '
SELECT
  column_name,
  data_type,
  is_nullable
FROM `analytics-big-query-242119.dataform`
WHERE table_name = "products_invoices"
  AND (
    column_name LIKE "%state%"
    OR column_name LIKE "%uf%"
    OR column_name LIKE "%estado%"
    OR column_name LIKE "%region%"
    OR column_name LIKE "%endereco%"
    OR column_name LIKE "%cidade%"
    OR column_name LIKE "%address%"
    OR column_name LIKE "%location%"
  )
ORDER BY column_name;
'
```

**Expected outcomes**:

#### ✅ If state columns EXIST:
You'll see results like:
```
+------------------------------------------+-----------+-------------+
|               column_name                | data_type | is_nullable |
+------------------------------------------+-----------+-------------+
| emittercity_naturaloperator              | STRING    | YES         |
| emitterstateuf_naturaloperator           | STRING    | YES         |
| receivercity_legaloperator               | STRING    | YES         |
| receiverstateuf_legaloperator            | STRING    | YES         |
+------------------------------------------+-----------+-------------+
```

**Next step**: Add these columns to the canonical schema (Phase 2 of ACTION_PLAN_CHARTS_FIX.md)

#### ❌ If NO state columns found:
You'll see:
```
Query returned zero rows
```

**Next step**: Choose alternative solution (Phase 3 of ACTION_PLAN_CHARTS_FIX.md)

---

## Step 3: Get Full Column List (Optional but Recommended)

This gives you a complete view of all 84 columns in the BigQuery table:

```bash
bq query --use_legacy_sql=false --format=prettyjson '
SELECT
  ordinal_position,
  column_name,
  data_type,
  is_nullable
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = "maua_materials"
ORDER BY ordinal_position;
' > /Users/lucascruz/Documents/GitHub/vizu-mono/bigquery_full_schema.json
```

Or for readable table format:

```bash
bq query --use_legacy_sql=false --max_rows=100 '
SELECT
  ordinal_position,
  column_name,
  data_type,
  is_nullable
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = "maua_materials"
ORDER BY ordinal_position;
'
```

This will show ALL columns so you can see what's available for mapping.

---

## Step 4: Sample Data for State Columns (If Found)

If Step 2 found state columns, check if they have actual data:

```bash
bq query --use_legacy_sql=false --max_rows=10 '
SELECT
  receiverstateuf_legaloperator,
  emitterstateuf_naturaloperator,
  receivercity_legaloperator,
  emittercity_naturaloperator,
  receivername_legaloperator,
  emittername_naturaloperator
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.maua_materials`
WHERE receiverstateuf_legaloperator IS NOT NULL
   OR emitterstateuf_naturaloperator IS NOT NULL
LIMIT 10;
'
```

**Replace column names** with the actual column names found in Step 2.

---

## Step 5: Count NULL Percentages (Data Quality Check)

```bash
bq query --use_legacy_sql=false '
SELECT
  COUNT(*) as total_rows,
  COUNTIF(receiverstateuf_legaloperator IS NOT NULL) as receiver_state_count,
  ROUND(COUNTIF(receiverstateuf_legaloperator IS NOT NULL) / COUNT(*) * 100, 2) as receiver_state_pct,
  COUNTIF(emitterstateuf_naturaloperator IS NOT NULL) as emitter_state_count,
  ROUND(COUNTIF(emitterstateuf_naturaloperator IS NOT NULL) / COUNT(*) * 100, 2) as emitter_state_pct
FROM `pdi-bigquery-434820.maua_materiais_reciclagem.maua_materials`;
'
```

**Replace column names** with actual names found.

**Good data quality**: > 90% populated
**Poor data quality**: < 50% populated (may not be useful for charts)

---

## Alternative: Use bq CLI to Show Table Schema

```bash
# Quick schema view
bq show --schema --format=prettyjson pdi-bigquery-434820:maua_materiais_reciclagem.maua_materials

# Or simpler format
bq show pdi-bigquery-434820:maua_materiais_reciclagem.maua_materials
```

---

## Troubleshooting

### Error: "gcloud: command not found"

Install gcloud SDK:
```bash
# macOS
brew install --cask google-cloud-sdk

# Then authenticate
gcloud auth login
```

### Error: "bq: command not found"

Install bq CLI (part of gcloud SDK):
```bash
gcloud components install bq
```

### Error: "Access Denied" or "Permission Denied"

Ensure your Google account has at least **BigQuery Data Viewer** role on the project.

```bash
# Check current authenticated account
gcloud auth list

# Check project permissions
gcloud projects get-iam-policy pdi-bigquery-434820
```

---

## What to Share

After running the commands, share:

1. **Output of Step 2** (state column search) - This is the CRITICAL one
2. **Output of Step 3** (full column list) - Helps understand what else is available
3. **If state columns found**: Output of Step 4 (sample data)
4. **If state columns found**: Output of Step 5 (data quality percentages)

---

## Quick Reference: Column Names We're Looking For

**For customer regional chart** (`chart_clientes_por_regiao`):
- `receiverstateuf` OR
- `receiver_estado` OR
- `receiver_state` OR
- `receiverstate` OR
- Similar variations

**For supplier regional chart** (`chart_fornecedores_por_regiao`):
- `emitterstateuf` OR
- `emitter_estado` OR
- `emitter_state` OR
- `emitterstate` OR
- Similar variations

**Alternative location data** (if no state columns):
- `receivercity` / `emittercity` (city names)
- `receiveraddress` / `emitteraddress` (full addresses)
- `receiverzip` / `emitterzip` (ZIP codes)

Any of these can be used to derive state information.

---

## Next Steps Based on Results

### If State Columns FOUND ✅
→ Go to **Phase 2** in [ACTION_PLAN_CHARTS_FIX.md](ACTION_PLAN_CHARTS_FIX.md)
- Add columns to canonical schema
- Update metric_service.py search lists
- Re-run ingestion
- Verify charts populate

### If State Columns NOT FOUND ❌
→ Go to **Phase 3** in [ACTION_PLAN_CHARTS_FIX.md](ACTION_PLAN_CHARTS_FIX.md)
- Option A: Derive from city/address data (complex)
- Option B: Remove chart components (quick)
- Option C: Use mock data for demo (fastest)

---

## Summary

Run **Step 2** first to determine if state columns exist. This single query determines the entire solution path forward.

**Estimated time**: 2-3 minutes to authenticate and run query.
