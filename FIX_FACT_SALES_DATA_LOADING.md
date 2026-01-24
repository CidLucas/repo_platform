# Fix Data Flow: Schema Matcher → fact_sales

**Problem**: Data loads successfully to `dim_*` tables but `fact_sales` remains empty.

**Root Cause**: The data ingestion pipeline doesn't have logic to populate `fact_sales` with transactional data from source invoices.

---

## 📊 Current Data Flow (Incomplete)

```
Source Invoice Data
    ↓ (extracted from XML/REST)
Schema Matcher Service
    ↓ (maps columns)
Canonical Invoice Format
    ↓ (silver layer)
    ├→ dim_customer (WORKS ✅) - Static dimension
    ├→ dim_supplier (MAYBE)
    ├→ dim_product (WORKS ✅) - Static dimension
    └→ fact_sales (MISSING ❌) - Should contain transactions!
        └→ Views auto-compute aggregates (v_time_series, v_regional, etc.)
```

---

## 🔍 What Should Happen

### Option A: Direct SQL Insert (Recommended)
After schema matching, instead of just writing dimensions, execute:

```sql
-- Step 1: Ensure dimensions exist
INSERT INTO analytics_v2.dim_customer (client_id, cpf_cnpj, name, telefone, ...)
VALUES (?, ?, ?, ?, ...)
ON CONFLICT (client_id, cpf_cnpj) DO UPDATE SET ...;

INSERT INTO analytics_v2.dim_supplier (client_id, cnpj, name, ...)
VALUES (?, ?, ?, ...)
ON CONFLICT (client_id, cnpj) DO UPDATE SET ...;

INSERT INTO analytics_v2.dim_product (client_id, product_name, ...)
VALUES (?, ?, ...)
ON CONFLICT (client_id, product_name) DO UPDATE SET ...;

-- Step 2: Insert fact from matched invoice
INSERT INTO analytics_v2.fact_sales (
    client_id,
    customer_id,
    supplier_id,
    product_id,
    order_id,
    data_transacao,
    quantidade,
    valor_unitario,
    valor_total,
    customer_cpf_cnpj,
    supplier_cnpj
)
SELECT
    :client_id,
    (SELECT customer_id FROM dim_customer WHERE cpf_cnpj = :receiver_cpf_cnpj AND client_id = :client_id),
    (SELECT supplier_id FROM dim_supplier WHERE cnpj = :emitter_cnpj AND client_id = :client_id),
    (SELECT product_id FROM dim_product WHERE product_name = :product_name AND client_id = :client_id),
    :order_id,
    :data_transacao::TIMESTAMPTZ,
    :quantidade,
    :valor_unitario,
    :valor_total,
    :receiver_cpf_cnpj,
    :emitter_cnpj
WHERE (SELECT customer_id FROM dim_customer WHERE cpf_cnpj = :receiver_cpf_cnpj AND client_id = :client_id) IS NOT NULL
  AND (SELECT supplier_id FROM dim_supplier WHERE cnpj = :emitter_cnpj AND client_id = :client_id) IS NOT NULL
  AND (SELECT product_id FROM dim_product WHERE product_name = :product_name AND client_id = :client_id) IS NOT NULL;
```

---

## 📝 Data Mapping Reference

From **invoice source** → **fact_sales columns**:

| Source Field | Target Column | Note |
|---|---|---|
| `emitter_cnpj` | `supplier_cnpj` | Supplier who issued invoice |
| `emitter_nome` | `dim_supplier.name` | Lookup supplier_id via cnpj |
| `receiver_cpf_cnpj` | `customer_cpf_cnpj` | Customer who received |
| `receiver_nome` | `dim_customer.name` | Lookup customer_id via cpf_cnpj |
| `raw_product_description` | `dim_product.product_name` | Lookup product_id via name |
| `order_id` | `order_id` | Invoice/order number |
| `data_transacao` | `data_transacao` | Transaction date/time |
| `quantidade` | `quantidade` | Line item qty |
| `valor_unitario` | `valor_unitario` | Unit price |
| `valor_total_emitter` OR `valor_total` | `valor_total` | Line total |

---

## 🚀 Implementation Steps

### Step 1: Check Current State
```sql
-- Verify what data we have
SELECT COUNT(*) FROM analytics_v2.dim_customer;  -- Should have data
SELECT COUNT(*) FROM analytics_v2.dim_supplier;  -- Might be empty
SELECT COUNT(*) FROM analytics_v2.dim_product;   -- Should have data
SELECT COUNT(*) FROM analytics_v2.fact_sales;    -- Should be EMPTY (this is the problem!)
```

### Step 2: Fix Data Ingestion Service
Update `data_ingestion_api` to write fact_sales after dimensions:

```python
# In the invoice processing flow:

# 1. Write dimension tables (already done)
write_dim_customer(matched_data)
write_dim_supplier(matched_data)
write_dim_product(matched_data)

# 2. NEW: Write fact_sales
write_fact_sales(
    client_id=client_id,
    order_id=matched_data['order_id'],
    data_transacao=matched_data['data_transacao'],
    customer_cpf_cnpj=matched_data['receiver_cpf_cnpj'],
    supplier_cnpj=matched_data['emitter_cnpj'],
    product_name=matched_data['raw_product_description'],
    quantidade=matched_data['quantidade'],
    valor_unitario=matched_data['valor_unitario'],
    valor_total=matched_data['valor_total']
)
```

### Step 3: Verify with Views
Once fact_sales has data:

```sql
-- These will now return data!
SELECT * FROM analytics_v2.v_time_series WHERE client_id = 'your-client';
SELECT * FROM analytics_v2.v_regional WHERE client_id = 'your-client';
SELECT * FROM analytics_v2.v_last_orders WHERE client_id = 'your-client';
SELECT * FROM analytics_v2.v_customer_products WHERE client_id = 'your-client';
```

---

## 📍 Where to Make Changes

**File**: `/services/analytics_api/src/analytics_api/services/metric_service.py`
- Lines 350-450: Where customer & product data is written
- **ADD**: New method `write_fact_sales()` after dimensions are written

**File**: `/services/analytics_api/src/analytics_api/data_access/postgres_repository.py`
- Implement `write_fact_sales()` method with proper FK lookups
- Handle errors gracefully (missing dimension records)

---

## ⚠️ Important Notes

1. **Foreign Key Integrity**: fact_sales REQUIRES valid customer_id, supplier_id, product_id
   - Must load dimensions FIRST
   - Must skip any invoices with missing dimensions

2. **On Conflict**: Use business keys for upsert:
   ```sql
   ON CONFLICT (client_id, customer_id, supplier_id, product_id, order_id, line_item_sequence)
   DO UPDATE SET valor_total = EXCLUDED.valor_total, updated_at = NOW();
   ```

3. **Aggregate Updates**: Triggers will auto-update dimension aggregates when fact_sales is inserted

4. **Views Auto-Update**: Once fact_sales has data, all views (v_time_series, v_regional, etc.) will auto-populate

---

## ✅ Success Criteria

After implementing fact_sales writes:

1. ✅ `SELECT COUNT(*) FROM analytics_v2.fact_sales` > 0
2. ✅ API calls to dashboard no longer fail on missing views
3. ✅ Time-series view returns data: `SELECT * FROM v_time_series`
4. ✅ Regional view returns data: `SELECT * FROM v_regional`
5. ✅ Customer metrics auto-update: `SELECT total_revenue FROM dim_customer`

---

## 🔧 Quick Fix (Temporary)

If you want to manually test the views with sample data:

```sql
-- Insert test customer
INSERT INTO analytics_v2.dim_customer (client_id, cpf_cnpj, name)
VALUES ('test-client', '123.456.789-00', 'Test Customer')
RETURNING customer_id;

-- Insert test supplier
INSERT INTO analytics_v2.dim_supplier (client_id, cnpj, name)
VALUES ('test-client', '12.345.678/0001-90', 'Test Supplier')
RETURNING supplier_id;

-- Insert test product
INSERT INTO analytics_v2.dim_product (client_id, product_name)
VALUES ('test-client', 'Test Product')
RETURNING product_id;

-- Insert test transaction
INSERT INTO analytics_v2.fact_sales (
    client_id, customer_id, supplier_id, product_id,
    order_id, data_transacao, quantidade, valor_unitario, valor_total,
    customer_cpf_cnpj, supplier_cnpj
)
VALUES (
    'test-client',
    (SELECT customer_id FROM dim_customer WHERE cpf_cnpj = '123.456.789-00'),
    (SELECT supplier_id FROM dim_supplier WHERE cnpj = '12.345.678/0001-90'),
    (SELECT product_id FROM dim_product WHERE product_name = 'Test Product'),
    'ORD-001',
    NOW(),
    100.00,
    10.00,
    1000.00,
    '123.456.789-00',
    '12.345.678/0001-90'
);

-- Now test the view
SELECT * FROM analytics_v2.v_time_series WHERE client_id = 'test-client';
```

If this returns data, views work. If nothing, check fact_sales inserts succeeded.
