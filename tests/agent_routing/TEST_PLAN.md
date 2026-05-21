# Agent Routing Test Plan

## Architecture context

Routing happens in `service.py` via keyword detection — NOT via LLM classification.
Priority order (first match wins):

```
1. detect_platform_intent()   → PlatformAgent
2. detect_synthesis_intent()  → SynthesisAgent  (strategic keywords OR 2+ dimensions)
3. detect_specialist_intent() → Specialist (supplier, scheduler, fiscal, doc-writer, crm, estrategia)
4. fallback                   → Frontdesk (RAG + SQL general)
```

**Important gaps identified in the routing logic:**
- `data-analyst` has no keyword route — only reachable if synthesis routes to it internally
- `agenda` room agent has no specialist route — calendar questions hit frontdesk
- `compras` / `financeiro` room agents have no specialist route — hit frontdesk
- `biblioteca` has no specialist route
- Ambiguous queries (e.g. "quais clientes priorizar essa semana") may hit synthesis instead of crm

---

## Layer 1 — Routing Coverage
*Goal: verify each routing path fires correctly. One clear query per agent.*

| # | Query | Expected Agent | Keyword(s) that trigger it |
|---|-------|---------------|---------------------------|
| 01 | "Cria uma rotina de digest financeiro toda segunda às 8h" | platform | "cria uma rotina" |
| 02 | "Ativa o monitor de estoque baixo" | platform | "ativa o monitor" |
| 03 | "Define uma meta de R$80k de faturamento para junho" | platform | "define uma meta" |
| 04 | "O que está puxando meu custo para cima esse mês?" | synthesis | "custo" + financial intent triggers synthesis keyword |
| 05 | "Como meu faturamento está afetando minha capacidade de compras?" | synthesis | 2 dimensions (financeiro + compras) |
| 06 | "Qual é o momento certo para fazer um investimento maior em estoque?" | synthesis | "investimento" keyword |
| 07 | "Quero fazer uma cotação de arroz com os fornecedores" | supplier-agent | "cotação" |
| 08 | "Manda mensagem no whatsapp pro fornecedor Atacado XYZ" | supplier-agent | "whatsapp fornecedor" |
| 09 | "Agenda uma reunião para quinta às 14h" | scheduler-agent | "agenda para" |
| 10 | "Verifica conflito de agenda para semana que vem" | scheduler-agent | "conflito de agenda" |
| 11 | "Emite uma nota fiscal para o cliente João Silva, R$1500, serviço de consultoria" | fiscal-agent | "nota fiscal" |
| 12 | "Qual meu regime tributário atual?" | fiscal-agent | "regime tributário" |
| 13 | "Redige um SOP de processo de compras" | doc-writer | "sop de" |
| 14 | "Cria um relatório de performance do time" | doc-writer | "cria um relatório" |
| 15 | "Quais clientes têm maior risco de churn?" | crm | "clientes em risco" |
| 16 | "Analisa o LTV por segmento de clientes" | crm | "ltv" |
| 17 | "Qual é o foco estratégico para o próximo trimestre?" | estrategia | "foco estratégico" |
| 18 | "Monta um plano trimestral para crescimento" | estrategia | "plano trimestral" |
| 19 | "Qual foi meu faturamento do mês passado?" | frontdesk | no keyword match → fallback |
| 20 | "Quantos clientes ativos tenho?" | frontdesk | no keyword match → fallback |

---

## Layer 2 — Routing Edge Cases & Gaps
*Goal: find where keyword routing breaks or misroutes.*

| # | Query | Expected Agent | Risk |
|---|-------|---------------|------|
| 21 | "Quais clientes devo priorizar essa semana?" | synthesis (2 dims: clientes+agenda) | may hit frontdesk if dimension terms not matched |
| 22 | "Quanto meu estoque parado está custando?" | synthesis | "custo" may trigger synthesis; "estoque" alone may not |
| 23 | "Cria uma meta e me mostra o dashboard de metas" | platform | "cria uma meta" should win over "mostra" |
| 24 | "Preciso de uma cotação e também verificar a agenda do fornecedor" | supplier-agent | first match wins — supplier should win |
| 25 | "Agenda uma reunião e define uma meta para o resultado" | platform | platform check is first — should win |
| 26 | "Análise de cohort dos clientes novos" | crm | "cohort" is the keyword |
| 27 | "Planejamento para o próximo mês" | estrategia | "plano mensal" — but query uses "planejamento" (different word) |
| 28 | "Qual fornecedor tem melhor histórico de entrega?" | supplier-agent | "fornecedor" keyword — should route there |
| 29 | "Escreve uma ata da reunião de hoje" | doc-writer | "ata da reunião" |
| 30 | "Qual o prazo da entrega do projeto X?" | scheduler-agent | "prazo" keyword |

---

## Layer 3 — Tool Invocation
*Goal: verify the correct tool is called, not just that routing is right.*

| # | Query | Agent | Tool expected |
|---|-------|-------|--------------|
| 31 | "Lista os fornecedores cadastrados" | supplier-agent | `list_suppliers` |
| 32 | "Verifica minha agenda para amanhã" | scheduler-agent | `query_calendar` |
| 33 | "Quais rotinas tenho ativas?" | platform | `listar_rotinas_catalogo` |
| 34 | "Quais são minhas metas?" | platform | `listar_metas` |
| 35 | "Mostra os clientes inativos nos últimos 90 dias" | crm | `execute_sql` |
| 36 | "Busca documentos sobre processo de vendas" | frontdesk | `executar_rag_cliente` |
| 37 | "Qual meu ticket médio do trimestre?" | frontdesk | `execute_sql` |
| 38 | "Quais SKUs estão abaixo do estoque mínimo?" | frontdesk | `execute_sql` |
| 39 | "Mostra os boards do Monday" | scheduler-agent | `monday_list_boards` |
| 40 | "Manda mensagem no Slack para o time comercial" | crm | `slack_post_message` |

---

## Layer 4 — Graceful Failure
*Goal: agent handles missing data, ambiguity, or impossible requests well.*

| # | Query | Expected behavior |
|---|-------|------------------|
| 41 | "Emite nota fiscal pro cliente XYZ" (sem valor) | fiscal-agent pede valor e descrição |
| 42 | "Manda cotação para os fornecedores" (sem especificar produto) | supplier-agent pede produto e quantidade |
| 43 | "Cria uma rotina" (sem especificar o quê) | platform elicita trigger e objetivo |
| 44 | "Define uma meta" (sem KPI) | platform pede dimensão, valor e prazo |
| 45 | "O que está acontecendo com meu negócio?" | synthesis ou frontdesk entrega snapshot geral |
| 46 | "Qual foi o resultado em 1990?" | frontdesk ou agente relevante retorna sem dados (sem inventar) |
| 47 | "Agenda uma reunião amanhã às 99h" | scheduler-agent rejeita horário inválido |
| 48 | "Quais clientes no planeta Marte?" | crm ou frontdesk retorna sem dados |
| 49 | "Cria tudo de uma vez" | platform ou frontdesk pede clareza |
| 50 | "Obrigado" | frontdesk responde sem chamar nenhuma tool |

---

## Identified routing gaps (to fix in service.py)

1. **`data-analyst`** — sem rota direta. Queries como "análise de tendência de vendas" vão para frontdesk.
   Fix: adicionar keywords `"análise de tendência"`, `"série histórica"`, `"correlação entre"` → `data-analyst`

2. **`agenda` room** — queries sobre agenda de negócios (ex: "quando vence o contrato X") vão para frontdesk.
   Fix: distinguir agenda de compromissos (scheduler) de agenda de prazos de negócio (frontdesk/synthesis)

3. **`planejamento` vs `plano`** — `"planejamento estratégico"` está nas keywords mas `"planejamento para"` não.
   Fix: adicionar `"planejamento para"` ao `estrategia` routing

4. **Synthesis false positive risk** — "custo" é uma synthesis keyword mas muitas queries simples sobre custo deveriam ir para frontdesk.
   Review: avaliar se `"custo"` sozinho é threshold suficiente ou se precisa estar combinado com outra dimensão.
