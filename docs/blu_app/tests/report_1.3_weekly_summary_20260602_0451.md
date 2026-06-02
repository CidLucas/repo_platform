# Report — 1.3 weekly_summary
**Date:** 2026-06-02 04:51
**Skill:** weekly_summary | **Expected tool:** execute_sql | **Expected agent:** financeiro
**Pass rate:** 0/5

---

## 1. Summary

| Field | Value |
|---|---|
| Skill | 1.3 weekly_summary |
| Pass rate | 0/5 |
| Draft written | YES — `agents/financeiro` v2 (label: draft) |
| Context issues | Test client 6446d4fa has no transactions in current/prior week → SQL returns empty |

**Primary failures:**
- TC1–TC4: Frontdesk handled inline (no routing to `financeiro`), SQL returned empty data, agent gave "no data" responses
- TC5: Routed to `strategy` (wrong agent) — crashed with generic error

**Root causes:** `ROUTING_CONFIG` (skill not in any agent's skill_slugs) + `PROMPT_STATIC` (agents/financeiro uses wrong table names `fact_sales`, `dim_customer`)

---

## 2. Context Service — Test Client 6446d4fa

| Section | Status | Notes |
|---|---|---|
| company_profile | Unknown | Could not instantiate ContextService (requires RedisService arg) |
| brand_voice | Unknown | — |
| team_structure | Unknown | — |
| policies | Unknown | — |
| data_schema | Unknown | — |
| available_tools | Unknown | — |
| enabled_tool_names | N/A | Diagnosed via registry.py instead |
| default_system_prompt | N/A | No override detected |

**Note:** ContextService could not be instantiated outside agent container (requires injected dependencies). Diagnosis done via registry.py and direct Langfuse inspection.

---

## 3. TC Results Table

| TC | Message | HTTP | Agent routed | Tool called | Expected agent | PASS/FAIL |
|---|---|---|---|---|---|---|
| TC1 | "Ei, como foi minha semana?" | 200 | frontdesk | execute_sql (inline) | financeiro | ❌ FAIL |
| TC2 | "Gostaria de receber um resumo semanal completo..." | 200 | frontdesk | execute_sql (inline) | financeiro | ❌ FAIL |
| TC3 | "Resumo semanal agora." | 200 | frontdesk | execute_sql (inline) | financeiro | ❌ FAIL |
| TC4 | "Me passa o resumo de desempenho da semana passada..." | 200 | frontdesk | execute_sql (inline) | financeiro | ❌ FAIL |
| TC5 | "Preciso do relatório semanal para apresentar..." | 200 | strategy | none (crash) | financeiro | ❌ FAIL |

**Response quality:**
- TC1-TC3: SQL ran, returned empty (no data for test client this week). Agent acknowledged no data. Technically correct behavior for empty DB — but wrong agent.
- TC4: "Dificuldade ao processar SQL" — SQL error in prior-week query
- TC5: "Erro ao processar solicitação" — strategy agent crashed (likely Ollama 403 on deepseek-v4-flash/POWERFUL tier)

---

## 4. Root Cause Breakdown

| TC | Root Cause | Class | Priority |
|---|---|---|---|
| TC1–TC4 | `weekly_summary` not in `financeiro.skill_slugs`; frontdesk resolves inline | ROUTING_CONFIG | P1 |
| TC1–TC4 | Frontdesk routing table missing "resumo semanal/weekly" trigger terms for `financeiro` | ROUTING_CONFIG | P1 |
| TC5 | "relatório semanal para equipe" → `detect_specialist_intent` or LLM routes to strategy | ROUTING_CONFIG | P1 |
| TC5 | `strategy` agent uses POWERFUL model tier (deepseek-v4-flash) → Ollama 403 → crash | P0 code bug | P0 |
| TC1–TC4 | `agents/financeiro` Langfuse prompt references `fact_sales` + `dim_customer` (non-existent tables) | PROMPT_STATIC | P1 |

---

## 5. Prompt Improvements Applied

### agents/financeiro — `fact_sales` → `fato_transacoes` fix

**Draft written:** `agents/financeiro` v2 (label: `draft`)

**Old (problematic):**
```
1. Use `execute_sql` para consultar `analytics_v2.fact_sales` filtrando sempre por `client_id`
...
2. Verifique concentração: ... `analytics_v2.dim_customer` para ranking de clientes por receita
```

**New (fixed):**
```
1. Use `execute_sql` para consultar `analytics_v2.fato_transacoes f` — NUNCA `fact_sales`
2. Data: JOIN `analytics_v2.dim_datas d ON f.data_competencia_id = d.data_id`
...
- Tabelas: `fato_transacoes`, `dim_fornecedores`, `dim_inventory`, `dim_datas`
- NUNCA: `dim_clientes`, `dim_customer`, `dim_tipo_transacao`, `dim_categoria`, `fact_sales`
```

Also added: improved routing triggers, weekly summary output format template, and max_turns constraint.

---

## 6. Manual Fixes Needed (Code Changes)

### Fix A — Add `weekly_summary` to `financeiro.skill_slugs` (REQUIRED)

**File:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`

Current `financeiro` skill_slugs:
```python
skill_slugs=["financeiro_ops", "data_access", "sql_analytics", "analytics_charts", "csv_analytics"],
```

Needs:
```python
skill_slugs=["financeiro_ops", "data_access", "sql_analytics", "analytics_charts", "csv_analytics", "weekly_summary", "end_of_day_digest", "reconciliation_report"],
```

Then rebuild: `docker compose build --no-cache agent_api && docker compose up -d agent_api`

### Fix B — Add routing keywords to frontdesk prompt (Langfuse)

The `financeiro` routing hint in `agents/frontdesk` should include:
```
| Fluxo de caixa, DRE, análise financeira, relatório financeiro, resumo semanal, resumo da semana, balanço semanal, KPIs da semana, faturamento semanal | `financeiro` |
```

### Fix C — strategy agent crashes (Ollama 403)

Per `references/systemic-bugs-20260529.md`: `strategy` agent uses `ModelTier.POWERFUL` (deepseek-v4-flash) which returns 403. Fix: change to `OllamaCloudModel.QWEN3_5` in `client.py:~359`. This is a systemic P0 bug affecting all POWERFUL agents.

---

## 7. Re-run Results (Worst TCs)

| TC | 1st run | Re-run | Consistent? |
|---|---|---|---|
| TC4 | frontdesk → SQL error → "dificuldade ao processar" | frontdesk → SQL empty → "dados insuficientes" | Partially — different SQL error mode, same wrong agent |
| TC5 | strategy → crash → generic error | strategy → crash → generic error | ✅ Deterministic failure (strategy crash is consistent) |

**TC4:** Inconsistent failure mode — first run hit SQL error (recursion?), re-run got empty result. Root issue same: wrong agent. 
**TC5:** Deterministic — strategy agent crash is a systemic bug (Ollama 403 on POWERFUL tier).

---

## 8. Next Recommended Actions

1. **[P0 code]** Fix Ollama 403 on POWERFUL tier (`deepseek-v4-flash` → `qwen3.5`) in `client.py` — unblocks TC5 and all strategy agent tests
2. **[P1 code]** Add `weekly_summary`, `end_of_day_digest`, `reconciliation_report` to `financeiro.skill_slugs` in `registry.py` + rebuild
3. **[P1 Langfuse]** Promote `agents/financeiro` draft v2 to `production` in Langfuse UI — fixes `fact_sales`/`dim_customer` table name bugs
4. **[P1 Langfuse]** Update `agents/frontdesk` routing table to add "resumo semanal", "weekly", "KPIs da semana" trigger terms for `financeiro`
5. **[P1 data]** Test client 6446d4fa appears to have no fato_transacoes data for current week — run SQL validation before next QA cycle: `SELECT COUNT(*) FROM analytics_v2.fato_transacoes WHERE client_id = '6446d4fa-b845-4d1b-b3a3-ceed2dda6d44'`
6. **[QA next]** After fixes 1-3 above: re-test 1.3 with `--ids` flag targeting TC4/TC5; also test 1.4 (reconciliation_report) which likely has same routing/orphan issue
