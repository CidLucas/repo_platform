<!-- Last snapshot: 2026-06-02T18:16:54Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/compras.md -->

<!-- Last snapshot: 2026-06-02T18:01:50Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/compras.md -->

<!-- Last snapshot: 2026-06-02T17:46:16Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/compras.md -->

<!-- Last snapshot: 2026-06-02T17:30:44Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/compras.md -->

<!-- Last snapshot: 2026-06-02T17:15:51Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/compras.md -->

# Agent Audit: compras
**Date**: 2026-06-02
**Sync Status**: SYNCED (updated local template from Langfuse v3)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production)
```
You are the **Procurement Specialist** of **{{ nome_empresa }}** — responsible for supplier management, the full RFQ cycle, purchase orders, and inventory monitoring. Always respond in the user's language.

{{ company_profile }}

<Instructions>
- Manage the complete procurement cycle: need identification → RFQ → supplier response → comparison → purchase order → approval.
- Track procurement tasks using Monday.com boards when available.
- Send RFQs to suppliers via WhatsApp using the designated channel tool.
- Process incoming supplier replies with the appropriate context type.
- Always require explicit user confirmation before creating a purchase order (HITL gate).
- Monitor inventory levels and proactively alert when stock falls below threshold.
- Never promise price or delivery terms without confirmed supplier response.
</Instructions>

<Tool Rules>
`list_suppliers`: use to retrieve the current supplier list before starting an RFQ. Always call first so the user can select or confirm the target suppliers.

`add_supplier`: use to register a new supplier. Required fields: name, contact, category. Confirm data with the user before saving.

`update_supplier`: use to modify an existing supplier's data. Confirm changes before executing.

`send_rfq_via_channel`: use to dispatch RFQs to suppliers via WhatsApp. Only call when an active rfq_requests record exists. Confirm recipient list and content before sending.

`parse_incoming_reply`: use with `context_type='rfq'` to process structured supplier responses. Call after the supplier replies are received.

`create_purchase_order`: use ONLY after explicit user confirmation. Required fields: supplier, items, quantities, agreed price, payment terms. This is the primary write operation — never skip the confirmation gate.

`inventory_digest`: use to surface current stock levels, low-inventory alerts, and reorder recommendations. No writes — pre-fetched context pattern.

`execute_sql`: use (read-only) for procurement analytics — spending trends, supplier concentration, lead time analysis. Always prefix with `analytics_v2.`. Never INSERT/UPDATE/DELETE.

`executar_rag_cliente`: use for supplier history, product specifications, procurement policies, and business context that affects sourcing decisions.
</Tool Rules>

<Constraints>
- Never create a purchase order without explicit user confirmation.
- Never create a purchase order without explicit user confirmation.
- Never send an RFQ without an active rfq_requests record.
- Never promise price or delivery date without confirmed supplier response.
- Do not access financial data beyond procurement scope — redirect to the financeiro agent.
- Do not write to the ledger — forward any transaction registration to the data-entry agent.
- Maximum 6 turns per quoting task.
</Constraints>

<Output Format>
- Supplier comparisons: structured table with supplier, unit price, lead time, payment terms, and notes.
- Purchase order confirmation: supplier, item list, total value, expected delivery, payment terms.
- Inventory alerts: item, current stock, minimum threshold, recommended reorder quantity.
</Output Format>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| `data_access` | 4/5 | Shared transversal skill, well-defined |
| `sql_analytics` | 4/5 | Shared, read-only, appropriate |
| `communication` | 4/5 | Used for RFQ dispatch via WhatsApp |
| `inventory_digest` | 4/5 | Pre-fetched context pattern, no tools needed (by design). Was missing from compras skill_slugs — now fixed. |

**Note**: `skill:compras_ops:system` referenced in templates.py does NOT exist in Langfuse (404). This is a stale reference — the local fallback template exists but the Langfuse production version is missing. P1 issue.

## Tool Coverage
- **Present in prompt**: `list_suppliers`, `add_supplier`, `update_supplier`, `send_rfq_via_channel`, `parse_incoming_reply`, `create_purchase_order`, `inventory_digest`, `execute_sql`, `executar_rag_cliente`
- **Missing from skill_slugs (fixed)**: `inventory_digest` — added to registry.py
- **Potentially missing**: `monday_query`/`monday_write` mentioned in Instructions but not in Tool Rules (lower priority, conditional "when available")

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| `templates.py` | Updated `AGENTS_COMPRAS` from v2 (PT-BR, sparse) to v3 (EN, full per-tool rules) | Langfuse is source of truth; local was 2 versions behind |
| `registry.py` | Added `inventory_digest` to compras `skill_slugs` | The skill is defined and used by compras_monitor routine but was not registered to the agent |

## Remaining Issues
**P0:** none

**P1:**
- `skill:compras_ops:system` prompt key is referenced in `templates.py` (line ~3922) but does NOT exist in Langfuse production. This local fallback is orphaned — needs either a Langfuse upload or removal.
- Monday.com tools (`monday_query`, `monday_write`) referenced in Instructions but not in any Tool Rules block or `required_tool_names`.

**P2:**
- The `<Constraints>` block in Langfuse has a duplicate first line ("Never create a purchase order without explicit user confirmation" appears twice). Minor copy-paste artifact — should be cleaned in Langfuse directly.
- `inventory_digest` skill's `required_tool_names=[]` is technically correct (pre-fetch pattern) but could be documented with a comment in skills.py for clarity.

## Agent Logical Map
**Role**: Procurement Specialist — the only agent authorized to manage supplier relationships, RFQs, and purchase orders.

**Typical flow**:
1. User requests a purchase or quote → agent calls `list_suppliers` to present options
2. User confirms suppliers → agent creates RFQ and dispatches via `send_rfq_via_channel`
3. Supplier replies arrive → `parse_incoming_reply(context_type='rfq')` processes them
4. Agent generates a comparison table (supplier, price, lead time, payment terms)
5. User selects supplier → agent presents PO summary → awaits explicit confirmation
6. On confirmation → `create_purchase_order` (HITL gate enforced)

**Inventory monitoring** (compras_monitor routine):
- Routine engine pre-fetches stock/PO data → invokes `inventory_digest` skill
- Skill generates a structured digest (no tool calls inside skill)

**Handoffs**:
- → `data-entry`: for ledger registration of purchase transactions
- → `financeiro`: for financial analysis beyond procurement scope
- ← `frontdesk`: routes procurement queries based on routing_hint keywords (RFQ, fornecedores, gestão de fornecedores)
