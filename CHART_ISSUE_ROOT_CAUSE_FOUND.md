# Chart Issue - Root Cause Analysis COMPLETE

## Executive Summary

**ROOT CAUSE IDENTIFIED**: Charts are empty because the gold endpoints (`/dashboard/clientes/gold`, `/dashboard/fornecedores/gold`, `/dashboard/produtos/gold`) have **hardcoded empty arrays** with TODO comments.

The chart generation logic exists in `MetricService` (Nível 2 methods), but the frontend is calling the `/gold` endpoints instead, which never implemented chart generation.

---

## Evidence Chain

### 1. Frontend Calls Gold Endpoints (Not MetricService)

**File**: [apps/vizu_dashboard/src/services/analyticsService.ts](apps/vizu_dashboard/src/services/analyticsService.ts)

```typescript
// Line 201
export const getFornecedores = async (): Promise<FornecedoresOverviewResponse> => {
  const response = await axiosInstance.get<FornecedoresOverviewResponse>('/dashboard/fornecedores/gold');
  return response.data;
};

// Line 213
export const getClientes = async (): Promise<ClientesOverviewResponse> => {
  const response = await axiosInstance.get<ClientesOverviewResponse>('/dashboard/clientes/gold');
  return response.data;
};

// Line 224
export const getProdutos = async (): Promise<ProdutosOverviewResponse> => {
  const response = await axiosInstance.get<ProdutosOverviewResponse>('/dashboard/produtos/gold');
  return response.data;
};
```

### 2. Gold Endpoints Return Hardcoded Empty Charts

**File**: [services/analytics_api/src/analytics_api/api/endpoints/dashboard.py](services/analytics_api/src/analytics_api/api/endpoints/dashboard.py)

#### Clientes Endpoint (Lines 230-241)
```python
return {
    "scorecard_total_clientes": total_clientes,
    "scorecard_ticket_medio_geral": float(ticket_medio),
    "scorecard_frequencia_media_geral": float(frequencia_media),
    "scorecard_crescimento_percentual": None,
    "chart_clientes_por_regiao": [],  # ❌ TODO: Aggregate by region from analytics_silver
    "chart_cohort_clientes": [],      # ❌ TODO: Build cohort analysis
    "ranking_por_receita": ranking_por_receita,  # ✅ Rankings work
    "ranking_por_ticket_medio": ranking_por_ticket_medio,
    "ranking_por_qtd_pedidos": ranking_por_qtd_pedidos,
    "ranking_por_cluster_vizu": ranking_por_cluster_vizu,
}
```

#### Fornecedores Endpoint (Lines 310-321)
```python
return {
    "scorecard_total_fornecedores": total_fornecedores,
    "scorecard_crescimento_percentual": None,
    "chart_fornecedores_no_tempo": [],    # ❌ TODO: Build time series
    "chart_fornecedores_por_regiao": [],  # ❌ TODO: Aggregate by region
    "chart_cohort_fornecedores": [],      # ❌ TODO: Build cohort analysis
    "ranking_por_receita": ranking_por_receita,  # ✅ Rankings work
    "ranking_por_qtd_media": ranking_por_qtd_media,
    "ranking_por_ticket_medio": ranking_por_ticket_medio,
    "ranking_por_frequencia": ranking_por_frequencia,
    "ranking_produtos_mais_vendidos": produtos_vendidos_formatted,
}
```

#### Produtos Endpoint (Expected similar pattern)
Likely has empty chart arrays as well.

### 3. Chart Logic EXISTS in MetricService But Isn't Called

**File**: [services/analytics_api/src/analytics_api/services/metric_service.py](services/analytics_api/src/analytics_api/services/metric_service.py)

The chart generation logic exists in:
- `get_clientes_overview()` (lines 405-478) - ✅ Has chart generation
- `get_fornecedores_overview()` (lines 338-403) - ✅ Has chart generation
- `get_produtos_overview()` (lines 480-493) - ✅ Has chart generation

**BUT** these methods are never called because the frontend calls `/gold` endpoints instead!

### 4. Why We Don't See "Nível 2" Logs

**User observation**: "We only see métrica nivel 1, we don't see logs from nível 2"

**Explanation**:
- "Nível 2" logs come from `MetricService` methods like `get_clientes_overview()`
- Frontend calls `/dashboard/clientes/gold` which goes directly to `get_customers_gold()` endpoint
- This endpoint never calls `MetricService.get_clientes_overview()`, so no "Nível 2" logs appear
- Only when you visit clientes page, we see "Nível 1" logs from `get_home_metrics()` which is called by all pages

---

## The Architecture Mismatch

### Current State

```
Frontend → /dashboard/clientes/gold → dashboard.py:get_customers_gold() → Returns hardcoded [] charts
                                                                         ↓
                                                                    analytics_gold_customers table
```

### What Was Intended (But Not Connected)

```
Frontend → ??? → dashboard.py:??? → MetricService.get_clientes_overview() → Generates charts from silver data
                                                                           ↓
                                                                      analytics_silver table
```

**The Problem**: The chart generation logic in `MetricService` was built for in-memory pandas operations on `analytics_silver`, but the `/gold` endpoints were created later to read from `analytics_gold_*` tables and **never implemented chart generation**.

---

## Why Rankings Work But Charts Don't

### Rankings: ✅ WORK
```python
ranking_por_receita = sorted(
    customers_data,  # ← From analytics_gold_customers
    key=lambda x: x.get("lifetime_value", 0),
    reverse=True
)[:10]
```

Rankings work because they're simple sorts of the gold table data - no aggregation needed.

### Charts: ❌ DON'T WORK
```python
"chart_clientes_por_regiao": [],  # ← Hardcoded empty!
```

Charts need aggregations (groupby region, time series, cohorts) which were **never implemented** in the gold endpoints.

---

## The 12 Mapped Columns Issue

**User's log**: "⚠️ Mapped: 12 columns, UNMATCHED: 72 columns"

This is a **separate issue** from empty charts. Even if we had 84 mapped columns, charts would still be empty because of the hardcoded `[]`.

**However**: The missing state columns (receiverstateuf, emitterstateuf) will prevent chart generation **even after we fix the code**, because:

```python
# MetricService.get_clientes_overview() line 418
if state_col and 'receiver_nome' in self.df.columns:
    # Generate regional chart
else:
    logger.warning("Missing state column; skipping chart")
    df_clientes_regiao = pd.DataFrame()  # Empty!
```

So we have **TWO problems**:
1. ❌ Gold endpoints don't generate charts (hardcoded `[]`)
2. ❌ Missing state columns in column mapping (even if we fix #1)

---

## Solution Options

### Option A: Implement Chart Generation in Gold Endpoints ⭐ RECOMMENDED

**Approach**: Keep using `/gold` endpoints but add chart generation logic

**Implementation**:
1. Query `analytics_silver` foreign table for raw data
2. Use pandas groupby operations to generate charts
3. Return charts alongside rankings

**Pros**:
- ✅ No frontend changes needed
- ✅ Uses existing gold tables for scorecards/rankings
- ✅ Adds missing chart functionality
- ✅ Can access raw data via foreign table

**Cons**:
- ⚠️ Requires analytics_silver foreign table to exist
- ⚠️ More complex endpoint logic
- ⚠️ Still need to fix column mapping (missing state columns)

**Files to modify**:
- `services/analytics_api/src/analytics_api/api/endpoints/dashboard.py:171-241` (clientes)
- `services/analytics_api/src/analytics_api/api/endpoints/dashboard.py:244-321` (fornecedores)
- `services/analytics_api/src/analytics_api/api/endpoints/dashboard.py:92-168` (produtos)

---

### Option B: Switch Frontend to Use MetricService Endpoints

**Approach**: Change frontend to call existing chart-enabled endpoints

**Implementation**:
1. Create new endpoints that use `MetricService` methods
2. Update frontend to call these new endpoints

**Pros**:
- ✅ Chart logic already exists
- ✅ Well-tested pandas operations
- ✅ Reuses existing code

**Cons**:
- ⚠️ Requires frontend changes
- ⚠️ Still need to fix column mapping
- ⚠️ May have performance issues (in-memory aggregation vs pre-computed gold)

**Files to modify**:
- `apps/vizu_dashboard/src/services/analyticsService.ts` (change URLs)
- `services/analytics_api/src/analytics_api/api/endpoints/dashboard.py` (add new routes)

---

### Option C: Hybrid Approach

**Approach**: Use gold tables for scorecards/rankings, MetricService for charts

**Implementation**:
1. Keep `/gold` endpoints for scorecards and rankings
2. Add separate chart endpoints that call `MetricService`
3. Frontend makes two API calls per page

**Pros**:
- ✅ Uses best of both worlds
- ✅ Minimal changes to existing code
- ✅ Clear separation of concerns

**Cons**:
- ⚠️ Requires frontend changes (two API calls)
- ⚠️ More complex architecture
- ⚠️ Still need to fix column mapping

---

### Option D: Remove Charts Entirely ❌ NOT RECOMMENDED

**Approach**: Accept that charts don't work, focus on rankings

**Pros**:
- ✅ No backend changes needed
- ✅ Works with existing data

**Cons**:
- ❌ Major UX regression
- ❌ Doesn't solve user's problem
- ❌ Wastes existing chart generation code

---

## Immediate Next Steps

### Phase 1: Verify Column Mapping (5 minutes)
Run ingestion again with new logging to see which 12 columns are mapped:

```bash
# Trigger new sync
curl -X POST http://localhost:8002/etl/sync \
  -H "Content-Type: application/json" \
  -d '{"credential_id": "...", "client_id": "...", "resource_type": "invoices"}'

# Check logs for:
# "📍 Mapped source columns (these WILL be available):"
```

**Look for**: Are `receiverstateuf` and `emitterstateuf` in the mapped or unmatched list?

### Phase 2: Decide on Solution (10 minutes)
Based on column mapping results:

#### If state columns ARE mapped:
→ Go with **Option A** (implement charts in gold endpoints)
→ Charts will work immediately after implementation

#### If state columns NOT mapped:
→ Need to fix column mapping FIRST:
  1. Add state column aliases to schema_matcher_service.py
  2. Re-run ingestion
  3. Then implement Option A

### Phase 3: Implement Solution (30-60 minutes)
See implementation guide below based on chosen option.

---

## Option A Implementation Guide

### Step 1: Add Analytics Silver Query to Repository

**File**: `services/analytics_api/src/analytics_api/data_access/postgres_repository.py`

```python
def get_silver_data_for_charts(self, client_id: str, limit: int = 10000) -> List[Dict[str, Any]]:
    """
    Query analytics_silver foreign table for raw data needed for charts.

    Returns up to `limit` rows with all columns for chart generation.
    """
    # Determine foreign table name (client-specific)
    # This assumes foreign table naming convention: bigquery_<client_id>_<table>
    # Adjust based on actual naming in etl_service_v2.py

    # For now, use a generic query that works with any foreign table structure
    query = text("""
        SELECT *
        FROM bigquery_fdw_tables
        WHERE client_id = :client_id
        LIMIT :limit
    """)

    with self.Session() as session:
        result = session.execute(query, {"client_id": client_id, "limit": limit})
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

    logger.info(f"Fetched {len(rows)} rows from analytics_silver for client {client_id}")
    return rows
```

### Step 2: Modify Clientes Gold Endpoint

**File**: `services/analytics_api/src/analytics_api/api/endpoints/dashboard.py`

```python
@router.get("/clientes/gold", ...)
async def get_customers_gold(
    repo: PostgresRepository = Depends(get_postgres_repository),
    client_id: str = Depends(get_client_id)
):
    # Existing code for scorecards and rankings
    customers_data = repo.get_gold_customers_metrics(client_id)

    # ... (keep existing scorecard/ranking logic) ...

    # NEW: Generate charts from raw data
    import pandas as pd

    # Fetch raw data for chart generation
    raw_data = repo.get_silver_data_for_charts(client_id)

    if raw_data:
        df = pd.DataFrame(raw_data)

        # Chart 1: Clientes por região
        chart_clientes_por_regiao = []
        state_col = None

        # Find state column (same logic as MetricService)
        for col in df.columns:
            if 'receiverstateuf' in col.lower() or 'receiver_estado' in col.lower():
                state_col = col
                break

        if state_col and 'receiver_nome' in df.columns:
            df_regiao = df.groupby(state_col)['receiver_nome'].nunique().reset_index(name='contagem')
            total_clientes_regiao = df_regiao['contagem'].sum()
            df_regiao['percentual'] = (df_regiao['contagem'] / total_clientes_regiao) * 100
            df_regiao.rename(columns={state_col: 'name'}, inplace=True)
            chart_clientes_por_regiao = df_regiao.to_dict('records')

        # Chart 2: Cohort analysis
        chart_cohort_clientes = []

        # Check if cluster_tier exists in customers_data
        cluster_data = [c for c in customers_data if c.get("customer_type")]
        if cluster_data:
            df_cohort = pd.DataFrame(cluster_data)
            cohort_agg = df_cohort.groupby('customer_type').size().reset_index(name='contagem')
            cohort_agg.rename(columns={'customer_type': 'name'}, inplace=True)
            chart_cohort_clientes = cohort_agg.to_dict('records')
    else:
        chart_clientes_por_regiao = []
        chart_cohort_clientes = []

    return {
        "scorecard_total_clientes": total_clientes,
        "scorecard_ticket_medio_geral": float(ticket_medio),
        "scorecard_frequencia_media_geral": float(frequencia_media),
        "scorecard_crescimento_percentual": None,
        "chart_clientes_por_regiao": chart_clientes_por_regiao,  # ✅ Now populated!
        "chart_cohort_clientes": chart_cohort_clientes,          # ✅ Now populated!
        "ranking_por_receita": ranking_por_receita,
        "ranking_por_ticket_medio": ranking_por_ticket_medio,
        "ranking_por_qtd_pedidos": ranking_por_qtd_pedidos,
        "ranking_por_cluster_vizu": ranking_por_cluster_vizu,
    }
```

### Step 3: Repeat for Fornecedores and Produtos

Apply same pattern to:
- `/fornecedores/gold` endpoint
- `/produtos/gold` endpoint

---

## Testing Checklist

After implementation:

- [ ] Run ingestion with new logging
- [ ] Verify 12 mapped columns include state columns
- [ ] Test `/dashboard/clientes/gold` endpoint
- [ ] Verify charts array is not empty
- [ ] Test frontend clientes page
- [ ] Verify graphs render
- [ ] Repeat for fornecedores
- [ ] Repeat for produtos
- [ ] Check for NaN values in scorecards
- [ ] Verify all rankings have data

---

## Summary

**Root Cause**: Gold endpoints return hardcoded `[]` for charts with TODO comments.

**Why It Happened**: Architecture evolved - gold endpoints were added later for pre-computed metrics, but chart generation was never migrated from `MetricService`.

**Best Solution**: **Option A** - Add chart generation to gold endpoints while keeping rankings from gold tables.

**Quick Win**: Once we verify state columns are mapped, implementation is ~30 lines of pandas code per endpoint.

**Current Blocker**: Need to see ingestion logs to confirm which 12 columns are mapped and whether state columns are in the unmatched list.
