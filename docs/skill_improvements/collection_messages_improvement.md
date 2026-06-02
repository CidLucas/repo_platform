# Skill Improvement Report: collection_messages
**Date:** 2026-05-29T22:59:18Z
**Round:** 1

## What Changed

### Before (template fallback)
- Written in PT-BR (violating the English-prompt requirement)
- No explicit trigger condition
- No architecture section
- Tone rules existed but were only listed as bullet points without enforcement guidance
- Output format used template variables (`{{ dias_recencia }}`, `{{ valor }}`) that don't exist in the SkillDefinition
- No pitfalls section
- No constraint about never sending/scheduling messages
- No Jinja guards for optional variables
- No channel-specific length guidance

### After (rewritten prompt)
- Fully in ENGLISH as required
- Clear one-sentence **Trigger** condition
- Explicit **Architecture** pipeline (input → tone classification → drafting → output)
- **Tool Rules** section with numbered steps (no external tools, in-context only)
- **Constraints** section with hard limits, Jinja guards for optional variables
- **Output Format** with exact block structure per customer + summary line
- **Pitfalls** section covering 6 known LLM failure modes (tone leakage, invented data, CTA omission, channel mismatch, multi-customer confusion, missing days)

### Patterns borrowed from
- Hermes `business-documents` skill: structured architecture pipeline, format decision trees, explicit output block templates
- Hermes skill library conventions: Trigger/Architecture/Tool Rules/Constraints/Output Format/Pitfalls structure
- Blu platform conventions: Jinja guards for optional variables, `{{max_turns}}` in constraints, PT-BR output note

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current is adequate. Suggest minor improvement: *"Draft personalised debt-collection messages for overdue customers; automatically selects friendly, firm, or urgent tone based on days overdue; supports WhatsApp and e-mail channels."* — adds channel info and makes tone automation explicit for planner routing.
- **required_tool_names**: `[]` is correct — no tools needed. Consider adding a CRM read tool (e.g. `crm_get_overdue_customers`) in a future iteration so the skill can self-fetch customer data instead of requiring it as input.
- **max_turns**: `2` is appropriate for a pure-drafting skill. No change needed.
- **tags**: Current tags `["routines", "clients", "collection", "messages"]` are good English tags. Consider adding `"finance"` to improve routing when the request comes from a finance context.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `collection_batch_scheduler` | Given a list of drafted collection messages, schedule them for delivery via WhatsApp or e-mail at optimal send times, tracking delivery status | collection, automation | blu_agent |
| `payment_negotiation_script` | Generate a structured negotiation script for a human agent to use in phone/video calls with heavily overdue customers (91+ days), including objection handling | collection, clients | blu_agent |
| `overdue_risk_classifier` | Analyse customer payment history from CRM/ERP and classify each customer into a risk tier (low/medium/high churn risk), outputting a ranked list for prioritised collection action | finance, clients, analytics | blu_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `crm_get_overdue_customers` | Query the CRM/ERP for all customers with overdue invoices, returning name, amount, days overdue, and contact channel | `collection_messages`, `overdue_risk_classifier`, `clients_monitor_report` |
| `whatsapp_send_message` | Send a drafted message via WhatsApp Business API to a specific contact (requires message text + phone number) | `collection_batch_scheduler`, `followup_draft`, `reactivation_proposal` |
| `email_send_draft` | Send or save-as-draft an e-mail message via SMTP/Gmail API | `collection_batch_scheduler`, `followup_draft`, `reactivation_proposal` |

---

## Langfuse Prompt Published
- **Prompt name:** `skill:collection_messages:system`
- **Labels:** `["production"]`
- **Langfuse ID:** `36f11fcb-32fd-4bc3-8a0c-3482ee95aa1c`
- **Status:** ✅ Published (HTTP 201 — new prompt created)
