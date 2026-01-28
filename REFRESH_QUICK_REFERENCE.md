# Quick Reference: Data Refresh Strategy

## 🎯 The Three-Layer Architecture

```
SILVER (BigQuery FDW)
  ↓ MetricService.recompute()
GOLD (fact_sales + dim_*)
  ↓ Materialized Views (need refresh!)
FRONTEND (React Dashboard)
```

## 📊 Current Lifecycle (NOW FIXED ✅)

### 1️⃣ New User Registration
```
POST /api/ingest/recompute
├─ Write to fact_sales (new transactions)
├─ Write to dim_customer/product/supplier (new entities)
└─ ✅ AUTO-REFRESH MVs (AUTOMATIC)
    ├─ mv_customer_summary
    ├─ mv_product_summary
    └─ mv_monthly_sales_trend
```

### 2️⃣ Scheduled Data Ingestion (2x/day)
```
[Connector] ─→ New data arrives
              ↓
POST /api/ingest/recompute (incremental=true)
├─ Load only NEW silver data
├─ Write to fact_sales
└─ ✅ AUTO-REFRESH MVs
```

### 3️⃣ Manual Refresh (If Needed)
```
POST /api/ingest/refresh-views
├─ NO data recomputation
├─ Just refresh MVs
└─ Fast (10-30 seconds)
```

---

## 🔄 Before vs After

| Step | Before ❌ | After ✅ |
|------|-----------|--------|
| Write data | ✅ Works | ✅ Works |
| Refresh MVs | ❌ Manual/None | ✅ Automatic |
| Data lag | Hours/Days | <2-3 hours |
| User experience | Stale dashboards | Fresh data |

---

## 📈 Response Format

```json
POST /api/ingest/recompute

{
  "status": "success",
  "mode": "full|incremental",
  "rows_processed": 12345,
  "materialized_views_refreshed": true,
  "materialized_views": {
    "mv_customer_summary": "Refreshed in 2.3s",
    "mv_product_summary": "Refreshed in 1.8s",
    "mv_monthly_sales_trend": "Refreshed in 0.5s"
  }
}
```

---

## 🚀 New Endpoints

### Automatic (Part of /recompute)
```
POST /api/ingest/recompute
POST /api/ingest/recompute/full
└─ Both now auto-refresh MVs
```

### Manual Admin Refresh
```
POST /api/ingest/refresh-views

Response:
{
  "status": "success",
  "elapsed_seconds": 4.6,
  "views": {
    "mv_customer_summary": "Refreshed in 2.3s",
    "mv_product_summary": "Refreshed in 1.8s",
    "mv_monthly_sales_trend": "Refreshed in 0.5s"
  }
}
```

---

## ⚡ Performance

| Operation | Time | Frequency |
|-----------|------|-----------|
| MV Refresh | 5-20s | Auto after ingest |
| Full Recompute | 30-120s | 2x/day (or as needed) |
| Incremental Recompute | 5-30s | 2x/day |

---

## 🔍 Monitoring Checklist

- [ ] MV refresh completes < 30s
- [ ] Last fact_sales insert < 6 hours ago
- [ ] Frontend shows current data
- [ ] No "STALE" warnings in logs
- [ ] Charts update after ingest

---

## 🎓 Architecture Diagram

```
User Logs In
    ↓
GET /dashboard/home
    ↓
SELECT FROM mv_monthly_sales_trend  ← MUST be fresh!
    ↓
Show Charts

Data Flow:
────────
Source Data
    ↓
POST /recompute
    ├─ Write fact_sales
    └─ ✅ Refresh MVs (AUTO)
         ↓
      Data now FRESH
         ↓
    Frontend reads fresh MVs
         ↓
    User sees current data
```

---

## ✅ How to Verify It's Working

```bash
# 1. Trigger recompute
curl -X POST http://localhost:8004/api/ingest/recompute \
  -H "Authorization: Bearer $TOKEN"

# Look for in response:
# "materialized_views_refreshed": true

# 2. Check logs for:
# ✅ All materialized views refreshed in X.Xs
# ✅ mv_customer_summary: Refreshed in Xs

# 3. Verify in database
psql -c "
  SELECT client_id, COUNT(*) as rows
  FROM analytics_v2.mv_monthly_sales_trend
  GROUP BY client_id;
"

# 4. Test dashboard loads fresh data
# Go to http://localhost:3000/dashboard
# Refresh page → Should show up-to-date charts
```

---

## 🐛 Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Charts show old data | MVs not refreshed | Call POST /api/ingest/refresh-views |
| Refresh takes > 1 min | Large dataset | Normal, monitor performance |
| fact_sales empty | No data ingested | Run POST /api/ingest/recompute |
| MV refresh fails | DB connection issue | Check logs, retry |

---

## 📋 Configuration

For **most B2B clients**:
```python
INGEST_FREQUENCY = 2  # 2x daily (12:00, 18:00 UTC)
AUTO_REFRESH_MVS = True
ALLOW_MANUAL_REFRESH = True
```

For **e-commerce clients**:
```python
INGEST_FREQUENCY = 4  # 4x daily
AUTO_REFRESH_MVS = True
SCHEDULED_MV_REFRESH = "every 30 min"
```

For **real-time dashboards**:
```python
INGEST_FREQUENCY = "hourly"
AUTO_REFRESH_MVS = True
SCHEDULED_MV_REFRESH = "every 15 min"
```
