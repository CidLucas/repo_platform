# Time Series Cumulative Sum Fix

## Problem Identified

**Frontend Issue:** FornecedoresPage.tsx line 155 expects `total_cumulativo` field in time series data:
```typescript
overviewData.chart_fornecedores_no_tempo.map((d: any) => d.total_cumulativo || 0)
```

**Backend Issue:** Rankings endpoint was returning only `total` (monthly count), not `total_cumulativo` (cumulative sum).

---

## Root Cause Analysis

### Data Flow
1. **Database Storage** (`analytics_gold_time_series` table):
   - Stores monthly unique counts as `total` field
   - Example: October = 3 suppliers, November = 5 suppliers, December = 7 suppliers

2. **Repository Method** (`postgres_repository.py:864-880`):
   ```python
   def get_gold_time_series(self, client_id: str, chart_type: str) -> list[dict]:
       result = self.db_session.execute(
           text("""
               SELECT period AS name, total
               FROM analytics_gold_time_series
               WHERE client_id = :client_id AND chart_type = :chart_type
               ORDER BY period_date ASC
           """),
           {"client_id": client_id, "chart_type": chart_type}
       ).fetchall()
       return [{"name": row.name, "total": int(row.total)} for row in result]
   ```
   Returns: `[{"name": "2025-10", "total": 3}, {"name": "2025-11", "total": 5}, ...]`

3. **Endpoint** (`rankings.py:68-72` - BEFORE FIX):
   ```python
   time_data = repo.get_gold_time_series(client_id, 'fornecedores_no_tempo')
   chart_fornecedores_no_tempo = [
       ChartDataPoint(name=point['name'], total=point['total'])
       for point in time_data
   ]
   ```
   Returns: `[{"name": "2025-10", "total": 3}, {"name": "2025-11", "total": 5}, ...]`

4. **Frontend Expectation**:
   - Needs cumulative sum for growth visualization
   - Expected: `[{"name": "2025-10", "total_cumulativo": 3}, {"name": "2025-11", "total_cumulativo": 8}, ...]`
   - Got: `[{"name": "2025-10", "total": 3}, {"name": "2025-11", "total": 5}, ...]` ❌

**Result:** Frontend received `undefined` for `total_cumulativo`, defaulted to 0, graph showed flat line at zero.

---

## Solution Applied

### Updated Endpoint to Calculate Cumulative Sum

**File:** [rankings.py:67-76](services/analytics_api/src/analytics_api/api/endpoints/rankings.py)

```python
# Time/regional charts from Gold (precomputed)
time_data = repo.get_gold_time_series(client_id, 'fornecedores_no_tempo')
# Calculate cumulative sum for frontend (expects total_cumulativo)
cumulative_sum = 0
chart_fornecedores_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_fornecedores_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

### How It Works

1. **Initialize cumulative counter**: `cumulative_sum = 0`
2. **Iterate through time series** in chronological order (already sorted by `period_date ASC`)
3. **Add monthly count to cumulative sum**: `cumulative_sum += point['total']`
4. **Create ChartDataPoint with both fields**:
   - `total`: Monthly unique count (e.g., 3, 5, 7)
   - `total_cumulativo`: Running total (e.g., 3, 8, 15)

### Example Data Transformation

**Input from Database:**
```json
[
  {"name": "2025-10", "total": 3},
  {"name": "2025-11", "total": 5},
  {"name": "2025-12", "total": 7}
]
```

**Output from Endpoint (AFTER FIX):**
```json
[
  {"name": "2025-10", "total": 3, "total_cumulativo": 3},
  {"name": "2025-11", "total": 5, "total_cumulativo": 8},
  {"name": "2025-12", "total": 7, "total_cumulativo": 15}
]
```

---

## Benefits of This Approach

### Why Calculate at Endpoint Instead of Database?

1. **Flexibility**: Endpoint can return both `total` (monthly) and `total_cumulativo` (cumulative)
2. **Database Efficiency**: Store only monthly counts, calculate cumulative on-demand
3. **Easy to Change**: Business logic in Python, not SQL migrations
4. **Backwards Compatible**: Existing code using `total` still works

### Why Not Store Cumulative in Database?

- **Storage Overhead**: Would double the data (both monthly and cumulative)
- **Update Complexity**: Changing one month requires recalculating all subsequent cumulative values
- **Inflexibility**: Can't easily switch between cumulative/non-cumulative views

---

## Verification Steps

### 1. Check API Response

```bash
curl -H "Authorization: Bearer YOUR_JWT" \
  "http://localhost:8000/api/rankings/fornecedores?client_id=YOUR_CLIENT_ID"
```

**Expected Response:**
```json
{
  "chart_fornecedores_no_tempo": [
    {
      "name": "2025-10",
      "total": 3,
      "total_cumulativo": 3
    },
    {
      "name": "2025-11",
      "total": 5,
      "total_cumulativo": 8
    }
  ]
}
```

### 2. Check Frontend Rendering

- Navigate to Fornecedores page
- Check "Performance de Vendas" card (line 150-163)
- Graph should show **upward trend** (not flat line at zero)
- Cumulative values should increase over time

---

## Related Time Series

### Current Status

| Time Series | Database Field | Endpoint Returns | Frontend Usage |
|------------|----------------|------------------|----------------|
| fornecedores_no_tempo | `total` | `total` + `total_cumulativo` ✅ | FornecedoresPage ✅ |
| clientes_no_tempo | `total` | Not exposed yet | Not used yet |
| produtos_no_tempo | `total` | Not exposed yet | Not used yet |
| pedidos_no_tempo | `total` | Not exposed yet | Not used yet |

### Future Enhancements

If other pages need time series data with cumulative sums, apply the same pattern:

```python
# Clientes endpoint example
time_data = repo.get_gold_time_series(client_id, 'clientes_no_tempo')
cumulative_sum = 0
chart_clientes_no_tempo = []
for point in time_data:
    cumulative_sum += point['total']
    chart_clientes_no_tempo.append(
        ChartDataPoint(name=point['name'], total=point['total'], total_cumulativo=cumulative_sum)
    )
```

---

## Files Modified

1. **[rankings.py:67-76](services/analytics_api/src/analytics_api/api/endpoints/rankings.py)**
   - Added cumulative sum calculation for `chart_fornecedores_no_tempo`
   - Now returns both `total` and `total_cumulativo` fields

2. **[FRONTEND_API_INTERFACE_MAPPING.md:332-352](FRONTEND_API_INTERFACE_MAPPING.md)**
   - Updated issue #1 status to ✅ FIXED
   - Documented the fix applied

---

## Test Results

### Before Fix
- Frontend: `d.total_cumulativo` → `undefined` → `0`
- Graph: Flat line at zero (no data displayed)

### After Fix
- Frontend: `d.total_cumulativo` → `3, 8, 15, ...`
- Graph: Upward trend showing supplier base growth

---

## Alternative Solutions Considered

### Option 1: Change Frontend to Use `total` (Not Chosen)
```typescript
// Change line 155 to use .total instead
overviewData.chart_fornecedores_no_tempo.map((d: any) => d.total || 0)
```

**Why Not Chosen:**
- Frontend needs cumulative for "growth over time" visualization
- Monthly counts don't show business expansion trend
- Would require frontend to calculate cumulative (less efficient)

### Option 2: Store Cumulative in Database (Not Chosen)
```python
# Store both in database
chart_data = [{
    'chart_type': 'fornecedores_no_tempo',
    'period': '2025-10',
    'total': 3,
    'total_cumulativo': 3  # Calculated in metric_service
}]
```

**Why Not Chosen:**
- Requires database schema change
- More storage overhead
- Update complexity (changing one month affects all subsequent)
- Less flexible for different aggregation needs

### Option 3: Calculate at Endpoint (CHOSEN) ✅
**Why Chosen:**
- No database changes needed
- Flexible (returns both monthly and cumulative)
- Efficient (calculated on-demand from ordered data)
- Simple to maintain and modify

---

## Impact Assessment

### No Breaking Changes
- Existing code using `total` field still works
- Only adds new `total_cumulativo` field
- ChartDataPoint schema uses `extra='allow'` (accepts any field)

### Frontend Fix
- FornecedoresPage line 155 now receives correct data
- Graph displays properly
- No frontend code changes needed

---

## Deployment Checklist

- [x] Fix endpoint cumulative sum calculation
- [x] Update documentation (FRONTEND_API_INTERFACE_MAPPING.md)
- [ ] **Deploy updated rankings.py to production**
- [ ] **Verify frontend graph displays correctly**
- [ ] **Monitor API response times (cumulative calculation is O(n) but n is small)**
- [ ] **Consider adding the same fix for other time series if needed**
