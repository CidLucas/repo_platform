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
1. **Amount column is `valor`** — NOT `valor_total`! Always `SUM(f.valor)` for revenue/spend.
2. **No `data_transacao` column** — date filtering MUST join dim_datas ON f.data_competencia_id = d.data_id.
3. **ALWAYS prefix tables**: `analytics_v2.fato_transacoes`, etc.
4. **NEVER include `client_id` in SQL** — security filtering is automatic.
5. **Always use ON for joins** — USING breaks with subquery wrappers injected by security layer.
6. **No `dim_tipo_transacao` table** — filter by `f.tipo_transacao` or `f.categoria` (TEXT columns on fato).
7. **No `nome_mes` column** — use `d.mes` (INT 1-12) or `TO_CHAR(d.data, 'Month')`.
8. **No `current_stock`** — use `dim_inventory.quantidade_total_vendida`.
9. **CTE aliases must be consistent** — what you name in WITH, use exactly in SELECT.
10. **If SQL errors → STOP. Report the error. Do NOT retry.**

## Defaults
- No period specified → last 6 months (WHERE d.data >= CURRENT_DATE - INTERVAL '6 months')
- No limit specified → LIMIT 10
- Currency → R$ format

## TOOL USAGE
1. Generate SQL from the schema
2. Call `execute_sql` once
3. If error → stop and explain the error to the user
