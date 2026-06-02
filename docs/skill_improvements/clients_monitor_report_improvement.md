# Skill Improvement Report: clients_monitor_report
**Date:** 2026-05-30T00:36:38Z
**Round:** 1

## What Changed

### Before (fallback template in templates.py)
- Written in Portuguese ("Você é o especialista em clientes...") — violates English-prompt policy
- Instructions were a short bullet list with no trigger definition, no architecture, no pitfalls
- No explicit constraint on health-status assignment (🟢/🟡/🔴)
- No output format spec — LLM could produce any structure
- Missing Jinja guards for several optional variables
- No guidance on missing-data handling (LLM would hallucinate)

### After (published to Langfuse)
- Full English prompt following the canonical Hermes skill structure
- Explicit **Trigger** sentence for planner routing clarity
- **Architecture** section (input → steps → output pipeline)
- **Tool Rules** with 5 numbered steps including classification logic
- Hard **Constraints** with status-assignment thresholds (no 🟢 when overdue > 10% or churn is non-zero without context)
- Strict **Output Format** with exact PT-BR template (emojis, sections, footer metrics)
- **Pitfalls** covering: fabricated data, over-optimistic status, vague recommendations, language drift, length overflow

### Patterns borrowed from
- `business-documents` Hermes skill → numbered-step tool rules, quality constraints, pitfall section structure
- Hermes skill canonical template (Trigger / Architecture / Tool Rules / Constraints / Output Format / Pitfalls)
- Prior improved skills in this round (`finance_monitor_report`, `followup_draft`) for consistent report output format

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current description is good but could add "Classifies client base health as 🟢/🟡/🔴 based on overdue ratio and churn." for better planner disambiguation from `finance_monitor_report`.
- **required_tool_names**: `[]` is correct — this is a pure generation skill, no tools needed.
- **max_turns**: `3` is appropriate for a report-generation skill with no tool calls. Could be reduced to `2` since there's no iteration expected.
- **tags**: Current tags `["routines", "clients", "monitor", "report", "alert"]` are correct English. Consider adding `"churn"` and `"nps"` for better semantic routing.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `churn_risk_analysis` | Deep-dive churn prediction: analyze client engagement patterns, identify pre-churn signals, and generate retention action plan with priority tiers | `clients` | clientes_agent |
| `nps_response_drafter` | Draft personalized responses to NPS detractors and promoters; route promoters to referral request, detractors to recovery flow | `clients` | clientes_agent |
| `client_reactivation_campaign` | Build a structured reactivation plan for churned clients: segment by reason, draft re-engagement messages, schedule follow-up sequence | `clients` | clientes_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_client_health_metrics` | Query CRM/database for active client count, overdue ratio, new clients in period, churn rate, and NPS aggregate | `clients_monitor_report`, `churn_risk_analysis`, `finance_monitor_report` |
| `get_nps_signals` | Fetch latest NPS survey responses, compute score, segment by detractor/passive/promoter | `clients_monitor_report`, `nps_response_drafter`, `satisfaction_survey` |
| `tag_client_risk_level` | Write back a risk label (🟢/🟡/🔴) to the CRM for a given client or segment | `churn_risk_analysis`, `clients_monitor_report` |

---

## Langfuse Prompt Published
- **Prompt name:** skill:clients_monitor_report:system
- **Labels:** ["production"]
- **Tags:** ["skill", "clients_monitor_report", "blu", "auto-improved"]
- **Langfuse ID:** 654666e8-7ecc-4428-94a8-8d83daebc415
- **Status:** ✅ Published (HTTP 201)
