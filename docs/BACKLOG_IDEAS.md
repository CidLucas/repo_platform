# Backlog de Ideias — Blu Platform

Arquivo de captura de ideias para exploração futura. Não são tarefas confirmadas — são direções que valem ser exploradas quando o momento for certo.

Atualizado continuamente durante o desenvolvimento.

---

## Tier Enforcement & Resource Assignment — PRIMEIRA PRIORIDADE FUTURA


## Agente RFQ — Simplificação radical

**Problema:** agente atual está desenhado de forma burocrática (geração de documento PDF/formal), inadequado para PMEs brasileiras.

**Visão correta:** fluxo simples em 3 passos:
1. Recebe uma lista de compras (itens + quantidades)
2. Compara com fornecedores cadastrados e cotas disponíveis
3. Retorna resultado em cards — cotações por fornecedor ou sugestões ranqueadas

**Princípios:**
- Sem geração de documento — se o usuário precisar de um documento formal, usa o agente de documentos
- Output em cards, não em PDF/texto longo
- Leve, rápido, conversacional

**Problema identificado durante testes de routing (Layer 1):**
A atribuição de tools aos agentes está errada. Hoje o tier do cliente filtra tools diretamente
(`TierValidator` em `factory.py`) — mas tools não são a unidade certa de controle.

**Modelo correto (a implementar):**

```
Tier do cliente
  → define quais Features estão habilitadas (ex: "sql_analytics", "crm_advanced", "fiscal")
    → cada Feature seleciona um conjunto de Resources (agents, skills, tools, data sources)
      → esses Resources são atribuídos dinamicamente ao agente no build-time
```

**O que mapear antes de implementar:**
1. Inventário de todos os agents + tools + skills existentes
2. Agrupamento em Features lógicas (ex: Feature "Compras" = ComprasMonitor + supplier-agent + tools de estoque)
3. Mapa Tier → Features habilitadas (FREE / BASIC / SME / PREMIUM / ENTERPRISE)
4. Como o AgentBuilder recebe a lista de resources no build-time (hoje recebe `enabled_tools: list[str]` hard-coded)

**Arquivos centrais para o redesign:**
- `libs/blu_tool_registry/src/blu_tool_registry/tier_validator.py` — lógica atual de tier filtering
- `libs/blu_tool_registry/src/blu_tool_registry/tool_metadata.py` — TierLevel enum
- `services/agent_api/src/agent_api/core/factory.py` — onde tools são filtradas por tier no build
- `libs/blu_agent_framework/src/blu_agent_framework/registry.py` — AgentTypeRegistry com enabled_tools por agente

---

## Arquitetura & Infra

### Shared Memory com pgvector
**Status:** não implementado — `dimension_state` é o substituto atual (1 row por dimensão, upsert simples)

**Ideia original:**
Substituir ou complementar o `dimension_state` com uma tabela `shared_business_memory` que suporte múltiplos blocos por dimensão, com TTL por tipo de bloco e busca semântica via embedding.

Schema proposto:
```sql
CREATE TABLE shared_business_memory (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id       uuid NOT NULL REFERENCES clients(client_id),
  dimension       text NOT NULL,   -- 'compras' | 'financeiro' | 'clientes' | 'agenda' | 'biblioteca' | 'cross'
  block_type      text NOT NULL,   -- 'state' | 'alert' | 'insight' | 'goal' | 'decision'
  summary         text NOT NULL,   -- texto compacto legível por LLM (max ~300 tokens)
  structured_data jsonb,
  source_routine  text,
  valid_until     timestamptz,     -- state: 24h | insights: 7d
  created_at      timestamptz DEFAULT now(),
  embedding       vector(1536)
);
```

Tipos de bloco: `state` (snapshot atual) | `alert` (atenção ativa) | `insight` (padrão observado) | `goal` (meta com progresso) | `decision` (pendente de aprovação).

Função `get_business_memory_snapshot(client_id, max_tokens=1500)`: retorna os blocos mais recentes ordenados por prioridade (alerts → goals → state → insights), respeitando TTL, com teto de ~1500 tokens (~6 blocos de 250 tokens).

**Quando explorar:** quando o `dimension_state` atual começar a ser insuficiente para casos de uso com múltiplos alertas simultâneos ou quando o Synthesis Agent precisar de contexto vetorial.

---

## i18n — App Multi-idioma

**Ideia:** tornar o Blu disponível em múltiplos idiomas (PT-BR, EN, ES como prioridade).

**Abordagem técnica proposta:**
- Todo o código, prompts internos, nomes de tools, descriptions e registry ficam em inglês (já é o padrão definido)
- O conteúdo dos prompts (o que o LLM lê) é internacionalizado
- Adicionar um nó dedicado no LangGraph de resposta: `response_language_node` que detecta o idioma do usuário (via `user_language` no perfil ou detecção automática da mensagem) e formata/traduz a resposta final antes de entregar
- Alternativa mais simples: injetar `user_language` como variável nos prompts e instruir o agente a responder naquele idioma (já fazemos `Responda sempre no idioma do usuário` nos prompts novos)

**Quando explorar:** após estabilização dos agentes principais (Fase 2-3 completas).

---

## Integrações Externas

### NotebookLM — Bases de Conhecimento por Tarefa
**Ideia:** integrar o Hermes/Blu com o NotebookLM para gerar bases de conhecimento especializadas por domínio (ex: base financeira para o FinanceiroMonitor, base de clientes para o CRM Specialist).

Fluxo proposto:
1. Alimentar o NotebookLM com documentos, relatórios e histórico de cada dimensão do negócio do cliente
2. Usar o podcast/summary gerado como contexto enriquecido para os agentes
3. Ou usar o NotebookLM como ferramenta de RAG alternativa ao pgvector para casos de conhecimento mais narrativo

**Quando explorar:** próximo horizonte — útil para onboarding de novos clientes onde a base de documentos é rica.

### GitHub Cloud — Fluxo de Desenvolvimento Automatizado
**Ideia:** integrar o Hermes com o GitHub Cloud (Actions, Issues, PRs) para criar um fluxo de desenvolvimento automatizado:
- Criar issues a partir de conversas de backlog
- Abrir PRs com código gerado via Codex/Claude Code
- Receber notificações de CI/CD e agir sobre falhas
- Vincular tarefas do Linear/Asana a commits e PRs automaticamente

**Quando explorar:** próximo horizonte — desbloquearia um loop completo de desenvolvimento assistido por IA.

---

## Padrões & Convenções

### Prompt Standards (definido em 21/05/2026)
- Nomes de prompts, descriptions, tool names e campos de registry: **inglês**
- Conteúdo dos prompts (o que o LLM lê): **português** (por enquanto — mudará com i18n)
- Prompts existentes NÃO serão migrados em massa — revisão gradual
- Todos os agentes novos seguem o padrão com seções: `<Instructions>`, `<Tool Rules>`, `<Constraints>`, `<Output Format>`

---

*Última atualização: 21/05/2026*

---
## MVP Roadmap — registrado 2026-05-21

### Fase atual (em andamento)
- Estabilizar infra dos agentes: eliminar 500s, routing correto, model names, CancelledError

### Próximas fases (em ordem)

**1. Limpeza de dados**
- Criar função no BD: ao deletar cliente, deletar todos os dados associados (cascade completo)
- Deletar clientes existentes na base e validar que nada fica órfão

**2. Onboarding — ciclo completo (2 clientes)**
- Cliente A: fonte BigQuery
- Cliente B: fonte Google Sheets
- Validar todo o fluxo de entrada de dados para cada fonte

**3. Validação de métricas**
- Pegar todas as métricas elencadas no frontend
- Validar geração correta de cada uma

**4. Integrações**
- Monday
- Slack
- Google Drive, Gmail, Google Agenda
- Open Finance

**5. Mesa de trabalho da Agenda**
- Hoje hardcoded/figurativa
- Tornar dinâmica e funcional

### Pós-MVP (quando produto estiver pronto para receber clientes)
- Otimizar fluxos dos agentes
- Otimizar retrieval (chunking, metadata, estrutura da base)
- Refinamento contínuo de prompts e routing

---
## Pós-MVP — Routing de Agentes (prioridade alta no ciclo de otimização)

**Problema atual:** routing baseado em exact match de nuvem de palavras (_PLATFORM_KEYWORDS, _SPECIALIST_ROUTING, _SYNTHESIS_KEYWORDS) — frágil, não generaliza.

**O que precisa:**
- Estratégia mais sofisticada: embedding similarity, classificador leve, ou LLM call dedicado ao routing
- Exemplos que falham hoje: "Ativa o monitor de estoque baixo", "Agenda uma reunião para quinta", "Quais clientes têm maior risco de churn?" — todos caem no frontdesk por não terem exatamente a keyword certa
- Considerar: classificador treinado com exemplos por agente, ou zero-shot com modelo FAST dedicado ao routing intent
- Timing: pós-onboarding, no ciclo de otimização dos agentes
