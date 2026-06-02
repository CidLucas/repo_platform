# Backlog — Agentes & Skills

---

## 🐛 BUG — Skills dos monitores ausentes do SKILL_REGISTRY (Jun/2026)

**Detectado em:** testes de validação do sistema de rotinas (02/Jun/2026)

As seguintes skills referenciadas em steps de rotina de monitor não existem no `SKILL_REGISTRY`:
- `agenda_monitor_report` (agenda_monitor → step build_timeline)
- `clients_monitor_report` (clientes_monitor → step analyze_customers)
- `inventory_digest` (compras_monitor → step analyze_stock)
- `finance_monitor_report` (financeiro_monitor → step analyze_cashflow)

**Comportamento atual:** engine faz fallback para `_invoke_worker` → `Unknown worker` → step retorna `summary=""` → `write_memory` falha com `'summary' is required`.

**Fix:** registrar as 4 skills em `blu_agent_framework/skills.py → SKILL_REGISTRY` com a assinatura correta, retornando pelo menos `{"summary": str}`.

---

## 🐛 BUG — Mismatch de chave `summary` vs `memory_summary` nos monitors (Jun/2026)

**Detectado em:** testes de validação do sistema de rotinas (02/Jun/2026)

Steps de skill retornam a chave `summary`, mas o step `write_memory` usa `{{memory_summary}}`.
Enquanto as skills não existem no registry, o state tem `summary=""` mas não tem `memory_summary`.
O placeholder `{{memory_summary}}` é passado literal ao banco.

**Fix:** alinhar o template do step `write_memory` de todos os monitors para usar `{{summary}}` OU garantir que as skills retornem `memory_summary` explicitamente. Preferência: usar `{{summary}}` (mais simples).

---

## 🐛 BUG — `{{threshold_caixa}}` não resolvido no financeiro_monitor (Jun/2026)

**Detectado em:** testes de validação do sistema de rotinas (02/Jun/2026)

Steps `get_projection` e `eval_alert` do financeiro_monitor recebem a string `{{threshold_caixa}}` em vez do float esperado.

**Causa:** `config_schema` do catálogo define `threshold_caixa` com default `5000`, mas `schema_defaults` não está sendo injetado no state quando o default não está em `client_routines.config`.

**Fix:** verificar o loop de injeção de `schema_defaults` no engine (`_execute_one`). O default do `config_schema` deve ir para o state mesmo quando `client_routines.config` está vazio.

---

## 🐛 BUG — `cash_flow_alert` usa metric `saldo_conta_corrente` fora do NUMERIC_METRIC_REGISTRY (Jun/2026)

**Detectado em:** testes de validação do sistema de rotinas (02/Jun/2026)

O catálogo define `cash_flow_alert` com `trigger_config.metric = saldo_conta_corrente`, mas essa métrica não existe no `_NUMERIC_METRIC_REGISTRY`. O poller silencia a rotina → nunca dispara.

**Fix:** adicionar RPC `get_saldo_conta_corrente_monthly_rate` ao registry, OU migrar `cash_flow_alert` para trigger `cron` já que o threshold de caixa é melhor avaliado como cheque periódico (o monitor `financeiro_monitor` já cobre esse caso via function step `eval_alert`).

---

## ⏳ PENDENTE — Migração Agent Catalog PT → EN

**Status:** Slugs PT (`compras`, `financeiro`, `agenda`, `estrategia`, `clientes`, `documentos`) ainda ativos. Nenhuma migration de rename encontrada em `applied/`.

**Decisão registrada (Lucas, 25/Mai/2026):** Unificar tudo em EN. Não bloquear onboarding — fazer sprint dedicada (~2-3h).

**Escopo:**
1. SQL UPDATE em `agent_catalog` (compras→purchasing, financeiro→finance, agenda→scheduling, documentos→documents, estrategia→strategy, clientes→clients)
2. UPDATE em cascata: `approval_requests.agent_slug`, `documents.agent_slug`, `client_enabled_agents.agent_slug`, `client_routines.agent_slug`, `client_routine_executions`
3. Refactor front (20+ arquivos): ComprasRoom.tsx, FinanceiroRoom.tsx, EstrategiaRoom.tsx, etc.
4. Resolver duplicatas Gen1 vs Gen2 pós-migração (`finance` Gen1 conflitará com `financeiro→finance`)

**⚠ Pitfall:** fazer fora de horário ou usar dual-write (alias temporário) por 24h para não quebrar tenants ativos.

---

## ⏳ PENDENTE — Tier Enforcement & Resource Assignment Redesign

**Status:** `features.py` e `tier_validator.py` existem, mas Tier→Features→Resources não implementado. Tier ainda filtra tools diretamente em `factory.py`.

**Modelo correto:**
```
Tier → Features habilitadas → Resources (agents, skills, tools, data sources) → atribuídos no build-time
```

**Antes de implementar:**
1. Inventário de todos agents + tools + skills
2. Agrupamento em Features lógicas (ex: Feature "Compras" = ComprasMonitor + supplier-agent + tools de estoque)
3. Mapa Tier → Features (FREE / BASIC / SME / PREMIUM / ENTERPRISE)
4. Como AgentBuilder recebe a lista no build-time (hoje `enabled_tools: list[str]` hard-coded)

**Arquivos centrais:** `tier_validator.py`, `features.py`, `factory.py`, `registry.py`

---

## ⏳ PENDENTE — Agente RFQ Simplificação Radical

**Problema:** Agente atual gera PDF/documento formal — inadequado para PMEs.

**Visão:** Fluxo simples em 3 passos:
1. Recebe lista de compras (itens + quantidades)
2. Compara com fornecedores cadastrados e cotas
3. Retorna resultado em cards — cotações ranqueadas

**Princípios:** sem geração de documento, output em cards, leve e conversacional.

---

## ⏳ PENDENTE — [SKILL] strategy_analysis

**Contexto:** Skill removida do `skill_slugs` do agente `strategy` (prompt deletado do Langfuse). Agente atual usa `insights_synthesis` + `hidden_patterns` — produz narrativa mas não prescrição estruturada.

**Gap:** Perguntas "o que priorizar esse trimestre?" não têm framework estruturado de resposta.

**Proposta:**
- Nome: `strategy_analysis`
- Fanout: coleta paralela (finance + CRM + compras + agenda) → reduce → Top 3 iniciativas priorizadas com KPI-alvo, timeline e risco
- Diferença de `insights_synthesis`: synthesis=narrativa descritiva; strategy_analysis=prescrição priorizada
- Formato saída: `{titulo, situacao_atual, acao_recomendada, kpi_alvo, timeline, risco}`

**Discutir antes:** sub-skill ou integração direta? Fanout feito pelo agente pai ou pela skill?

**Estimativa:** 2-3h (prompt + SkillDefinition) + 1h (integração no agente strategy)

---

## ⏳ PENDENTE — [ARCH] Cross-Agent Data Entry

**Problema:** `data-entry` é o ÚNICO agente com `register_transaction`. Outros agentes read-only não conseguem registrar dados sem quebrar o fluxo de conversa.

**Caso concreto:** CRM negocia inadimplência → chega em acordo → precisa registrar pagamento → hoje: "vá para o agente financeiro" → quebra UX.

**Opções:**
1. Handoff tool com contexto passado (frontdesk gerencia — perde fio da conversa)
2. Skill proxy de escrita restrita (`record_payment` dentro do CRM — abre exceção pontual a D3)
3. Sub-agent spawn via `delegate_to_worker` com payload estruturado (preserva D3 e UX)
4. Formulário de confirmação no frontend (bypassa LLM completamente para escrita)

**Discutir:** qual padrão de spawn já existe? Quanto contexto é perdido num handoff? Opção 2 viola D3?

**Estimativa:** 1 dia (handoff) a 1 semana (sub-agent spawn infra)

---

## ⏳ PENDENTE — Parallel Tool Execution (Todos os Agentes)

**Status:** `fan_out_tool_calls` existe em `nodes.py` (linha 252) e em testes, mas agentes ainda executam tools sequencialmente. Confirmado que `service.py` menciona fanout apenas em comentário.

**Problema:** Agentes com 2-3 tools por turn (ex: `strategy`) rodam 2-3x mais lento.

**Solução:**
```python
graph.add_conditional_edges("elicit", fan_out_tool_calls, ["execute_single_tool"])
```
Ou: `Command(goto=[Send(...), Send(...)])` direto do nó elicit (LangGraph ≥ 0.2).

**Escopo:** agentes com `graph_topology="fanout"` (strategy, data-analyst). `collect_tool_results` e `execute_single_tool` já existem ✅.

**Estimativa:** 1-2 dias
