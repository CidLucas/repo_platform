# Human-in-the-Loop (HITL)

**Approval is architectural enforcement, not a prompt suggestion.** Any operation affecting the real world — registering a sale, sending a message, creating/modifying a document, creating a PO — is blocked at an approval node until the user explicitly responds. The agent cannot pass that node without an explicit user answer. This builds progressive trust.

Source: `docs/system_reference/PRODUCT_CONCEPT.md`, `docs/llm_wiki/08_produto_ux.md`, `docs/llm_wiki/07_dados_modelos.md`.

---

## Flow

```text
Agent proposes action
   ↓
Approval node (status: pending) — execution suspended
   ↓
User sees card in Home or the room
   ↓
User responds → approved | edited | rejected | snooze
   ↓
If approved: action executes + audit_log written
If edited: edited version executes
If rejected: action cancelled + feedback captured
If snoozed: reappears after Xh
```

Implementation: approval flow in `blu_agent_framework` (`approval.py`) + `blu_hitl_service` (Redis sorted sets, approval queues). Persisted in `approval_requests` table.

---

## HITL-flagged tools (examples)

From `TOOL_INVENTORY.md` (✓ HITL):
- `create_purchase_order`, `approve_purchase_order` (compras/rfq)
- `register_transaction` (financeiro/dados)
- `update_schema_mapping` (dados/contexto)

Operation categories requiring approval: register transactions, send messages, create/modify docs, create PO.

---

## Progressive trust

- `client_approval_stats` tracks approval history → drives `trust_level`.
- When `trust_level=auto`, agents may execute **without** HITL in low-risk contexts the user has defined.
- The approval card surfaces in Home (urgent/pending) and in the relevant room.

---

## Routine approval steps

Routines can include a `type="approval"` step. After the user responds, the routine is re-dispatched via `trg_redispatch_after_approval` to continue the step chain.

---

## Interaction with plan/decision surfacing

Home (`/app`, `strategy`) surfaces: daily plan, urgent alerts, and **pending approvals**. The product philosophy is to surface *decisions*, not data — approvals are first-class UI.

---

## Next

- Which agents trigger writes → [agents/catalog](agents/catalog.md) (`data-entry` only)
- Approval data model → [data-models/schema](data-models/schema.md) (`approval_requests`, `client_approval_stats`)
- Routine approval step → [routines](architecture/routines.md)
