---
name: fragment/fallback-strategy
category: system
version: 1
required_variables: []
optional_variables: {}
---

<!--
This file is the in-repo fallback for prompt `fragment/fallback-strategy`.
It is used when Langfuse is unreachable. The canonical content lives
in Langfuse under label `production` (see
docs/internal/llm-sql-allowlist.md and the Phase 0 / F0.5 audit).

Description: Fallback strategies when metrics/dimensions unavailable
-->

# FALLBACK STRATEGIES

| Request | If unavailable | Offer |
|---------|---------------|-------|
| By neighborhood | → | By city or state |
| By city | → | By state or region |
| Recency | → | Monthly frequency or last purchase date |
| Margin/profit | → | Total revenue or average ticket |
| New customer count | → | Total customers or orders |
| By salesperson | → | By region |
| By category | → | By product (top 10) |

Always explain when using a fallback.
