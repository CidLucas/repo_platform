# Skill Improvement Report: finance_monitor_report
**Date:** 2026-05-30T00:30:00
**Round:** 1

## What Changed

### Before (fallback template)
- Written in **Portuguese**, with inline Jinja2 blocks for financial variables
- Flat structure: raw `# INSTRUÇÕES` header with 3 bullet items
- No trigger definition — model had no signal for when this skill activates
- No traffic-light thresholds specified (LLM guesses)
- No constraints against fabricating figures or asking clarifying questions
- No pitfall section
- Max 300 words mentioned but no enforcement mechanism

### After (Langfuse v2 prompt)
- Written entirely in **English** (per platform convention for new prompts)
- Full Hermes skill anatomy: **Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls**
- Explicit trigger sentence for frontdesk routing clarity
- ASCII architecture diagram showing context injection → narrative flow
- Tool Rules explicitly forbid tool calls (pure narrative skill)
- Traffic-light calibration thresholds specified (🔴 < 80% target, 🟡 80–95%, 🟢 ≥ 95%)
- Constraint: NEVER fabricate missing figures — flag the gap instead
- Constraint: complete in 1 turn, no clarifying questions
- Concrete PT-BR output template with emoji headers and conditional alerts block
- 6 documented pitfalls with root causes and mitigations

### Patterns Borrowed From
- `~/.hermes/skills/software-development/blu-skills-development/SKILL.md` — L3 routine skill pattern (required_tool_names=[], Jinja guards, max_turns=2–3 for narrative)
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — Rich agent prompt anatomy (trigger at top, XML-ish sections, output format with concrete examples, confirmation gates)
- Hermes skill anatomy template: Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current is adequate. Suggested improvement for better planner selection:
  `"Synthesise pre-fetched financial KPIs (revenue vs target, cash position, cost centres) into a structured PT-BR health snapshot with traffic-light status and 2–3 prioritised actions. Called by financeiro_monitor routine."`
- **required_tool_names**: Currently `[]` — correct. This is a pure narrative skill; no tools needed.
- **max_turns**: Currently `3`. For a pure narrative skill with all data injected, `2` is sufficient and avoids turn waste. Recommend reducing to `2` (consistent with `morning_plan` and similar narrative L3 skills).
- **tags**: Currently `["routines", "finance", "monitor", "report", "alert"]`. All English ✅. Suggested addition: `"narrative"` to aid tag-intersection routing with the finance agent. Final: `["routines", "finance", "monitor", "report", "alert", "narrative"]`

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `budget_vs_actual` | Compare current-period spend against budget lines, flag overruns >10%, and list top 5 variance drivers. Consumes SQL analytics data. | `finance` | finance |
| `cash_flow_forecast` | Project 30/60/90-day cash position based on receivables, payables, and recurring costs. Outputs risk-level and recommended actions. | `finance` | finance |
| `financial_anomaly_detection` | Identify statistical outliers in transaction data (e.g. duplicate payments, unusual vendor charges) and surface them for review. | `finance` | finance |

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_cash_position` | Fetch current bank balance, accounts receivable total, and accounts payable total from the financial data source. | `finance_monitor_report`, `cash_flow_forecast` |
| `get_revenue_vs_target` | Query revenue for the current period and compare against configured targets, returning Δ% and traffic-light status. | `finance_monitor_report`, `budget_vs_actual` |
| `get_top_cost_centres` | Return top N cost centres by spend for a given period, with MoM variation. | `finance_monitor_report`, `budget_vs_actual` |

## Langfuse Prompt Published
- **Prompt name:** `skill:finance_monitor_report:system`
- **Version:** 2 (upgraded from v1)
- **Labels:** `["production"]`
- **Status:** ✅ Published
