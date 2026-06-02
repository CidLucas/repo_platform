---
name: fragment/sql-schema
category: system
version: 1
required_variables: []
optional_variables: {'schema_description': ''}
---

<!--
This file is the in-repo fallback for prompt `fragment/sql-schema`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Analytics V2 star schema reference
-->

{% if schema_description %}
# CLIENT SCHEMA
{{ schema_description }}

{% endif %}
# DATABASE SCHEMA (Analytics V2 — Star Schema)

All tables in schema `analytics_v2`. Security filtering by `client_id` is applied AUTOMATICALLY — NEVER include it in queries.

## Fact: `analytics_v2.fato_transacoes`
| Column | Type | Notes |
|--------|------|-------|
| `transacao_id` | TEXT | PK |
| `fornecedor_id` | INTEGER | FK → dim_fornecedores |
| `data_competencia_id` | INTEGER | FK → dim_datas.data_id |
| `documento` | TEXT | Invoice/order reference (nullable) |
| `quantidade` | NUMERIC | Quantity (nullable) |
| `valor_unitario` | NUMERIC | Unit price (nullable) |
| `valor` | NUMERIC | **Total amount (BRL) — USE THIS for revenue/spend** |
| `status` | TEXT | Transaction status (nullable) |
| `tipo_transacao` | TEXT | e.g. 'compra', 'venda' |
| `entry_type` | TEXT | e.g. 'purchase', 'sale' |
| `categoria` | TEXT | Category (e.g. 'INSTALAÇÕES', 'MATERIAIS') |
| `subcategoria` | TEXT | Subcategory (nullable) |

## Dim: `analytics_v2.dim_fornecedores`
| Column | Type | Notes |
|--------|------|-------|
| `fornecedor_id` | INTEGER | PK |
| `nome` | TEXT | Supplier name — use ILIKE for search |
| `cnpj` | TEXT | Tax ID (nullable) |
| `endereco_cidade` | TEXT | City (nullable) |
| `endereco_uf` | TEXT | State (nullable) |
| `receita_total` | NUMERIC | Cumulative revenue |
| `total_pedidos_recebidos` | INTEGER | Order count |
| `ticket_medio` | NUMERIC | Average ticket |
| `is_active` | BOOLEAN | |

## Dim: `analytics_v2.dim_datas` (global — no client_id)
| Column | Type | Notes |
|--------|------|-------|
| `data_id` | INTEGER | PK (format YYYYMMDD) |
| `data` | DATE | Use for date range filters |
| `ano` | INTEGER | Year |
| `mes` | INTEGER | Month 1–12 |
| `dia` | INTEGER | Day of month |
| `numero_dia_semana` | INTEGER | Day of week |
| `numero_semana_ano` | INTEGER | Week of year |
| `numero_semestre` | INTEGER | 1 or 2 |
| `periodo_trimestral` | TEXT | 'Q1', 'Q2', 'Q3', 'Q4' |

## Dim: `analytics_v2.dim_inventory`
| Column | Type | Notes |
|--------|------|-------|
| `inventory_id` | UUID | PK |
| `nome` | TEXT | Product name — use ILIKE |
| `sku` | TEXT | |
| `ncm` | TEXT | |
| `quantidade_total_vendida` | NUMERIC | Total units sold |
| `receita_total` | NUMERIC | |
| `preco_medio` | NUMERIC | |

## JOINS (always use ON — USING breaks with subquery wrappers)
```
fato_transacoes → dim_fornecedores : ON f.fornecedor_id = s.fornecedor_id
fato_transacoes → dim_datas        : ON f.data_competencia_id = d.data_id
fato_transacoes → dim_inventory    : ON f.produto_id = i.inventory_id  (nullable → LEFT JOIN)
```

## WHAT DOES NOT EXIST
- `dim_tipo_transacao` table — filter via `f.tipo_transacao TEXT` or `f.categoria TEXT` directly
- `dim_categoria` table — use `f.categoria` column on fato_transacoes
- `nome_mes` column — use `d.mes` (INT) or `TO_CHAR(d.data, 'Month')`
- `current_stock` column — use `quantidade_total_vendida` on dim_inventory
- `inventory_id` on fato_transacoes — use `produto_id` (nullable, LEFT JOIN)
- `client_id` in your SQL — injected automatically, never write it
