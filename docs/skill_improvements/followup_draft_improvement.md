# Skill Improvement Report: followup_draft
**Date:** 2026-05-29T23:11:03Z
**Round:** 1

## What Changed

### Before (fallback template)
- Written entirely in Portuguese (prompt language mixed PT-BR instructions + PT-BR output)
- No trigger definition — LLM must infer when to activate
- Tool rules were a loose numbered list (4 items) without strict guards
- Cross-sell gate was present but no fallback if `{{historico}}` missing
- No channel-specific output format distinction
- No pitfalls section

### After (new Langfuse prompt)
- **Trigger** added: one-sentence activation condition in English
- **Architecture** section: explicit data-flow description (input → steps → output)
- **Tool Rules** expanded to 7 ordered steps with explicit guards (missing pedido, missing historico, channel defaulting)
- **Constraints** section: hard sentence limits per channel, explicit NEVER rules, Jinja guard reminders
- **Output Format**: channel-specific formatting (WhatsApp vs Email), PT-BR enforcement, anti-prose-list rule
- **Pitfalls**: 6 concrete LLM failure modes documented (verbosity, hallucination, double CTA, channel ambiguity)

### Patterns Borrowed From
- `improve_skill_eod.py` (existing repo script) — section structure (Trigger → Architecture → Tool Rules → Constraints → Output Format → Pitfalls)
- General Hermes skill library pattern: one-sentence trigger, numbered tool steps, explicit NEVER constraints, channel-aware output format

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current: *"Write a post-sale follow-up message for a specific customer, optionally including cross-sell suggestions based on purchase history."* → Suggested: *"Compose a personalised post-sale follow-up message for WhatsApp or email, with optional cross-sell recommendations based on purchase history and delivery channel."* (adds channel context for better frontdesk routing)
- **required_tool_names**: Currently empty `[]` — this is correct; no tools needed. Consider adding a future `get_customer_profile` tool when CRM integration matures.
- **max_turns**: `2` is appropriate for a pure generation task. No change needed.
- **tags**: Current: `["routines", "clients", "followup", "sales"]` — consider adding `"messaging"` and `"crm"` for richer routing signal.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `bulk_followup_scheduler` | Given a list of customers with recent orders, generate and schedule batch follow-up messages with personalized content per customer | sales, messaging | crm_agent |
| `nps_followup_router` | After receiving NPS survey response, route to the correct follow-up action: detractor escalation, promoter referral request, or passive nurture | clients, satisfaction | crm_agent |
| `delivery_confirmation_message` | Send a confirmation message to the customer when an order is marked as delivered, with delivery details and return policy reminder | logistics, clients | fulfillment_agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_customer_purchase_history` | Query CRM/ERP for a customer's full purchase history, returning structured product/date/value data | `followup_draft`, `reactivation_proposal`, `satisfaction_survey` |
| `send_whatsapp_message` | Send a pre-composed message to a customer's WhatsApp number via Twilio/Z-API | `followup_draft`, `collection_messages`, `reactivation_proposal` |
| `get_order_details` | Fetch order metadata (products, value, status, delivery date) by order ID | `followup_draft`, `delivery_confirmation_message` |

---

## Langfuse Prompt Published
- **Prompt name:** `skill:followup_draft:system`
- **Labels:** `["production"]`
- **Tags:** `["skill", "followup_draft", "blu", "auto-improved"]`
- **Langfuse ID:** `8db7d9ed-9bb8-4aa8-8ae3-2f85cea90712`
- **Status:** ✅ Published (HTTP 201)
