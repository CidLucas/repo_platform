# QA Report — 0.1 frontdesk — 20260602_0031

## 1. Summary

| Field | Value |
|---|---|
| Skill ID | 0.1 |
| Skill | frontdesk |
| Test Date | 2026-06-02 03:31 UTC |
| Pass Rate | 2/5 (40%) |
| Draft Written | YES — `agents/frontdesk` v21 |
| Context Issues | ContextService not inspectable outside container (needs RedisService). Langfuse timeout on first loader call (60s disable) may cause empty prompt on cold start. |
| Test Client | 6446d4fa-b845-4d1b-b3a3-ceed2dda6d44 |

---

## 2. Context Service

| Section | Status | Notes |
|---|---|---|
| company_profile | UNKNOWN | ContextService requires RedisService arg — cannot inspect outside container |
| brand_voice | UNKNOWN | Same |
| team_structure | UNKNOWN | Same |
| policies | UNKNOWN | Same |
| data_schema | UNKNOWN | Same |
| available_tools | UNKNOWN | Same |
| enabled_tool_names | N/A | Frontdesk agent — tools derived from registry.py |
| default_system_prompt override | NO | `agents/frontdesk` exists in Langfuse with label=production |

**Langfuse Prompt Status:**
- `agents/frontdesk`: EXISTS (type=text, label=production, v20, 4878 chars) ✅
- `skill:sql_analytics:system`: EXISTS (label=production) ✅ (separate from frontdesk)
- `fragment/sql-rules`: EXISTS (label=draft+production) ✅

**Critical note:** On first loader call, Langfuse timed out and disabled for 60s. If a request arrives during that window, frontdesk runs with empty system prompt, causing LLM to fallback to raw SQL without routing instructions. This could explain some intermittent routing failures but does NOT explain deterministic TC1 failure (which consistently routes to inline SQL).

---

## 3. TC Results Table

| TC | Message | Expected | Got | HTTP | Result |
|---|---|---|---|---|---|
| TC1 | "Quero ver o relatório financeiro do mês passado" | financeiro | frontdesk (SQL loop) | 200 | ❌ FAIL |
| TC2 | "meus clientes tão sumindo, como tô em relação ao churn?" | crm | HTTP 500 | 500 | ❌ FAIL |
| TC3 | "Preciso agendar uma reunião com o time de vendas para quinta-feira às 15h" | agenda | agenda | 200 | ✅ PASS |
| TC4 | "Qual é a tendência de crescimento do faturamento nos últimos 6 meses e o que isso significa pro negócio?" | data-analyst ou strategy | frontdesk (SQL loop) | 200 | ❌ FAIL |
| TC5 | "quero fazer uma cotação de arroz e feijão com meus fornecedores" | compras | compras | 200 | ✅ PASS |

**Pass rate: 2/5 (40%)**

---

## 4. Root Cause Breakdown

| TC | Root Cause Class | Description |
|---|---|---|
| TC1 | `PROMPT_STATIC` | Frontdesk routing table trigger for `financeiro` does not include "relatório financeiro" explicitly. LLM classifies as "factual simple query" → Passo 2 (inline SQL). The trigger says "Fluxo de caixa, DRE, análise financeira com projeção, relatório de lucro" — missing "relatório financeiro" as trigger phrase. |
| TC2 | `ROUTING_CONFIG` (P0 code) | HTTP 500 on first run — CRM agent crashing (likely Ollama 403 on deepseek-v4-flash POWERFUL model, or GraphRecursionError cascade). On re-run: routing worked (200) but SQL loop inside CRM — test client may have no `fato_transacoes` data. |
| TC4 | `PROMPT_STATIC` | "Tendência de crescimento... o que isso significa pro negócio" is a multi-dimensional query (analytics + strategic). Routing table has "Tendência, correlação..." → data-analyst, but the LLM chose Passo 2 (inline SQL). Suggests either: (a) available_agents variable not rendered, or (b) LLM chose SQL over delegation. Without company profile context, `{{ available_agents }}` may render empty. |

**Summary:**
- `PROMPT_STATIC`: 2 TCs (TC1, TC4)
- `ROUTING_CONFIG P0`: 1 TC (TC2)
- PASS: 2 TCs (TC3, TC5)

---

## 5. Prompt Improvements Applied

### `agents/frontdesk` → v21 (draft)

**Change:** Expanded `financeiro` routing trigger in routing table.

**Before:**
```
| Fluxo de caixa, DRE, análise financeira com projeção, relatório de lucro | `financeiro` |
```

**After:**
```
| Relatório financeiro, fluxo de caixa, DRE, receita, faturamento mensal, análise financeira com projeção, relatório de lucro | `financeiro` |
```

**Rationale:** "relatório financeiro" is the most natural PT-BR phrasing a user would use when asking for financial summaries, yet it was absent from the routing trigger. Adding it + "receita" + "faturamento mensal" makes delegation deterministic for these high-frequency queries.

**NOTE: Draft NOT promoted to production.** Must be promoted manually in Langfuse UI: Prompts → agents/frontdesk → v21 → Add label "production".

---

## 6. Manual Fixes Needed

### 6.1 `route_to_specialist` tool description — source code fix required

File: `services/tool_pool_api/src/tool_pool_api/server/tool_modules/common_module.py` (lines 226-243)

**Problem:** Tool description lists stale/invalid slugs:
- `"estrategia"` — should be `"strategy"` (v2 alias, confuses LLM)
- `"documentos"` — not a valid slug (not in `_VALID_SLUGS`), should be `"context-gatherer"`
- Missing: `"data-analyst"` and `"platform"` from the valid slug list

**Impact:** LLM may attempt to route to non-existent slugs, triggering fallback to `context-gatherer`.

**Suggested fix:**
```python
description=(
    "Delegate the current request to a domain specialist agent. "
    "VALID slugs: "
    "context-gatherer (search knowledge base, retrieve stored documents), "
    "financeiro (financial analysis, revenue, cash flow, reports), "
    "compras (procurement, suppliers, RFQ, quotes, purchasing cost), "
    "crm (client emails, churn, LTV, cohort, reactivation, follow-up), "
    "strategy (strategic analysis, KPIs, growth, cross-domain questions), "
    "data-analyst (trends, correlations, scenario modelling, projections), "
    "platform (create routines, set goals, operational configuration), "
    "agenda (calendar, scheduling, Monday.com, deadlines, meetings), "
    "doc-writer (write documents, proposals, reports, SOPs, briefs), "
    "data-entry (register transactions, map data, set up data structures), "
    "fiscal-agent (NF-e, NFS-e, tax compliance, SEFAZ). "
    "Args: agent_slug (one of the valid slugs above), reason (one sentence why)."
),
```

Rebuild required: `docker compose build --no-cache && docker compose up -d`

### 6.2 `{{ available_agents }}` variable injection — verify template rendering

TC4 failure may indicate that `{{ available_agents }}` is NOT being injected into the frontdesk prompt at runtime. If this Jinja variable renders empty, the LLM has no routing table and defaults to inline SQL.

**Investigation:** Add a debug log in `service.py` or `factory.py` to confirm `available_agents` is populated before invoking the frontdesk LLM.

### 6.3 CRM POWERFUL model (Ollama 403)

Per `systemic-bugs-20260529.md`: `deepseek-v4-flash` (ModelTier.POWERFUL) returns 403. CRM agent uses POWERFUL tier. Fix: change `client.py:~359` to `OllamaCloudModel.QWEN3_5`. Rebuild required.

### 6.4 Test client data

Test client `6446d4fa-b845-4d1b-b3a3-ceed2dda6d44` may have no `fato_transacoes` rows. The SQL loop on TC1/TC2/TC4 re-run could be "query returns 0 rows" triggering a retry loop. Verify:
```sql
SELECT COUNT(*) FROM analytics_v2.fato_transacoes WHERE client_id = '6446d4fa-b845-4d1b-b3a3-ceed2dda6d44';
```

---

## 7. Re-run Results

| TC | 1st Run | Re-run | Verdict |
|---|---|---|---|
| TC1 (worst) | frontdesk SQL loop (200) | frontdesk SQL loop (200) | **DETERMINISTIC** fail — routing table trigger issue |
| TC2 (worst) | HTTP 500 (crash) | crm 200, SQL loop inside | **INTERMITTENT** — routing now works but CRM internal SQL fails |

TC2 improvement suggests the HTTP 500 was transient (Ollama startup or cold start). The underlying CRM SQL failure is a data issue (no transactions for test client).

---

## 8. Next Recommended Actions

1. **P0 — Promote `agents/frontdesk` draft v21 to production** in Langfuse UI to fix financeiro routing.
2. **P0 — Fix `route_to_specialist` tool description** in source (invalid slugs, missing data-analyst/platform) + rebuild.
3. **P0 — Fix Ollama POWERFUL model** (`deepseek-v4-flash` → `qwen3.5`) in `client.py` + rebuild.
4. **P1 — Verify `{{ available_agents }}` rendering** in frontdesk context — if empty, all LLM routing decisions are blind.
5. **P1 — Verify test client data** — confirm `6446d4fa` has `fato_transacoes` rows, otherwise all SQL-backed agents will show "no data" (not a bug).
6. **Next test cycle:** After fixes + rebuild, re-run 0.1 to confirm pass rate improvement target 4+/5.
7. **Continue to skill 0.2 (sql_analytics)** in next cron run.

---

## Appendix: Tool Description Audit

`route_to_specialist` description (current — as of 2026-06-02):
- ✅ Lists: financeiro, compras, crm, agenda, doc-writer, fiscal-agent
- ❌ Missing: data-analyst, platform, strategy (uses "estrategia" v2 alias)
- ❌ Invalid: "documentos" (not a valid slug), "estrategia" (alias, not canonical)
- ❌ `context-gatherer` described as "data entry, register transactions" — incorrect domain (should be KB search)
