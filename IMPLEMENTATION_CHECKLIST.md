# Star Schema Correction: Implementation Checklist

## ✅ What's Been Completed

### Documentation & Design (✅ DONE)
- [x] Identified the architectural flaw (aggregates in wrong location)
- [x] Designed corrected star schema following Kimball methodology
- [x] Created comprehensive documentation:
  - `CORRECTED_STAR_SCHEMA_DESIGN.md` - Full guide with examples
  - `STAR_SCHEMA_VISUAL_GUIDE.md` - Visual diagrams and explanations
  - `STAR_SCHEMA_CORRECTION_SUMMARY.md` - Executive summary

### Database Schema (✅ READY TO DEPLOY)
- [x] Created SQL migration: `20260122_fix_star_schema_aggregates.sql`
  - Adds aggregate columns to dim_customer, dim_supplier, dim_product
  - Creates fact_sales (transactional table)
  - Creates fact_customer_product (bridge table)
  - Creates 3 materialized views
  - Creates triggers for automatic aggregate updates
  - Creates refresh function for views

### API Endpoints (✅ READY TO DEPLOY)
- [x] Created validation endpoints: `schema_validation.py`
  - `GET /api/debug/compare/{client_id}` - Compare old vs new
  - `GET /api/debug/validate/{client_id}` - Validate completeness
  - `GET /api/debug/metrics/{client_id}` - Get detailed metrics

---

## 📋 Implementation Steps (TO DO)

### Phase 1: Database Migration
- [ ] **Deploy SQL Migration**
  ```bash
  cd /Users/lucascruz/Documents/GitHub/vizu-mono
  # Option A: Via Supabase CLI
  supabase db push supabase/migrations/20260122_fix_star_schema_aggregates.sql

  # Option B: Via Supabase dashboard
  # SQL Editor → Copy & paste migration content → Execute
  ```

- [ ] **Verify Schema Changes**
  ```sql
  -- Check dimension columns added
  SELECT column_name FROM information_schema.columns
  WHERE table_schema = 'analytics_v2'
  AND table_name = 'dim_customer'
  ORDER BY column_name;
  -- Should include: total_orders, total_revenue, avg_order_value, frequency_per_month, recency_days, etc.

  -- Check new tables created
  SELECT table_name FROM information_schema.tables
  WHERE table_schema = 'analytics_v2'
  ORDER BY table_name;
  -- Should include: fact_sales, fact_customer_product

  -- Check materialized views
  SELECT matviewname FROM pg_matviews
  WHERE schemaname = 'analytics_v2';
  -- Should include: mv_customer_summary, mv_product_summary, mv_monthly_sales_trend

  -- Check triggers exist
  SELECT trigger_name FROM information_schema.triggers
  WHERE trigger_schema = 'analytics_v2';
  -- Should include: trig_update_customer_metrics, trig_update_product_metrics
  ```

### Phase 2: Update ETL Code
- [ ] **Update metric_service.py**
  - [ ] Modify `write_dim_customer()` to populate aggregates from metric calculations
    ```python
    def write_dim_customer(self, client_id: str, customers_data: list[dict]) -> int:
        # Ensure each customer dict has:
        # - total_orders (from self.df_clientes_agg)
        # - total_revenue (from self.df_clientes_agg)
        # - avg_order_value (calculated)
        # - frequency_per_month (from metric calc)
        # - recency_days (from metric calc)
        # etc.
    ```

  - [ ] Modify `write_dim_product()` similarly with product metrics

  - [ ] Add new `write_fact_sales()` method
    ```python
    def write_fact_sales(self, client_id: str, orders_data: list[dict]) -> int:
        # Takes raw transaction data (self.df, not aggregated)
        # Writes one row per order line item
        # Grain: (order_id, line_item_sequence)
    ```

  - [ ] Add new `write_fact_customer_product()` method
    ```python
    def write_fact_customer_product(self, client_id: str, customer_product_data: list[dict]) -> int:
        # Writes customer-product pairs
        # Grain: (customer_cpf_cnpj, product_name)
    ```

  - [ ] Remove or stop calling `write_fact_order_metrics()` and `write_fact_product_metrics()`
    (These were the wrong implementations)

### Phase 3: Deploy API Validation Endpoints
- [ ] **Copy validation endpoints file**
  ```bash
  # Already created in:
  /services/analytics_api/src/analytics_api/api/endpoints/schema_validation.py
  ```

- [ ] **Register endpoints in main FastAPI app**
  ```python
  # In services/analytics_api/src/analytics_api/main.py or your router setup:
  from .api.endpoints.schema_validation import router as validation_router
  app.include_router(validation_router)
  ```

- [ ] **Test endpoints locally**
  ```bash
  # Start API server
  cd services/analytics_api
  uvicorn src.analytics_api.main:app --reload

  # Test with a known client_id (e.g., test client from Phase 3)
  curl http://localhost:8000/api/debug/compare/e0e9c949-18fe-4d9a-9295-d5dfb2cc9723
  curl http://localhost:8000/api/debug/validate/e0e9c949-18fe-4d9a-9295-d5dfb2cc9723
  curl http://localhost:8000/api/debug/metrics/e0e9c949-18fe-4d9a-9295-d5dfb2cc9723
  ```

### Phase 4: Testing Strategy
- [ ] **Test 1: Verify Dimension Aggregates**
  ```sql
  -- For test client
  SELECT
    customer_id,
    total_orders,
    total_revenue,
    avg_order_value,
    frequency_per_month,
    recency_days
  FROM analytics_v2.dim_customer
  WHERE client_id = 'test-client-id'
  LIMIT 5;
  -- Should have non-zero aggregates populated
  ```

- [ ] **Test 2: Verify Fact Table Grain**
  ```sql
  -- fact_sales should have more rows than orders
  SELECT
    COUNT(*) as total_line_items,
    COUNT(DISTINCT order_id) as unique_orders,
    (COUNT(*) > COUNT(DISTINCT order_id)) as has_multiple_items_per_order
  FROM analytics_v2.fact_sales
  WHERE client_id = 'test-client-id';
  -- Should show multiple line items per order
  ```

- [ ] **Test 3: Trigger Auto-Update**
  ```sql
  -- Manually insert a fact_sales row and verify dimension updates
  BEGIN;

  -- Insert test row
  INSERT INTO analytics_v2.fact_sales (
    client_id, order_id, customer_cpf_cnpj, product_name, quantity, unit_price
  ) VALUES (
    'test-client-id', 'TEST-ORDER', '123.456.789-00', 'Test Product', 10, 100.00
  );

  -- Check if dim_customer was updated
  SELECT total_orders, total_revenue
  FROM analytics_v2.dim_customer
  WHERE cpf_cnpj = '123.456.789-00';

  ROLLBACK;  -- Don't keep test data
  ```

- [ ] **Test 4: Compare Schemas**
  ```bash
  # API endpoint test
  curl http://localhost:8000/api/debug/compare/test-client-id

  # Response should show:
  # {
  #   "schemas_match": true,
  #   "migration_status": "ready",
  #   "differences": {...}
  # }
  ```

- [ ] **Test 5: Validate Migration**
  ```bash
  curl http://localhost:8000/api/debug/validate/test-client-id

  # Response should show:
  # {
  #   "all_valid": true,
  #   "status": "✅ PASSED",
  #   "validation_checks": {...}
  # }
  ```

- [ ] **Test 6: Run Full ETL Cycle**
  ```bash
  # Upload test data via data_ingestion_api
  # Let ETL process
  # Check that:
  # - dim_customer has populated aggregates
  # - fact_sales has transactional data
  # - fact_customer_product has customer-product pairs
  # - Materialized views are populated
  ```

### Phase 5: Materialized View Refresh Setup
- [ ] **Schedule View Refreshes (Optional)**
  ```bash
  # If using scheduled jobs (e.g., via Supabase Edge Functions):
  SELECT analytics_v2.refresh_materialized_views();

  # Or call from Python:
  db_session.execute(text("SELECT analytics_v2.refresh_materialized_views();"))
  ```

- [ ] **Monitor View Refresh Performance**
  - Time how long refreshes take
  - Consider running during off-peak hours
  - May take 30+ seconds for large datasets

### Phase 6: Data Consistency Monitoring
- [ ] **Create Monitoring Query**
  ```sql
  -- Verify dimension aggregates match fact sums
  SELECT
    d.customer_id,
    d.total_orders as dim_orders,
    COUNT(DISTINCT f.order_id) as fact_orders,
    (d.total_orders = COUNT(DISTINCT f.order_id)) as match
  FROM analytics_v2.dim_customer d
  LEFT JOIN analytics_v2.fact_sales f
    ON d.cpf_cnpj = f.customer_cpf_cnpj
    AND d.client_id = f.client_id
  WHERE d.client_id = 'client-id'
  GROUP BY d.customer_id, d.total_orders
  HAVING d.total_orders != COUNT(DISTINCT f.order_id);

  -- Should return NO ROWS if triggers are working
  ```

- [ ] **Add Health Check Endpoint** (Optional)
  ```python
  @router.get("/api/health/star-schema/{client_id}")
  async def check_star_schema_health(client_id: str):
      """Quick health check for star schema consistency"""
      # Run consistency check from above query
      # Return pass/fail
  ```

### Phase 7: Deprecation & Cleanup
- [ ] **Keep Gold Tables for 2-3 Months**
  - Maintain dual compatibility
  - Monitor for issues
  - Keep for rollback capability

- [ ] **After Stability Confirmed**
  - Remove fallback from read endpoints
  - Consider archiving vs deleting gold tables
  - Update documentation

---

## 📊 Success Criteria

After implementation, verify:

✅ **Dimensions**: All have correct aggregates
```sql
SELECT COUNT(*) FROM analytics_v2.dim_customer WHERE total_orders > 0;
-- Should return > 0
```

✅ **Fact Tables**: Have correct grain
```sql
SELECT COUNT(*) / COUNT(DISTINCT order_id) as avg_lines_per_order
FROM analytics_v2.fact_sales;
-- Should be > 1 (multiple items per order)
```

✅ **Triggers**: Auto-updating aggregates
```sql
-- Insert test row, verify dimension updated
-- (See Phase 4: Test 3)
```

✅ **Validation Endpoints**: All pass
```bash
curl http://localhost:8000/api/debug/validate/{client_id}
# all_valid = true
```

✅ **Consistency**: Facts and dimensions match
```sql
-- Run monitoring query (Phase 6)
-- Should return ZERO mismatches
```

✅ **Performance**: Queries are fast
```sql
-- Direct dimension read < 1ms
-- Materialized view read < 0.1ms
-- Join between dim + fact < 10ms
```

---

## ⏱️ Estimated Timeline

| Phase | Task | Estimated Time |
|-------|------|-----------------|
| 1 | Deploy SQL migration | 5-10 minutes |
| 2 | Update ETL code | 1-2 hours |
| 3 | Deploy API endpoints | 30 minutes |
| 4 | Testing & validation | 1-2 hours |
| 5 | View refresh setup | 30 minutes |
| 6 | Monitoring setup | 1 hour |
| **Total** | | **4-7 hours** |

---

## 🆘 Troubleshooting

### Issue: "Triggers not firing"
- Check: `SELECT * FROM pg_trigger WHERE tgname LIKE 'trig_update%';`
- Verify: Triggers are enabled (should be by default)
- Test: Manual insert to verify trigger execution

### Issue: "Dimension aggregates not updating"
- Check: Trigger code in schema migration
- Test: Manual update via trigger statement
- Verify: Constraints allow writes to aggregate columns

### Issue: "Materialized views very slow"
- Check: View refresh time
- Consider: Scheduling during off-peak hours
- Option: Disable concurrent refresh if locking issues

### Issue: "Data mismatch between dimension and facts"
- Check: Trigger logic is correct
- Verify: No concurrent updates causing race conditions
- Consider: Recalculating aggregates via batch job

---

## 📞 Key Contacts & Resources

- **Schema Migration**: `supabase/migrations/20260122_fix_star_schema_aggregates.sql`
- **Validation Endpoints**: `/services/analytics_api/src/analytics_api/api/endpoints/schema_validation.py`
- **Documentation**:
  - `CORRECTED_STAR_SCHEMA_DESIGN.md`
  - `STAR_SCHEMA_VISUAL_GUIDE.md`
  - `STAR_SCHEMA_CORRECTION_SUMMARY.md`

---

**Status**: Ready for implementation!
**Next Step**: Deploy SQL migration, then update ETL code
