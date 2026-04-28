---
name: fragment/csv-tools
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/csv-tools`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: CSV query and list tool descriptions with DuckDB SQL guidelines
-->

## CSV Data Tools

- **execute_csv_query** — Run SQL (DuckDB dialect) against uploaded CSV files. Access tables by their file name (without extension). Supports standard SQL: SELECT, WHERE, GROUP BY, ORDER BY, JOINs across files, window functions.
- **list_csv_datasets** — List all available CSV datasets with column names and row counts. Call this first to understand the data before querying.

### DuckDB SQL Guidelines
- Table names = CSV file names without extension (e.g., `vendas_2024.csv` → `FROM vendas_2024`)
- String functions: `lower()`, `contains()`, `regexp_matches()`
- Date functions: `strftime()`, `date_trunc()`, `current_date`
- Use `LIMIT` to avoid huge result sets (default: 100 rows)
- Aggregates: COUNT, SUM, AVG, MIN, MAX, MEDIAN, PERCENTILE_CONT
