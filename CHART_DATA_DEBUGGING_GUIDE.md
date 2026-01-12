# Chart Data Debugging Guide

## Problem Summary

Frontend console shows:
- ✅ Rankings populated (10 items each)
- ✅ Scorecards working (total_clientes: 1586, ticket_medio, frequencia)
- ❌ Charts EMPTY: `chart_clientes_por_regiao: Array(0)`, `chart_cohort_clientes: Array(0)`
- ❌ All `customer_cpf_cnpj: null`

## Added Enhanced Logging

Enhanced logging has been added to `metric_service.py` to diagnose why charts are empty.

**File Modified**: [services/analytics_api/src/analytics_api/services/metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py)

**Lines Modified**: 405-478

### What the Logs Will Tell Us

After restarting `analytics_api` and accessing the Clientes page, check the logs for these key messages:

```bash
docker-compose logs analytics_api | grep -A 20 "\[MetricService\] Calculando métricas Nível 2 (Clientes)"
```

---

## Diagnostic Log Messages to Look For

### 1. DataFrame Shape and Columns

```
[DEBUG] self.df shape: (72865, 25), columns: ['order_id', 'data_transacao', 'emitter_nome', ...]
[DEBUG] df_clientes_agg shape: (1586, 13), columns: ['nome', 'receita_total', 'ticket_medio', 'cluster_tier', ...]
```

**What to check**:
- Does `self.df` have data? (rows > 0)
- Does it have the columns we need?

### 2. State Column Detection

```
[DEBUG] State column search result: state_col=None, receiver_nome in columns: False
```

**Possible outcomes**:

#### ❌ Both Missing (Current Issue):
```
state_col=None, receiver_nome in columns: False
```
**Meaning**: Source data doesn't have state or receiver_nome columns mapped.
**Fix**: Check column mapping in `client_data_sources` table.

#### ⚠️ Partially Missing:
```
state_col=receiverstateuf, receiver_nome in columns: False
```
**Meaning**: Has state column but missing receiver_nome.
**Fix**: Ensure receiver_nome is mapped from source data.

#### ✅ Both Present:
```
state_col=receiverstateuf, receiver_nome in columns: True
```
**Expected next log**:
```
[DEBUG] chart_clientes_por_regiao generated: 27 regions
[DEBUG] chart_clientes_por_regiao sample: [{'name': 'SP', 'contagem': 450, 'percentual': 28.4}, ...]
```

### 3. Cluster Tier Check

```
[DEBUG] Checking cluster_tier: 'cluster_tier' in df_clientes_agg.columns = False
```

**Possible outcomes**:

#### ❌ Missing (Current Issue):
```
'cluster_tier' in df_clientes_agg.columns = False
⚠️  Missing cluster_tier column in df_clientes_agg; cohort chart will be empty
```
**Meaning**: RFM clustering didn't calculate `cluster_tier`.
**Fix**: Check `_get_aggregated_metrics_by_dimension()` to ensure clustering logic runs.

#### ✅ Present:
```
'cluster_tier' in df_clientes_agg.columns = True
[DEBUG] chart_cohort_clientes generated: 4 tiers
[DEBUG] chart_cohort_clientes data: [{'name': 'A (Melhores)', 'contagem': 395, 'percentual': 25.0}, ...]
```

### 4. Final Response Lengths

```
[DEBUG] Response chart lengths - regiao: 0, cohort: 0
[DEBUG] Response ranking lengths - receita: 10, ticket: 10
```

**What to check**:
- If charts are 0 but rankings are 10, the problem is in chart data generation
- If both are 0, the problem is in the entire metric service

---

## Root Cause Analysis Tree

```
Chart Data Empty
├── Missing State Columns
│   ├── Check: self.df.columns for receiverstateuf/receiver_estado/receiver_state
│   ├── Check: client_data_sources.column_mapping for state fields
│   └── Action: Add state column mapping if source data has it
│
├── Missing receiver_nome Column
│   ├── Check: self.df.columns for receiver_nome
│   ├── Check: client_data_sources.column_mapping for receiver_nome
│   └── Action: Add receiver_nome mapping if source data has it
│
└── Missing cluster_tier Column
    ├── Check: df_clientes_agg.columns for cluster_tier
    ├── Check: _get_aggregated_metrics_by_dimension() RFM logic
    └── Possible causes:
        ├── RFM scoring failed (NaN values)
        ├── pd.qcut failed (not enough unique scores)
        └── cluster_tier calculation was skipped due to error

```

---

## Step-by-Step Debugging Process

### Step 1: Restart Analytics API

```bash
docker-compose restart analytics_api
```

### Step 2: Access Clientes Page

Open the frontend and navigate to `/dashboard/clientes`

### Step 3: Check Logs

```bash
# Full debug output
docker-compose logs -f analytics_api | grep -E "\[DEBUG\]|\[MetricService\]|⚠️"

# Specific to clientes overview
docker-compose logs analytics_api | grep -A 30 "Calculando métricas Nível 2 (Clientes)"
```

### Step 4: Analyze Log Output

Based on the log messages, identify which scenario matches:

#### Scenario A: Missing Columns in self.df
**Log shows**: `state_col=None, receiver_nome in columns: False`

**Next steps**:
1. Check what columns ARE in self.df: Look at the `columns: [...]` log
2. Check column mapping: Query `client_data_sources` table
3. Verify BigQuery source has these columns

```sql
-- Check column mapping
SELECT id, client_id, source_name, column_mapping
FROM client_data_sources
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
```

#### Scenario B: Missing cluster_tier in Aggregated Data
**Log shows**: `'cluster_tier' in df_clientes_agg.columns = False`

**Next steps**:
1. Check if RFM scoring is running: Look for logs about cluster_score calculation
2. Check for errors in `_get_aggregated_metrics_by_dimension()`
3. Add more logging to RFM clustering section

#### Scenario C: Data Quality Issues
**Log shows**: `df_clientes_regiao generated: 0 regions` OR `df_cohort generated: 0 tiers`

**Next steps**:
1. Check if groupby operations return empty dataframes
2. Verify data isn't being filtered out unexpectedly
3. Check for NULL values in grouping columns

---

## Expected Column Names

### For chart_clientes_por_regiao (Regional Chart)

**Required in self.df**:
- One of: `receiverstateuf`, `receiver_estado`, `receiver_state`
- And: `receiver_nome`

**Source data examples** (BigQuery):
```
receiverstateuf: 'SP', 'RJ', 'MG', ...
receiver_nome: 'KLABIN S.A.', 'GERDAU ACOS LONGOS S.A.', ...
```

### For chart_cohort_clientes (Cohort/Tier Chart)

**Required in df_clientes_agg**:
- `cluster_tier` (calculated by RFM clustering)

**Expected values**:
- "A (Melhores)"
- "B"
- "C"
- "D (Piores)"

---

## Column Mapping Investigation

### Check What's Mapped

```sql
-- View current column mapping
SELECT
    client_id,
    source_name,
    resource_type,
    column_mapping
FROM client_data_sources
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723';
```

### Expected Mapping (Example)

```json
{
  "emittedat_operatorinvoice": "data_transacao",
  "emittername_naturaloperator": "emitter_nome",
  "receivername_legaloperator": "receiver_nome",
  "receiverstateuf_legaloperator": "receiverstateuf",
  "receivercpfcnpj_legaloperator": "receiver_cpf_cnpj",
  "valorinbrl_operatorinvoice": "valor_total_emitter",
  "material_product": "raw_product_description",
  "weight_product": "quantidade"
}
```

**Key fields for charts**:
- `receiver_nome` → Must map to customer name field
- `receiverstateuf` → Must map to state field (or similar)
- `receiver_cpf_cnpj` → Should map to CPF/CNPJ field (currently missing)

---

## Common Issues and Fixes

### Issue 1: Column Not Mapped

**Symptom**: `state_col=None`

**Check**:
```bash
docker-compose logs data_ingestion_api | grep "Schema match for 'invoices'"
```

Look for:
```
✓ Matched: 10 columns
✗ UNMATCHED: 74 columns
```

**Fix**: Add more aliases or adjust fuzzy matching threshold to capture state columns.

### Issue 2: cluster_tier Not Calculated

**Symptom**: `'cluster_tier' in df_clientes_agg.columns = False`

**Possible causes**:
1. RFM scoring failed due to NaN values
2. pd.qcut requires at least 4 unique values
3. Exception in clustering logic

**Check**: Add logging to `_get_aggregated_metrics_by_dimension()` line ~200:
```python
logger.info(f"[DEBUG] Before clustering: cluster_score column exists: {'cluster_score' in agg_df.columns}")
logger.info(f"[DEBUG] cluster_score unique values: {agg_df['cluster_score'].nunique()}")
```

### Issue 3: Empty Dataframes

**Symptom**: `df_clientes_regiao generated: 0 regions`

**Possible causes**:
1. All state values are NULL
2. Groupby filtered everything out
3. receiver_nome has only NULL values

**Check**: Look at raw data quality:
```python
logger.info(f"[DEBUG] receiver_nome NULL count: {self.df['receiver_nome'].isna().sum()}")
logger.info(f"[DEBUG] state column NULL count: {self.df[state_col].isna().sum()}")
```

---

## Next Steps After Log Analysis

1. **Share the logs** from the debugging session
2. **Identify which scenario** matches (A, B, or C above)
3. **Fix the root cause**:
   - Add column mappings if missing
   - Fix RFM clustering if broken
   - Clean data quality if NULL values are the issue

---

## Testing Checklist

After implementing fixes:

- [ ] Restart analytics_api: `docker-compose restart analytics_api`
- [ ] Clear browser cache and refresh
- [ ] Check logs show: `chart_clientes_por_regiao generated: X regions` (X > 0)
- [ ] Check logs show: `chart_cohort_clientes generated: 4 tiers`
- [ ] Verify frontend console shows non-empty arrays for charts
- [ ] Verify graphs render in the UI

---

## Summary

The enhanced logging will pinpoint exactly which columns are missing or why chart generation is failing. The most likely issues are:

1. **Missing column mapping** for state fields (receiverstateuf/receiver_estado)
2. **Missing column mapping** for receiver_nome
3. **RFM clustering not calculating** cluster_tier

Once we see the logs, we'll know exactly which fix to apply.
