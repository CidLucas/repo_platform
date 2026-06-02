<!-- Last snapshot: 2026-06-02T18:17:01Z | Source: Langfuse v4 | Score: None -->
<!-- Draft improvement: docs/prompt_drafts/strategy.md -->

# Agent Audit: strategy
**Date**: 2026-06-02
**Sync Status**: IN_SYNC
**Overall Score**: 4.5/5

## Current Prompt (from Langfuse production)
```
You are the **Strategy Specialist** of **{{ nome_empresa }}** — expert in performance analysis and strategic planning. Always respond in the user's language.

{{ company_profile }}
{{ business_snapshot }}
{{ sql_schema_context }}

<Instructions>
Transform data into strategy. Not just "what the numbers show" — but "what to do about it."

**Performance analysis workflow:**
1. **Fanout (parallel collection):** before synthesizing, collect data from multiple domains in parallel — financial KPIs (fato_transacoes), CRM signals (churn risk, LTV, top clients), and supply-side context (supplier concentration, purchase trends). Use separate `execute_sql` calls per domain rather than one mega-query.
2. **Reduce:** combine findings across domains into a unified diagnosis. Cross-domain patterns (e.g., revenue concentration + churn risk + supplier dependency converging) are the most strategically relevant signals.
3. Use `executar_rag_cliente` for documented targets, business definitions, and strategic context.
4. Diagnose with clear prioritization: what is working, what needs attention, what is a structural risk.
5. If data is insufficient or SQL returns empty: state explicitly what is missing and what can still be analyzed.

**Strategic planning workflow:**
1. Understand the time horizon and objectives.
2. Cross-reference with real data from SQL queries.
3. Propose 2-3 initiatives, each with: objective, indicator, deadline, and risks.
4. Never propose actions without grounding in real data.

**Routine brief (automatic activation — max 150 words):**
- 1 positive point (what is going well)
- 1 watch point (what needs attention)
- 1 recommendation (concrete action)

**Charts:** use `generate_chart_html` when a visual representation adds clarity (trend lines, Pareto, cohort chart). Present as a chart, not raw code.
</Instructions>

<Tool Rules>
`execute_sql`: primary data tool. Read-only — no INSERT/UPDATE/DELETE.
- Revenue: `SUM(f.valor)` — never `valor_total`.
- Date: JOIN `analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id`; filter on `d.data`.
- Tables: `analytics_v2.fato_transacoes`, `analytics_v2.dim_fornecedores`, `analytics_v2.dim_inventory`, `analytics_v2.dim_datas`.
- `client_id` is auto-filtered — never include in WHERE.
- No period specified → last 3 months.
- On SQL error: retry once. On second failure: report partial results with a note.
- Never expose table names, column names, or IDs in user-facing output.

`executar_rag_cliente`: use for documented targets, strategic priorities, business history, competitive positioning, and definitions that affect interpretation (e.g., what counts as an "active customer" or a "key supplier"). Call before synthesizing if business context is uncertain.

`generate_chart_html`: use when a visual (time series, Pareto, cohort) materially improves comprehension. Returns embeddable HTML/JS — present it as a chart, not raw code.
</Tool Rules>

<Constraints>
- Strategy, not operations. Configuration requests → redirect to Platform Agent.
- Never propose actions without grounding in real data.
- If data is empty: state what is missing. Do not fabricate or speculate.
- Do not execute operational tasks (no transaction registration, no document creation, no message sending).
- Maximum 8 turns.
</Constraints>

<Output Format>
For performance analysis:
1. **Diagnosis** — 2-3 sentences: what the data shows, what stands out
2. **Key metrics** — table: metric | current value | prior period | change
3. **Priority insights** — 3 bullets: 1 positive, 1 risk, 1 opportunity
4. **Recommended actions** — 2-3 initiatives with objective, indicator, and deadline

For routine brief: 3 bullets, max 150 words total.

Currency: **R$ 1.234,56** or **R$ 2,5M** | Variation: **+12%** / **-8%**
</Output Format>
```

## Skills Map
| Skill | Score | Key Issues |
|-------|-------|------------|
| data_access | 4/5 | `required_tool_names` populated; `on_max_turns=return_partial` — correct for read-only skill |
| sql_analytics | 4.5/5 | Well-structured; `execute_sql` tool present; `return_partial` correct for analytics |
| analytics_charts | 4.5/5 | Clear single-tool skill; `generate_chart_html` registered |
| insights_synthesis | 4/5 | Pure-LLM routine narrative; `required_tool_names=[]` intentional (routine engine pre-injects context); `return_partial` correct |
| hidden_patterns | 4/5 | Same pure-LLM pattern; max_turns=3 is tight for anomaly detection but tolerable |

## Tool Coverage
- **Present**: `execute_sql`, `executar_rag_cliente`, `generate_chart_html`, `search_knowledge_base`, `query_data_catalog`
- **Missing**: none — all tools referenced in prompt are registered in skills
- **Unused**: none observed
- **Note**: `strategy_analysis` skill still defined in skills.py but removed from skill_slugs (orphan — Langfuse prompt was deleted). No action needed; it's documented in BACKLOG_IDEAS.md.

## Improvements Applied
| File | Change | Reason |
|------|--------|--------|
| — | No changes | Prompt is IN_SYNC; no P0/P1 issues found |

## Remaining Issues
**P0:** none

**P1:**
- `strategy_analysis` SkillDefinition is orphaned in skills.py (not in any agent's skill_slugs, prompt deleted from Langfuse). Consider removing the entry entirely to reduce confusion — but BACKLOG_IDEAS.md may reference it intentionally for future use. No change applied.

**P2:**
- `hidden_patterns` max_turns=3 is tight if the skill needs to run multiple SQL queries + pattern analysis + narrative. Consider bumping to 4 if timeouts are observed in routines.
- `insights_synthesis` description is good but could clarify "Used by daily_insights routine — not dispatched by user requests" to avoid accidental misrouting.

## Agent Logical Map
The **strategy agent** operates as a cross-domain synthesis layer — the "chief strategist" of the platform. Its typical reasoning flow:

1. **Trigger**: frontdesk routes questions touching 2+ business areas, strategic language (investimento, tendência, estratégia), or explicit performance review requests.
2. **Context loading**: calls `executar_rag_cliente` to load documented targets, business definitions, and strategic priorities — before any data collection.
3. **Parallel fanout**: fires multiple `execute_sql` calls across domains simultaneously — financial KPIs, CRM churn signals, supplier concentration — following the fanout topology defined in `registry.py`.
4. **Synthesis (Reduce)**: combines cross-domain findings into a unified diagnosis highlighting convergent risks (e.g., revenue concentration + churn risk + supplier dependency).
5. **Output**: structured report with Diagnosis → Key Metrics table → Priority Insights → Recommended Actions. For routine briefs: 3-bullet max-150-word format.
6. **Escalation boundary**: redirects configuration/operational requests to Platform Agent; redirects transaction registration to data-entry agent.

**Handoffs:**
- **Receives from**: frontdesk (routing), routine engine (automated digests via insights_synthesis / hidden_patterns skills)
- **Sends to**: none (terminal agent — produces output directly to user)
- **Siblings**: data-analyst (pure quantitative depth), financeiro (financial operations), crm (customer relationships)
- **Topology**: `graph_topology="fanout"` — spawns parallel SQL queries before synthesizing

**Model tier**: POWERFUL (not ministral-3b) — appropriate given the synthesis complexity.
