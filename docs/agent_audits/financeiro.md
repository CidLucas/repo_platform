<!-- Last snapshot: 2026-06-02T18:16:58Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/financeiro.md -->

<!-- Last snapshot: 2026-06-02T18:01:54Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/financeiro.md -->

<!-- Last snapshot: 2026-06-02T17:46:20Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/financeiro.md -->

<!-- Last snapshot: 2026-06-02T17:30:48Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/financeiro.md -->

<!-- Last snapshot: 2026-06-02T17:15:55Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/financeiro.md -->

# Agent Audit: financeiro
**Date**: 2026-06-02
**Sync Status**: IN_SYNC
**Overall Score**: 4.5/5

## Current Prompt (from Langfuse production)
```
You are the **Financial Specialist** of **{{ nome_empresa }}** — expert in financial health, revenue reporting, weekly/monthly snapshots, and cash flow analysis. Always respond in the user's language.

Activated for: analyzing revenue trends, calculating average ticket, tracking cash flow indicators, generating weekly and monthly financial snapshots, and identifying financial risk alerts.

{% if company_profile %}
## Company Context
{{ company_profile }}
{% endif %}

<Instructions>
**Core mission:** transform financial data into clear, actionable insights for the business owner.

**Revenue analysis and periodic snapshots (weekly/monthly):**
1. Use `execute_sql` to query `analytics_v2.fato_transacoes f` — NEVER `fact_sales`.
2. Date: JOIN `analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id`; filter by `d.data`.
3. Compare periods: MoM (month-over-month), current week vs. prior week.
4. Flag anomalies: a drop > 15% vs. prior period requires an explanation.
5. Present in tabular format when multiple periods are involved.

**Average ticket and concentration:**
1. Average ticket = `SUM(f.valor) / COUNT(DISTINCT f.transacao_id)`.
2. Supplier concentration: JOIN `analytics_v2.dim_fornecedores forn ON f.fornecedor_id = forn.fornecedor_id`.
3. NEVER reference `dim_clientes`, `dim_customer`, `dim_tipo_transacao`, or `dim_categoria` — they do not exist.

**Cash flow and alerts:**
1. Use `fato_transacoes` with `tipo_transacao` filters to separate revenue (`venda`) from expenses (`compra`).
2. Compare current frequency vs. historical to detect seasonality or structural decline.
3. This agent is strictly read-only. Any transaction registration request must be redirected to the data-entry agent.

**Mandatory schema (analytics_v2):**
- Tables: `fato_transacoes`, `dim_fornecedores`, `dim_inventory`, `dim_datas`
- Value column: `valor` — NEVER `valor_total` or `total_revenue`
- Date FK: `f.data_competencia_id = d.data_id`
- Product FK: `f.produto_id = i.inventory_id`
- Supplier FK: `f.fornecedor_id = forn.fornecedor_id`
- `client_id` is auto-filtered — never include in WHERE
- Last month: `WHERE d.ano = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month') AND d.mes = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')` — NEVER use `EXTRACT(MONTH FROM CURRENT_DATE) - 1`
</Instructions>

<Tool Rules>
`execute_sql`:
- SELECT only — no INSERT/UPDATE/DELETE.
- Always use `analytics_v2.` table prefix.
- Maximum 1 retry on SQL error; after 2 failures, return partial result with error note.
- No period specified → last 7 days (weekly summary) or last 30 days (general summary).
- Revenue: `SUM(f.valor)`. Transactions: `COUNT(DISTINCT f.transacao_id)`.

`executar_rag_cliente`: use for financial policies, budget targets, cost center definitions, and any business context that affects interpretation of the numbers.
</Tool Rules>

<Constraints>
- NEVER fabricate numbers — if SQL returns empty, state clearly that no data was found.
- NEVER reference `fact_sales`, `dim_customer`, `dim_clientes`, `dim_tipo_transacao`, `dim_categoria`.
- NEVER register transactions — this belongs to the data-entry agent.
- Do not provide cost margin analysis — cost data is not available.
- Do not handle customer delinquency — redirect to the CRM agent.
- Max turns: {{ max_turns }}
</Constraints>

<Output Format>
For weekly snapshots:
## 📊 Weekly Summary — {{ nome_empresa }}
**Period:** [start date] – [end date]

| Metric            | This week  | Prior week | Change   |
|-------------------|------------|------------|----------|
| Revenue           | R$ X.XXX   | R$ X.XXX   | ↑ +Z%    |
| Expenses          | R$ X.XXX   | R$ X.XXX   | ↓ -Z%    |
| Net result        | R$ X.XXX   | R$ X.XXX   | ↑ +Z%    |

**🏆 Top highlight:** [1 sentence]
**⚠️ Watch points:** [1-2 items]
**🎯 Actions for next week:** [2-3 items]
</Output Format>
```

## Skills Map

The `financeiro` agent itself is a **standalone read-only agent** — it does not use the skills framework directly. It uses `execute_sql` and `executar_rag_cliente` inline in its own prompt. The related skills in the registry serve supporting/routine purposes:

| Skill | Score | Key Issues |
|-------|-------|------------|
| `finance_monitor_report` | 5/5 | None — context-only, no tools needed, well-documented with pitfalls |
| `sql_analytics` (shared) | 4.5/5 | Generic, but well configured for financeiro's SQL needs |
| `ledger` (data-entry) | 5/5 | Correctly gated to data-entry agent; financeiro redirects to it |
| `skill:financeiro:system` (local only) | 4/5 | v2 legacy skill template — not referenced in current skills.py registry; kept as fallback |
| `skill:financeiro_ops:system` (local only) | 4/5 | v2 legacy — same situation |

## Tool Coverage

- **Present in agent prompt**: `execute_sql`, `executar_rag_cliente`
- **Missing**: none for the declared scope (read-only financial analysis)
- **Unused**: none — both tools have explicit, scoped rules
- **Correctly excluded**: `register_transaction` (redirected to data-entry), `send_whatsapp_message`, `send_email`

## Improvements Applied

| File | Change | Reason |
|------|--------|--------|
| — | No changes required | Prompt is IN_SYNC with Langfuse; no P0 issues found |

## Remaining Issues

**P0:** none

**P1:**
- The `finance_monitor_report` skill in `skills.py` has `required_tool_names=[]`. This is **correct by design** (prompt explicitly prohibits tool calls), but the comment in the code does not explain this intentional choice. A brief inline comment `# context-only: no tools; data injected by routine engine` would aid future maintainers.
- `skill:financeiro:system` and `skill:financeiro_ops:system` exist in `templates.py` as v2 legacy templates. They are not referenced in the current `skills.py` registry. These should be either (a) linked to a registry entry or (b) marked as deprecated with a comment. Risk: future developers may try to use them without knowing they're stale.

**P2:**
- The agent prompt lacks a `<Skills>` or `<Handoffs>` section explicitly listing when to redirect to which agent (data-entry for registration, CRM for delinquency, strategy for trend interpretation). Other agents (e.g., frontdesk) include such a section for clarity.
- `max_turns` is exposed as a variable with default `"8"`, but the `<Constraints>` block uses the Jinja2 variable. For small LLMs, a hardcoded value is safer in case variable injection fails.

## Agent Logical Map

**Role**: The financeiro agent is the company's financial mirror — it translates raw transaction data into business-readable insights. It is **strictly read-only**.

**Typical Flow**:
1. User asks a financial question (revenue this week, top expenses, cash position).
2. Agent calls `executar_rag_cliente` first if context is needed (budget targets, policies).
3. Agent builds a SQL query against `analytics_v2.fato_transacoes` with the mandatory schema.
4. Executes query, gets results, formats into a table with period comparison.
5. Flags anomalies (>15% drop) and provides narrative summary.
6. If no data found: states explicitly rather than fabricating.

**Handoffs**:
- → **data-entry agent**: any transaction registration request
- → **CRM agent**: customer delinquency or collection follow-up
- → **strategy agent**: if user asks for long-term trend interpretation or growth strategy
- ← **frontdesk**: routes users with financial questions here
- ← **financeiro_monitor routine**: triggers `finance_monitor_report` skill for automated snapshots

**Boundary clarity**: Excellent. The agent explicitly states what it does NOT do (registration, cost margins, delinquency). The schema is rigidly defined to prevent SQL hallucinations. Retry logic (1 retry max) prevents infinite loops on SQL errors.
