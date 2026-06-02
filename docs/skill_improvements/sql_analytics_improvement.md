# Skill Improvement Report: sql_analytics
**Date:** 2026-05-30T06:43:30Z
**Round:** 1

## What Changed

### Before
- Generic system prompt with high-level instructions ("parse the user's question", "map to correct table")
- No explicit schema declaration — relied on the LLM's general knowledge of table names
- No "last month" anti-pattern guard → exposed to the TC4 GraphRecursionError bug
- No hard list of non-existent tables (dim_clientes, dim_tipo_transacao, dim_categoria)
- No FK direction documentation
- No loop-guard instruction (LLM could exhaust all max_turns on the same broken query)
- No client_id scoping enforcement
- Missing Jinja guard on `company_profile`

### After
- Explicit `analytics_v2` schema table with all key columns documented inline
- Hard "does NOT exist" annotations for the 3 phantom tables
- FK direction documented: `fato.produto_id = dim_inventory.inventory_id` (not the inverse)
- "Last month" correct pattern provided with explicit WRONG pattern named in Pitfalls
- Loop-guard instruction: stop after 2 consecutive SQL errors, return partial answer
- `client_id` scoping is a hard constraint with error fallback if unavailable
- `{% if company_profile %}` Jinja guard added
- Pitfalls section with 6 distinct failure modes

### Patterns borrowed from
- `blu-prompt-engineering/references/sql-prompt-divergences.md` — live schema, FK corrections, dim_datas columns, TC4 root cause analysis
- `blu-skills-development/SKILL.md` — Hermes skill anatomy (Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls)
- Hermes skill structure patterns: numbered steps, hard constraint lists, anti-pattern documentation in Pitfalls

---

## SkillDefinition Suggestions (not auto-applied)

- **description:** Current is good but could be more routing-specific:
  ```
  "Execute ad-hoc SQL queries on analytics_v2 (sales, revenue, inventory, suppliers, expenses). Returns tables and aggregates. Use for specific data questions requiring SQL, not for scheduled reports."
  ```
- **required_tool_names:** `["execute_sql", "executar_sql_agent"]` — `executar_sql_agent` appears to be an alias or legacy tool. Verify if both are truly needed; if `execute_sql` is the primary tool, `executar_sql_agent` may be redundant and add tool-selection noise.
- **max_turns:** 5 is reasonable. However, given the loop-guard pitfall (TC4), consider also applying the `recursion_limit=12` fix in `service.py` as noted in the sql-prompt-divergences reference. Keep at 5.
- **tags:** Current: `["sql", "analytics", "finance", "sales", "inventory", "clients"]`. Suggestion: add `"data"` as a type tag for consistency with the Data Analysis Skills pattern. Remove `"clients"` (ambiguous — `crm` agent owns clients domain). Revised: `["sql", "analytics", "finance", "sales", "inventory", "data"]`

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `sql_explain` | Takes a previous SQL result and generates a plain-language business interpretation with trend analysis and actionable recommendations | analytics | sql_analytics / strategy agent |
| `data_export` | Runs a SQL query and exports the result as CSV or Excel, returning a download link | analytics | sql_analytics agent |
| `kpi_snapshot` | Fetches a pre-defined set of KPIs (revenue, units sold, active clients, overdue invoices) in a single multi-query call, formatted as a dashboard summary | analytics | finance / strategy agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `explain_sql_result` | Accepts a SQL result set + original question and returns a GPT-generated business insight narrative | `sql_analytics`, `sql_explain` |
| `export_to_csv` | Accepts tabular data (list of dicts) and returns a signed URL to a CSV file stored in object storage | `sql_analytics`, `data_export`, `reconciliation_report` |
| `validate_sql_dry_run` | Runs EXPLAIN (no execute) on a generated SQL query and returns estimated rows + any syntax errors, before actual execution | `sql_analytics` |

---

## Langfuse Prompt Published

- **Prompt name:** skill:sql_analytics:system
- **Labels:** ["production"]
- **Tags:** ["skill", "sql_analytics", "blu", "auto-improved"]
- **Status:** ✅ Published (HTTP 201, id: acc55e06-4f63-4ffd-923c-452e37057d2e)
- **Published at:** 2026-05-30T06:43:28Z
