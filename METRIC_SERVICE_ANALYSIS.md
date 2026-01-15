# MetricService Code Review & Analysis

**Date:** 2026-01-14
**File:** `services/analytics_api/src/analytics_api/services/metric_service.py`
**Status:** ✅ All tests passing after bug fixes

## Summary

Comprehensive review of metric_service.py revealed 1 critical bug (now fixed), repeated code patterns, legacy methods, and excessive debug statements.

---

## 🐛 Bugs Found & Fixed

### 1. **CRITICAL: Produtos Overview Pydantic Validation Error** ✅ FIXED

**Location:** Lines 117-119, 957-985

**Issue:**
- Products were aggregated using `_get_product_aggregation()` which only returned 5 columns
- `get_produtos_overview()` tried to convert products to `RankingItem` (requires 13 fields)
- Caused Pydantic validation error at runtime

**Fix:**
- Changed `self.df_produtos_agg = self._get_product_aggregation(self.df)`
- To: `self.df_produtos_agg = self._get_aggregated_metrics_by_dimension(self.df, 'raw_product_description')`
- Updated `get_produtos_overview()` to use proper product-specific schemas (`ProdutoRankingReceita`, `ProdutoRankingVolume`, `ProdutoRankingTicket`) instead of `RankingItem`

**Test Result:** ✅ All product rankings now work correctly

---

## 🔁 Repeated Code Patterns

### 1. **Repeated Column Name Search Pattern** (6+ occurrences)

**Locations:**
- Lines 375-379 (emitter state search)
- Lines 382-386 (receiver state search)
- Lines 509-512 (emitter state search)
- Lines 467-470 (receiver state search)
- Lines 726-729 (emitter state search)
- Lines 821-824 (receiver state search)

**Pattern:**
```python
state_col = None
for col in ['emitterstateuf', 'emitter_estado', 'emitter_state']:
    if col in self.df.columns:
        state_col = col
        break
```

**Recommendation:**
Create helper method:
```python
def _find_column(self, possible_names: list[str]) -> str | None:
    """Find first matching column from list of possible names."""
    for col in possible_names:
        if col in self.df.columns:
            return col
    return None
```

**Savings:** ~30 lines of code

---

### 2. **Repeated Chart Data Conversion Pattern** (5+ occurrences)

**Locations:**
- Lines 765-769 (fornecedores no tempo)
- Lines 773-777 (fornecedores por regiao)
- Lines 779-783 (fornecedores cohort)
- Lines 880-884 (clientes por regiao)
- Lines 886-890 (clientes cohort)

**Pattern:**
```python
chart_data = [
    ChartDataPoint(**record)
    for record in df.to_dict('records')
]
```

**Recommendation:**
Already using ChartDataPoint, but could extract to helper for consistency checking.

---

### 3. **Repeated Growth Calculation Logic** (2 occurrences)

**Locations:**
- Lines 743-762 (fornecedores)
- Lines 858-877 (clientes)

**Pattern:**
```python
df_novos = self.df.sort_values('data_transacao').drop_duplicates('entity_name')[['entity_name', 'ano_mes']]
entidades_por_mes = df_novos.groupby('ano_mes').size()

if len(entidades_por_mes) >= 2:
    mes_atual = entidades_por_mes.iloc[-1]
    mes_anterior = entidades_por_mes.iloc[-2]
    if mes_anterior > 0:
        crescimento_percentual = float(((mes_atual - mes_anterior) / mes_anterior) * 100)
```

**Recommendation:**
✅ ALREADY FIXED! Now uses `self._calculate_time_series_growth('ano_mes', 'emitter_nome')` helper method.

---

### 4. **Repeated Ranking Conversion Pattern** (15+ occurrences)

**Locations:**
- Lines 797-800 (fornecedores por receita)
- Lines 802-805 (fornecedores por qtd media)
- Lines 807-810 (fornecedores por ticket)
- Lines 812-815 (fornecedores por frequencia)
- Lines 817-820 (fornecedores produtos mais vendidos)
- Lines 890-893 (clientes por receita)
- Lines 895-898 (clientes por ticket)
- Lines 900-903 (clientes por qtd pedidos)
- Lines 905-908 (clientes por cluster)
- Lines 960-966 (produtos por receita)
- Lines 969-975 (produtos por volume)
- Lines 978-984 (produtos por ticket)

**Pattern:**
```python
ranking_por_X = [
    SomeSchema(**record)
    for record in df_agg.sort_values('metric', ascending=False).head(10).to_dict('records')
]
```

**Recommendation:**
Create helper method:
```python
def _create_ranking(
    self,
    df: pd.DataFrame,
    sort_by: str,
    schema_class: type,
    limit: int = 10,
    ascending: bool = False
) -> list:
    """Create ranking from dataframe using schema."""
    return [
        schema_class(**record)
        for record in df.sort_values(sort_by, ascending=ascending).head(limit).to_dict('records')
    ]
```

**Savings:** ~50 lines of code

---

## 🗑️ Legacy / Unused Code

### 1. **`_get_product_aggregation()` method** ⚠️ NO LONGER USED

**Location:** Lines 230-268

**Status:** Orphaned after fixing products bug

**Recommendation:** DELETE (39 lines)

**Reason:** Products now use `_get_aggregated_metrics_by_dimension()` like customers/suppliers

---

### 2. **Excessive Debug Logging in `get_clientes_overview()`**

**Locations:**
- Line 812-813 (DEBUG df shapes)
- Line 826 (DEBUG state column)
- Line 834-835 (DEBUG regional chart)
- Line 840-841 (DEBUG cluster_tier check)
- Line 846-847 (DEBUG cohort data)
- Line 850 (WARNING cohort missing)

**Recommendation:**
- Keep INFO level logs
- Remove or downgrade DEBUG logs to TRACE level
- Remove redundant warnings that don't help users

**Savings:** ~6-8 lines

---

### 3. **Commented-Out Code**

**Locations:** None found (good!)

---

## 📊 Performance & Quality Observations

### ✅ Good Practices Found:

1. **Defensive Programming:** Extensive null/empty checks
2. **Data Quality Logging:** `DataQualityLogger` integration
3. **Pydantic Validation:** Type safety enforced
4. **Error Handling:** Try/except blocks around critical sections
5. **Pandas Best Practices:** Using `.copy()`, `.fillna()`, `.replace()`

### ⚠️ Potential Issues:

1. **Memory Usage:** Loading full silver dataframe into memory (could be 100k+ rows)
   - **Mitigation:** Already uses gold tables to avoid reloading on each request

2. **Datetime Handling:** Multiple timezone conversions
   - Lines 97-98: `dt.tz_localize(None)` removes timezone
   - Could cause issues if source data has mixed timezones

3. **Magic Numbers:**
   - Line 206: `(agg_df['score_r'] * 0.2) + (agg_df['score_f'] * 0.4) + (agg_df['score_m'] * 0.4)`
   - Should be constants: `RFM_WEIGHT_RECENCY = 0.2`, etc.

---

## 🎯 Recommended Refactoring

### Priority 1: Remove Legacy Code
- [ ] Delete `_get_product_aggregation()` method (lines 230-268)
- [ ] Remove excessive debug statements from `get_clientes_overview()`

### Priority 2: Extract Helper Methods
- [ ] `_find_column(possible_names)` - Find matching column
- [ ] `_create_ranking(df, sort_by, schema, limit)` - Create rankings consistently

### Priority 3: Extract Constants
- [ ] RFM score weights (0.2, 0.4, 0.4)
- [ ] Default quantiles for clustering (4 tiers)
- [ ] Column name aliases (state columns, etc.)

### Priority 4: Code Organization
- [ ] Group related methods together (Level 1, Level 2, Level 3, Helpers, Writers)
- [ ] Add section comments for clarity

---

## 📈 Test Coverage

✅ **All core functionality tested:**
- Home metrics (Level 1)
- Fornecedores overview (Level 2)
- Clientes overview (Level 2)
- Produtos overview (Level 2) - **FIXED**
- Pedidos overview (Level 2)
- Gold table writes
- Time series writes (**NEW: customer time series added**)
- Regional writes
- Last orders writes

**Test Results:** 100% pass rate after fixes

---

## 🔄 Recent Improvements Made

1. ✅ **Regional aggregation**: Added `_calculate_total_regions()` helper
2. ✅ **Growth metrics**: Added `_calculate_time_series_growth()` helper
3. ✅ **Customer time series**: Now writes `clientes_no_tempo` to gold
4. ✅ **Fornecedores growth**: Uses new helper method (removed duplication)
5. ✅ **Clientes growth**: Uses new helper method (removed duplication)
6. ✅ **Products bug**: Fixed Pydantic validation error

---

## 📝 Conclusion

**Overall Code Quality:** B+ (Good, with room for improvement)

**Strengths:**
- Comprehensive functionality
- Good error handling
- Type safety with Pydantic
- Successful test coverage

**Areas for Improvement:**
- Remove 1 legacy method (~40 lines)
- Extract 2 helper methods (~80 lines of duplication)
- Clean up debug statements (~8 lines)
- Extract magic numbers to constants

**Estimated Cleanup:** Could reduce file size by ~150 lines (~12%) while improving maintainability.
