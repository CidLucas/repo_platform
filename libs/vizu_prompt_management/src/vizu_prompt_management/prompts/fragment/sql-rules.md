---
name: fragment/sql-rules
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/sql-rules`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: SQL generation critical rules and defaults
-->

# SQL GENERATION RULES

## CRITICAL
1. **Amount column is `valor`** — NOT `valor_total`! Always `SUM(f.valor)` for revenue.
2. **No `data_transacao` column exists** — date filtering MUST join dim_datas.
3. **ALWAYS prefix tables**: `analytics_v2.fato_transacoes`, etc.
4. **NEVER include `client_id` filters** — security filtering is automatic.
5. For geography → always join `dim_clientes`.
6. For "top N per group" → use CTE with `ROW_NUMBER()`.
7. Use `ILIKE` for product text search on `dim_inventory.nome`.
8. `dim_datas` and `dim_tipo_transacao` are GLOBAL — NO `client_id` column.

## Defaults
- No period → last 6 months
- No limit → TOP 10
- Currency → R$ format

## TOOL USAGE (SQL)
1. Generate SQL using the schema and rules
2. Call `execute_sql` with your query
