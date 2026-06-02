# Backlog — Frontend & Métricas

---

## ⏳ PENDENTE — BKL-02: HomePage widget semanas com `'—'` hardcoded

**Arquivo:** `HomePage.tsx:482–483`

**Fix:** Substituir por contagem real de `approval_requests` agrupadas por semana.

**Esforço:** 2h

---

## ⏳ PENDENTE — BKL-03: ComprasRoom `lead_time_medio_dias` e `otif_perc` sempre `'—'`

**Fix:**
- OTIF requer `promised_delivery_at` em `approval_requests` (não existe — migration necessária)
- Lead time calculável: `AVG(decided_at - created_at)` das aprovações

**Esforço:** 3h (migration + atualizar `get_supply_indicators`)

---

## ⏳ PENDENTE — BKL-06: FinanceiroRoom `dso_dias`, `dpo_dias`, `ccc_dias`, `working_capital_ratio` sempre NULL

**Bloqueio:** Requerem tabelas de contas a pagar/receber (ausentes no schema) e `due_date` em transações.

**Esforço:** 4h para versão aproximada

---

## ⏳ PENDENTE — BKL-07: AtividadeScreen NPS sempre `'—'`

**Fix:** RPC `analytics_v2.get_nps_score` não existe no DB. Criar função que lê de `client_insights` com `kpi='nps'` ou retorna NULL.

**Status:** baseline_v2.sql tem referências a analytics_v2, mas a função NPS específica não foi encontrada.

**Esforço:** 2h

---

## ⏳ PENDENTE — BKL-09: EstrategiaRoom sem KPIs próprios

**Fix:** Criar `get_strategy_summary()`: crescimento receita YoY, projeção de meta, market share.

**Esforço:** 5h

---

## ⏳ PENDENTE — BKL-11: `get_marketing_indicators` existe mas nunca usada

**Fix:** Integrar ao EstrategiaRoom ou criar MarketingRoom futuro.

**Esforço:** 3h

---

## 🔵 BAIXO — BKL-12: ComprasRoom `cost_savings_perc` e `ppv` sempre NULL

**Bloqueio:** Requerem `preco_referencia` por produto/fornecedor em `dim_inventory` (ausente). Decisão de produto necessária.

---

## 🔵 BAIXO — BKL-13: FinanceiroRoom EBITDA, CAC, inadimplência

**Bloqueio estrutural:** EBITDA requer separação OPEX vs COGS. CAC: sem dados de aquisição. Inadimplência: sem `contas_receber`.

---

## 🔵 BAIXO — BKL-14: Refresh periódico de Google Sheets

**Status:** `enqueue_incremental_syncs` só cobre BigQuery; Sheets é one-shot no onboarding.

**Fix:** verificar `drive_modified_time` como watermark → `upload-drive-source` → `run-csv-etl`.

**Parte da Fase 2 pendente.** Esforço: 4h

---

## 🔵 BAIXO — BKL-15: AdminScreen "Economia gerada" — definição pendente

**Decisão necessária:** diferença `custo_total` atual vs anterior, ou comparação com `valor_referencia`?
