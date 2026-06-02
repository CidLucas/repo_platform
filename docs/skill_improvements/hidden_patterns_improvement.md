# Skill Improvement Report: hidden_patterns
**Date:** 2026-05-30T00:00:06Z
**Round:** 1

## What Changed

### Before (v1)
- Single-paragraph activation description; no structured trigger
- Instructions listed as numbered points but no clear architecture diagram
- No explicit "never fabricate" constraint
- No Jinja guards on optional variables
- Output format was described in prose; no visual template shown
- No pitfalls section
- Prompt was partially in Portuguese (mixed language)
- No word-limit enforcement mechanism (just "Máximo 400 palavras" as prose)

### After (v2)
- **Trigger** block: one-sentence activation condition tied to routing logic
- **Architecture** block: explicit input → reasoning loop → output flow with max_turns reference
- **Tool Rules** block: 7 ordered internal reasoning steps (no tool calls needed, but steps are explicit)
- **Constraints** block: hard limits including NEVER fabricate, NEVER generic advice, 500-word cap, full Jinja guards for all optional vars
- **Output Format** block: exact templated structure with emoji section headers — LLM cannot drift from format
- **Pitfalls** block: 6 known failure modes with explicit guidance
- Prompt written entirely in **English** (output to user remains PT-BR per constraint)

### Patterns Borrowed From
- `~/.hermes/skills/software-development/blu-skills-development/SKILL.md` — Trigger/Architecture/Tool Rules/Constraints/Output Format/Pitfalls anatomy
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — Jinja guard patterns, variable naming conventions
- Hermes skill improvement loop instructions — constraint section structure (NEVER, max_turns, confirmation gates)

## SkillDefinition Suggestions (not auto-applied)

- **description:** Consider expanding to: `"Detect anomalies, seasonality, correlations, and hidden opportunities in sales time-series and KPI data, delivering a structured PT-BR findings report with concrete recommendations."` — more specific for planner selection.
- **required_tool_names:** Currently `[]`. Consider adding `query_kpis` or `get_sales_timeseries` if those tools exist or are planned — the skill currently relies on data being passed in context, which limits autonomous use.
- **max_turns:** `3` is appropriate for a reasoning-only skill with complete data. If tool calls are added in the future, increase to `5`.
- **tags:** Current tags are `["routines", "strategy", "analytics", "patterns"]`. Consider adding `"anomaly_detection"` and `"timeseries"` for more precise routing. Confirm all tags are English (they are ✅).

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `trend_forecast` | Generate a short-term (7–30 day) sales forecast based on historical time-series using trend + seasonality decomposition | `analytics` | analytics_agent |
| `kpi_alert_digest` | Monitor KPIs against configured thresholds and generate a concise alert digest when breaches are detected | `monitor` | monitor_agent |
| `cohort_analysis` | Segment customers into cohorts by acquisition period and compare retention/LTV across cohorts | `analytics` | analytics_agent |

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_sales_timeseries` | Query aggregated daily/weekly sales data from the data warehouse for a given period and dimension filters | `hidden_patterns`, `trend_forecast`, `weekly_summary` |
| `get_kpi_snapshot` | Retrieve current KPI values vs targets for all configured metrics | `hidden_patterns`, `kpi_alert_digest`, `finance_monitor_report` |
| `detect_anomalies` | Statistical anomaly detection (z-score, IQR) over a numeric series — returns flagged dates and magnitudes | `hidden_patterns`, `kpi_alert_digest` |

## Langfuse Prompt Published
- Prompt name: `skill:hidden_patterns:system`
- Version: 2
- Labels: `["production"]`
- Tags: `["skill", "hidden_patterns", "blu", "auto-improved"]`
- Status: ✅ Published (HTTP 201)
