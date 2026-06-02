# Agent Routing Test Plan

> **Last updated:** 2026-06-01 — rewritten to reflect Arq v3 LLM routing.

## Architecture (Arq v3)

Routing is **LLM-driven**, not keyword-based. The frontdesk agent decides which specialist
to call by invoking the `route_to_specialist` tool with a slug and a reason sentence.

```
User message
    ↓
frontdesk graph (LLM)
    ↓  (calls route_to_specialist tool)
service.py intercepts __ROUTE_TO_SPECIALIST__:<slug>:<reason>
    ↓
specialist graph (slug)
    ↓
response → user
```

The frontdesk LLM chooses the slug based on:
1. The `routing_hint` of each agent (from `registry.py`) — injected into the frontdesk catalog prompt
2. The `route_to_specialist` tool description (from `common_module.py`) — lists valid slugs + domains

**`_SLUG_ALIASES`** in `common_module.py` normalises any non-canonical slug the LLM emits into a valid slug.

---

## Valid Agent Slugs (Arq v3)

| Slug | Domain |
|---|---|
| `frontdesk` | Entry point — simple questions, SQL queries, RAG |
| `platform` | Routine management, goal setting, operational config |
| `financeiro` | Financial reports, revenue, cash flow, expenses |
| `compras` | Procurement, suppliers, RFQ, purchasing cost |
| `crm` | Client outreach, churn, LTV, cohort, reactivation |
| `agenda` | Calendar, scheduling, Monday.com, deadlines |
| `data-analyst` | Trend analysis, correlation, scenario modelling |
| `strategy` | Strategic analysis, KPIs, growth recommendations |
| `doc-writer` | Documents, SOPs, proposals, reports, briefs |
| `fiscal-agent` | NF-e, NFS-e, fiscal compliance, SEFAZ |
| `data-entry` | Register transactions, map data, set up routines |
| `context-gatherer` | Knowledge base search, stored documents |

> **Note:** `synthesis` and `estrategia` are **Arq v2 legacy names** — do not use.
> They map via `_SLUG_ALIASES` to `strategy`. Tests must use current slug names.

---

## Known Routing Gaps (as of 2026-06-01)

- **`platform`** not in frontdesk catalog (`frontdesk_visible=True` set but routing_hint may be
  ignored when platform slug is absent from the tool description) — TCs #33, #43, #49 failing
- **`fiscal-agent`** intercepted by `context-gatherer` via legacy `_SLUG_ALIASES` entry for `"nota fiscal"` — TCs #11, #41 failing
- **`route_to_specialist` tool description** lists `"estrategia"` instead of `"strategy"` — causes _SLUG_ALIASES normalisation warning
- **`crm` routing_hint** covers churn/LTV/cohort but frontdesk LLM under-routes there for informal phrasing

---

## Layer 1 — Routing Coverage
*Goal: verify each agent slug is reachable from a clear, direct request.*

| # | Query | Expected Slug | Routing signal |
|---|---|---|---|
| 01 | "Cria uma rotina de digest financeiro toda segunda às 8h" | platform | routing_hint: "Routine management" |
| 02 | "Ativa o monitor de estoque baixo" | platform | routing_hint: "operational configuration" |
| 03 | "Define uma meta de R$80k de faturamento para junho" | platform | routing_hint: "goal setting" |
| 04 | "Qual a tendência de crescimento do meu faturamento nos últimos 6 meses?" | data-analyst | routing_hint: "Trend analysis" |
| 05 | "Qual é o impacto do aumento de custo de matéria-prima na minha margem?" | strategy | routing_hint: "scenario modelling, KPIs" |
| 06 | "Qual é o foco estratégico para o próximo trimestre?" | strategy | routing_hint: "Strategic analysis, growth" |
| 07 | "Quero fazer uma cotação de arroz com os fornecedores" | compras | routing_hint: "RFQ dispatch" |
| 08 | "Quais fornecedores têm melhor histórico de entrega?" | compras | routing_hint: "supplier reviews, fornecedores" |
| 09 | "Agenda uma reunião para quinta às 14h" | agenda | routing_hint: "scheduling" |
| 10 | "Verifica conflito de agenda para semana que vem" | agenda | routing_hint: "Calendar availability, scheduling conflicts" |
| 11 | "Emite uma nota fiscal para o cliente João Silva, R$1500, serviço de consultoria" | fiscal-agent | routing_hint: "NF-e, NFS-e" |
| 12 | "Qual meu regime tributário atual?" | fiscal-agent | routing_hint: "fiscal compliance" |
| 13 | "Redige um SOP de processo de compras" | doc-writer | routing_hint: "SOPs" |
| 14 | "Cria um relatório de performance do time" | doc-writer | routing_hint: "Document writing, reports" |
| 15 | "Quais clientes têm maior risco de churn?" | crm | routing_hint: "churn analysis" |
| 16 | "Analisa o LTV por segmento de clientes" | crm | routing_hint: "LTV, client segmentation" |
| 17 | "Registra uma entrada de R$3.200 de venda de produto hoje" | data-entry | routing_hint: "Register transactions" |
| 18 | "Qual foi meu faturamento do mês passado?" | frontdesk | simple SQL — no handoff needed |
| 19 | "Quantos clientes ativos tenho?" | frontdesk | simple SQL — no handoff needed |
| 20 | "Busca documentos sobre nosso processo de onboarding" | frontdesk | RAG — no handoff needed |

---

## Layer 2 — Routing Edge Cases
*Goal: find where the LLM misroutes due to ambiguous phrasing or overlapping domains.*

| # | Query | Expected Slug | Risk |
|---|---|---|---|
| 21 | "Quais clientes devo priorizar essa semana?" | crm | RISK: may go strategy (multi-dim) or frontdesk |
| 22 | "Quanto meu estoque parado está me custando?" | strategy | RISK: "custo" alone may stay frontdesk |
| 23 | "Cria uma meta e me mostra o dashboard de metas" | platform | compound: goal creation wins |
| 24 | "Preciso de uma cotação e também verificar a agenda do fornecedor" | compras | first clear intent: RFQ |
| 25 | "Agenda uma reunião e define uma meta para o resultado" | platform | RISK: "agenda" may win first |
| 26 | "Análise de cohort dos clientes novos" | crm | routing_hint: "cohort analysis" |
| 27 | "Planejamento estratégico para o próximo mês" | strategy | should not go frontdesk |
| 28 | "Lista os fornecedores cadastrados" | compras | routing_hint: "gestão de fornecedores" |
| 29 | "Escreve uma ata da reunião de hoje" | doc-writer | routing_hint: "briefs" |
| 30 | "Qual o prazo da entrega do projeto X?" | agenda | routing_hint: "deadline management" |

---

## Layer 3 — Tool Invocation
*Goal: verify the correct tool is called inside the specialist, not just that routing is right.*

| # | Query | Expected Slug | Tool expected |
|---|---|---|---|
| 31 | "Lista os fornecedores cadastrados" | compras | `list_suppliers` |
| 32 | "Verifica minha agenda para amanhã" | agenda | `query_calendar` |
| 33 | "Quais rotinas tenho ativas?" | platform | `listar_rotinas_catalogo` |
| 34 | "Quais são minhas metas?" | platform | `listar_metas` |
| 35 | "Mostra os clientes inativos nos últimos 90 dias" | crm | `execute_sql` |
| 36 | "Busca documentos sobre processo de vendas" | frontdesk | `executar_rag_cliente` |
| 37 | "Qual meu ticket médio do trimestre?" | frontdesk | `execute_sql` |
| 38 | "Quais SKUs estão abaixo do estoque mínimo?" | frontdesk | `execute_sql` |
| 39 | "Mostra os boards do Monday" | agenda | `monday_list_boards` |
| 40 | "Manda uma mensagem no WhatsApp para o fornecedor Atacado XYZ" | compras | `send_whatsapp` |

---

## Layer 4 — Graceful Failure
*Goal: agent handles missing data, ambiguity, or impossible requests correctly.*

| # | Query | Expected Slug | Expected behavior |
|---|---|---|---|
| 41 | "Emite nota fiscal pro cliente XYZ" (sem valor) | fiscal-agent | pede valor e descrição |
| 42 | "Manda cotação para os fornecedores" (sem produto) | compras | pede produto e quantidade |
| 43 | "Cria uma rotina" (sem especificar o quê) | platform | elicita trigger e objetivo |
| 44 | "Define uma meta" (sem KPI) | platform | pede dimensão, valor e prazo |
| 45 | "O que está acontecendo com meu negócio?" | strategy | snapshot geral sem alucinar |
| 46 | "Qual foi o resultado em 1990?" | frontdesk | retorna sem dados — não inventa |
| 47 | "Agenda uma reunião amanhã às 99h" | agenda | rejeita horário inválido |
| 48 | "Quais clientes no planeta Marte?" | frontdesk | retorna sem dados — não inventa |
| 49 | "Cria tudo de uma vez" | platform | pede clareza |
| 50 | "Obrigado" | frontdesk | responde sem chamar nenhuma tool |

---

## Known Bugs Affecting Test Results

See `references/systemic-bugs-20260528.md` and `references/systemic-bugs-20260529.md` for full details.

| Bug | Affected TCs | Root Cause | Fix Location |
|---|---|---|---|
| `fiscal-agent` → `context-gatherer` | #11, #41 | `_SLUG_ALIASES` legacy entry | `common_module.py` |
| `platform` not reached | #33, #43, #49 | Missing from `route_to_specialist` tool description | `common_module.py` |
| `crm` under-routed | #15, #16, #35 | Frontdesk LLM weak on informal phrasing | `agents/frontdesk` Langfuse prompt |
| HTTP 0 timeouts | #02, #18 | `deepseek-v4-flash` 403 on POWERFUL tier | `client.py` → swap to `qwen3.5` |
| `__ROUTE_TO_SPECIALIST__` token leaking | varies | `service.py` not consuming sentinel | `service.py` |
| GraphRecursionError | CRM/strategy | `recursion_limit=12` too low | `builder.py` |
