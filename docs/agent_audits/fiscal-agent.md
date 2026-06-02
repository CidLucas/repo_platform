<!-- Last snapshot: 2026-06-02T18:16:59Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T18:01:55Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T17:46:21Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T17:30:49Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T17:15:56Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T17:00:20Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T16:45:05Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T16:29:04Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

<!-- Last snapshot: 2026-06-02T16:13:32Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/fiscal-agent.md -->

# Agent Audit: fiscal-agent
**Date**: 2026-06-02
**Sync Status**: SYNCED (agent prompt v2→v3, skill prompt v1→v2)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production — v3)

```
You are the **Fiscal Specialist** of **{{ nome_empresa }}** — responsible for NF-e/NFS-e invoice issuance, tax compliance, and SEFAZ integration. Always respond in the user's language.

{{ company_profile }}

<Instructions>
- Assist with fiscal obligations: NF-e and NFS-e issuance, SEFAZ integration status, fiscal data preparation, and compliance monitoring.
- Always validate fiscal data before submitting to SEFAZ — confirm CNPJ and tax regime with the user.
- Flag discrepancies between financial records and fiscal documents.
- Every NF-e issuance requires explicit user confirmation (HITL gate).
- Do not write to the financial ledger — forward any transaction registration to the data-entry agent.
</Instructions>

<Tool Rules>
`executar_rag_cliente`: call FIRST before any fiscal operation. Use to retrieve: tax regime, CNPJ, NCM codes, service descriptions, CFOP codes, and any company-specific fiscal rules. Never issue an invoice without this context.

`fiscal_preparar_dados_nfe`: use to prepare and validate the NF-e data payload before submission. Required fields: CNPJ emitente, CNPJ/CPF destinatário, items with NCM and value, CFOP, payment method. Call before `fiscal_emitir_nfe`.

`fiscal_status_integracao`: use to check SEFAZ integration health — certificate validity, API connectivity, pending authorizations, and rejection history. Call when the user reports issuance errors or wants a status check.

`execute_sql`: use (read-only) for fiscal analytics — invoice volume by period, tax amounts, pending issuances. Always prefix with `analytics_v2.`. Never INSERT/UPDATE/DELETE.

`whatsapp_enviar_mensagem`: use to send the issued invoice (DANFE link or PDF) to the customer via WhatsApp after successful issuance. Requires explicit user confirmation before sending.
</Tool Rules>

<Constraints>
- Never issue an NF-e or NFS-e without explicit user confirmation of all required data.
- Always confirm CNPJ and tax regime before starting an issuance.
- Do not provide legal or tax advisory — fiscal orientation only (what the system can execute).
- Do not write to the financial ledger — redirect to the data-entry agent.
- Maximum 6 turns per fiscal task.
</Constraints>

<Output Format>
- Fiscal summaries: structured with status, document number, key fields, and action items.
- Issuance confirmation: NF-e number, access key, issuance date/time, SEFAZ status.
- Error report: error code, plain-language explanation, and recommended corrective action.
</Output Format>
```

## Skills Map

| Skill | Score | Key Issues |
|-------|-------|------------|
| fiscal | 4/5 | Tool names in skills.py were stale (english names ≠ actual PT tool names); `whatsapp_enviar_mensagem` missing; fixed. |

## Tool Coverage

- **Present (after fix)**: `executar_rag_cliente`, `fiscal_preparar_dados_nfe`, `fiscal_status_integracao`, `execute_sql`, `whatsapp_enviar_mensagem`
- **Missing (before fix)**: `executar_rag_cliente` (was `search_knowledge_base`), `fiscal_preparar_dados_nfe` (was `fiscal_prepare_nfe_data`), `fiscal_status_integracao` (was `fiscal_integration_status`), `whatsapp_enviar_mensagem`
- **Unused**: none

## Improvements Applied

| File | Change | Reason |
|------|--------|--------|
| `templates.py` | AGENTS_FISCAL_V3: synced v2→v3 from Langfuse (English, richer Tool Rules per-tool, explicit HITL gate, improved output format) | Langfuse is source of truth; local was outdated PT-BR minimal version |
| `templates.py` | SKILL_FISCAL: synced v1→v2 from Langfuse (`## Tool Rules` → `## Execution Steps` heading, added full Constraints/Output/Pitfalls sections) | Local was missing Constraints, Output Format, and Pitfalls sections |
| `skills.py` | Fixed `required_tool_names`: replaced stale English tool names with actual Portuguese tool names used in runtime; added `whatsapp_enviar_mensagem` | Tool names must match runtime registration; mismatches cause skill failures |

## Remaining Issues

**P0:** none

**P1:**
- Agent prompt references `fiscal_emitir_nfe` in Tool Rules but this tool is not in `required_tool_names` — if it's a real tool, it should be added. If it's a sub-step of `fiscal_preparar_dados_nfe`, the reference should be clarified.
- The skill prompt has `max_turns=4` but agent prompt says "Maximum 6 turns" — slight inconsistency; skill-level limit (4) is more restrictive, which is fine but should be documented intentionally.

**P2:**
- Could add explicit NCM vs CFOP validation step in skill prompt pitfalls (common source of SEFAZ rejection).

## Agent Logical Map

The **fiscal-agent** is a specialist sub-agent dispatched by the frontdesk when a user requests tax invoice operations. It does NOT handle financial ledger writes or general accounting.

**Typical flow:**
1. Frontdesk routes NF-e/NFS-e intent → fiscal-agent activated with `fiscal` skill
2. `executar_rag_cliente` → fetch company's tax regime, CNPJ, NCM/CFOP defaults
3. Collect invoice data from user (tomador, valor, serviço/produto)
4. `fiscal_preparar_dados_nfe` → validate and structure NF-e payload
5. `fiscal_status_integracao` → confirm SEFAZ connectivity is active
6. Present confirmation summary → wait for explicit user "yes"
7. Execute issuance → return NF-e number + access key + SEFAZ status
8. (Optional) `whatsapp_enviar_mensagem` → send DANFE to client

**Handoffs:**
- → **data-entry agent**: when the user also needs to register the transaction in the financial ledger
- ← **frontdesk**: all entry points come through frontdesk routing
- → **financeiro agent**: if the user asks for revenue/tax analytics beyond scope of fiscal validation

**Key constraints enforced:**
- Hard HITL gate before every issuance
- RAG-first policy (no alíquota claims without confirmation)
- READ-ONLY SQL (no ledger writes)
- Redirect to contador for complex tax advisory
