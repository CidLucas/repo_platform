# Blu System Report — QA Cron Consolidado
**Gerado:** 2026-06-02 | **Ciclos analisados:** 73 runs (27/05 → 02/06)  
**Cobertura de skills:** 0.1 sql_analytics · 0.3 dim_inventory · 0.4 register_transaction · 0.5 rag · 1.1 morning_plan · 1.2 end_of_day_digest · 2.1 ledger · 2.2 fornecedores · 2.5 financeiro (HITL) · 3.x agenda/calendar · 4.x monday · CRM · strategy · platform/routines

---

## 🚨 P0 — Bloqueadores Críticos

### P0-1 · Ollama Cloud 403 em ModelTier.POWERFUL
**Arquivo:** `libs/blu_llm_service/src/blu_llm_service/client.py` ~L359  
**Impacto:** Derruba 100% dos agentes com tier POWERFUL (`financeiro`, `crm`, `strategy`, `agenda`, `monday`). HTTP 500 / "Desculpe, ocorreu um erro." para o usuário.  
**Causa:** `deepseek-v4-flash` (e em fases posteriores `qwen3.5:397b` e `ministral-3:8b`) retornam 403 "this model requires a subscription" no Ollama Cloud.  
**Fix:**
```python
# client.py — atualizar _TIER_MAP para modelos sem assinatura
# Validar primeiro qual modelo está livre: llama3.2:3b, phi4:14b, gemma3:4b
# Rebuild obrigatório após mudança:
docker compose build --no-cache blu_agent_api && docker compose up -d blu_agent_api
```
**Evidência:** Todos os runs de 29/05 a 02/06 — 5/5 TCs falhando deterministicamente.

---

### P0-2 · Token `__ROUTE_TO_SPECIALIST__` vazando para o usuário
**Arquivo:** `services/agent_api/src/agent_api/service.py`  
**Impacto:** Usuário vê literalmente `__ROUTE_TO_SPECIALIST__:agenda:...` ou `commentary<|channel|>analysis<|message|>...` na resposta. Experiência quebrada.  
**Causa:** O token de roteamento interno não é consumido/filtrado antes de retornar a resposta ao cliente. Ocorre quando o specialist graph retorna o token como parte do output.  
**Fix:**
```python
# service.py — adicionar sanitização antes de retornar resposta
response_text = re.sub(r'__ROUTE_TO_SPECIALIST__:[^\s]+', '', response_text)
response_text = re.sub(r'commentary<\|.*?\|>.*?(?=\w)', '', response_text, flags=re.DOTALL)
```
**Evidência:** Observado em runs de 27/05, 28/05 (múltiplos ciclos), 29/05.

---

### P0-3 · `_SLUG_ALIASES` incorretos em `common_module.py`
**Arquivo:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/common_module.py`  
**Impacto:** Mensagens de registro financeiro roteadas para `context-gatherer` em vez dos agentes corretos. Todos os TCs de escrita falham.  
**Fixes necessários:**
```python
# Corrigir os seguintes aliases (linha ~50):
"register_transaction": "financeiro",     # era "context-gatherer"
"data_entry":           "data-entry",     # era "context-gatherer" (typo _ vs -)
# Verificar também: "fornecedor", "supplier" → "compras"
```
**Evidência:** Runs de 29/05 19:57, 30/05 02:57, 02/06 06:57.

---

### P0-4 · `agente compras` mal configurado em `registry.py`
**Arquivo:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`  
**Problemas:**
- `prompt_name="agents/frontdesk"` no AgentTypeConfig de `compras` (deveria ser `agents/compras`)
- `_SLUG_ALIASES` mapeia `"fornecedor"` e `"supplier"` para `"context-gatherer"` em vez de `"compras"`
**Evidência:** Run 28/05 15:04.

---

### P0-5 · `loader.py` — `LoadedPrompt not subscriptable` (bug sistêmico)
**Arquivo:** `libs/blu_prompt_management/src/blu_prompt_management/loader.py`  
**Impacto:** Todos os prompts do Langfuse com `type=chat` falham ao carregar no container — agente roda com system prompt vazio. Afeta `agents/frontdesk`, `skill:financeiro:system`, `skill:end_of_day_digest:system`, e potencialmente todos os prompts.  
**Causa:** Falta guard `isinstance(compiled_text, list)` no loader — quando o Langfuse retorna estrutura `chat`, o código tenta subscriptá-la como string.  
**Fix:**
```python
# loader.py — adicionar guard antes de retornar texto compilado
if isinstance(compiled_text, list):
    compiled_text = "\n".join(m.get("content", "") for m in compiled_text if m.get("role") == "system")
```
**Evidência:** Runs de 29/05 02:01, 30/05 06:01, 02/06 04:01.

---

### P0-6 · `route_to_specialist` tool description com slugs inválidos
**Arquivo:** `services/agent_api` (tool description da ferramenta `route_to_specialist`)  
**Impacto:** Frontdesk passa slugs inválidos (`"estrategia"`, `"documentos"`) para o router — specialist graph não encontrado → crash.  
**Fix:** Atualizar description da tool para listar apenas os slugs válidos: `financeiro`, `crm`, `agenda`, `monday`, `compras`, `data-entry`, `strategy`, `platform`.  
**Evidência:** Run 02/06 00:42.

---

### P0-7 · `detect_synthesis_intent` / `detect_specialist_intent` interceptando indevidamente
**Arquivo:** `services/agent_api/src/agent_api/service.py`  
**Impacto:** Queries que deveriam ir ao frontdesk são capturadas pelo keyword router antes do LLM:
- "relatório automático" / "resumo + estoque" → roteado para `agenda` (errado)
- "digest do dia" / "fechamento do dia" → roteado para `strategy` (POWERFUL → 403)
- "projetos do Monday hoje" → roteado para `agenda` em vez de `monday`  
**Fix:**
- Adicionar padrão negativo em `detect_synthesis_intent` para queries com "digest/resumo do dia/encerramento"
- Revisar `_TAG_MAP`/`_DOMAIN_RULES` em `nodes.py` para evitar false positives
- Adicionar aliases em `_SLUG_ALIASES`: "relatório automático", "configurar rotina" → `"platform"`
**Evidência:** Runs 02/06 04:01, 02/06 08:58, 28/05 17:10.

---

### P0-8 · `GraphRecursionError` — recursion_limit alto + sem stop condition
**Arquivo:** `services/agent_api` — `graph.ainvoke()`  
**Impacto:** SQL com edge case (ex: "mês passado" em janeiro) falha, LangGraph retenta indefinidamente, atinge limite de 40 iterações → HTTP 500.  
**Fix:**
```python
# Baixar recursion_limit para 15 em graph.ainvoke para chat
await graph.ainvoke(state, config={"recursion_limit": 15})
```
E adicionar no prompt: *"Se `execute_sql` retornar erro: PARE. Não gere nova query. Reporte o erro ao usuário."*  
**Evidência:** Runs 27/05 16:43, 29/05 02:01.

---

### P0-9 · `google_calendar_write` não implementada
**Arquivo:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/google_module.py`  
**Impacto:** Agente `agenda` só consegue ler eventos. Qualquer TC de criação/atualização de evento falha — agente alucina "evento criado" sem tool call real.  
**Fix:** Implementar `google_calendar_write` usando Google Calendar API `events.insert`.  
**Evidência:** Run 28/05 19:01.

---

### P0-10 · `get_specialist_graph()` kwarg crash
**Arquivo:** `libs/blu_agent_framework`  
**Sintoma:** `UnifiedAgentFactory.get_specialist_graph() got an unexpected keyword argument`  
**Impacto:** Specialist graph não inicializa para certos agentes → HTTP 500 silencioso.  
**Evidência:** Run 28/05 19:49.

---

## ⚠️ P1 — Bugs Importantes

### P1-1 · Token Google Calendar nulo para cliente de teste
**Impacto:** Tool `query_calendar` falha para `cid.lucas@gmail.com` — `access_token=null, refresh_token=null` no Vault.  
**Fix:** Migrar token Fernet de `default@unknown.com` para Vault sob `cid.lucas@gmail.com` + refresh OAuth.  
**Evidência:** Runs 28/05 19:01, 29/05 (múltiplos).

---

### P1-2 · Token Monday ausente/inválido para cliente de teste
**Impacto:** Todas as chamadas `monday_list_boards` falham para o cliente `6446d4fa`.  
**Fix:** Verificar/renovar token Monday no Vault para este client_id.  
**Evidência:** Runs 28/05 17:10, 28/05 19:28.

---

### P1-3 · `execute_sql` description com nomes de tabela errados
**Arquivo:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/sql_module.py` ~L1059  
**Problema:** Description usa `fact_sales`, `dim_customer`, `dim_supplier`, `dim_product` (inglês) — tabelas não existem.  
**Tabelas reais:** `fato_transacoes`, `dim_clientes`, `dim_fornecedores`, `dim_inventory`, `dim_datas`  
**Fix:** Atualizar campo `description` da tool com nomes corretos.  
**Evidência:** Run 27/05 16:43.

---

### P1-4 · `agents/financeiro` prompt referencia tabelas inexistentes
**Prompt Langfuse:** `agents/financeiro`  
**Problema:** Usa `analytics_v2.fact_sales` + `dim_customer` — não existem. Deve usar `analytics_v2.fato_transacoes`, `dim_fornecedores`, JOIN com `dim_datas`.  
**Status:** Draft v2 criado (02/06 05:03). **Ação: promover para `production` no Langfuse UI.**  
**Evidência:** Runs 30/05 07:00, 02/06 05:03.

---

### P1-5 · Agente `financeiro` sem tool `register_transaction`
**Arquivo:** `libs/blu_agent_framework/src/blu_agent_framework/registry.py`  
**Problema:** `enabled_tools` do agente `financeiro` contém apenas `execute_sql` + `executar_rag_cliente`. A tool `register_transaction` não está declarada.  
**Fix:** Adicionar `register_transaction` ao `enabled_tools` do agente financeiro.  
**Evidência:** Run 28/05 19:49.

---

### P1-6 · `whatsapp_enviar_mensagem`/`lote` não habilitadas no agente CRM
**Arquivo:** `registry.py` — AgentTypeConfig do agente `crm`  
**Impacto:** TC de "mandar mensagem pro cliente" falha internamente.  
**Fix:** Verificar/adicionar `whatsapp_enviar_mensagem` e `whatsapp_enviar_mensagem_lote` ao `enabled_tools` do CRM.  
**Evidência:** Run 30/05 04:59.

---

### P1-7 · Prompts ausentes ou em draft no Langfuse

| Prompt | Status | Ação necessária |
|---|---|---|
| `skill:sql_analytics:system` | ❌ Ausente (404) | Criar + publicar `production` |
| `skill:end_of_day_digest:system` | ⚠️ Draft v1 criado | Promover → `production` |
| `skill:agenda:system` | ⚠️ Draft v3 criado | Promover → `production` |
| `skill:monday:system` | ⚠️ Draft v3 criado | Promover → `production` |
| `skill:crm:system` | ⚠️ Draft v3 criado | Promover → `production` |
| `skill:financeiro:system` | ⚠️ Draft v5/v7 criado | Promover → `production` |
| `agents/frontdesk` | ⚠️ Draft v21 criado | Promover → `production` |
| `agents/financeiro` | ⚠️ Draft v2 criado | Promover → `production` |

---

### P1-8 · `agents/frontdesk` como `type=chat` no Langfuse → causa LoadedPrompt bug
**Impacto:** O bug P0-5 (`LoadedPrompt not subscriptable`) é amplificado porque `agents/frontdesk` está salvo como `type=chat`.  
**Fix:** Recriar `agents/frontdesk` como `type=text` no Langfuse UI.  
**Evidência:** Run 02/06 06:57.

---

### P1-9 · `morning_plan` e `end_of_day_digest` não expostas via chat
**Contexto:** São *routine skills* (invocadas por `morning_sync`), não chat skills. Frontdesk não tem instrução para roteá-las via input direto do usuário.  
**Impacto:** "Faz meu planejamento do dia" / "Fecha o dia" → 0/5 por mismatch arquitetural.  
**Fix:** Decisão de design necessária: (A) expor via frontdesk com roteamento explícito, ou (B) documentar que só são ativadas por rotinas automáticas.  
**Evidência:** Runs 27/05 23:54, 28/05 01:59.

---

### P1-10 · Raw JSON vazando para o usuário (output de `execute_sql`)
**Impacto:** Usuário vê `{"success":true,"data":[{"data":"2024-05-01","receita_total":123456.78,...}]}` diretamente.  
**Fix (PROMPT_STATIC):** Adicionar em `<Tool Rules>` do prompt do agente SQL: *"Formate o resultado como tabela Markdown — NUNCA mostre JSON bruto ao usuário."*  
**Evidência:** Run 27/05 16:43.

---

### P1-11 · `frontdesk_visible=False` no `scheduler-agent`
**Impacto:** `scheduler-agent` é o único agente com ferramentas Monday (`monday_list_boards` etc.), mas está invisível para o frontdesk → impossível rotear para ele via chat.  
**Fix:** Alterar `frontdesk_visible=True` no AgentTypeConfig do `scheduler-agent` em `registry.py`, ou criar agente `monday` separado.  
**Evidência:** Run 28/05 16:32.

---

### P1-12 · `data_schema` EMPTY para clientes de teste
**Impacto:** Agente não tem knowledge de colunas (`dim_inventory`: `nome`, `quantidade_total_vendida`, `estoque_minimo`). Agrava bugs de PROMPT_STATIC — sem schema, não gera SQL correto.  
**Fix:** Verificar pipeline de context service para o client_id `6446d4fa` / Guillen.  
**Evidência:** Run 27/05 17:31.

---

### P1-13 · `weekly_summary` ausente em `financeiro.skill_slugs`
**Impacto:** Skill `weekly_summary` está orphã no Level 2 — não pode ser roteada para o agente financeiro.  
**Fix:** Adicionar `weekly_summary` aos `skill_slugs` do agente `financeiro` em `registry.py`.  
**Evidência:** Run 02/06 05:03.

---

### P1-14 · Resposta vazia no fallback de crash de specialist
**Impacto:** Quando specialist crasha após invocação, usuário recebe resposta completamente vazia (sem "Desculpe, ocorreu um erro"). Silent failure.  
**Fix:** Adicionar handler de fallback em `service.py` para retornar mensagem de erro amigável quando specialist retorna `None` ou string vazia.  
**Evidência:** Run 28/05 19:49.

---

### P1-15 · Alucinação em queries analíticas (dados fabricados)
**Causa provável:** `execute_sql` não foi chamada (PROMPT_STATIC — falta regra anti-alucinação) ou foi chamada mas retornou dados incorretos (CONTEXT_WRONG).  
**Diagnóstico bloqueado:** Campo `tool_calls` na resposta da API sempre retorna `[]` — impossível confirmar externamente se tool foi chamada.  
**Fix:** (1) Expor `tool_calls` na resposta da API para debugging. (2) Adicionar regra no prompt: *"NUNCA invente dados. Se `execute_sql` não retornar resultados, informe que não há dados disponíveis."*  
**Evidência:** Runs 27/05 16:43, múltiplos.

---

## 🟡 P2 — Melhorias

### P2-1 · `{{ available_agents }}` possivelmente não renderizado no frontdesk
O template Jinja do frontdesk pode não estar recebendo a lista de agentes no contexto de execução.  
**Fix:** Verificar renderização em `service.py` / `builder.py`.  
**Evidência:** Run 02/06 00:42.

---

### P2-2 · EXTRACT anti-pattern para "mês passado" em janeiro
Queries com `MONTH(date) = MONTH(NOW()) - 1` quebram em janeiro (retorna 0).  
**Fix (PROMPT_STATIC):** Adicionar regra de SQL seguro no prompt: usar `DATE_TRUNC('month', NOW() - INTERVAL '1 month')`.  
**Evidência:** Run 30/05 04:59.

---

### P2-3 · Elicitation em vez de defaults de inventário
Para queries de estoque crítico/baixo, agente pergunta ao usuário para definir threshold em vez de usar coluna `estoque_minimo`.  
**Fix (PROMPT_STATIC):** Adicionar defaults explícitos no prompt de `sql_analytics`: *"Para 'estoque baixo/crítico': use `quantidade_total_vendida < estoque_minimo` ou TOP 20 ordenado por quantidade ASC."*  
**Evidência:** Run 27/05 17:31.

---

### P2-4 · Race condition em `/v1/chat` retornando estado parcial
TC1 retornou `(Executing SQL request...)` como resposta final — streaming state vazando no endpoint síncrono.  
**Evidência:** Run 27/05 16:24.

---

### P2-5 · `customer_id` possivelmente não populado em `fato_transacoes` para Guillen
Impacta diagnóstico de queries CRM que deveriam filtrar por cliente.  
**Fix:** Verificar `SELECT COUNT(*) FROM analytics_v2.fato_transacoes WHERE client_id = '6446d4fa-...' AND customer_id IS NOT NULL`.  
**Evidência:** Run 29/05 02:01.

---

## 📋 Checklist de Execução

### Fase 1 — Infra (requer rebuild)
- [ ] **P0-1** Identificar modelo Ollama Cloud sem assinatura + atualizar `client.py` `_TIER_MAP`
- [ ] **P0-3** Corrigir `_SLUG_ALIASES` em `common_module.py`
- [ ] **P0-4** Corrigir AgentTypeConfig do `compras` em `registry.py`
- [ ] **P0-8** Baixar `recursion_limit` para 15 em `graph.ainvoke`
- [ ] **P1-5** Adicionar `register_transaction` ao `enabled_tools` do `financeiro`
- [ ] **P1-6** Adicionar `whatsapp_enviar_mensagem` ao `enabled_tools` do `crm`
- [ ] **P1-11** Corrigir `frontdesk_visible` do `scheduler-agent`
- [ ] **P1-13** Adicionar `weekly_summary` aos `skill_slugs` do `financeiro`
- [ ] **🔁 Rebuild:** `docker compose build --no-cache blu_agent_api && docker compose up -d blu_agent_api`

### Fase 2 — Code (sem rebuild)
- [ ] **P0-2** Sanitizar tokens internos em `service.py` antes de retornar resposta
- [ ] **P0-5** Fix `loader.py` — guard `isinstance(compiled_text, list)`
- [ ] **P0-6** Atualizar description da tool `route_to_specialist` com slugs válidos
- [ ] **P0-7** Revisar `detect_synthesis_intent` / `_TAG_MAP` / `_DOMAIN_RULES`
- [ ] **P0-10** Fix kwarg em `get_specialist_graph()`
- [ ] **P1-3** Atualizar `execute_sql` description com nomes de tabela corretos
- [ ] **P1-14** Adicionar fallback handler para specialist vazio em `service.py`
- [ ] **P1-15** Expor `tool_calls` na resposta da API
- [ ] **P2-4** Investigar race condition no endpoint síncrono

### Fase 3 — Dados / Credenciais
- [ ] **P1-1** Renovar token Google Calendar no Vault para `cid.lucas@gmail.com`
- [ ] **P1-2** Renovar token Monday no Vault para client `6446d4fa`
- [ ] **P1-12** Verificar `data_schema` pipeline para clientes de teste
- [ ] **P2-5** Verificar `customer_id` em `fato_transacoes` para Guillen

### Fase 4 — Langfuse (após Fase 1+2 validadas)
- [ ] **P1-7** Promover todos os drafts para `production`:
  - `agents/frontdesk` v21
  - `agents/financeiro` v2
  - `skill:financeiro:system` v5/v7
  - `skill:crm:system` v3
  - `skill:agenda:system` v3
  - `skill:monday:system` v3
  - `skill:end_of_day_digest:system` v1
  - Criar `skill:sql_analytics:system` v1
- [ ] **P1-8** Recriar `agents/frontdesk` como `type=text` no Langfuse UI
- [ ] **P1-10** Adicionar regra anti-JSON-bruto no prompt SQL
- [ ] **P2-2** Adicionar regra EXTRACT para "mês passado" nos prompts SQL
- [ ] **P2-3** Adicionar defaults de estoque no prompt `sql_analytics`

### Fase 5 — Design Decision
- [ ] **P1-9** Decidir se `morning_plan` / `end_of_day_digest` são expostas via chat ou apenas via rotinas automáticas

---

## 📊 Resumo de Impacto

| Categoria | Bugs | Skills afetadas |
|---|---|---|
| Infra (Ollama 403) | 1 P0 | `financeiro`, `crm`, `strategy`, `agenda`, `monday` — ~60% dos agentes |
| Routing (slugs/detect) | 3 P0 + 2 P1 | Todos os agentes write-ops |
| Token leak (interno) | 1 P0 | `frontdesk` + todos specialists |
| loader.py | 1 P0 | Todos os prompts `type=chat` |
| Tools faltando | 2 P1 | `financeiro`, `crm` |
| Prompts ausentes/draft | 1 P1 | 8 prompts pendentes de promoção |
| Dados/Credenciais | 3 P1 | Google Calendar, Monday, data_schema |

**Pass rate atual (02/06):** ~10–40% dependendo do skill testado  
**Pass rate esperado pós-fixes P0:** ~70–80%  
**Pass rate esperado pós-fixes P0+P1:** ~90%+
