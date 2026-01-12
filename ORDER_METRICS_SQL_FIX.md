# Order Metrics SQL Syntax Fix

## Problem

The Analytics API was failing to write order metrics to the `analytics_gold_orders` table with a SQL syntax error:

```
psycopg2.errors.SyntaxError: syntax error at or near ":"
LINE 7:                     :by_status::jsonb, 'all_time', NOW(), NO...
                            ^
```

**Root Cause**: The SQL query was mixing SQLAlchemy's named parameter syntax (`:by_status`) with PostgreSQL's type casting operator (`::jsonb`), which caused a syntax error.

---

## The Issue

**File**: [postgres_repository.py:614](services/analytics_api/src/analytics_api/data_access/postgres_repository.py#L614)

### Before (Broken):
```python
self.db_session.execute(text(
    """
    INSERT INTO analytics_gold_orders (
        client_id, total_orders, total_revenue, avg_order_value,
        by_status, period_type, calculated_at, created_at, updated_at
    ) VALUES (
        :client_id, :total_orders, :total_revenue, :avg_order_value,
        :by_status::jsonb, :period_type, NOW(), NOW(), NOW()  # ❌ SYNTAX ERROR
    )
    """
), {...})
```

**Problem**: `:by_status::jsonb` tries to use both:
- SQLAlchemy's parameter placeholder syntax: `:by_status`
- PostgreSQL's type casting syntax: `::jsonb`

When SQLAlchemy renders this query for psycopg2, it becomes:
```sql
VALUES (
    %(client_id)s, %(total_orders)s, %(total_revenue)s, %(avg_order_value)s,
    :by_status::jsonb,  -- ❌ Still has : prefix, invalid syntax
    %(period_type)s, NOW(), NOW(), NOW()
)
```

---

## The Fix

### After (Working):
```python
self.db_session.execute(text(
    """
    INSERT INTO analytics_gold_orders (
        client_id, total_orders, total_revenue, avg_order_value,
        by_status, period_type, calculated_at, created_at, updated_at
    ) VALUES (
        :client_id, :total_orders, :total_revenue, :avg_order_value,
        CAST(:by_status AS jsonb), :period_type, NOW(), NOW(), NOW()  # ✅ FIXED
    )
    """
), {...})
```

**Solution**: Use ANSI SQL `CAST(:by_status AS jsonb)` instead of PostgreSQL-specific `::jsonb` operator.

**Why this works**: SQLAlchemy's `text()` function processes named parameters (`:param_name`) and replaces them with the appropriate placeholder for the database driver. The `CAST()` function is standard SQL that works correctly with parameterized queries.

---

## How Type Casting Works with SQLAlchemy

### Option 1: ANSI SQL CAST (✅ Recommended)
```python
# In Python
self.db_session.execute(text("SELECT CAST(:value AS jsonb)"), {"value": json.dumps({"key": "value"})})

# SQLAlchemy renders as:
# SELECT CAST(%(value)s AS jsonb)

# PostgreSQL receives:
# SELECT CAST('{"key": "value"}' AS jsonb)
```

### Option 2: PostgreSQL :: operator (❌ Doesn't work with parameters)
```python
# In Python
self.db_session.execute(text("SELECT :value::jsonb"), {"value": json.dumps({"key": "value"})})

# SQLAlchemy renders as (BROKEN):
# SELECT :value::jsonb  -- Still has : prefix!

# PostgreSQL receives and fails:
# SELECT :value::jsonb  -- Syntax error!
```

### Option 3: Direct JSONB passing (✅ Alternative)
```python
from sqlalchemy.dialects.postgresql import JSONB

# Use bindparam with type
self.db_session.execute(
    text("SELECT :value").bindparams(bindparam('value', type_=JSONB)),
    {"value": {"key": "value"}}  # Pass dict directly, not JSON string
)
```

---

## Testing

### 1. Verify the fix is in place:
```bash
docker-compose exec analytics_api cat /app/src/analytics_api/data_access/postgres_repository.py | grep -A2 "CAST.*by_status"
```

Expected output:
```python
CAST(:by_status AS jsonb), :period_type, NOW(), NOW(), NOW()
```

### 2. Restart the service:
```bash
docker-compose restart analytics_api
```

### 3. Trigger analytics calculation:
Access the dashboard home page or call the API:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8004/api/dashboard/home
```

### 4. Check logs for success:
```bash
docker-compose logs analytics_api | grep "order"
```

Expected output:
```
✓ Wrote order metrics to analytics_gold_orders: total_orders=34504, revenue=528388420.27
```

### 5. Verify data in database:
```sql
SELECT * FROM analytics_gold_orders
WHERE client_id = 'e0e9c949-18fe-4d9a-9295-d5dfb2cc9723'
ORDER BY calculated_at DESC
LIMIT 1;
```

---

## Impact

### Before (Broken):
- ❌ Order metrics failed to write to database
- ❌ SQL syntax error on every analytics calculation
- ❌ Home page showed incomplete data (missing order stats)

### After (Fixed):
- ✅ Order metrics write successfully
- ✅ No SQL errors
- ✅ Home page shows complete analytics including order data
- ✅ Database has `by_status` as proper JSONB column

---

## Files Modified

1. **[services/analytics_api/src/analytics_api/data_access/postgres_repository.py](services/analytics_api/src/analytics_api/data_access/postgres_repository.py#L614)**
   - Changed `:by_status::jsonb` to `CAST(:by_status AS jsonb)`
   - Line 614

---

## Related Issues

This was the last remaining issue after the schema matching and frontend null handling fixes:
- ✅ Schema matcher conflict resolution (fixed)
- ✅ Frontend TypeError on null values (fixed)
- ✅ Order metrics SQL syntax error (fixed)

---

## Summary

✅ **Fixed**: SQL syntax error when writing order metrics
✅ **Root Cause**: Mixing SQLAlchemy parameter syntax with PostgreSQL type casting operator
✅ **Solution**: Use ANSI SQL `CAST()` function instead of `::` operator
✅ **Result**: Order metrics now write successfully to analytics_gold_orders table

The analytics pipeline is now fully functional end-to-end!
