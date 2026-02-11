#!/usr/bin/env python3
"""Create analytics_v2 schema prompts in Langfuse."""

import requests
from base64 import b64encode

# Auth
PUBLIC_KEY = "pk-lf-c64e4914-b8ab-426d-a5ea-14989b564e13"
SECRET_KEY = "sk-lf-dc053e58-e9e3-4822-abfe-89421ca9c2d4"
BASE_URL = "https://us.cloud.langfuse.com"

auth_token = b64encode(f"{PUBLIC_KEY}:{SECRET_KEY}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {auth_token}",
    "Content-Type": "application/json"
}

# Prompt 1: Technical Schema Reference
SCHEMA_PROMPT = """# Analytics V2 Star Schema - Technical Reference

## Overview
Multi-tenant star schema for sales analytics. All tables have `client_id` for tenant isolation.

---

## Fact Table

### `analytics_v2.fact_sales` (145K+ rows)
Central fact table containing individual sales transactions.

| Column | Type | Description |
|--------|------|-------------|
| `sale_id` | UUID | Primary key (auto-generated) |
| `client_id` | TEXT | **Tenant ID** - ALWAYS filter by this |
| `customer_id` | UUID | FK → dim_customer |
| `supplier_id` | UUID | FK → dim_supplier |
| `product_id` | UUID | FK → dim_product |
| `date_id` | INTEGER | FK → dim_date (YYYYMMDD format) |
| `order_id` | TEXT | External order reference |
| `data_transacao` | TIMESTAMPTZ | Transaction timestamp |
| `quantidade` | NUMERIC | Quantity sold |
| `valor_unitario` | NUMERIC | Unit price (BRL) |
| `valor_total` | NUMERIC | Total value = quantidade × valor_unitario |
| `customer_cpf_cnpj` | TEXT | Denormalized customer ID |
| `supplier_cnpj` | TEXT | Denormalized supplier ID |

---

## Dimension Tables

### `analytics_v2.dim_customer` (10K+ rows)
Customer master data with pre-aggregated metrics.

| Column | Type | Description |
|--------|------|-------------|
| `customer_id` | UUID | Primary key |
| `client_id` | TEXT | Tenant ID |
| `cpf_cnpj` | TEXT | Brazilian tax ID (CPF/CNPJ) |
| `name` | TEXT | Customer name |
| `telefone` | TEXT | Phone number |
| `endereco_rua` | TEXT | Street address |
| `endereco_numero` | TEXT | Street number |
| `endereco_bairro` | TEXT | Neighborhood |
| `endereco_cidade` | TEXT | City |
| `endereco_uf` | TEXT | State (2-letter code: SP, RJ, MG...) |
| `endereco_cep` | TEXT | Postal code |
| **Pre-aggregated Metrics:** | | |
| `total_orders` | INTEGER | Lifetime order count |
| `total_revenue` | NUMERIC | Lifetime revenue (BRL) |
| `avg_order_value` | NUMERIC | Average ticket size |
| `total_quantity` | NUMERIC | Lifetime units purchased |
| `orders_last_30_days` | INTEGER | Recent activity |
| `frequency_per_month` | NUMERIC | Purchase frequency |
| `recency_days` | INTEGER | Days since last purchase |
| `lifetime_start_date` | DATE | First purchase date |
| `lifetime_end_date` | DATE | Last purchase date |

### `analytics_v2.dim_supplier` (1.3K+ rows)
Supplier/vendor master data with aggregated metrics.

| Column | Type | Description |
|--------|------|-------------|
| `supplier_id` | UUID | Primary key |
| `client_id` | TEXT | Tenant ID |
| `cnpj` | TEXT | Supplier CNPJ |
| `name` | TEXT | Supplier/company name |
| `telefone` | TEXT | Contact phone |
| `endereco_cidade` | TEXT | City |
| `endereco_uf` | TEXT | State |
| **Pre-aggregated Metrics:** | | |
| `total_orders_received` | INTEGER | Orders from this supplier |
| `total_revenue` | NUMERIC | Total spent with supplier |
| `avg_order_value` | NUMERIC | Average PO value |
| `total_products_supplied` | INTEGER | SKU count |
| `frequency_per_month` | NUMERIC | Order frequency |
| `recency_days` | INTEGER | Days since last order |
| `first_transaction_date` | DATE | Relationship start |
| `last_transaction_date` | DATE | Most recent order |

### `analytics_v2.dim_product` (17K+ rows)
Product catalog with sales performance metrics.

| Column | Type | Description |
|--------|------|-------------|
| `product_id` | UUID | Primary key |
| `client_id` | TEXT | Tenant ID |
| `product_name` | TEXT | Product description |
| `categoria` | TEXT | Product category (may be NULL) |
| `ncm` | TEXT | Brazilian NCM tax code |
| `cfop` | TEXT | Tax operation code |
| **Pre-aggregated Metrics:** | | |
| `total_quantity_sold` | NUMERIC | Lifetime units sold |
| `total_revenue` | NUMERIC | Lifetime revenue |
| `avg_price` | NUMERIC | Average selling price |
| `number_of_orders` | INTEGER | Order count containing this product |
| `avg_quantity_per_order` | NUMERIC | Typical quantity per order |
| `frequency_per_month` | NUMERIC | Sales frequency |
| `recency_days` | INTEGER | Days since last sale |
| `last_sale_date` | DATE | Most recent sale |
| `cluster_score` | NUMERIC | ABC/clustering score |
| `cluster_tier` | VARCHAR | Tier label (A/B/C) |

### `analytics_v2.dim_date` (18K+ rows)
Date dimension for time-based analysis.

| Column | Type | Description |
|--------|------|-------------|
| `date_id` | INTEGER | PK - YYYYMMDD format |
| `date` | DATE | Actual date |
| `year` | INTEGER | Year (2024, 2025...) |
| `quarter` | INTEGER | Quarter (1-4) |
| `quarter_name` | TEXT | "Q1", "Q2", etc. |
| `month` | INTEGER | Month (1-12) |
| `month_name` | TEXT | "January", "February"... |
| `day` | INTEGER | Day of month (1-31) |
| `day_of_week` | INTEGER | 1=Monday, 7=Sunday |
| `day_name` | TEXT | "Monday", "Tuesday"... |
| `week_of_year_iso` | INTEGER | ISO week number |
| `is_weekend` | BOOLEAN | Saturday/Sunday flag |
| `is_month_start` | BOOLEAN | First day of month |
| `is_month_end` | BOOLEAN | Last day of month |

---

## Key Relationships
```
fact_sales.customer_id  → dim_customer.customer_id
fact_sales.supplier_id  → dim_supplier.supplier_id
fact_sales.product_id   → dim_product.product_id
fact_sales.date_id      → dim_date.date_id
```

## Important Notes
- **ALWAYS filter by `client_id`** - This is a multi-tenant database
- Monetary values are in **BRL (Brazilian Real)**
- Pre-aggregated metrics in dimensions are updated periodically
- For real-time totals, aggregate from `fact_sales`"""

# Prompt 2: Analysis Guide for LLM Decision Making
ANALYSIS_PROMPT = """# Analytics V2 - Analysis Guide for AI Assistant

## What Data is Available

You have access to a **star schema** with sales transaction data:

- **145K+ sales transactions** (fact_sales)
- **10K+ customers** with addresses and purchase history
- **17K+ products** with categories and performance metrics
- **1.3K+ suppliers** with relationship metrics
- **Complete date dimension** for time-based analysis

---

## Analysis You Can Perform

### 1. Sales Performance
- Total revenue by period (day/week/month/quarter/year)
- Order count and average ticket size
- Revenue growth comparisons (YoY, MoM)
- Best/worst performing periods

### 2. Customer Analysis
- Top customers by revenue or order count
- Customer geographic distribution (by city, state)
- RFM analysis (Recency, Frequency, Monetary)
- Customer lifetime value
- New vs returning customers
- Customers at risk (high recency_days)

### 3. Product Analysis
- Top selling products (by revenue or quantity)
- Product category performance
- ABC analysis (cluster_tier: A/B/C)
- Slow-moving inventory (high recency_days)
- Price analysis (avg_price trends)

### 4. Supplier Analysis
- Top suppliers by purchase volume
- Supplier concentration risk
- Purchase frequency patterns
- Geographic distribution of suppliers

### 5. Time-Based Analysis
- Seasonality patterns
- Day-of-week trends
- Month-over-month comparisons
- Weekend vs weekday performance

---

## Decision-Making Tips

### Geographic Analysis
- **If `endereco_uf` (state) is empty** → Use `endereco_cidade` (city)
- **If city is empty** → Use `endereco_bairro` (neighborhood)
- State codes are 2-letter: SP, RJ, MG, RS, PR, SC, BA, etc.

### Time Period Defaults
- **No period specified** → Assume last 6 months
- **"Recent"** → Last 30 days
- **"This year"** → Current calendar year

### Ranking Defaults
- **No limit specified** → Use TOP 10
- **"Main" or "principais"** → TOP 5
- **"All" or "todos"** → Limit to 50 max for readability

### Metric Selection
| User Asks For | Recommended Metric |
|--------------|-------------------|
| "Best customers" | total_revenue DESC |
| "Most active" | total_orders DESC |
| "Frequent buyers" | frequency_per_month DESC |
| "At risk customers" | recency_days DESC |
| "New customers" | lifetime_start_date DESC |
| "Best products" | total_revenue DESC |
| "Most popular" | total_quantity_sold DESC |

### Unavailable Data Fallbacks
| If Asked For | But Not Available | Suggest Instead |
|-------------|-------------------|-----------------|
| Profit margin | ❌ No cost data | Revenue or avg_price |
| Customer age | ❌ No demographics | Lifetime tenure |
| Employee sales | ❌ No employee data | By supplier or region |
| Payment method | ❌ Not tracked | Order value distribution |

### Query Efficiency Tips
- Use **pre-aggregated metrics** in dim_* tables when possible
- Only join fact_sales when you need transaction-level detail
- Filter by `client_id` FIRST (partition key)
- Use `date_id` for date filtering (it's indexed)

### Fuzzy Matching (Handling Typos)
- **Use `ILIKE`** for case-insensitive partial matching: `WHERE name ILIKE '%joao%'`
- **Use `SOUNDEX`** to match phonetically similar names: `WHERE SOUNDEX(name) = SOUNDEX('João')`
- **Combine both** for robust matching:
  ```sql
  WHERE name ILIKE '%search_term%'
     OR SOUNDEX(name) = SOUNDEX('search_term')
  ```
- **Common typos**: accents (João/Joao), case (SILVA/Silva), abbreviations (Ltda/LTDA)
- For product searches, also consider `similarity()` from pg_trgm extension

### Response Formatting
- Always show currency as **R$ X.XXX,XX** or **R$ X,XM** for millions
- Percentages as **XX%** (not decimals)
- Round averages to 2 decimal places
- Dates in Brazilian format: DD/MM/YYYY

---

## Example Analysis Patterns

### Revenue by State
```sql
SELECT c.endereco_uf AS estado, SUM(f.valor_total) AS receita
FROM analytics_v2.fact_sales f
JOIN analytics_v2.dim_customer c ON f.customer_id = c.customer_id
WHERE f.client_id = '{{client_id}}'
GROUP BY c.endereco_uf
ORDER BY receita DESC
```

### Top 10 Customers (using pre-aggregated)
```sql
SELECT name, total_revenue, total_orders, avg_order_value
FROM analytics_v2.dim_customer
WHERE client_id = '{{client_id}}'
ORDER BY total_revenue DESC
LIMIT 10
```

### Monthly Trend
```sql
SELECT d.year, d.month, d.month_name,
       SUM(f.valor_total) AS receita,
       COUNT(DISTINCT f.order_id) AS pedidos
FROM analytics_v2.fact_sales f
JOIN analytics_v2.dim_date d ON f.date_id = d.date_id
WHERE f.client_id = '{{client_id}}'
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year DESC, d.month DESC
```"""


def create_prompt(name: str, prompt: str, tags: list[str]) -> tuple[int, dict | str]:
    """Create a prompt in Langfuse."""
    url = f"{BASE_URL}/api/public/v2/prompts"
    payload = {
        "name": name,
        "prompt": prompt,
        "type": "text",
        "labels": ["production"],
        "tags": tags,
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    return resp.status_code, resp.json() if resp.status_code < 300 else resp.text


def main():
    """Create the two analytics prompts."""
    prompts = [
        ("sql/analytics-v2-schema", SCHEMA_PROMPT, ["sql", "schema", "reference"]),
        ("sql/analytics-v2-guide", ANALYSIS_PROMPT, ["sql", "guide", "decision-making"]),
    ]

    print("Creating analytics_v2 prompts in Langfuse...\n")
    for name, prompt, tags in prompts:
        status, result = create_prompt(name, prompt, tags)
        emoji = "✅" if status in [200, 201] else "❌"
        print(f"{emoji} {name}: {status}")
        if status >= 300:
            print(f"   Error: {result[:200] if isinstance(result, str) else result}")

    print("\n✅ Done! View at: https://us.cloud.langfuse.com/prompts")


if __name__ == "__main__":
    main()
