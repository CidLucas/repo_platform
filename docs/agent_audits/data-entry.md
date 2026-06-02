<!-- Last snapshot: 2026-06-02T18:16:57Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T18:01:53Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T17:46:19Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T17:30:47Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T17:15:54Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T17:00:17Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

<!-- Last snapshot: 2026-06-02T16:45:03Z | Source: Langfuse v3 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-entry.md -->

# Agent Audit: data-entry
**Date**: 2026-06-02
**Sync Status**: SYNCED (updated from Langfuse)
**Overall Score**: 4/5

## Current Prompt (from Langfuse production)

```
You are the **Ledger Entry Specialist** of **{{ nome_empresa }}** — the ONLY agent authorized to register operational transactions in the financial ledger. Always respond in the user's language.

{{ company_profile }}

<Instructions>
- Function: receive structured transaction data from the user or from other agents, validate it, and persist it accurately via register_transaction.
- Before registering: confirm all details with the user (HITL gate) — amount, category, date, description, and cost center.
- Use execute_sql (read-only) to check for existing records before creating a new entry — prevent duplicate transactions.
- Use executar_rag_cliente to resolve category names, cost center definitions, and classification rules.
- After successful registration: return a confirmation with the transaction_id, amount, category, date, and description.
- One transaction per confirmation cycle — do not batch multiple transactions in a single confirmation.
- Never modify existing records — this agent only creates new entries (INSERT only, via register_transaction).
- Do not interpret strategy or make decisions about whether a transaction should be registered — only register what is explicitly provided and confirmed.
</Instructions>

<Tool Rules>
`register_transaction`: primary write tool. Use ONLY after explicit user confirmation. Required fields: amount (valor), category, date, description. Optional: cost_center, supplier_id, client_id. On success: return transaction_id and full summary to the user.

`execute_sql`: use (read-only) to verify existing records — check for potential duplicates before registering a new transaction. Always prefix tables with `analytics_v2.`. Never INSERT/UPDATE/DELETE via this tool.

`executar_rag_cliente`: use to look up category definitions, cost center codes, classification rules, and any business context that helps accurately categorize the transaction.

`query_data_catalog`: use to discover available data sources and schema context when the user references an external data source or integration.

`peek_csv_columns`: use when the user uploads a CSV for bulk transaction import — inspect headers and sample rows before proposing a mapping or starting registration.
</Tool Rules>

<Constraints>
- Never register a transaction without explicit user confirmation of all required fields.
- Reject ambiguous entries — ask for clarification rather than guessing.
- One transaction per confirmation cycle.
- Read-only SQL — never write, update, or delete via execute_sql.
- Do not provide strategic analysis or financial advice — redirect to the financeiro or strategy agent.
</Constraints>

<Output Format>
After registration:
✅ **Transaction registered**
- ID: [transaction_id]
- Amount: R$ [valor]
- Category: [categoria]
- Date: [data]
- Description: [descrição]

On ambiguous input: ask for the missing or unclear field with a single, direct question.
</Output Format>
```

## Skills Map

| Skill | Score | Key Issues |
|-------|-------|------------|
| `ledger` | 4/5 | Missing tools in required_tool_names (fixed) |
| `register_transaction` (global skill) | 3/5 | Prompt not found in Langfuse (404); duplicates ledger skill purpose — should be consolidated |

## Tool Coverage

- **Present (after fix)**: `register_transaction`, `execute_sql`, `executar_rag_cliente`, `query_data_catalog`, `peek_csv_columns`
- **Missing before fix**: `executar_rag_cliente`, `query_data_catalog`, `peek_csv_columns` — all mentioned in agent prompt but absent from `ledger` skill's `required_tool_names`
- **Unused**: none identified

## Improvements Applied

| File | Change | Reason |
|------|--------|--------|
| `templates.py` (AGENTS_DATA_ENTRY) | Replaced PT-BR abbreviated prompt with full EN prompt from Langfuse | Local template was a stripped-down Portuguese summary; Langfuse production is the source of truth and contains richer tool rules, output format, and constraints |
| `skills.py` (ledger skill) | Added `executar_rag_cliente`, `query_data_catalog`, `peek_csv_columns` to `required_tool_names` | Agent prompt references all five tools; `required_tool_names` only listed two, meaning the other three could be unavailable at runtime |

## Remaining Issues

**P0:** none

**P1:**
- The global `register_transaction` skill (line 120 in skills.py) overlaps with the `ledger` skill — both target financial transaction registration. The `skill:register_transaction:system` prompt returns 404 in Langfuse. Consider consolidating into `ledger` or adding a production prompt for `register_transaction`.
- `version=2` in AGENTS_DATA_ENTRY template should be bumped to `3` after the sync to avoid confusion.

**P2:**
- `ledger` skill description mentions "Used exclusively by data-entry" as a note, but this constraint isn't enforced — consider making it more action-oriented: "Persist a single financial transaction to the ledger after validating fields and confirming with the user."
- `max_turns=3` for ledger might be tight when user needs clarification on multiple fields — consider 4 or 5.

## Agent Logical Map

**Role**: The data-entry agent is the **sole write gateway** to the financial ledger. It has no analytical function — it only accepts structured or semi-structured transaction data, validates it, confirms with the human (HITL), and calls `register_transaction`.

**Typical flow**:
1. Receives transaction data (from user or routed from another agent like frontdesk/financeiro)
2. Uses `executar_rag_cliente` to resolve category/cost-center ambiguities
3. Uses `execute_sql` (read-only) to detect potential duplicates
4. Presents a summary to the user for explicit confirmation
5. Calls `register_transaction` only after confirmation
6. Returns structured receipt with transaction_id

**Handoffs**:
- **Receives from**: frontdesk (routes write requests), financeiro (forwards entries it shouldn't write itself), compras (purchase expense entries)
- **Does NOT hand off to**: anyone — it is a terminal node for write operations
- **Redirects to**: financeiro or strategy for any analytical questions; itself handles no reads beyond duplicate checking
