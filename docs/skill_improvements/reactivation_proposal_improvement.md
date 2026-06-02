# Skill Improvement Report: reactivation_proposal
**Date:** 2026-05-29T23:30:00
**Round:** 1

## What Changed

### Before (templates.py fallback — PT-BR, minimal structure)
- Written entirely in Portuguese
- Had no explicit **Trigger** (no one-sentence activation condition)
- No **Architecture** description
- Steps were simple numbered instructions without tool/constraint separation
- No **Pitfalls** section
- No **Output Format** specification (format left entirely to LLM inference)
- Conditional for `incluir_proposta` was embedded inline without explicit guards

### After (Langfuse prompt — EN, structured)
- Full English prompt following the canonical Blu skill structure
- Clear **Trigger**: one sentence defining when frontdesk routes here
- **Architecture**: input → compose → output (no external tool calls needed)
- **Tool Rules**: explicit note that no tool calls are required; steps map directly to input variables
- **Constraints** section: hard rules against hallucination, tone drift into collection, price invention, bloat
- **Output Format**: 5-step structure with numbered sections, tone spec, length constraint, language declaration
- **Pitfalls** section: 6 failure modes with mitigations (hallucinated history, offer without context, formal tone, missing question, collection drift, multi-paragraph bloat)
- Jinja guards explicitly documented for all optional variables

### Patterns Borrowed From
- `~/.hermes/skills/software-development/blu-prompt-engineering/SKILL.md` — XML-tagged section structure, confirmation-gate pattern, optional variables pattern, constraint/pitfall block conventions
- `~/.hermes/skills/productivity/business-documents/SKILL.md` — structured output sections, checklist approach, tone/length constraints

---

## SkillDefinition Suggestions (not auto-applied)

- **description**: Current is good but could be sharpened → `"Compose a warm, personalized reactivation message for an inactive customer, grounded in their purchase history. Optionally includes a tailored return offer. Routes here for client retention and win-back flows."` — makes the retention/win-back routing signal explicit.
- **required_tool_names**: Currently `[]` — correct, no tools needed. Consider adding `whatsapp_enviar_mensagem` if the skill should have the option to dispatch directly after confirmation. Keep empty for now; the skill generates text only.
- **max_turns**: `2` is appropriate for a text-generation skill with no tool calls. If a confirmation gate is added (show draft → user confirms → dispatch), bump to `4`.
- **tags**: `["routines", "clients", "reactivation", "retention"]` — good. Consider adding `"winback"` for better agent-skill routing signal, and `"copywriting"` to align with similar text-generation skills.

---

## New Skills Suggested

| Name | Description | Domain Tag | Agent |
|------|-------------|------------|-------|
| `winback_campaign` | Batch-generate reactivation messages for a list of inactive customers, grouped by segment and inactivity tier (30/60/90 days). Outputs a CSV or WhatsApp batch payload. | `clients`, `retention`, `batch` | Clients Monitor Agent |
| `churn_risk_alert` | Detect customers who are approaching inactivity threshold (e.g., 25 days since last purchase) and generate a proactive soft-touch message before they go cold. | `clients`, `retention`, `proactive` | Clients Monitor Agent |
| `loyalty_recognition` | Generate a celebratory message for loyal/high-LTV customers (anniversaries, milestone orders, tier upgrades) to strengthen retention before churn risk emerges. | `clients`, `retention`, `loyalty` | Clients Monitor Agent |

---

## New Tools Suggested

| Name | Description | Skills that would use it |
|------|-------------|--------------------------|
| `get_inactive_customers` | Query the database for customers inactive for N+ days, returning name, last purchase date, top products, and segment. | `reactivation_proposal`, `winback_campaign`, `churn_risk_alert` |
| `compute_customer_ltv` | Return the lifetime value and purchase frequency for a given customer ID — useful for personalizing offer aggressiveness. | `reactivation_proposal`, `winback_campaign`, `loyalty_recognition` |
| `whatsapp_enviar_lote_clientes` | Send a batch of reactivation messages (one per customer) via WhatsApp, with rate limiting and delivery tracking. | `winback_campaign` |

---

## Langfuse Prompt Published
- **Prompt name:** skill:reactivation_proposal:system
- **Version:** 1
- **Labels:** ["production"]
- **Tags:** ["skill", "reactivation_proposal", "blu", "auto-improved"]
- **Status:** ✅ Published
