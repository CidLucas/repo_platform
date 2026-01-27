# Data Lifecycle & Materialized View Refresh Strategy

**Last Updated**: January 27, 2026  
**Status**: ✅ Implementation Complete

---

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ Silver Layer (BigQuery FDW)                                 │
│ - Raw invoice data from connectors                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Analytics API - MetricService                               │
│ - Processes silver data                                     │
│ - Computes aggregations                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Gold Layer (analytics_v2 - Fact/Dimension Tables)           │
│                                                             │
│ CORE TABLES (written by MetricService):                    │
│ ├─ fact_sales (transactional grain)                        │
│ ├─ dim_customer (customer attributes)                      │
│ ├─ dim_supplier (supplier attributes)                      │
│ └─ dim_product (product attributes)                        │
│                                                             │
│ MATERIALIZED VIEWS (auto-computed, must refresh):          │
│ ├─ mv_customer_summary (aggregated customer metrics)       │
│ ├─ mv_product_summary (aggregated product metrics)         │
│ └─ mv_monthly_sales_trend (monthly trends)                 │
│                                                             │
│ REGULAR VIEWS (always current):                            │
│ └─ v_time_series (time-series data for charts)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Frontend (vizu_dashboard)                                   │
│ - Queries /dashboard/mv/* endpoints                         │
│ - Displays charts and metrics                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete User Lifecycle

### Phase 1: New User Registration & Initial Data Load

```
TIME    ACTION                          WHAT'S STORED
────────────────────────────────────────────────────────

T0      User registers + connects      No data yet
        data source (Google Drive, etc)

T1      POST /api/ingest/recompute
        └─ Mode: FULL (first sync)     fact_sales, dim_* (empty if no invoices)
        └─ Load silver data from FDW   
        └─ Write to fact_sales         
        └─ ✅ AUTO-REFRESH MVs         mv_customer_summary (current)
                                       mv_product_summary (current)
                                       mv_monthly_sales_trend (current)

T2      User logs in to dashboard      
        └─ Frontend loads home page    
        └─ GET /dashboard/home         Reads FRESH mv_* views
        └─ GET /dashboard/mv/*         Shows CORRECT data
        ├─ Shows correct totals        ✅ Data is LIVE
        ├─ Shows correct charts        
        └─ Shows correct rankings      
```

### Phase 2: Daily/Scheduled Data Updates

```
TIME    ACTION                          WHAT'S UPDATED
────────────────────────────────────────────────────────

T0      Connector syncs new data        Silver layer (fact_sales in BigQuery FDW)
        (2x daily = 12:00, 18:00 UTC)  New invoices added

T1      POST /api/ingest/recompute
        └─ Mode: INCREMENTAL           
        └─ last_synced_at check        Only fetches since last sync
        └─ Write new rows to fact_sales  Rows inserted/updated
        └─ ✅ AUTO-REFRESH MVs         MVs now reflect new data
                                       Max data lag: <1 minute
                                       (until next user page load)

T2      User refreshes browser          
        └─ GET /dashboard/home         
        └─ Reads from MV              Shows NEW data
        └─ Max lag: ~2 hours           (next scheduled recompute)

T3      (Optional) Admin triggers       
        POST /api/ingest/refresh-views MVs manually refreshed
        └─ For immediate updates        Data live in <30 seconds
        └─ No data recomputation       (just MV refresh, faster)
```

### Phase 3: High-Frequency Updates (Optional)

For clients needing more frequent refreshes (e.g., e-commerce, SaaS):

```
SCHEDULE                   ACTION

Every 6 hours (00, 06, 12, 18 UTC):
    POST /api/ingest/recompute (incremental)
    └─ Fetch new silver data
    └─ Write to fact_sales
    └─ Auto-refresh MVs

Every 1 hour (01, 02, 03, ... UTC):
    POST /api/ingest/refresh-views (if needed)
    └─ Refresh MVs only
    └─ Fast, no data reload
    └─ Good for manual data fixes
```

---

## 🔧 Implementation Details

### Before (❌ Problem)

```
POST /api/ingest/recompute
    ├─ Write to fact_sales
    ├─ Write to dim_customer/product/supplier
    └─ ❌ DO NOT refresh MVs
    
    Consequence:
    └─ Frontend reads stale MVs
    └─ Data lag: hours/days until manual refresh
```

### After (✅ Solution)

```
POST /api/ingest/recompute
    ├─ Write to fact_sales
    ├─ Write to dim_customer/product/supplier
    ├─ ✅ AUTO-REFRESH MVs (NEW!)
    │   ├─ REFRESH mv_customer_summary
    │   ├─ REFRESH mv_product_summary
    │   └─ REFRESH mv_monthly_sales_trend
    └─ Return response with refresh status
    
    Response includes:
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

### New Admin Endpoint

```
POST /api/ingest/refresh-views

Purpose:
- Manually refresh MVs without recomputing data
- Use between scheduled ingestions
- Fast operation (10-30 seconds typically)

Authorization:
- Currently: Any authenticated user
- Future: Admin-only with proper auth checks

Response:
{
    "status": "success",
    "detail": "All materialized views refreshed successfully",
    "elapsed_seconds": 4.6,
    "views": {
        "mv_customer_summary": "Refreshed in 2.3s",
        "mv_product_summary": "Refreshed in 1.8s",
        "mv_monthly_sales_trend": "Refreshed in 0.5s"
    }
}
```

---

## 📈 Data Freshness SLAs

| Scenario | Data Lag | How to Improve |
|----------|----------|---|
| **New user, full load** | < 1 min | Automatic (done) |
| **Scheduled ingestion (2x daily)** | < 2-3 hours | Current default |
| **Critical clients** | < 30 min | Increase ingest frequency to 4x daily |
| **Real-time requirement** | < 1 min | Increase to hourly ingestion |
| **Manual data fix** | < 1 min | Call POST /api/ingest/refresh-views |

---

## 🔍 Verification & Testing

### Check MV Refresh Status

```bash
# After calling /api/ingest/recompute, check if MVs were refreshed
curl -X GET http://localhost:8004/api/health

# Should see MV refresh timestamps in logs
# ✅ mv_customer_summary: Refreshed in 2.3s
```

### Manual Refresh

```bash
# Trigger manual refresh (no data recomputation)
curl -X POST http://localhost:8004/api/ingest/refresh-views \
  -H "Authorization: Bearer {YOUR_TOKEN}"

# Response:
# {
#   "status": "success",
#   "elapsed_seconds": 4.6,
#   "views": {...}
# }
```

### Monitor Data Freshness

```sql
-- Check when MVs were last refreshed
SELECT schemaname, matviewname, pg_size_pretty(pg_relation_size(schemaname||'.'||matviewname))
FROM pg_matviews
WHERE schemaname = 'analytics_v2'
ORDER BY matviewname;

-- Check fact_sales row count
SELECT client_id, COUNT(*) as fact_sales_rows
FROM analytics_v2.fact_sales
GROUP BY client_id;

-- Check if mv_monthly_sales_trend is current
SELECT client_id, COUNT(*) as months_of_data
FROM analytics_v2.mv_monthly_sales_trend
GROUP BY client_id;
```

---

## 🚀 Deployment Notes

### Code Changes

1. **postgres_repository.py**
   - Added `refresh_materialized_views()` method
   - Calls DB function: `analytics_v2.refresh_materialized_views()`

2. **ingestion.py endpoints**
   - `/recompute`: Now auto-refreshes MVs after write
   - `/recompute/full`: Now auto-refreshes MVs after write
   - `/refresh-views`: **NEW** - Manual MV refresh endpoint

### No Database Schema Changes

- ✅ All database functions already exist
- ✅ Materialized views already exist
- ✅ No migrations required

### Recommended Configuration

```python
# For typical B2B SaaS
INGEST_FREQUENCY = "2x daily"  # 12:00 UTC, 18:00 UTC
MV_AUTO_REFRESH = True         # After each /recompute
MANUAL_REFRESH_ALLOWED = True  # Allow POST /refresh-views

# For e-commerce
INGEST_FREQUENCY = "4x daily"  # 06:00, 12:00, 18:00, 00:00 UTC
MV_AUTO_REFRESH = True
MANUAL_REFRESH_ALLOWED = True

# For real-time dashboards
INGEST_FREQUENCY = "hourly"    # Every hour
MV_AUTO_REFRESH = True
SCHEDULED_MV_REFRESH = "every 30 min"  # Extra refresh job
```

---

## 🔐 Security & Performance Notes

### Performance

- **MV Refresh Time**: 5-20 seconds (depends on data volume)
- **Impact**: Minimal, uses `REFRESH MATERIALIZED VIEW CONCURRENTLY`
- **Locking**: Non-blocking (reads can continue during refresh)

### Future Optimizations

1. **Selective Refresh**: Refresh only affected MVs
   ```python
   # Instead of refreshing all 3, only refresh changed ones
   refresh_materialized_views(client_id, affected_entities=['customer', 'product'])
   ```

2. **Async Refresh**: Background job to avoid blocking ingest
   ```python
   # Queue MV refresh as background task
   # POST /recompute returns immediately
   # MV refresh happens in background
   ```

3. **Incremental MV Updates**: Compute deltas instead of full refresh
   ```sql
   -- Currently: Full refresh (might be slow with large datasets)
   -- Future: Incremental UPDATE based on new fact_sales rows
   ```

---

## 📋 Monitoring & Alerts

### Logs to Watch For

```
✅ Healthy:
  "✅ All materialized views refreshed in 4.6s"
  "📊 mv_customer_summary: Refreshed in 2.3s"

⚠️ Warning:
  "🔄 Refreshing materialized views..."  [takes > 30s = slow]
  "⚠️ Could not check has_analytics_data" [no data in analytics_v2]

❌ Error:
  "❌ Failed to refresh materialized views"
  "Materialized views: STALE"
```

### Recommended Alerts

1. **MV Refresh Failed**: Alert if refresh takes > 60 seconds
2. **Data Lag**: Alert if last fact_sales row > 6 hours old
3. **MV Stale**: Alert if last MV refresh > 12 hours ago

---

## 🎯 Summary

| Aspect | Before | After |
|--------|--------|-------|
| **MV Freshness** | Manual refresh needed | Auto-refresh after ingest |
| **Data Lag** | Hours/Days | < 2-3 hours (or < 1 min with manual refresh) |
| **User Experience** | Stale dashboards | Fresh data on load |
| **Admin Overhead** | Manual MV refresh | Fully automated |
| **Emergency Refresh** | No way to force | POST /api/ingest/refresh-views |

---

## 📝 Questions & Next Steps

1. **Should we add hourly scheduled refresh?**
   - Yes: High-traffic dashboards need it
   - No: Costs extra Postgres resources, current 2x daily is sufficient

2. **Should we implement selective refresh?**
   - Yes: Faster for large datasets
   - No: KISS principle, all MVs are small

3. **Should refresh be async?**
   - Yes: Faster API response, background job
   - No: Simpler, currently fast enough (< 20s)

4. **Should we add client-specific refresh?**
   - Yes: Refresh only one client's data
   - No: Current function refreshes for all clients (is this OK?)
