# Current Database Schema - Analytics Tables

**Generated:** January 22, 2026
**Source:** Supabase Production Database

## Analytics Gold Tables

### 1. analytics_gold_customers
**Purpose:** Aggregated customer metrics and contact information
**Rows:** 4,827
**Primary Key:** id (UUID)

#### Columns:
- **Identity & Core Metrics:**
  - `id` - UUID PRIMARY KEY
  - `client_id` - TEXT NOT NULL
  - `customer_name` - TEXT NOT NULL
  - `customer_cpf_cnpj` - TEXT (government ID)
  - `total_orders` - INTEGER DEFAULT 0
  - `lifetime_value` - NUMERIC(12,2) DEFAULT 0
  - `avg_order_value` - NUMERIC(10,2) DEFAULT 0
  - `first_order_date` - TIMESTAMPTZ
  - `last_order_date` - TIMESTAMPTZ
  - `customer_type` - TEXT (new/returning/vip)

- **Ranking & Segmentation Fields:**
  - `quantidade_total` - NUMERIC(12,2) DEFAULT 0
  - `num_pedidos_unicos` - INTEGER DEFAULT 0
  - `ticket_medio` - NUMERIC(10,2) DEFAULT 0
  - `qtd_media_por_pedido` - NUMERIC(10,2) DEFAULT 0
  - `frequencia_pedidos_mes` - NUMERIC(10,4) DEFAULT 0
  - `recencia_dias` - INTEGER DEFAULT 0
  - `valor_unitario_medio` - NUMERIC(10,2) DEFAULT 0
  - `cluster_score` - NUMERIC(5,2) DEFAULT 0
  - `cluster_tier` - TEXT (A/B/C/D)
  - `primeira_venda` - TIMESTAMPTZ
  - `ultima_venda` - TIMESTAMPTZ

- **Contact & Address Fields (Added 2026-01-22):**
  - `telefone` - TEXT (phone number)
  - `endereco_rua` - TEXT (street)
  - `endereco_numero` - TEXT (number)
  - `endereco_bairro` - TEXT (neighborhood)
  - `endereco_cidade` - TEXT (city)
  - `endereco_uf` - TEXT (state)
  - `endereco_cep` - TEXT (postal code)

- **Metadata:**
  - `period_start` - TIMESTAMPTZ
  - `period_end` - TIMESTAMPTZ
  - `period_type` - TEXT DEFAULT 'all_time'
  - `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
  - `created_at` - TIMESTAMPTZ DEFAULT NOW()
  - `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_customers_client_id` ON (client_id)
- `idx_gold_customers_cluster_tier` ON (cluster_tier)
- `idx_gold_customers_cluster_score` ON (cluster_score DESC)
- `idx_gold_customers_cidade` ON (endereco_cidade)
- `idx_gold_customers_uf` ON (endereco_uf)
- `idx_gold_customers_cep` ON (endereco_cep)
- `idx_gold_customers_cidade_uf` ON (endereco_cidade, endereco_uf)

---

### 2. analytics_gold_suppliers
**Purpose:** Aggregated supplier metrics and contact information
**Rows:** 1,322
**Primary Key:** id (UUID)

#### Columns:
- **Identity & Core Metrics:**
  - `id` - UUID PRIMARY KEY
  - `client_id` - TEXT NOT NULL
  - `supplier_name` - TEXT NOT NULL
  - `supplier_cnpj` - TEXT
  - `total_orders` - INTEGER DEFAULT 0
  - `total_revenue` - NUMERIC(12,2) DEFAULT 0
  - `avg_order_value` - NUMERIC(10,2) DEFAULT 0
  - `unique_products` - INTEGER DEFAULT 0

- **Ranking & Segmentation Fields:**
  - `quantidade_total` - NUMERIC(12,2) DEFAULT 0
  - `num_pedidos_unicos` - INTEGER DEFAULT 0
  - `ticket_medio` - NUMERIC(10,2) DEFAULT 0
  - `qtd_media_por_pedido` - NUMERIC(10,2) DEFAULT 0
  - `frequencia_pedidos_mes` - NUMERIC(10,4) DEFAULT 0
  - `recencia_dias` - INTEGER DEFAULT 0
  - `valor_unitario_medio` - NUMERIC(10,2) DEFAULT 0
  - `cluster_score` - NUMERIC(5,2) DEFAULT 0
  - `cluster_tier` - TEXT
  - `primeira_venda` - TIMESTAMPTZ
  - `ultima_venda` - TIMESTAMPTZ

- **Contact & Address Fields (Added 2026-01-22):**
  - `telefone` - TEXT
  - `endereco_rua` - TEXT
  - `endereco_numero` - TEXT
  - `endereco_bairro` - TEXT
  - `endereco_cidade` - TEXT
  - `endereco_uf` - TEXT
  - `endereco_cep` - TEXT

- **Metadata:**
  - `period_start` - TIMESTAMPTZ
  - `period_end` - TIMESTAMPTZ
  - `period_type` - TEXT DEFAULT 'all_time'
  - `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
  - `created_at` - TIMESTAMPTZ DEFAULT NOW()
  - `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_suppliers_client_id` ON (client_id)
- `idx_gold_suppliers_cluster_tier` ON (cluster_tier)
- `idx_gold_suppliers_cluster_score` ON (cluster_score DESC)
- `idx_gold_suppliers_cidade` ON (endereco_cidade)
- `idx_gold_suppliers_uf` ON (endereco_uf)

---

### 3. analytics_gold_products
**Purpose:** Aggregated product metrics
**Rows:** 12,537
**Primary Key:** id (UUID)

#### Columns:
- **Identity & Core Metrics:**
  - `id` - UUID PRIMARY KEY
  - `client_id` - TEXT NOT NULL
  - `product_name` - TEXT NOT NULL
  - `total_quantity_sold` - NUMERIC(12,2) DEFAULT 0
  - `total_revenue` - NUMERIC(12,2) DEFAULT 0
  - `avg_price` - NUMERIC(10,2) DEFAULT 0
  - `order_count` - INTEGER DEFAULT 0
  - `revenue_rank` - INTEGER

- **Ranking & Segmentation Fields:**
  - `quantidade_total` - NUMERIC(12,2) DEFAULT 0
  - `num_pedidos_unicos` - INTEGER DEFAULT 0
  - `ticket_medio` - NUMERIC(10,2) DEFAULT 0
  - `qtd_media_por_pedido` - NUMERIC(10,2) DEFAULT 0
  - `frequencia_pedidos_mes` - NUMERIC(10,4) DEFAULT 0
  - `recencia_dias` - INTEGER DEFAULT 0
  - `cluster_score` - NUMERIC(5,2) DEFAULT 0
  - `cluster_tier` - TEXT
  - `primeira_venda` - TIMESTAMPTZ
  - `ultima_venda` - TIMESTAMPTZ

- **Metadata:**
  - `period_start` - TIMESTAMPTZ
  - `period_end` - TIMESTAMPTZ
  - `period_type` - TEXT DEFAULT 'all_time'
  - `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
  - `created_at` - TIMESTAMPTZ DEFAULT NOW()
  - `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_products_client_id` ON (client_id)
- `idx_gold_products_cluster_tier` ON (cluster_tier)
- `idx_gold_products_cluster_score` ON (cluster_score DESC)

---

### 4. analytics_gold_orders
**Purpose:** Aggregated order metrics
**Rows:** 82
**Primary Key:** order_id (UUID)

#### Columns:
- **Identity & Metrics:**
  - `order_id` - UUID PRIMARY KEY
  - `client_id` - TEXT NOT NULL
  - `total_orders` - INTEGER DEFAULT 0
  - `total_revenue` - NUMERIC(12,2) DEFAULT 0
  - `avg_order_value` - NUMERIC(10,2) DEFAULT 0
  - `quantidade_total` - NUMERIC(12,2) DEFAULT 0
  - `frequencia_pedidos_mes` - NUMERIC(10,4) DEFAULT 0
  - `recencia_dias` - INTEGER DEFAULT 0

- **Relationships:**
  - `customer_cpf_cnpj` - TEXT (FK to analytics_gold_customers)

- **Time Tracking:**
  - `primeira_transacao` - TIMESTAMPTZ
  - `ultima_transacao` - TIMESTAMPTZ

- **Metadata:**
  - `period_start` - TIMESTAMPTZ
  - `period_end` - TIMESTAMPTZ
  - `period_type` - TEXT DEFAULT 'all_time'
  - `by_status` - JSONB DEFAULT '{}'
  - `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
  - `created_at` - TIMESTAMPTZ DEFAULT NOW()
  - `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_orders_client_id` ON (client_id)

---

### 5. analytics_gold_last_orders
**Purpose:** Precomputed last 20 orders for quick retrieval
**Rows:** 40
**Primary Key:** id (UUID)

#### Columns:
- `id` - UUID PRIMARY KEY
- `client_id` - TEXT NOT NULL
- `order_id` - TEXT NOT NULL
- `data_transacao` - TIMESTAMPTZ NOT NULL
- `customer_cpf_cnpj` - TEXT (FK to analytics_gold_customers.customer_cpf_cnpj)
- `customer_name` - TEXT
- `ticket_pedido` - NUMERIC(12,2) DEFAULT 0
- `qtd_produtos` - INTEGER DEFAULT 0
- `order_rank` - INTEGER
- `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
- `created_at` - TIMESTAMPTZ DEFAULT NOW()
- `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_last_orders_client` ON (client_id)
- `idx_gold_last_orders_date` ON (data_transacao DESC)
- `idx_gold_last_orders_rank` ON (order_rank) WHERE order_rank <= 20
- `idx_unique_last_orders` UNIQUE ON (client_id, order_id)

---

### 6. analytics_gold_time_series
**Purpose:** Precomputed time-series charts
**Rows:** 960
**Primary Key:** id (UUID)

#### Columns:
- `id` - UUID PRIMARY KEY
- `client_id` - TEXT NOT NULL
- `chart_type` - TEXT NOT NULL (e.g., 'fornecedores_no_tempo')
- `dimension` - TEXT NOT NULL
- `period` - TEXT NOT NULL
- `period_date` - DATE NOT NULL
- `total` - INTEGER DEFAULT 0
- `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
- `created_at` - TIMESTAMPTZ DEFAULT NOW()
- `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_time_series_client` ON (client_id)
- `idx_gold_time_series_period` ON (period_date)
- `idx_unique_time_series` UNIQUE ON (client_id, chart_type, dimension, period)

---

### 7. analytics_gold_regional
**Purpose:** Precomputed regional breakdowns
**Rows:** 106
**Primary Key:** id (UUID)

#### Columns:
- `id` - UUID PRIMARY KEY
- `client_id` - TEXT NOT NULL
- `chart_type` - TEXT NOT NULL (e.g., 'fornecedores_por_regiao')
- `dimension` - TEXT NOT NULL
- `region_name` - TEXT NOT NULL
- `region_type` - TEXT NOT NULL (cidade/uf)
- `total` - INTEGER DEFAULT 0
- `contagem` - INTEGER DEFAULT 0
- `percentual` - NUMERIC DEFAULT 0
- `calculated_at` - TIMESTAMPTZ DEFAULT NOW()
- `created_at` - TIMESTAMPTZ DEFAULT NOW()
- `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_gold_regional_client` ON (client_id)
- `idx_gold_regional_total` ON (total DESC)
- `idx_unique_regional` UNIQUE ON (client_id, chart_type, dimension, region_name, region_type)

---

## Analytics Silver Table

### analytics_silver
**Purpose:** Flexible JSONB storage for transactional data
**Rows:** 0 (currently unused - BigQuery FDW used instead)
**Primary Key:** id (UUID)

#### Columns:
- `id` - UUID PRIMARY KEY
- `client_id` - TEXT NOT NULL
- `order_id` - TEXT
- `data_transacao` - TIMESTAMPTZ
- `quantidade` - TEXT
- `valor_unitario` - TEXT
- `valor_total_emitter` - TEXT
- `valor_total_receiver` - TEXT
- `emitter_nome` - TEXT
- `emitter_cidade` - TEXT
- `emitter_estado` - TEXT
- `emitter_cnpj` - TEXT
- `emitter_telefone` - TEXT
- `receiver_nome` - TEXT
- `receiver_cidade` - TEXT
- `receiver_estado` - TEXT
- `receiver_cnpj` - TEXT
- `receiver_telefone` - TEXT
- `raw_product_description` - TEXT
- `raw_product_category` - TEXT
- `raw_ncm` - TEXT
- `raw_cfop` - TEXT
- `created_at` - TIMESTAMPTZ DEFAULT NOW()
- `updated_at` - TIMESTAMPTZ DEFAULT NOW()

#### Indexes:
- `idx_analytics_silver_client_id` ON (client_id)

**Note:** This table is currently replaced by BigQuery foreign tables for better performance with large datasets.

---

## Observed Issues & Redundancies

### 1. Duplicate Quantity Fields
**Issue:** Both `total_quantity_sold` AND `quantidade_total` exist in products table
**Impact:** Potential data inconsistency
**Recommendation:** Use `quantidade_total` consistently across all tables

### 2. Duplicate Order Count Fields
**Issue:** Both `order_count` AND `num_pedidos_unicos` exist
**Impact:** Potential confusion
**Recommendation:** Standardize on `num_pedidos_unicos` for consistency

### 3. Date Field Naming Inconsistency
**Issue:** Mix of `first_order_date`/`last_order_date` vs `primeira_venda`/`ultima_venda`
**Impact:** Confusion in code
**Recommendation:** Use Portuguese naming consistently for all date fields

### 4. Missing Unique Constraints
**Issue:** No unique constraint on `analytics_gold_customers(client_id, customer_name, period_type)`
**Impact:** Potential duplicate records
**Recommendation:** Add unique constraint for data integrity

### 5. Period Fields Redundancy
**Issue:** All tables have `period_start`, `period_end`, `period_type` but many records use DEFAULT 'all_time'
**Impact:** Unnecessary storage
**Recommendation:** Consider separate tables for time-windowed vs all-time aggregations

---

## Migration History

1. **20251226_drop_views_create_tables_with_rls.sql** - Initial table creation
2. **20260109_enhance_gold_tables_with_ranking_fields.sql** - Added RankingItem fields (quantidade_total, cluster_tier, etc.)
3. **20260109_add_gold_charts_tables.sql** - Added time_series and regional tables
4. **20260122_add_contact_fields_to_gold_tables.sql** - Added telefone and endereco_* fields

---

## Data Source Canonical Schema

The ETL pipeline expects these canonical column names in source data:

- `receiver_telefone` → Maps to `telefone` in gold tables
- `receiver_cpf_cnpj` → Maps to `customer_cpf_cnpj`
- `receiver_nome` → Maps to `customer_name`
- `receiver_cidade` → Maps to `endereco_cidade`
- `receiver_uf` → Maps to `endereco_uf`
- `emitter_nome` → Maps to `supplier_name`
- `emitter_cnpj` → Maps to `supplier_cnpj`
- `raw_product_description` → Maps to `product_name`
- `valor_total_emitter` → Maps to `total_revenue`
- `quantidade` → Maps to `quantidade_total`
- `data_transacao` → Maps to date fields

**Note:** The column mapping is stored in `client_data_sources.column_mapping` as JSONB.
