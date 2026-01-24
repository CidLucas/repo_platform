# Star Schema Visual Guide

## ❌ What We Had (Wrong)

```
FACT Tables (with AGGREGATES - WRONG!)
┌─────────────────────────────────────────────┐
│ fact_order_metrics                          │
├─────────────────────────────────────────────┤
│ order_id    │ total_orders │ total_revenue  │  ← These are AGGREGATES!
│ order_id_2  │ total_orders │ total_revenue  │  ← Belongs in DIMENSION!
│ ...         │ ...          │ ...            │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ fact_product_metrics                        │
├─────────────────────────────────────────────┤
│ product_id  │ total_qty_sold  │ total_rev   │  ← These are AGGREGATES!
│ product_id_2│ total_qty_sold  │ total_rev   │  ← Belongs in DIMENSION!
│ ...         │ ...             │ ...         │
└─────────────────────────────────────────────┘

Problem: Aggregates in facts, dimensions flat, no transactional data
```

## ✅ Correct Architecture

```
DIMENSIONS (with AGGREGATES)
─────────────────────────────────────────────────────────────────

┌─ dim_customer ─────────────────────────────────────────┐
│ Attributes:                                            │
│  customer_id│ name        │ cpf_cnpj    │ estado      │
│  001        │ João Silva  │ 123.456...  │ SP          │
│  002        │ Maria Foo   │ 789.012...  │ RJ          │
│                                                        │
│ AGGREGATES (Calculated from fact_sales):              │
│  total_orders│ total_revenue│ avg_order_value│ freq...│
│  45          │ R$50,000     │ R$1,111       │ 3.2/mo │
│  28          │ R$28,500     │ R$1,018       │ 2.1/mo │
└────────────────────────────────────────────────────────┘

┌─ dim_supplier ──────────────────────────────────────────┐
│ Attributes:                                             │
│  supplier_id│ name         │ emitter_cnpj│ estado      │
│  S001       │ Empresa A    │ 111.222...  │ MG          │
│  S002       │ Empresa B    │ 333.444...  │ BA          │
│                                                         │
│ AGGREGATES (Calculated from fact_sales):               │
│  total_orders_received│ total_revenue│ avg_order_value │
│  120                  │ R$180,000    │ R$1,500        │
│  89                   │ R$95,000     │ R$1,067        │
└─────────────────────────────────────────────────────────┘

┌─ dim_product ───────────────────────────────────────────┐
│ Attributes:                                             │
│  product_id│ product_name   │ categoria    │ unit      │
│  P001      │ Parafuso 5mm   │ Hardware     │ caixa     │
│  P002      │ Pneu 205/55R16 │ Pneus        │ unidade   │
│                                                         │
│ AGGREGATES (Calculated from fact_sales):               │
│  total_qty_sold│ total_revenue│ avg_price│ orders_count│
│  5,000         │ R$15,000     │ R$3.00   │ 234        │
│  1,200         │ R$96,000     │ R$80.00  │ 156        │
└─────────────────────────────────────────────────────────┘


FACT TABLES (TRANSACTIONAL - One row per transaction detail)
─────────────────────────────────────────────────────────────────

┌─ fact_sales [GRAIN: order_id + line_item_sequence] ────┐
│ TRANSACTIONAL DATA (one row per product per order)     │
├───────────────────────────────────────────────────────┤
│ order_id│customer│supplier│product    │qty│unit_price │
│ ORD001  │001     │S001    │P001       │10 │ R$3.00   │
│ ORD001  │001     │S002    │P002       │2  │ R$80.00  │  ← Same order, 2 items
│ ORD002  │002     │S001    │P001       │50 │ R$3.00   │
│ ORD003  │001     │S001    │P001       │5  │ R$3.00   │
│ ...     │...     │...     │...        │...│ ...      │
│                                                        │
│ Key Point: One row PER LINE ITEM, not aggregated!     │
└────────────────────────────────────────────────────────┘

┌─ fact_customer_product [GRAIN: customer + product] ────┐
│ BRIDGE TABLE (customer-product pairs)                  │
├──────────────────────────────────────────────────────┤
│ customer_id│product_id│qty_purchased│times_purchased  │
│ 001        │P001      │ 250         │ 34              │
│ 001        │P002      │ 15          │ 8               │
│ 002        │P001      │ 120         │ 14              │
│ 002        │P003      │ 50          │ 2               │
│                                                        │
│ Answers: "Which products does each customer buy?"     │
└──────────────────────────────────────────────────────┘


MATERIALIZED VIEWS (Pre-computed for Performance)
─────────────────────────────────────────────────────────────────

┌─ mv_customer_summary ───────────────────────────┐
│ SELECT c.*, COUNT(f.order_id), SUM(f.revenue)   │
│ FROM dim_customer c JOIN fact_sales f ...       │
│ GROUP BY c.customer_id;                         │
│                                                  │
│ Result: Pre-computed, fast queries for UI      │
└──────────────────────────────────────────────────┘

┌─ mv_product_summary ────────────────────────────┐
│ SELECT p.*, COUNT(f.order_id), SUM(f.qty)       │
│ FROM dim_product p JOIN fact_sales f ...        │
│ GROUP BY p.product_id;                          │
└──────────────────────────────────────────────────┘

┌─ mv_monthly_sales_trend ────────────────────────┐
│ SELECT DATE_TRUNC('month', order_date),         │
│        COUNT(*), SUM(revenue), ...               │
│ FROM fact_sales GROUP BY month;                 │
└──────────────────────────────────────────────────┘
```

## Data Consistency: How Triggers Keep Things In Sync

```
ETL writes new fact_sales row:
┌──────────────────────────────────┐
│ fact_sales insert:               │
│ ORD999 | 001 | S001 | P001 | ... │  ← New transaction
└──────────────────────────────────┘
           ↓
     TRIGGER FIRES AUTOMATICALLY
           ↓
┌──────────────────────────────────────────────────────┐
│ Trigger: update_customer_metrics_trigger()           │
├──────────────────────────────────────────────────────┤
│ UPDATE dim_customer SET                              │
│   total_orders = (count distinct orders for cust)   │
│   total_revenue = (sum revenue for cust)            │
│   avg_order_value = (avg revenue for cust)          │
│ WHERE customer_id = 001;                            │
└──────────────────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────────────────┐
│ Trigger: update_product_metrics_trigger()            │
├──────────────────────────────────────────────────────┤
│ UPDATE dim_product SET                               │
│   total_quantity_sold = (sum qty for product)       │
│   total_revenue = (sum revenue for product)         │
│   number_of_orders = (count orders with product)    │
│ WHERE product_id = P001;                            │
└──────────────────────────────────────────────────────┘
           ↓
        RESULT:
   Dimensions automatically stay in sync
   with fact table changes! ✅
```

## Query Examples

### ❌ Old Way (Wrong - Aggregates Scattered)
```sql
-- Can't even tell if the aggregate is correct
SELECT * FROM fact_order_metrics WHERE customer_id = '001';
-- Returns pre-computed aggregate, but is it up-to-date?
-- Who computed it? When?
```

### ✅ New Way (Correct - Aggregate in Dimension)
```sql
-- Read aggregate directly from dimension
SELECT total_orders, total_revenue, avg_order_value
FROM dim_customer
WHERE customer_id = '001';

-- Verify by calculating from facts
SELECT
  COUNT(DISTINCT order_id) as orders,
  SUM(line_total) as revenue
FROM fact_sales
WHERE customer_cpf_cnpj = (SELECT cpf_cnpj FROM dim_customer WHERE customer_id = '001');

-- If they don't match, check triggers (they should always match!)
```

## Testing: Compare Old vs New

```bash
# Endpoint shows side-by-side:
GET /api/debug/compare/client-id

old_schema:
  customers: 1,624
  time_series: 960
  regional: 106

new_schema:
  customers: 1,624        ✅ Match!
  time_series: 960        ✅ Match!
  regional: 106           ✅ Match!
  fact_sales: 45,000      ← New transactional data

Result: schemas_match = true, migration_status = "ready"
```

## Performance Comparison

```
OLD APPROACH (Wrong):
┌────────────────────────┐
│ Query: Get customer    │
│ metrics               │
├────────────────────────┤
│ SELECT * FROM         │
│ fact_order_metrics    │
│ Direct read           │
│ Response: < 1ms       │
│ But: Unclear if       │
│ aggregate is correct  │
└────────────────────────┘

NEW APPROACH (Correct):
┌────────────────────────────────┐
│ Query: Get customer metrics    │
├────────────────────────────────┤
│ SELECT * FROM dim_customer     │
│ Direct read of aggregate       │
│ Response: < 1ms                │
│ Benefit: Guaranteed to match   │
│ fact_sales via triggers        │
│                                │
│ Optional: Use materialized     │
│ view for even more speed       │
│ mv_customer_summary            │
│ Response: < 0.1ms              │
└────────────────────────────────┘
```

---

**Key Takeaway**:
- Dimensions hold attributes + aggregates ✅
- Facts hold transactions at consistent grain ✅
- Triggers keep them in sync automatically ✅
- Views provide pre-computed queries for speed ✅
- Everything validated via comparison endpoints ✅
