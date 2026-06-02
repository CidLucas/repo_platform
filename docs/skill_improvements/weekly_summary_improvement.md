# Skill Improvement Report: weekly_summary
**Date:** 2026-05-29T22:40:00
**Round:** 1

## What Changed

### Before (v1)
- Prompt had **wrong SQL table references**: `dim_clientes` (doesn't exist), `dim_produtos` (should be `dim_inventory`)
- Date filtering used `data_completa` column (actual column is `d.data`)
- No `{% if var %}` guards around optional variables — would render empty blocks when variables not injected
- No Pitfalls section documenting known failure modes
- No explicit architecture section clarifying "variable injection path vs SQL path"
- Missing `company_profile` optional variable
- `isActive: True` was set but `labels` structure was inconsistent

### After (v2)
- **Fixed SQL schema**: `dim_fornecedores` (JOIN for suppliers), `dim_inventory` (JOIN for products), `d.data` for date filtering
- **Added Jinja guards** for all optional variables with explicit list in Constraints section
- **Added architecture block**: clarifies that injected variables take precedence over live SQL queries
- **Added Pitfalls section** with 6 known failure modes (wrong tables, wrong date column, January bug, empty report, fabricated trends, max_turns exceeded)
- **Added `company_profile`** optional variable following standard pattern
- Corrected `data_completa` → `d.data` (the actual column name in `dim_datas`)
- SQL examples use `date_trunc('week', CURRENT_DATE)` arithmetic for safe weekly filtering (avoids January edge case)

### Patterns Borrowed From
- `blu-prompt-engineering/SKILL.md`: XML tag structure (`<Instructions>`, `<Tool Rules>`, `<Constraints>`, `<Output Format>`), SQL schema rules verbatim block, Jinja guard pattern, `{% if var %}` optional variable approach
- `blu-prompt-engineering/SKILL.md`: Rich Anatomy pattern (trigger + architecture header, activation statement at top)
- `blu-prompt-engineering/references/sql-prompt-divergences.md`: SQL anti-patterns (dim_clientes doesn't exist, January EXTRACT bug)

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current: *"Generate a weekly performance summary with highlights, KPI trends, and recommended focus areas for the following week."* → Suggested: *"Synthesize a weekly performance summary for {{nome_empresa}} — compares this week vs last week KPIs, highlights top wins and concerns, and recommends 2–3 focus areas for the following week. Uses injected KPI variables when available; falls back to execute_sql against analytics_v2."*
  - Why: More specific about the dual-path (injected vs SQL), helps planner understand when to route here.

- **required_tool_names**: Currently `[]`. Suggested: leave as `[]` but add a note in docs that `execute_sql` should be in the parent agent's enabled_tools — this skill's prompt invokes it conditionally. If `required_tool_names=["execute_sql"]` is added, the skill factory must guarantee the tool is available.

- **max_turns**: Currently `2`. This is appropriate for the skill complexity (1 SQL turn + 1 synthesis or follow-up). No change recommended.

- **tags**: Currently `["routines", "weekly", "summary", "narrative"]`. Suggested: add `"finance"` and `"kpi"` — the skill heavily uses financial data, and `kpi` helps the frontdesk route queries about KPI trends here instead of `finance_monitor_report`.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `weekly_comparison` | Deep week-over-week comparison across multiple KPI dimensions (revenue, expenses, transactions, top suppliers). More granular than weekly_summary — produces a breakdown table per category. | `finance`, `analytics` | financeiro-agent |
| `weekly_goals_tracker` | Compare actual weekly results against defined goals/targets (meta vs realizado). Flags metrics below target threshold and generates action triggers. | `goals`, `kpi` | financeiro-agent, crm |
| `kpi_trend_alert` | Proactively detects when a KPI deviates more than X% from its moving average and drafts an alert message for the responsible manager. | `monitoring`, `alerts` | monitor-agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_week_kpis` | Fetch pre-aggregated current and prior week KPI data from analytics_v2. Returns structured JSON: `{revenue_this, revenue_last, expenses_this, expenses_last, top_suppliers, top_products}`. Eliminates the need for multi-step SQL in the skill prompt. | `weekly_summary`, `weekly_comparison`, `morning_plan` |
| `format_kpi_table` | Given a dict of metric/value/prior/change rows, render a markdown table with trend arrows (↑ ↓ →). Ensures consistent formatting across all summary skills. | `weekly_summary`, `end_of_day_digest`, `morning_plan`, `finance_monitor_report` |

---

## Langfuse Prompt Published
- Prompt name: `skill:weekly_summary:system`
- Version: 2
- Labels: `["production", "latest"]`
- Status: ✅ Published
