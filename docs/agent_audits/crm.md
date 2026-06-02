<!-- Last snapshot: 2026-06-02T18:16:55Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/crm.md -->

<!-- Last snapshot: 2026-06-02T18:01:52Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/crm.md -->

<!-- Last snapshot: 2026-06-02T17:46:17Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/crm.md -->

<!-- Last snapshot: 2026-06-02T17:30:45Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/crm.md -->

# Agent Audit: crm
**Date**: 2026-06-02
**Sync Status**: IN_SYNC (minor Jinja2 whitespace diff: Langfuse uses `{{ var }}`, local uses `{{var}}` — functionally equivalent)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production)

```
You are the **CRM Specialist** of **{{ nome_empresa }}** — expert in customer relationship management, follow-ups, NPS, and commercial pipeline. Always respond in the user's language.

{{ company_profile }}
{{ sql_schema_context }}

<Instructions>
- Monitor inactive customers, opportunity pipeline, pending NPS surveys, and overdue follow-ups.
- Prioritize customers by highest LTV and highest churn risk.
- Draft and send customer communications only with explicit user approval.
- Process incoming NPS and survey replies to update customer health scores.
- Run WhatsApp engagement campaigns in bulk only on confirmed, opted-in lists.
- Never register financial transactions — redirect to the data-entry agent.
</Instructions>

<Tool Rules>
`execute_sql`: use to query customer data, interaction history, engagement metrics, churn signals, LTV calculations, and pipeline status. Always prefix tables with `analytics_v2.`. Revenue column: `valor` — never `valor_total`. Read-only — no INSERT/UPDATE/DELETE.

`executar_rag_cliente`: use for customer segmentation criteria, relationship policies, documented follow-up sequences, and business definitions (e.g., what counts as an "inactive customer").

`send_message`: use to draft and send a message to a specific customer or contact. Always present the draft to the user for review and require explicit approval before sending.

`send_whatsapp_message`: use for individual WhatsApp messages to a single customer. Requires explicit user confirmation before sending.

`whatsapp_enviar_lote`: use for bulk WhatsApp campaigns to a customer segment. Confirm the recipient list, message content, and send timing with the user before executing.

`parse_incoming_reply`: use with `context_type='nps'` to process structured NPS survey responses and update customer health records.
</Tool Rules>

<Constraints>
- Never send any message without explicit user approval.
- Do not register financial transactions — redirect to the data-entry agent.
- Do not access financial data beyond what is needed for customer LTV or churn context.
- Maximum 6 turns per relationship task.
- Do not reference tool names directly in user-facing messages.
</Constraints>

<Output Format>
- Customer lists: name, last purchase date, LTV, churn risk score, recommended action.
- Campaign summaries: segment, message preview, recipient count, send timing.
- NPS results: score distribution, verbatim highlights, trend vs. prior period.
</Output Format>
```

## Skills Map

| Skill | Score | Key Issues |
|-------|-------|------------|
| data_access | 3/5 | `required_tool_names` in skills.py lists `search_knowledge_base` (non-existent) instead of `executar_rag_cliente` (actual tool name per features.py) |
| sql_analytics | 4/5 | Correct tool (`execute_sql`). `on_max_turns=return_partial` is appropriate for analytics. |
| communication | 3/5 | `required_tool_names` lists `send_whatsapp_message`, `send_whatsapp_batch`, `check_whatsapp_replies`, `send_email`, `parse_business_reply` — but runtime tools (per features.py `communication` feature) are `send_message`, `send_rfq_via_channel`, `parse_incoming_reply`, `read_emails`. Mismatch between skill definition and feature registry. |
| analytics_charts | 5/5 | Clean, single-tool skill. Correct. |

## Tool Coverage

**Tools referenced in agent prompt:**
- `execute_sql` ✅ (in sql_analytics skill)
- `executar_rag_cliente` ✅ (available via data_access feature in features.py; but missing from data_access skill's `required_tool_names` in skills.py)
- `send_message` ✅ (in communication feature per features.py)
- `send_whatsapp_message` ⚠️ (in tool registry metadata but NOT in communication feature)
- `whatsapp_enviar_lote` ✅ (in crm_avancado feature per features.py)
- `parse_incoming_reply` ✅ (in communication feature per features.py)

**Missing from skills.py `required_tool_names`:**
- `executar_rag_cliente` should be in data_access skill
- `parse_incoming_reply` is called `parse_business_reply` in skills.py communication skill (inconsistent naming)

**Unused tools in skills.py communication skill:**
- `check_whatsapp_replies` (not in any feature for CRM)
- `send_rfq_via_channel` (compras use case, not CRM)

**Cross-cutting issue (do not fix here):**
- `skills.py` `data_access` skill `required_tool_names` = `["search_knowledge_base", "query_data_catalog"]` — but `search_knowledge_base` does not appear in any tool module. The actual tool is `executar_rag_cliente` (per features.py and all other references). This affects ALL agents using `data_access` skill and should be fixed in a dedicated cross-agent patch.

## Improvements Applied

No changes applied this run. All issues found are cross-cutting (affect multiple agents) and require coordinated fixes to avoid regressions.

| File | Change | Reason |
|------|--------|--------|
| — | No changes | Cross-cutting skill mismatches (data_access, communication) require multi-agent review before patching |

## Remaining Issues

**P0:** None

**P1:**
- `skills.py` → `data_access` skill: `required_tool_names` lists `search_knowledge_base` (ghost tool); should be `executar_rag_cliente`. Affects ALL agents. Fix in dedicated cross-agent audit.
- `skills.py` → `communication` skill: tool names diverge between skill definition (`send_whatsapp_message`, `send_whatsapp_batch`, `parse_business_reply`) and feature registry (`send_message`, `parse_incoming_reply`). Needs alignment.
- Agent prompt references `send_whatsapp_message` as a named tool rule but `communication` feature uses `send_message` for CRM. Prompt should be updated to reflect the actual tool name or the feature registry should be updated.

**P2:**
- Add `whatsapp_enviar_mensagem` (from crm_avancado feature) to agent prompt Tool Rules for completeness — currently only `whatsapp_enviar_lote` is mentioned; both are available to CRM.
- Consider a CRM-specific skill (e.g., `crm_ops`) to replace the generic `communication` skill, scoped to CRM's actual tools: `send_message`, `parse_incoming_reply`, `whatsapp_enviar_lote`.

## Agent Logical Map

**Typical flow:**
1. **Trigger**: User asks about inactive clients, churn risk, NPS results, or wants to send a campaign.
2. **Discovery**: CRM queries `analytics_v2.*` via `execute_sql` to surface customer segments (LTV, last purchase, churn signals).
3. **Context enrichment**: Uses `executar_rag_cliente` to retrieve segmentation rules, follow-up policies, and what "inactive" means for this client.
4. **Decision/draft**: Presents customer list + recommended action (reactivation, follow-up, NPS invite).
5. **Communication**: Drafts message via `send_message` (individual) or `whatsapp_enviar_lote` (bulk campaign). Shows draft and requires explicit user approval before sending.
6. **NPS processing**: Incoming replies processed via `parse_incoming_reply(context_type='nps')` to update health scores.
7. **Visualization**: Uses `generate_chart_html` to render NPS trends, churn cohorts, LTV distributions.

**Handoffs:**
- → **data-entry**: any financial transaction to register (sales, payments)
- → **financeiro**: collection/billing escalation for overdue customers
- → **strategy**: cohort/churn analysis requiring deeper segmentation or forecasting
- ← **frontdesk**: routes customer relationship requests (inactive clients, NPS campaigns) to CRM

**Agent boundary:**
CRM owns the relationship layer (who to contact, when, why, how). It does NOT own financial write operations, scheduling (→ agenda), or deep BI analysis (→ data-analyst/strategy). Its max_turns=8 in registry but prompt constraints say 6 per task — minor inconsistency worth noting.
