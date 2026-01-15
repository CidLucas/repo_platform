# Time Series Charts Fix - Complete Solution

## Problem Identified

**Missing Time Series in gold_time_series table:**
- ✅ fornecedores_no_tempo (existed)
- ✅ clientes_no_tempo (existed)
- ❌ produtos_no_tempo (missing)
- ❌ pedidos_no_tempo (missing)

The `_write_time_series_charts()` method was only generating time series for suppliers and customers, but not for products and orders.

---

## Solution Applied

### Added produtos_no_tempo (Products Over Time)

**File:** [metric_service.py:536-559](services/analytics_api/src/analytics_api/services/metric_service.py)

```python
# Produtos no tempo (products over time)
if 'raw_product_description' in self.df.columns:
    df_time = self.df.copy()
    dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
    df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
    df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

    # Count unique products per month
    time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['raw_product_description'].nunique().reset_index()
    time_series.rename(columns={'raw_product_description': 'total'}, inplace=True)

    chart_data = [
        {
            'chart_type': 'produtos_no_tempo',
            'dimension': 'products',
            'period': row['ano_mes'],
            'period_date': pd.Timestamp(row['period_date']).date(),
            'total': int(row['total'])
        }
        for _, row in time_series.iterrows()
    ]

    if chart_data:
        self.repository.write_gold_time_series(self.client_id, chart_data)
        logger.info(f"  ✓ Written {len(chart_data)} produtos time series points")
```

**What it does:**
- Groups transactions by month (`ano_mes`)
- Counts unique products (`raw_product_description`) per month
- Creates time series showing product catalog growth/changes over time

**Example data:**
```json
{
  "chart_type": "produtos_no_tempo",
  "dimension": "products",
  "period": "2025-10",
  "period_date": "2025-10-01",
  "total": 12  // 12 unique products sold in October 2025
}
```

---

### Added pedidos_no_tempo (Orders Over Time)

**File:** [metric_service.py:561-584](services/analytics_api/src/analytics_api/services/metric_service.py)

```python
# Pedidos no tempo (orders over time - count of orders, not unique entities)
if 'order_id' in self.df.columns:
    df_time = self.df.copy()
    dt_no_tz = df_time['data_transacao'].dt.tz_localize(None)
    df_time['ano_mes'] = dt_no_tz.dt.to_period('M').astype(str)
    df_time['period_date'] = dt_no_tz.dt.to_period('M').dt.to_timestamp()

    # Count unique order_ids per month
    time_series = df_time.dropna(subset=['ano_mes']).groupby(['ano_mes', 'period_date'])['order_id'].nunique().reset_index()
    time_series.rename(columns={'order_id': 'total'}, inplace=True)

    chart_data = [
        {
            'chart_type': 'pedidos_no_tempo',
            'dimension': 'orders',
            'period': row['ano_mes'],
            'period_date': pd.Timestamp(row['period_date']).date(),
            'total': int(row['total'])
        }
        for _, row in time_series.iterrows()
    ]

    if chart_data:
        self.repository.write_gold_time_series(self.client_id, chart_data)
        logger.info(f"  ✓ Written {len(chart_data)} pedidos time series points")
```

**What it does:**
- Groups transactions by month (`ano_mes`)
- Counts unique orders (`order_id`) per month
- Creates time series showing order volume over time

**Example data:**
```json
{
  "chart_type": "pedidos_no_tempo",
  "dimension": "orders",
  "period": "2025-10",
  "period_date": "2025-10-01",
  "total": 35  // 35 orders placed in October 2025
}
```

---

## Complete Time Series Coverage

After the fix, `analytics_gold_time_series` table now includes:

| chart_type | dimension | What it tracks |
|------------|-----------|----------------|
| fornecedores_no_tempo | suppliers | Unique suppliers per month |
| clientes_no_tempo | customers | Unique customers per month |
| produtos_no_tempo | products | Unique products sold per month |
| pedidos_no_tempo | orders | Total orders per month |

All time series use the same structure:
- `period`: String month (e.g., "2025-10")
- `period_date`: Date timestamp (e.g., 2025-10-01)
- `total`: Count for that month
- `dimension`: Entity type (suppliers/customers/products/orders)

---

## Test Results

**Before Fix:**
```
✓ Written 4 fornecedores time series points
✓ Written 4 clientes time series points
```

**After Fix:**
```
✓ Written 4 fornecedores time series points
✓ Written 4 clientes time series points
✓ Written 4 produtos time series points    ← NEW
✓ Written 4 pedidos time series points     ← NEW
```

All tests passing with 4 months of data for each time series.

---

## Frontend Integration

The frontend can now query all 4 time series:

### Query Products Over Time
```sql
SELECT period, period_date, total
FROM analytics_gold_time_series
WHERE client_id = 'your-client-id'
  AND chart_type = 'produtos_no_tempo'
ORDER BY period_date ASC;
```

### Query Orders Over Time
```sql
SELECT period, period_date, total
FROM analytics_gold_time_series
WHERE client_id = 'your-client-id'
  AND chart_type = 'pedidos_no_tempo'
ORDER BY period_date ASC;
```

---

## Use Cases

### produtos_no_tempo (Products Time Series)
**Business Value:**
- Track product catalog expansion over time
- Identify months with new product launches
- Monitor product portfolio diversity
- Detect seasonal product offerings

**Example Insight:**
- "Product catalog grew from 12 to 18 items between Q4 2025 and Q1 2026"
- "Only 8 products were sold in January (out of 15 total) - investigate inactive products"

### pedidos_no_tempo (Orders Time Series)
**Business Value:**
- Track order volume trends
- Identify seasonal patterns
- Monitor business growth
- Detect anomalies or drops in order activity

**Example Insight:**
- "Order volume increased 25% month-over-month in December (holiday season)"
- "Average 35 orders/month with peak of 45 in November"

---

## Database Schema

No schema changes required - the `analytics_gold_time_series` table already supports all chart types via the `chart_type` column:

```sql
CREATE TABLE analytics_gold_time_series (
    id UUID PRIMARY KEY,
    client_id TEXT NOT NULL,
    chart_type TEXT NOT NULL,  -- 'fornecedores_no_tempo', 'clientes_no_tempo', 'produtos_no_tempo', 'pedidos_no_tempo'
    dimension TEXT,             -- 'suppliers', 'customers', 'products', 'orders'
    period TEXT,                -- '2025-10', '2025-11', etc.
    period_date TIMESTAMPTZ,    -- 2025-10-01, 2025-11-01, etc.
    total INTEGER,              -- Count for that period
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Deployment Checklist

- [x] Add produtos_no_tempo calculation
- [x] Add pedidos_no_tempo calculation
- [x] Test with sample data (all passing)
- [ ] **Deploy updated code to production**
- [ ] **Re-process existing client data**
- [ ] **Verify all 4 time series in database**
- [ ] **Update frontend charts to display products and orders time series**

---

## Files Modified

1. **[metric_service.py:536-584](services/analytics_api/src/analytics_api/services/metric_service.py)**
   - Added `produtos_no_tempo` time series (lines 536-559)
   - Added `pedidos_no_tempo` time series (lines 561-584)

---

## Comparison with Other Dimensions

| Dimension | What's Counted | Business Meaning |
|-----------|----------------|------------------|
| **fornecedores_no_tempo** | Unique suppliers | Supplier network expansion/retention |
| **clientes_no_tempo** | Unique customers | Customer acquisition and retention |
| **produtos_no_tempo** | Unique products | Product catalog diversity and growth |
| **pedidos_no_tempo** | Unique orders | Transaction volume and business activity |

All four metrics combined give a complete picture of business growth across all dimensions.
