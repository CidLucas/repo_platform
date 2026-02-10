# ERP API Specification

## Overview

Asynchronous (writes) and synchronous (reads) multi-tenant ERP API for orders, purchases, transactions, inventory, customers, and suppliers.

- **Write endpoints** (POST/PATCH): Queued — return immediate `202` with `job_id`
- **Read endpoints** (GET): Synchronous — return immediate `200` with data

## Authentication

- JWT required for every request
- JWT includes `client_id` for tenant isolation
- Header: `Authorization: Bearer {token}`

## General Patterns

### Write Operations
- All POST/PATCH requests are queued; immediate `202` response: `{ status: "queued", job_id, message }`
- Idempotency via `external_id`
- Required fields marked with `*`
- Non-required fields are optional

### Read Operations
- All GET requests return immediate `200` responses
- Paginated list responses use envelope: `{ data: [...], pagination: { total, limit, offset, has_more } }`
- Default pagination: `limit=50`, `offset=0` (max `limit=200`)
- All list endpoints support `sort_by` and `sort_order` (`asc` | `desc`) query params
- Multi-tenant isolation enforced server-side via JWT `client_id`

### Common Query Parameters (all list endpoints)

| Parameter    | Type   | Default | Description                       |
|--------------|--------|---------|-----------------------------------|
| `limit`      | int    | 50      | Page size (max 200)               |
| `offset`     | int    | 0       | Number of records to skip         |
| `sort_by`    | string | varies  | Field to sort by (per endpoint)   |
| `sort_order` | string | `desc`  | Sort direction: `asc` or `desc`   |

### Pagination Response

```json
{
  "data": [ ... ],
  "pagination": {
    "total": 248,
    "limit": 50,
    "offset": 0,
    "has_more": true
  }
}
```

---

## Errors

**Format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "fields": { "field_name": "error detail" }
  }
}
```

**Error codes:** `VALIDATION_ERROR`, `AUTH_ERROR`, `NOT_FOUND`, `DUPLICATE`, `INTERNAL_ERROR`

**Status codes:** `200`, `202`, `400`, `401`, `404`, `409`, `500`

---

## Endpoints

---

### Orders

#### POST /api/orders
Create customer order.

**Body:**
- `customer_cpf_cnpj`
- `order_number`
- `order_date`
- `products*` — array of `{ product_name, sku, quantity, unit_price*, categoria, ncm, cfop }`
- `delivery_date`
- `shipping_address`
- `notes`
- `external_id`

**Response (202):** `{ status, job_id, order_id }`

#### PATCH /api/orders/{order_id}
Update order status.

**Body:** `status`, `payment_status`, `delivery_date`, `notes`

**Response (202):** `{ status, job_id }`

#### GET /api/orders
List orders with pagination, filtering, and sorting. Each order is an aggregation of its line items.

**Query Parameters:**

| Parameter     | Type   | Default           | Description                           |
|---------------|--------|-------------------|---------------------------------------|
| `limit`       | int    | 50                | Page size                             |
| `offset`      | int    | 0                 | Skip N records                        |
| `sort_by`     | string | `data_transacao`  | Sort field: `data_transacao`, `order_total`, `line_count` |
| `sort_order`  | string | `desc`            | `asc` or `desc`                       |
| `date_from`   | date   | —                 | Filter from this date                 |
| `date_to`     | date   | —                 | Filter until this date                |
| `customer_id` | UUID   | —                 | Filter by customer                    |
| `supplier_id` | UUID   | —                 | Filter by supplier                    |
| `search`      | string | —                 | Search in order_id or customer name   |
| `min_total`   | float  | —                 | Minimum order total                   |
| `max_total`   | float  | —                 | Maximum order total                   |

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "ORD-2024-001",
      "data_transacao": "2024-06-15T10:30:00Z",
      "customer_name": "Maria Silva",
      "customer_cpf_cnpj": "123.456.789-00",
      "supplier_name": "Distribuidora ABC",
      "line_count": 3,
      "order_total": 1250.00
    }
  ],
  "pagination": { "total": 120, "limit": 50, "offset": 0, "has_more": true }
}
```

#### GET /api/orders/{order_id}
Full order detail with all line items.

**Path Parameter:** `order_id` (string)

**Response (200):**
```json
{
  "order_id": "ORD-2024-001",
  "data_transacao": "2024-06-15T10:30:00Z",
  "customer_id": "uuid",
  "customer_name": "Maria Silva",
  "customer_cpf_cnpj": "123.456.789-00",
  "supplier_id": "uuid",
  "supplier_name": "Distribuidora ABC",
  "supplier_cnpj": "12.345.678/0001-90",
  "line_items": [
    {
      "line_item_sequence": 1,
      "product_id": "uuid",
      "product_name": "Widget A",
      "quantidade": 10,
      "valor_unitario": 50.00,
      "valor_total": 500.00
    },
    {
      "line_item_sequence": 2,
      "product_id": "uuid",
      "product_name": "Widget B",
      "quantidade": 5,
      "valor_unitario": 150.00,
      "valor_total": 750.00
    }
  ],
  "order_total": 1250.00,
  "total_items": 2,
  "total_quantity": 15
}
```

---

### Purchase Orders

#### POST /api/purchase-orders
Create supplier purchase order.

**Body:**
- `supplier_cnpj`
- `po_number`
- `order_date`
- `products*` — array of `{ product_name, sku, quantity, unit_price*, categoria, ncm, cfop }`
- `expected_delivery`
- `payment_terms`
- `notes`
- `external_id`

**Response (202):** `{ status, job_id, purchase_order_id }`

#### PATCH /api/purchase-orders/{po_id}
Update purchase order status.

**Body:** `status`, `received_date`, `payment_status`, `notes`

**Response (202):** `{ status, job_id }`

#### GET /api/purchase-orders
List purchase orders (supplier-centric view). Same data as orders but grouped/filtered by supplier.

**Query Parameters:**

| Parameter     | Type   | Default           | Description                           |
|---------------|--------|-------------------|---------------------------------------|
| `limit`       | int    | 50                | Page size                             |
| `offset`      | int    | 0                 | Skip N records                        |
| `sort_by`     | string | `data_transacao`  | Sort field: `data_transacao`, `order_total`, `line_count` |
| `sort_order`  | string | `desc`            | `asc` or `desc`                       |
| `date_from`   | date   | —                 | Filter from this date                 |
| `date_to`     | date   | —                 | Filter until this date                |
| `supplier_id` | UUID   | —                 | Filter by supplier                    |
| `search`      | string | —                 | Search in PO number or supplier name  |

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "PO-2024-050",
      "data_transacao": "2024-06-10T08:00:00Z",
      "supplier_name": "Distribuidora ABC",
      "supplier_cnpj": "12.345.678/0001-90",
      "customer_name": null,
      "line_count": 5,
      "order_total": 8400.00
    }
  ],
  "pagination": { "total": 34, "limit": 50, "offset": 0, "has_more": false }
}
```

#### GET /api/purchase-orders/{po_id}
Full purchase order detail. Same structure as `GET /api/orders/{order_id}`.

---

### Transactions

#### POST /api/transactions
Record a transaction.

**Body:**
- `transaction_type*` — `"sale"` | `"purchase"` | `"payment"` | `"refund"` | `"inventory_adjustment"`
- `transaction_date`
- `amount`
- `customer_cpf_cnpj` — for sale/payment to customer
- `supplier_cnpj` — for purchase/payment to supplier
- `order_id`
- `purchase_order_id`
- `product_name`, `sku`, `quantity`, `unit_price`
- `payment_method`
- `reference_type`, `reference_id`
- `status`
- `external_id`

**Response (202):** `{ status, job_id, transaction_id }`

#### GET /api/transactions
List raw individual transactions (line-item level). Useful for auditing and reconciliation.

**Query Parameters:**

| Parameter     | Type   | Default          | Description                          |
|---------------|--------|------------------|--------------------------------------|
| `limit`       | int    | 50               | Page size (max 200)                  |
| `offset`      | int    | 0                | Skip N records                       |
| `sort_by`     | string | `data_transacao` | Sort field: `data_transacao`, `valor_total`, `quantidade` |
| `sort_order`  | string | `desc`           | `asc` or `desc`                      |
| `date_from`   | date   | —                | From date                            |
| `date_to`     | date   | —                | To date                              |
| `order_id`    | string | —                | Filter by order                      |
| `customer_id` | UUID   | —                | Filter by customer                   |
| `supplier_id` | UUID   | —                | Filter by supplier                   |
| `product_id`  | UUID   | —                | Filter by product                    |

**Response (200):**
```json
{
  "data": [
    {
      "fact_id": "uuid",
      "order_id": "ORD-2024-001",
      "line_item_sequence": 1,
      "data_transacao": "2024-06-15T10:30:00Z",
      "customer_cpf_cnpj": "123.456.789-00",
      "customer_name": "Maria Silva",
      "supplier_cnpj": "12.345.678/0001-90",
      "supplier_name": "Distribuidora ABC",
      "product_name": "Widget A",
      "quantidade": 10,
      "valor_unitario": 50.00,
      "valor_total": 500.00,
      "created_at": "2024-06-15T10:31:00Z"
    }
  ],
  "pagination": { "total": 1580, "limit": 50, "offset": 0, "has_more": true }
}
```

---

### Inventory

#### POST /api/inventory/adjustments
Manual stock adjustment.

**Body:**
- `product_name`, `sku`
- `adjustment_type` — `"increase"` | `"decrease"` | `"correction"`
- `quantity`
- `reason`
- `warehouse_location`
- `transaction_date`
- `external_id`

**Response (202):** `{ status, job_id, transaction_id }`

#### POST /api/inventory/restock
Receive supplier delivery.

**Body:**
- `purchase_order_id`
- `products*` — array of `{ product_name, sku, quantity_received, warehouse_location }`
- `received_date*`
- `notes`
- `external_id`

**Response (202):** `{ status, job_id }`

#### GET /api/inventory
Current stock levels for all products.

**Query Parameters:**

| Parameter       | Type   | Default         | Description                             |
|-----------------|--------|-----------------|-----------------------------------------|
| `limit`         | int    | 50              | Page size                               |
| `offset`        | int    | 0               | Skip N records                          |
| `sort_by`       | string | `product_name`  | Sort field: `product_name`, `current_stock`, `last_movement_date` |
| `sort_order`    | string | `asc`           | `asc` or `desc`                         |
| `search`        | string | —               | Search by product name or SKU           |
| `below_minimum` | bool   | false           | If true, only products below minimum stock level |
| `warehouse`     | string | —               | Filter by warehouse location            |

**Response (200):**
```json
{
  "data": [
    {
      "product_id": "uuid",
      "product_name": "Widget A",
      "sku": "WDG-A-001",
      "current_stock": 145,
      "minimum_stock": 50,
      "warehouse_location": "Warehouse-SP",
      "last_movement_date": "2024-06-14T16:00:00Z",
      "last_movement_type": "restock",
      "total_sold": 850,
      "total_restocked": 995,
      "updated_at": "2024-06-14T16:00:00Z"
    }
  ],
  "pagination": { "total": 67, "limit": 50, "offset": 0, "has_more": true }
}
```

#### GET /api/inventory/{product_id}
Stock detail for a specific product, including current levels and summary stats.

**Path Parameter:** `product_id` (UUID)

**Response (200):**
```json
{
  "product_id": "uuid",
  "product_name": "Widget A",
  "sku": "WDG-A-001",
  "current_stock": 145,
  "minimum_stock": 50,
  "warehouse_location": "Warehouse-SP",
  "last_movement_date": "2024-06-14T16:00:00Z",
  "last_movement_type": "restock",
  "total_sold": 850,
  "total_restocked": 995,
  "total_adjustments": 0,
  "avg_daily_consumption": 4.2,
  "days_of_stock_remaining": 34,
  "updated_at": "2024-06-14T16:00:00Z"
}
```

#### GET /api/inventory/{product_id}/movements
Stock movement history for a specific product.

**Path Parameter:** `product_id` (UUID)

**Query Parameters:**

| Parameter       | Type   | Default              | Description                             |
|-----------------|--------|----------------------|-----------------------------------------|
| `limit`         | int    | 50                   | Page size                               |
| `offset`        | int    | 0                    | Skip N records                          |
| `sort_by`       | string | `movement_date`      | Sort field: `movement_date`, `quantity`  |
| `sort_order`    | string | `desc`               | `asc` or `desc`                         |
| `date_from`     | date   | —                    | From date                               |
| `date_to`       | date   | —                    | To date                                 |
| `movement_type` | string | —                    | Filter: `sale`, `restock`, `adjustment`  |

**Response (200):**
```json
{
  "data": [
    {
      "movement_id": "uuid",
      "movement_type": "sale",
      "movement_date": "2024-06-15T10:30:00Z",
      "quantity": -10,
      "stock_after": 145,
      "reference_type": "order",
      "reference_id": "ORD-2024-001",
      "notes": null
    },
    {
      "movement_id": "uuid",
      "movement_type": "restock",
      "movement_date": "2024-06-14T16:00:00Z",
      "quantity": 200,
      "stock_after": 155,
      "reference_type": "purchase_order",
      "reference_id": "PO-2024-050",
      "notes": "Supplier delivery received"
    }
  ],
  "pagination": { "total": 42, "limit": 50, "offset": 0, "has_more": false }
}
```

---

### Customers

#### POST /api/customers
Register customer.

**Body:**
- `cpf_cnpj`, `name`, `telefone`
- `endereco_rua`, `endereco_numero`, `endereco_bairro`, `endereco_cidade`, `endereco_uf`, `endereco_cep`
- `customer_type`
- `credit_limit`
- `status` — default `"active"`
- `external_id`

**Response (202):** `{ status, job_id, customer_id }`

#### PATCH /api/customers/{customer_id}
Update customer. Any fields optional.

**Response (202):** `{ status, job_id }`

#### GET /api/customers
List customers with pagination, filtering, and sorting.

**Query Parameters:**

| Parameter      | Type   | Default         | Description                                |
|----------------|--------|-----------------|--------------------------------------------|
| `limit`        | int    | 50              | Page size                                  |
| `offset`       | int    | 0               | Skip N records                             |
| `sort_by`      | string | `total_revenue` | Sort field: `name`, `total_revenue`, `total_orders`, `recency_days`, `cluster_tier`, `created_at` |
| `sort_order`   | string | `desc`          | `asc` or `desc`                            |
| `search`       | string | —               | Case-insensitive search on name and cpf_cnpj |
| `uf`           | string | —               | Filter by state (endereco_uf)              |
| `cidade`       | string | —               | Filter by city (endereco_cidade)           |
| `cluster_tier` | string | —               | Filter by tier: `A`, `B`, `C`, `D`         |
| `min_revenue`  | float  | —               | Minimum total_revenue                      |
| `max_revenue`  | float  | —               | Maximum total_revenue                      |
| `active_only`  | bool   | false           | If true, only customers with recency <= 90 days |

**Response (200):**
```json
{
  "data": [
    {
      "customer_id": "uuid",
      "name": "Maria Silva",
      "cpf_cnpj": "123.456.789-00",
      "telefone": "(11) 99999-0000",
      "endereco_cidade": "São Paulo",
      "endereco_uf": "SP",
      "total_orders": 45,
      "total_revenue": 28500.00,
      "avg_order_value": 633.33,
      "recency_days": 12,
      "cluster_tier": "A",
      "created_at": "2023-01-15T10:00:00Z",
      "updated_at": "2024-06-15T10:30:00Z"
    }
  ],
  "pagination": { "total": 248, "limit": 50, "offset": 0, "has_more": true }
}
```

#### GET /api/customers/{customer_id}
Full customer detail.

**Path Parameter:** `customer_id` (UUID)

**Response (200):**
```json
{
  "customer_id": "uuid",
  "name": "Maria Silva",
  "cpf_cnpj": "123.456.789-00",
  "telefone": "(11) 99999-0000",
  "endereco_rua": "Rua Augusta",
  "endereco_numero": "1234",
  "endereco_bairro": "Consolação",
  "endereco_cidade": "São Paulo",
  "endereco_uf": "SP",
  "endereco_cep": "01310-100",
  "total_orders": 45,
  "total_revenue": 28500.00,
  "avg_order_value": 633.33,
  "total_quantity": 312,
  "orders_last_30_days": 3,
  "frequency_per_month": 3.75,
  "recency_days": 12,
  "lifetime_start_date": "2023-01-15",
  "lifetime_end_date": "2024-06-15",
  "cluster_score": 87.5,
  "cluster_tier": "A",
  "created_at": "2023-01-15T10:00:00Z",
  "updated_at": "2024-06-15T10:30:00Z"
}
```

#### GET /api/customers/{customer_id}/orders
List all orders placed by a specific customer.

**Path Parameter:** `customer_id` (UUID)

**Query Parameters:**

| Parameter    | Type   | Default          | Description              |
|--------------|--------|------------------|--------------------------|
| `limit`      | int    | 50               | Page size                |
| `offset`     | int    | 0                | Skip N records           |
| `sort_by`    | string | `data_transacao` | Sort field               |
| `sort_order` | string | `desc`           | `asc` or `desc`          |
| `date_from`  | date   | —                | From date                |
| `date_to`    | date   | —                | To date                  |

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "ORD-2024-001",
      "data_transacao": "2024-06-15T10:30:00Z",
      "line_count": 3,
      "order_total": 1250.00,
      "supplier_name": "Distribuidora ABC"
    }
  ],
  "pagination": { "total": 45, "limit": 50, "offset": 0, "has_more": false }
}
```

#### GET /api/customers/{customer_id}/products
Products this customer has purchased, with aggregated stats.

**Path Parameter:** `customer_id` (UUID)

**Query Parameters:** `limit` (50), `offset` (0)

**Response (200):**
```json
{
  "data": [
    {
      "product_id": "uuid",
      "product_name": "Widget A",
      "total_quantity": 120,
      "total_spent": 6000.00,
      "purchase_count": 15,
      "last_purchase": "2024-06-15T10:30:00Z"
    }
  ],
  "pagination": { "total": 22, "limit": 50, "offset": 0, "has_more": false }
}
```

#### GET /api/customers/lookup
Look up a customer by CPF/CNPJ. Used during order creation to auto-populate customer data.

**Query Parameters:**

| Parameter   | Type   | Required | Description        |
|-------------|--------|----------|--------------------|
| `cpf_cnpj`  | string | yes      | Customer CPF/CNPJ  |

**Response (200):** Same as `GET /api/customers/{customer_id}` or `404` if not found.

---

### Suppliers

#### POST /api/suppliers
Register supplier.

**Body:**
- `cnpj`, `name`, `telefone`
- `endereco_cidade`, `endereco_uf`
- `payment_terms`
- `status` — default `"active"`
- `external_id`

**Response (202):** `{ status, job_id, supplier_id }`

#### PATCH /api/suppliers/{supplier_id}
Update supplier. Any fields optional.

**Response (202):** `{ status, job_id }`

#### GET /api/suppliers
List suppliers with pagination, filtering, and sorting.

**Query Parameters:**

| Parameter      | Type   | Default         | Description                                     |
|----------------|--------|-----------------|-------------------------------------------------|
| `limit`        | int    | 50              | Page size                                       |
| `offset`       | int    | 0               | Skip N records                                  |
| `sort_by`      | string | `total_revenue` | Sort field: `name`, `total_revenue`, `total_orders_received`, `recency_days`, `total_products_supplied`, `created_at` |
| `sort_order`   | string | `desc`          | `asc` or `desc`                                  |
| `search`       | string | —               | Case-insensitive search on name and cnpj         |
| `uf`           | string | —               | Filter by state (endereco_uf)                    |
| `cidade`       | string | —               | Filter by city (endereco_cidade)                 |
| `min_revenue`  | float  | —               | Minimum total_revenue                            |
| `max_revenue`  | float  | —               | Maximum total_revenue                            |

**Response (200):**
```json
{
  "data": [
    {
      "supplier_id": "uuid",
      "name": "Distribuidora ABC",
      "cnpj": "12.345.678/0001-90",
      "telefone": "(11) 3333-4444",
      "endereco_cidade": "São Paulo",
      "endereco_uf": "SP",
      "total_orders_received": 120,
      "total_revenue": 450000.00,
      "avg_order_value": 3750.00,
      "total_products_supplied": 34,
      "recency_days": 5,
      "cluster_tier": "A",
      "created_at": "2022-06-01T08:00:00Z",
      "updated_at": "2024-06-15T10:30:00Z"
    }
  ],
  "pagination": { "total": 18, "limit": 50, "offset": 0, "has_more": false }
}
```

#### GET /api/suppliers/{supplier_id}
Full supplier detail.

**Path Parameter:** `supplier_id` (UUID)

**Response (200):**
```json
{
  "supplier_id": "uuid",
  "name": "Distribuidora ABC",
  "cnpj": "12.345.678/0001-90",
  "telefone": "(11) 3333-4444",
  "endereco_cidade": "São Paulo",
  "endereco_uf": "SP",
  "total_orders_received": 120,
  "total_revenue": 450000.00,
  "avg_order_value": 3750.00,
  "total_products_supplied": 34,
  "frequency_per_month": 10.0,
  "recency_days": 5,
  "first_transaction_date": "2022-06-15",
  "last_transaction_date": "2024-06-15",
  "cluster_score": 92.0,
  "cluster_tier": "A",
  "created_at": "2022-06-01T08:00:00Z",
  "updated_at": "2024-06-15T10:30:00Z"
}
```

#### GET /api/suppliers/{supplier_id}/orders
List all orders placed with this supplier.

**Path Parameter:** `supplier_id` (UUID)

**Query Parameters:** Same as `GET /api/customers/{customer_id}/orders`

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "PO-2024-050",
      "data_transacao": "2024-06-10T08:00:00Z",
      "line_count": 5,
      "order_total": 8400.00,
      "customer_name": "Loja XYZ"
    }
  ],
  "pagination": { "total": 120, "limit": 50, "offset": 0, "has_more": true }
}
```

#### GET /api/suppliers/{supplier_id}/products
Products supplied by this supplier, with aggregated stats.

**Path Parameter:** `supplier_id` (UUID)

**Query Parameters:** `limit` (50), `offset` (0)

**Response (200):**
```json
{
  "data": [
    {
      "product_id": "uuid",
      "product_name": "Widget A",
      "total_quantity": 5000,
      "total_value": 125000.00,
      "order_count": 48,
      "last_supplied": "2024-06-10T08:00:00Z"
    }
  ],
  "pagination": { "total": 34, "limit": 50, "offset": 0, "has_more": false }
}
```

#### GET /api/suppliers/lookup
Look up a supplier by CNPJ. Used during purchase order creation.

**Query Parameters:**

| Parameter | Type   | Required | Description     |
|-----------|--------|----------|-----------------|
| `cnpj`    | string | yes      | Supplier CNPJ   |

**Response (200):** Same as `GET /api/suppliers/{supplier_id}` or `404` if not found.

---

### Products

#### GET /api/products
List products with pagination, filtering, and sorting.

**Query Parameters:**

| Parameter      | Type   | Default         | Description                                |
|----------------|--------|-----------------|--------------------------------------------|
| `limit`        | int    | 50              | Page size                                  |
| `offset`       | int    | 0               | Skip N records                             |
| `sort_by`      | string | `total_revenue` | Sort field: `product_name`, `total_revenue`, `total_quantity_sold`, `number_of_orders`, `avg_price`, `cluster_tier`, `created_at` |
| `sort_order`   | string | `desc`          | `asc` or `desc`                            |
| `search`       | string | —               | Case-insensitive search on product_name    |
| `categoria`    | string | —               | Filter by product category                 |
| `cluster_tier` | string | —               | Filter by tier: `A`, `B`, `C`, `D`         |
| `min_revenue`  | float  | —               | Minimum total_revenue                      |

**Response (200):**
```json
{
  "data": [
    {
      "product_id": "uuid",
      "product_name": "Widget A",
      "categoria": "Components",
      "ncm": "8471.30.19",
      "total_quantity_sold": 850,
      "total_revenue": 42500.00,
      "avg_price": 50.00,
      "number_of_orders": 85,
      "cluster_tier": "A",
      "created_at": "2023-03-01T12:00:00Z",
      "updated_at": "2024-06-15T10:30:00Z"
    }
  ],
  "pagination": { "total": 67, "limit": 50, "offset": 0, "has_more": true }
}
```

#### GET /api/products/{product_id}
Full product detail.

**Path Parameter:** `product_id` (UUID)

**Response (200):**
```json
{
  "product_id": "uuid",
  "product_name": "Widget A",
  "categoria": "Components",
  "ncm": "8471.30.19",
  "cfop": "5102",
  "total_quantity_sold": 850,
  "total_revenue": 42500.00,
  "avg_price": 50.00,
  "number_of_orders": 85,
  "avg_quantity_per_order": 10.0,
  "frequency_per_month": 7.1,
  "recency_days": 3,
  "last_sale_date": "2024-06-15",
  "cluster_score": 91.0,
  "cluster_tier": "A",
  "created_at": "2023-03-01T12:00:00Z",
  "updated_at": "2024-06-15T10:30:00Z"
}
```

#### GET /api/products/{product_id}/sales
Sales history for a specific product.

**Path Parameter:** `product_id` (UUID)

**Query Parameters:**

| Parameter    | Type   | Default          | Description              |
|--------------|--------|------------------|--------------------------|
| `limit`      | int    | 50               | Page size                |
| `offset`     | int    | 0                | Skip N records           |
| `sort_by`    | string | `data_transacao` | Sort field               |
| `sort_order` | string | `desc`           | `asc` or `desc`          |
| `date_from`  | date   | —                | From date                |
| `date_to`    | date   | —                | To date                  |

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "ORD-2024-001",
      "data_transacao": "2024-06-15T10:30:00Z",
      "customer_name": "Maria Silva",
      "supplier_name": "Distribuidora ABC",
      "quantidade": 10,
      "valor_unitario": 50.00,
      "valor_total": 500.00
    }
  ],
  "pagination": { "total": 85, "limit": 50, "offset": 0, "has_more": true }
}
```

---

### Search

#### GET /api/search
Universal search across all ERP entities. Returns matching customers, suppliers, products, and orders.

**Query Parameters:**

| Parameter | Type   | Required | Description                                           |
|-----------|--------|----------|-------------------------------------------------------|
| `q`       | string | yes      | Search query (min 2 characters)                       |
| `entity`  | string | —        | Filter to entity type: `customers`, `suppliers`, `products`, `orders`. If omitted, searches all. |
| `limit`   | int    | 5        | Results per entity type                               |

**Response (200):**
```json
{
  "query": "maria",
  "results": [
    {
      "entity_type": "customer",
      "id": "uuid",
      "name": "Maria Silva",
      "subtitle": "123.456.789-00"
    },
    {
      "entity_type": "customer",
      "id": "uuid",
      "name": "Maria Santos",
      "subtitle": "987.654.321-00"
    },
    {
      "entity_type": "order",
      "id": "ORD-2024-MARIA-001",
      "name": "ORD-2024-MARIA-001",
      "subtitle": "123.456.789-00"
    }
  ],
  "total_found": 3
}
```

---

### Webhooks

#### POST /webhooks/order-created
Same body as `POST /api/orders`.

#### POST /webhooks/payment-received
Same as `POST /api/transactions` with `transaction_type="payment"`.

#### POST /webhooks/shipment-delivered
**Body:** `order_id`, `delivery_date`, `tracking_number`, `notes`

#### POST /webhooks/supplier-shipment
Same as `POST /api/inventory/restock`.

---

### Job Status

#### GET /api/jobs/{job_id}
Check the status of a queued write operation.

**Response (200):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "created_at": "2024-06-15T10:30:00Z",
  "completed_at": "2024-06-15T10:30:05Z",
  "result": {
    "entity_id": "uuid",
    "entity_type": "order"
  },
  "error": null
}
```

**Job statuses:** `queued`, `processing`, `completed`, `failed`

---

## Processing Logic

1. **Write requests:** Validate JWT and required fields → queue job → return `202` with `job_id`
2. **Read requests:** Validate JWT → query database with `client_id` filter → return `200` with data
3. **Worker processing:** Validate payload, upsert dimensions (customer, supplier, product), insert into `fact_sales`, update aggregates, mark job completed/failed
4. **Transaction types:** `sale`, `purchase`, `payment`, `refund`, `inventory_adjustment` processed with appropriate dimension lookups and fact inserts

---

## Endpoint Summary

| #  | Method | Path                                          | Type  | Description                           |
|----|--------|-----------------------------------------------|-------|---------------------------------------|
| 1  | POST   | `/api/orders`                                 | Write | Create customer order                 |
| 2  | PATCH  | `/api/orders/{order_id}`                      | Write | Update order status                   |
| 3  | GET    | `/api/orders`                                 | Read  | List orders (paginated)               |
| 4  | GET    | `/api/orders/{order_id}`                       | Read  | Order detail with line items          |
| 5  | POST   | `/api/purchase-orders`                        | Write | Create supplier PO                    |
| 6  | PATCH  | `/api/purchase-orders/{po_id}`                | Write | Update PO status                      |
| 7  | GET    | `/api/purchase-orders`                        | Read  | List POs (supplier view)              |
| 8  | GET    | `/api/purchase-orders/{po_id}`                | Read  | PO detail                             |
| 9  | POST   | `/api/transactions`                           | Write | Record transaction                    |
| 10 | GET    | `/api/transactions`                           | Read  | List transactions (line-item level)   |
| 11 | POST   | `/api/inventory/adjustments`                  | Write | Manual stock adjustment               |
| 12 | POST   | `/api/inventory/restock`                      | Write | Receive supplier delivery             |
| 13 | GET    | `/api/inventory`                              | Read  | Current stock levels                  |
| 14 | GET    | `/api/inventory/{product_id}`                 | Read  | Stock detail for product              |
| 15 | GET    | `/api/inventory/{product_id}/movements`       | Read  | Stock movement history                |
| 16 | POST   | `/api/customers`                              | Write | Register customer                     |
| 17 | PATCH  | `/api/customers/{customer_id}`                | Write | Update customer                       |
| 18 | GET    | `/api/customers`                              | Read  | List customers (paginated)            |
| 19 | GET    | `/api/customers/{customer_id}`                | Read  | Customer detail                       |
| 20 | GET    | `/api/customers/{customer_id}/orders`         | Read  | Customer's orders                     |
| 21 | GET    | `/api/customers/{customer_id}/products`       | Read  | Customer's product history            |
| 22 | GET    | `/api/customers/lookup`                       | Read  | Lookup customer by CPF/CNPJ           |
| 23 | POST   | `/api/suppliers`                              | Write | Register supplier                     |
| 24 | PATCH  | `/api/suppliers/{supplier_id}`                | Write | Update supplier                       |
| 25 | GET    | `/api/suppliers`                              | Read  | List suppliers (paginated)            |
| 26 | GET    | `/api/suppliers/{supplier_id}`                | Read  | Supplier detail                       |
| 27 | GET    | `/api/suppliers/{supplier_id}/orders`         | Read  | Supplier's orders                     |
| 28 | GET    | `/api/suppliers/{supplier_id}/products`       | Read  | Products from supplier                |
| 29 | GET    | `/api/suppliers/lookup`                       | Read  | Lookup supplier by CNPJ               |
| 30 | GET    | `/api/products`                               | Read  | List products (paginated)             |
| 31 | GET    | `/api/products/{product_id}`                  | Read  | Product detail                        |
| 32 | GET    | `/api/products/{product_id}/sales`            | Read  | Product sales history                 |
| 33 | GET    | `/api/search`                                 | Read  | Universal search                      |
| 34 | GET    | `/api/jobs/{job_id}`                          | Read  | Job status                            |
| 35 | POST   | `/webhooks/order-created`                     | Write | Webhook: order created                |
| 36 | POST   | `/webhooks/payment-received`                  | Write | Webhook: payment received             |
| 37 | POST   | `/webhooks/shipment-delivered`                | Write | Webhook: shipment delivered           |
| 38 | POST   | `/webhooks/supplier-shipment`                 | Write | Webhook: supplier shipment            |

**Total: 38 endpoints** (17 write + 21 read)
