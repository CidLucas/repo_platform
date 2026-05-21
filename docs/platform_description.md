# Blu (repo_platform) — Descrição da Plataforma

> Última atualização: 2026-05-21

## Visão geral

Blu é um **escritório virtual com IA** para donos de PMEs brasileiras. Não é um dashboard, não é um chatbot — é um time de agentes que trabalha para o dono de negócio. A interface é o espaço onde owner e agentes se encontram.

O monorepo `repo_platform` contém:

| Camada | Localização | Descrição |
|---|---|---|
| Frontend (app principal) | `apps/blu_v3/` | React 18 + TypeScript + Vite + Tailwind v3. App em salas. Porta: 5175 |
| Frontend (landing) | `apps/landing/` | Landing page + onboarding wizard |
| Agent API | `services/agent_api/` | FastAPI — orquestra agentes, executa rotinas, gerencia sessões |
| Tool Pool API | `services/tool_pool_api/` | FastAPI — ferramentas (SQL, RAG, Google, OCR, RFQ) expostas via MCP |
| blu_agent_framework | `libs/blu_agent_framework/` | Framework LangGraph: grafos, skills, agentes, routines engine |
| blu_context_service | `libs/blu_context_service/` | Contexto do cliente: Redis cache + snapshot de memória de negócio |
| blu_prompt_management | `libs/blu_prompt_management/` | Carregamento de prompts via Langfuse (com fallback builtin) |
| blu_models | `libs/blu_models/` | Pydantic models compartilhados |
| blu_supabase_client | `libs/blu_supabase_client/` | Client Supabase + CRUD compartilhado |
| DB | Supabase (hosted) | PostgreSQL + pgvector + RLS + pg_cron |

## Arquitetura escolhida: Event-Driven + Shared Memory + Swarm (Arquitetura C)

Agentes especialistas são stateless. Toda memória de negócio é persistida em tabelas. O User-Facing Agent (UFA) recebe um snapshot compacto de contexto a cada conversa — não carrega todas as skills.

```
Usuário ──→ User-Facing Agent ──→ Specialist Pool (slug-based)
                    ↑                      ↓
             Shared Memory ←── Room Monitors (Routines Engine)
             (dimension_state, client_goals,
              client_insights, approval_requests)
```

## Convenções do repo

- **Idioma:** código e docs em inglês; drafts e voz em português
- **Prompts:** sempre `type=skill` — nunca `type=llm` direto. Templates fallback em `blu_prompt_management/templates.py`
- **Rotinas:** steps do tipo `skill`, `function`, `artifact`, ou `approval`. Nunca `llm`
- **Sem dados hardcodados no frontend:** sempre skeleton loaders enquanto dados não chegam
- **Migrations:** `supabase/migrations/YYYYMMDDNNNNNN_nome.sql` — aplicadas via psql direto

## Login de desenvolvimento

| Campo | Valor |
|---|---|
| App | http://localhost:5175 |
| Email | lucascid@poli.ufrj.br |
| client_id | (ver Supabase auth) |
| external_user_id | 4f3a5908-6d5d-46fb-93b4-4938ef754314 |
| tier | free |

## Estado atual (2026-05-21)

- 21 rotinas no catálogo, todas com `llm_count = 0` (steps migrados para `type=skill`)
- Shared Memory Phase 0 deployada: `dimension_state` + `client_goals` + `get_business_memory_snapshot()`
- TypeScript: 0 erros introduzidos pelo time (3 pré-existentes em ComprasRoom + OnboardingApp)
- DB: 50 tabelas no schema `public`, pgvector disponível, RLS ativa em todas as tabelas de dados de cliente
