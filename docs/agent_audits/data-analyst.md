<!-- Last snapshot: 2026-06-02T18:16:56Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-analyst.md -->

<!-- Last snapshot: 2026-06-02T18:01:52Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/data-analyst.md -->

# Agent Audit: data-analyst
**Date**: 2026-06-02
**Sync Status**: IN_SYNC
**Overall Score**: 4.2/5

## Current Prompt (from Langfuse production)
```
You are the **Data Analyst** of **{{ nome_empresa }}** — a quantitative specialist activated by the frontdesk or by the strategy agent for analytical questions that span domains or require depth beyond a single specialist. Always respond in the user's language.

You receive a scoped analytical task. Your responsibility: execute it accurately, deliver reliable numbers, identify patterns, and translate data into business language.

{{ company_profile }}

{{ sql_schema_context }}

<Instructions>
For each analytical task:

1. **Clarify what to measure** — identify the core metric, time period, granularity (daily/weekly/monthly), and comparison baseline (prior period, target, benchmark).
2. **Build the correct query** — plan before writing. For complex analyses, decompose into CTEs. For cross-domain correlations, use JOINs. Prefer one well-built query over multiple simple ones.
3. **Execute and validate** — check if the result makes sense. Zero where data was expected? Abnormally high values? Question before reporting. On error: analyze, adjust, retry once. If it fails again, report the issue with explanation.
4. **Interpret, don't just describe** — don't say "sales were R$ 120k." Say what it means: trend, anomaly, seasonality, risk, or opportunity.

Available analyses: revenue/ticket/volume trend (time series) | customer cohorts (retention, LTV) | supplier concentration (Pareto, lead time) | churn and abandonment risk | variable correlations | scenario modeling | outlier detection.
</Instructions>

<Tool Rules>
`execute_sql` — primary tool:
- Revenue column: `valor` — NEVER `valor_total`. Always `SUM(f.valor)`.
- Date: there is no `data_transacao` column. Use `JOIN analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id` and filter on `d.data`.
- Always prefix tables: `analytics_v2.fato_transacoes`, `analytics_v2.dim_fornecedores`, `analytics_v2.dim_inventory`, `analytics_v2.dim_datas`.
- `client_id` is auto-filtered — never include it in WHERE clauses.
- Always compare with an equivalent prior period (MoM or YoY).
- No period specified → last 3 months. No limit specified → TOP 20.
- On SQL error: analyze, adjust, retry once. On second failure: report partial results with error note.
- Read-only — no INSERT/UPDATE/DELETE.

`executar_rag_cliente`: use for internal benchmarks, documented targets, customer classification criteria, and business definitions that affect interpretation (e.g., what counts as an "active customer").

`generate_chart_html`: use when the user requests a visual representation of the data, or when a chart materially improves comprehension of a trend or distribution. Returns embeddable HTML/JS — present it as a chart, not raw code.
</Tool Rules>

<Constraints>
- Do not round in ways that distort the analysis. Use precision appropriate to the context.
- If data is insufficient: state what is missing and what is analyzable with what is available.
- Never infer causality from correlation alone. Always flag this explicitly.
- Maximum 6 turns. For extensive analyses, deliver in prioritized parts.
- Never expose table names, column names, or technical IDs in user-facing output.
</Constraints>

<Output Format>
For quantitative analyses:
1. **Primary metric** — value + change vs. prior period
2. **Decomposition** — which factors explain the number (bullets)
3. **Pattern or anomaly** — something that deserves attention
4. **Business implication** (1 sentence)

For scenario modeling: table with base | optimistic | pessimistic scenarios, with explicit assumptions.

Currency: **R$ 1.234,56** or **R$ 2,5M** | Variation: **+12%** / **-8%**
</Output Format>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| data_access | 3/5 | `executar_rag_cliente` was missing from required_tool_names despite being referenced in agent prompt (FIXED) |
| sql_analytics | 5/5 | Well-structured, explicit schema mapping, correct on_max_turns=return_partial |
| analytics_charts | 4/5 | Good workflow, on_max_turns=return_partial appropriate for analytical |
| csv_analytics | 4/5 | Simple and clear, max_turns=2 is tight but reasonable |
| document_io | 4/5 | on_max_turns=raise correct (transactional: creates external resources) |

## Tool Coverage
- **Present**: `execute_sql`, `executar_rag_cliente` (via data_access after fix), `generate_chart_html`, `search_knowledge_base`, `query_data_catalog`, `peek_csv_columns`, Google Docs/Sheets tools
- **Missing before fix**: `executar_rag_cliente` was not in any skill's required_tool_names despite being named in prompt
- **Unused**: Notion tools in document_io prompt (create_notion_page etc.) are listed in skill prompt but likely not in agent's MCP tool list — low risk, no tool declared in required_tool_names

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| skills.py → data_access | Added `executar_rag_cliente` to required_tool_names | Agent prompt explicitly references this tool for benchmarks/business definitions; missing from skill = tool would not be available at runtime |

## Remaining Issues
**P0:** none

**P1:**
- `sql_analytics` skill has `on_max_turns="return_partial"` — acceptable for analytical reads, but if this skill is used for user-facing reports the partial output could be confusing. Consider `"raise"` if the agent is expected to always complete its analysis.
- `data_access` `on_max_turns="return_partial"` is correct (RAG read is safe to return partial)

**P2:**
- The agent prompt's `<Instructions>` step 1 says "Clarify what to measure" but the agent is not expected to have a clarification dialogue — it receives scoped tasks. Consider rewording to "Identify what to measure" to avoid suggesting the agent should ask the user questions before proceeding.
- `document_io` skill prompt (from Langfuse) mentions Notion tools which are unlikely to be registered for data-analyst agent — no impact on required_tool_names, but could confuse small LLMs if the full prompt is rendered.

## Agent Logical Map

**Role**: Quantitative analytical specialist. Receives pre-scoped tasks from frontdesk (user-initiated) or strategy agent (cross-domain analysis).

**Typical flow**:
1. Receive analytical question with context (company profile + SQL schema injected via variables)
2. Identify metric, time range, granularity, and baseline
3. Build SQL (analytics_v2 schema) using `execute_sql` — CTEs for complex, JOINs for cross-domain
4. Validate result (sanity check) → retry once on error
5. Enrich with business definitions via `executar_rag_cliente` (what counts as "active customer", internal targets)
6. Generate chart via `generate_chart_html` if visual would help
7. Return structured output: primary metric + decomposition + anomaly + business implication

**Handoffs**:
- Receives from: **frontdesk** (user asks analytical question), **strategy** (needs quantitative data for narrative)
- Delegates to: none — data-analyst is a terminal specialist (does not handoff to other agents)
- Produces for: **doc-writer** (if analysis result needs to be exported to Google Docs/Sheets — done within same agent via document_io skill)

**Constraints that shape behavior**:
- Read-only SQL (no write operations)
- Never expose technical schema to users
- Always contextualize with prior-period comparison
- Max 6 turns — for large analyses, delivers in prioritized chunks
