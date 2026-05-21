# Blu Platform — Agent System Map

> Última atualização: 2026-05-21
> Arquitetura: Event-Driven + Shared Memory + Swarm (Arquitetura C)

---

## 1. Visão Geral da Arquitetura

O sistema tem **4 camadas progressivas**. Cada camada delega para baixo; nenhuma pula uma camada.

```
┌────────────────────────────────────────────────────────────────┐
│  L4  Orchestrator (User-Facing Agent)                          │
│       recebe input do usuário → classifica → roteia para L3   │
├────────────────────────────────────────────────────────────────┤
│  L3  Domain Specialists (Agent Types)                          │
│       compras · financeiro · clientes · agenda · documentos   │
├────────────────────────────────────────────────────────────────┤
│  L2  Skills                                                    │
│       unidades de trabalho com prompt + tools — stateless     │
├────────────────────────────────────────────────────────────────┤
│  L1  Tools (Tool Pool API)                                     │
│       execute_sql · executar_rag · google_calendar · OCR …    │
└────────────────────────────────────────────────────────────────┘
```

**Shared Memory** (cross-cutting): agentes não conversam diretamente. Escrevem e leem da memória compartilhada via tabelas no Supabase.

---

## 2. Salas e Agentes por Dimensão

| Sala (Frontend) | Dimensão | Agent Slug(s) | Room Monitor (Rotinas) |
|---|---|---|---|
| Home | — | `frontdesk` | morning_plan, end_of_day_digest |
| Clientes | `clientes` | `clientes` | collection_messages, followup_draft, reactivation_proposal, satisfaction_survey |
| Compras | `compras` | `compras` | (ComprasMonitor — Fase 1) |
| Financeiro | `financeiro` | `financeiro` | reconciliation_report, weekly_summary |
| Agenda | `agenda` | `agenda` | meeting_brief |
| Estratégia | `estrategia` | `estrategia` | hidden_patterns, competitor_analysis |
| Documentos + Biblioteca | `documentos` | `documentos` | HITL documental (aprovação → RAG) |

---

## 3. Agentes registrados (`agent_catalog`)

Os agentes são definidos em `libs/blu_agent_framework/src/blu_agent_framework/` e persistidos em `agent_catalog` no banco.

Campos relevantes por agente:
- `slug` — identificador usado em todo o sistema
- `prompt_name` — nome do prompt no Langfuse (fallback em `templates.py`)
- `required_context` — seções do BluClientContext que o agente precisa
- `required_files` — document types obrigatórios (referência a `knowledge_document_types`)
- `workflow_graph` — grafo LangGraph (json)
- `tier_required` — `BASIC` | `PRO` | `ENTERPRISE`

---

## 4. Skills registradas (`SKILL_REGISTRY`)

Skills são registradas em `libs/blu_agent_framework/src/blu_agent_framework/skills.py` via `@register`.

Cada skill tem: `slug`, `description`, `prompt_name`, `required_tools`, `max_turns`, `on_max_turns`, `tags`.

**Skills L3 (LLM) ativas — vinculadas a rotinas:**

| Slug | Dimensão | Rotina |
|---|---|---|
| `morning_plan` | home | Plano matinal |
| `end_of_day_digest` | home | Digest fim de dia |
| `weekly_summary` | financeiro | Resumo semanal |
| `reconciliation_report` | financeiro | Conciliação |
| `collection_messages` | clientes | Mensagens de cobrança |
| `followup_draft` | clientes | Rascunho de follow-up |
| `reactivation_proposal` | clientes | Proposta de reativação |
| `satisfaction_survey` | clientes | Pesquisa de satisfação |
| `meeting_brief` | agenda | Brief de reunião |
| `hidden_patterns` | estratégia | Padrões ocultos |
| `competitor_analysis` | estratégia | Análise competitiva |

**Skills utilitárias (L1/L2):**
`analyze_csv`, `extract_document`, `create_routine_nl`, `data_entry_nl`, `compose_morning_brief`, `explain_alert`, `request_clarification`, `classify_intent`, `extract_entities`

---

## 5. Shared Memory — Tabelas de Estado

A memória compartilhada é composta de tabelas existentes + 2 novas (Fase 0):

| Tabela | Papel | Quem escreve | Quem lê |
|---|---|---|---|
| `dimension_state` | Estado compacto por sala (~250 tokens de prose) | Room Monitors (rotinas) | `get_business_memory_snapshot()` → UFA |
| `client_goals` | Metas ativas com progresso | Usuário via chat / agentes | Snapshot → qualquer agente |
| `client_insights` | Observações geradas por IA | Rotinas de análise | Snapshot + UI |
| `approval_requests` | Decisões pendentes (HITL) | Qualquer agente | UFA + UI aprovações |
| `notifications` | Alertas urgentes | Rotinas / agentes | Snapshot + UI notificações |

**Função de snapshot:** `ContextService.get_business_memory_snapshot(client_id, max_chars=6000)`
Agrega as 5 fontes acima em ordem de prioridade, retorna bloco `## Estado do Negócio` para injeção em prompts.

---

## 6. Routines Engine

Motor de execução de rotinas em `services/agent_api/src/agent_api/core/routines.py`.

**Step types suportados:**
- `function` — função Python determinística (`routine_functions.py`)
- `skill` — executa skill do SKILL_REGISTRY com LLM
- `artifact` — entrega artefato para o usuário (`routine_artifacts.py`)
- `approval` — cria `approval_request` e pausa execução aguardando HITL

**Disparo:** pg_cron roda `dispatch_routine_executions()` a cada minuto → HTTP POST para `agent_api`.

**Tabelas:**
- `cross_agent_routines` — catálogo global de rotinas (21 rotinas, todas `llm_count=0`)
- `client_routines` — inscrições de clientes em rotinas do catálogo
- `client_routine_executions` — histórico de execuções

---

## 7. Tool Pool API — Ferramentas disponíveis

Servidas via MCP por `services/tool_pool_api/`. Cada tool_module registra as tools no servidor.

| Tool | Módulo | Descrição |
|---|---|---|
| `execute_sql` | sql_module | Query em analytics_v2 ou tabelas do cliente |
| `executar_rag_cliente` | rag_module | Busca vetorial na coleção do cliente (pgvector) |
| `google_calendar_*` | google_module | Leitura e escrita de eventos Google Calendar |
| `extract_document_with_ocr` | ocr_module | Extração de texto/tabelas de PDFs e imagens |
| `rfq_*` | rfq_module | Geração de RFQ e propostas comerciais |
| `config_helper_*` | config_helper_module | Leitura de configurações e context do cliente |

---

## 8. Infraestrutura de Documentos / RAG

Pipeline: Upload → `uploaded_files_metadata` → OCR/extração → `client_knowledge_documents` → aprovação HITL → embedding pgvector → RAG disponível para todo o sistema.

Tipos de documentos definidos em `knowledge_document_types`. Requisitos por agente em `knowledge_agent_requirements` (com `coverage_threshold`).

**Aprovação documental:** `action_type = 'document_approval'` em `approval_requests`. Documento aprovado entra no RAG; rejeitado fica em `status = 'missing'`.

---

## 9. Roadmap de Fases

| Fase | Descrição | Status |
|---|---|---|
| 0 | Shared Memory: `dimension_state` + `client_goals` + `get_business_memory_snapshot()` | ✅ Concluída |
| 1 | ComprasMonitor: rotinas de compras + DataAnalyst Specialist | 🔲 Próxima |
| 2 | FinanceiroMonitor + FiscalAgent | 🔲 |
| 3 | ClientesMonitor + CRMSpecialist | 🔲 |
| 4 | Synthesis Agent + AgendaMonitor + integrações Monday/Excel | 🔲 |
