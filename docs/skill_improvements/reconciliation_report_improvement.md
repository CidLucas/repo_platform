# Skill Improvement Report: reconciliation_report
**Date:** 2026-05-29T23:00:00
**Round:** 1

## What Changed

### Before (v1)
- Prompt was written entirely in Portuguese
- No explicit trigger condition — model had to infer its own activation scope
- No output format template — model produced unstructured narrative
- No explicit pitfalls or anti-patterns documented
- No Jinja guards around optional variables — could fail when variables missing
- No word-count constraint (risk of verbose output)
- No explicit constraint against hallucinating data when variables are empty

### After (v2)
- Prompt rewritten entirely in **English** (as required)
- Clear **Trigger** section: one-sentence routing condition
- **Architecture** section: input → steps → output pipeline described
- **Tool Rules**: numbered 6-step generation workflow; confirms skill is pure generation (no tool calls)
- **Constraints**: max_turns bound, Jinja guards, anti-hallucination rule, 350-word cap
- **Output Format**: enforced structured template with emoji section headers (PT-BR output)
- **Pitfalls**: 6 concrete LLM failure modes with explicit handling

### Patterns Borrowed From
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md`: XML-section anatomy, confirmation-gating pattern, Jinja guard pattern, optional variable wrapping
- Existing `templates.py` template: preserved variable names and domain logic
- Hermes skill structure: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current: *"Generate a monthly cash reconciliation narrative: spot anomalies in categories, highlight top merchants, and flag discrepancies."* → Suggested: *"Generate a structured monthly cash reconciliation report: balance variance narrative, anomaly detection by category, top-merchant ranking, and actionable recommendations."* (more specific for planner routing)
- **required_tool_names**: Currently `[]` — correct, this is a pure generation skill. No changes needed.
- **max_turns**: Currently `3`. Appropriate — generation skill needs 1 turn but 3 provides buffer for clarification. Keep.
- **tags**: Currently `["routines", "finance", "reconciliation", "narrative"]` — all English ✅. Consider adding `"report"` tag to improve routing disambiguation from `finance_monitor_report`.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `cashflow_forecast` | Generate a 30/60/90-day cashflow forecast based on historical transaction patterns and recurring items | `finance` | financeiro |
| `budget_vs_actual` | Compare actual spending vs planned budget per category and generate variance analysis | `finance` | financeiro |
| `expense_approval_draft` | Draft structured expense approval requests with justification, amount, and category | `finance` | financeiro |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_monthly_transactions` | Fetch aggregated transactions for a given month from analytics_v2, returning balance, category breakdown, and top merchants in a structured dict | `reconciliation_report`, `finance_monitor_report`, `cashflow_forecast` |
| `get_category_benchmark` | Return historical average spend per category (last 3 months) to enable anomaly detection comparisons | `reconciliation_report`, `budget_vs_actual`, `hidden_patterns` |

---

## Langfuse Prompt Published
- **Prompt name:** `skill:reconciliation_report:system`
- **Labels:** `["production"]`
- **Version:** 2
- **Status:** ✅ Published successfully
