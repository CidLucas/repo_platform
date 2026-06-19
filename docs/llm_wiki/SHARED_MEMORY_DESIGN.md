# Shared Memory Design — Blu Platform

> Última atualização: 2026-06-19 | Fase 1, T1.2
> Documento de referência para o sistema de Shared Business Memory.

---

## 1. Visão Geral

A **Shared Business Memory** é o barramento de conhecimento entre agentes no Blu.
Em vez de agentes conversarem diretamente, eles leem e escrevem fatos atômicos
na tabela `shared_business_memory`, cada um identificado pela quádrupla
`(client_id, entity_type, entity_name, key)`.

### Filosofia

- **Stateless agents**: agentes não mantêm estado interno; toda memória de
  negócio vive no Supabase.
- **Atomic facts**: cada linha é um fato independente — decisão, descoberta,
  metadado de execução.
- **Observability**: todas as ações dos agentes são rastreáveis via shared memory.

---

## 2. Arquitetura em Camadas

```
┌──────────────────────────────────────────────────────────┐
│  Agentes (L3-L4)                                         │
│  frontdesk · crm · estrategia · supplier · scheduler ... │
└────────────┬──────────────────────────────┬──────────────┘
             │                              │
    ┌────────▼────────┐            ┌────────▼────────┐
    │  Pre-flight     │            │  Post-flight    │
    │  (T1.1 / #17)   │            │  (T1.2 / #18)   │
    │  lê contexto    │            │  persiste        │
    │  da shared      │            │  resultados      │
    │  memory         │            │  e metadados     │
    └────────┬────────┘            └────────┬────────┘
             │                              │
    ┌────────▼──────────────────────────────▼────────┐
    │           Shared Business Memory                │
    │  ┌──────────────────────────────────────┐      │
    │  │  shared_business_memory              │      │
    │  │  - entity_type: agent_result,        │      │
    │  │    agent_metadata, skill, client,     │      │
    │  │    contact, supplier, user            │      │
    │  │  - key: finding:*, decision:*,        │      │
    │  │    summary:*, tool_usage:*            │      │
    │  └──────────────────────────────────────┘      │
    │  ┌──────────────────────────────────────┐      │
    │  │  shared_memory_links                 │      │
    │  │  - source: agent_pending, manual,    │      │
    │  │    specialist, memory_agent, system   │      │
    │  └──────────────────────────────────────┘      │
    └────────────────────────────────────────────────┘
```

---

## 3. Entity Types

### 3.1 Tipos de negócio (Fase 0)

| Entity Type | Descrição | Exemplo de entity_name |
|-------------|-----------|----------------------|
| `skill` | Skill/tool que produziu o fato | `rag`, `sql_agent` |
| `client` | Cliente/empresa | `acme_corp` |
| `contact` | Pessoa de contato | `joao_silva` |
| `supplier` | Fornecedor | `distribuidora_x` |
| `user` | Usuário do sistema | `admin` |

### 3.2 Tipos de agente (Fase 1 — T1.2)

| Entity Type | Descrição | Exemplo de entity_name |
|-------------|-----------|----------------------|
| `agent_result` | Resultado da execução de um agente | `crm:a1b2c3d4` |
| `agent_metadata` | Metadados de execução do agente | `crm` |

### 3.3 Links pendentes (Fase 1 — T1.2)

`agent_link_pending` não é um entity_type na `shared_business_memory` — é
representado como `source='agent_pending'` na tabela `shared_memory_links`.
Links criados automaticamente pelos agentes ficam pendentes de validação
pela rotina T4.4.

---

## 4. T1.2 — Post-flight Memory

### 4.1 Propósito

Após cada execução de agente (frontdesk ou specialist), o **post-flight hook**
persiste automaticamente:

1. **agent_result**: o que o agente produziu (resumo, tools usadas)
2. **agent_metadata**: metadados da execução (session_id, elapsed, agent_slug)
3. **agent_link_pending**: links semânticos sugeridos pelo agente (opcional)

Tudo em **fire-and-forget** — nunca bloqueia a resposta ao usuário.

### 4.2 Naming Convention (DD-03)

As chaves (`key`) seguem prefixos semânticos para facilitar descoberta e
filtragem:

| Prefixo | Significado | Exemplo |
|---------|-------------|---------|
| `decision:` | Decisão tomada pelo agente | `decision:priorizar_fornecedor_x` |
| `finding:` | Descoberta/insight extraído | `finding:cliente_atrasado_3_meses` |
| `summary:` | Resumo da execução | `summary:execution` |
| `tool_usage:` | Ferramenta utilizada (apenas nome) | `tool_usage:execute_sql` |

### 4.3 Noise Suppression (DD-04)

Apenas o **último estado significativo** é persistido. Como o upsert usa a
constraint `UNIQUE (client_id, entity_type, entity_name, key)`, escritas
subsequentes com a mesma chave sobrescrevem a anterior.

- Estados intermediários do LangGraph NÃO são persistidos
- Apenas o último `AIMessage.content` é capturado
- Tool outputs são descartados; apenas nomes das tools vão para `tool_usage:*`

### 4.4 Fluxo Post-flight

```
┌─────────────────────────────────────────────────────────┐
│  ChatService.process_message()                          │
│                                                         │
│  1. graph.ainvoke() → final_state                       │
│  2. Extrai último AIMessage.content                     │
│  3. Extrai tool_calls do AIMessage (apenas nomes)       │
│  4. _fire_and_forget(                                   │
│       _shared_memory_post_flight_logic(                 │
│         client_id, agent_slug, session_id,              │
│         agent_result, agent_metadata                    │
│       )                                                 │
│     )                                                   │
│  5. return ChatResult (NÃO espera o post-flight)        │
└─────────────────────────────────────────────────────────┘
```

### 4.5 Hook Points

| Método | Local do hook | Agente afetado |
|--------|---------------|----------------|
| `process_message()` | Antes do `return ChatResult` | frontdesk + specialist |
| `process_message_stream()` | Após `yield done`, antes de retornar | frontdesk + specialist (stream) |

`AgentService.stream_agent_response()` **não** tem hook post-flight no escopo
T1.2 — fica para iteração futura.

---

## 5. Módulo memory_post_flight.py

### 5.1 Localização

`services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_post_flight.py`

### 5.2 Design Decisions

| ID | Decisão | Status |
|----|---------|--------|
| DD-01 | Módulo separado no tool_pool | ✅ |
| DD-02 | 3 entity_types: agent_result, agent_metadata, agent_link_pending | ✅ |
| DD-03 | Naming convention com prefixos semânticos | ✅ |
| DD-04 | Noise suppression via upsert (último estado) | ✅ |
| DD-05 | Fire-and-forget async no service.py | ✅ |
| DD-06 | Internal tool (não exposta via MCP) | ✅ |

### 5.3 API

```python
async def _shared_memory_post_flight_logic(
    client_id: str,
    agent_slug: str,
    session_id: str,
    agent_result: dict | None = None,
    agent_metadata: dict | None = None,
    suggested_links: list[dict] | None = None,
) -> dict:
```

Retorna `{"agent_result_entries": N, "agent_metadata_entries": N, "links_created": N}`.

---

## 6. Migration SQL

### 6.1 T1.2a: Agent Entity Types

Arquivo: `supabase/migrations/proposed/20260619000004_add_agent_entity_types.sql`

Adiciona `agent_result` e `agent_metadata` ao CHECK constraint da
`shared_business_memory`, e `agent_pending` ao CHECK constraint de `source`
na `shared_memory_links`.

---

## 7. Tabelas

### 7.1 shared_business_memory

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid PK | |
| `client_id` | uuid FK → clientes_blu | |
| `entity_type` | text | skill, client, contact, supplier, user, agent_result, agent_metadata |
| `entity_name` | text | Nome normalizado (lowercase) |
| `key` | text | Chave do fato (1-256 chars) |
| `category` | text | knowledge, rag, documents, memory-agent, context, decision, preference |
| `value` | jsonb | Conteúdo do fato |
| `source` | text | manual, memory_agent, specialist, migration, system |
| `confidence` | numeric | 0.0–1.0 |
| `metadata` | jsonb | Metadados de proveniência |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Unique constraint**: `(client_id, entity_type, entity_name, key)`

### 7.2 shared_memory_links

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid PK | |
| `client_id` | uuid FK → clientes_blu | |
| `source_entity_type` | text | |
| `source_entity_name` | text | |
| `target_entity_type` | text | |
| `target_entity_name` | text | |
| `link_type` | text | Relacionamento (2-128 chars) |
| `source` | text | manual, memory_agent, specialist, migration, system, agent_pending |
| `confidence` | numeric | 0.0–1.0 |
| `metadata` | jsonb | |
| `created_at` | timestamptz | |

**Unique constraint**: `(client_id, source_entity_type, source_entity_name, link_type, target_entity_type, target_entity_name)`

---

## 8. Próximos Passos

- T4.4: Rotina de validação de `agent_pending` links
- T1.1: Pre-flight memory (leitura de contexto antes da execução)
- TTL/Retention: Política de expurgo de entradas antigas (Fase 3)
