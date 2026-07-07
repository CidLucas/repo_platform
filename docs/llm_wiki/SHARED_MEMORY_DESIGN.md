---
title: Shared Memory Design — Fase 1 (T1.3)
created: 2026-06-24
updated: 2026-07-07
type: summary
tags: [arquitetura, agente, tool, persistencia, design-decisao]
sources: [system_reference/AGENT_SYSTEM.md, system_reference/TOOL_INVENTORY.md]
confidence: high
status: active
page_sha256: 9311caa1
hermes_sha256: eddcb9d9c9132509ca2656998f9e3a58452a46a4f26a27a39a34938ebb94c7b0
check_notes: Tick 694 — re-audit (rot=61, main 7/10). AGENT_SYSTEM 766e3dc4 ✅ zero drift, TOOL_INVENTORY 170bc9bb ✅ zero drift, HERMES eddcb9d9 ✅. Full file SHA 8934b954 (drift from 3ce037f4 — benign, mtime unchanged since tick 684, body semanticamente intacto). 0 wikilinks, 3 markdown links: AGENT_SYSTEM ✅ TOOL_INVENTORY ✅ roadmap/blu-intelligent-memory.md ❌ (still broken — file not found). 988 linhas (>>200, split flag mantida). Tags 5/5 na taxonomia ✅. 0 contradições.
---

# Shared Memory Design — Fase 1 (T1.3)

Documento de design completo do subsistema de memória compartilhada da plataforma BLU.
Cobre a visão geral, schemas, taxonomy de entidades, catálogo de ferramentas L1,
design do handoff hook (T1.3) e decisões de arquitetura.

> **Última atualização:** Junho 2026
> **Issue:** #19 — Fase 1, T1.3 (Hook de handoff entre agentes na shared memory)
> **Documentos relacionados:**
> - [Roadmap Blu Intelligent Memory](../roadmap/blu-intelligent-memory.md)
> - [Sistema de Agentes](../system_reference/AGENT_SYSTEM.md)
> - [Tool Inventory](../system_reference/TOOL_INVENTORY.md)

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Schema: shared_business_memory](#2-schema-shared_business_memory)
3. [Schema: shared_memory_links](#3-schema-shared_memory_links)
4. [Taxonomy de entity_type](#4-taxonomy-de-entity_type)
5. [Catálogo de Ferramentas L1](#5-catálogo-de-ferramentas-l1)
6. [T1.3 — Handoff Hook](#6-t13--handoff-hook)
7. [Entity Linking](#7-entity-linking)
8. [TTL e Ciclo de Vida](#8-ttl-e-ciclo-de-vida)
9. [Design Decisions e ADRs](#9-design-decisions-e-adrs)

---

## 1. Visão Geral

### 1.1 Princípios

A shared business memory é o mecanismo central de comunicação entre agentes
no Blu. Três princípios fundamentais guiam seu design:

1. **Agentes comunicam via shared memory, não por conversa direta.**
   Nenhum agente chama outro diretamente. Toda informação que precisa ser
   passada entre agentes é escrita na shared memory e lida pelo agente destino.

2. **Single Writer.** Cada fonte de escrita (`source`) só pode escrever nos
   tipos de entidade (`entity_type`) para os quais está autorizada. Isso
   previne que um agente corrompa dados de outro domínio.

3. **Stateless Agents, Stateful Memory.** Agentes são stateless — toda
   memória de negócio fica no Supabase, na shared business memory. Um mesmo
   agente pode ser reiniciado e recuperar todo o contexto da shared memory.

### 1.2 Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Agent A   │ ──→ │  Tool Pool   │ ──→ │  shared_business │
│ (specialist)│     │ (MCP Server) │     │  _memory (SBM)   │
└─────────────┘     └──────────────┘     └──────────────────┘
       │                                       │
       │  handoff_hook.py                      │ shared_memory_links
       │  (pós-route_to_specialist)            │ (relacionamentos)
       ▼                                       ▼
┌─────────────┐     ┌──────────────┐
│   Agent B   │ ←── │shared_memory │
│ (specialist)│     │ _context     │
└─────────────┘     └──────────────┘
```

O handoff hook (T1.3) é a peça central desta arquitetura: após o roteamento
via `route_to_specialist`, o hook escreve learning notes na shared memory, e
o módulo `shared_memory_context.py` carrega o contexto relevante no agente
destino.

### 1.3 Entidades e Fatos

A shared memory organiza informações em uma estrutura de três níveis:

```
client_id ──┬── entity_type ──┬── entity_name ──┬── key ── value (JSONB)
             │                 │                 │
             │                 │                 └── "contato_principal" → {...}
             │                 │
             │                 ├── "empresa_acme"
             │                 │     └── key ── value
             │                 │
             │                 └── "fornecedor_x"
             │                       └── key ── value
             │
             ├── "contact"
             ├── "supplier"
             ├── ...
```

Cada entrada é um **fato**: uma afirmação sobre uma entidade em um dado
momento. Fatos têm `source` (quem escreveu) e `confidence` (confiança).

### 1.4 Fontes de Escrita (Source)

| Source         | Quem usa                              | Nível de confiança típico |
|----------------|---------------------------------------|---------------------------|
| `system`       | Rotinas internas, cron jobs           | 1.0                       |
| `memory_agent` | DomainProjectionMemoryAgent (Fase 2)  | 0.7–1.0                   |
| `specialist`   | Agentes especialistas (L3)            | 0.7–0.95                  |
| `manual`       | Intervenção humana / API externa      | 1.0                       |
| `migration`    | Scripts de migração e seed            | 1.0                       |
| `curated`      | Confirmação humana (via morning plan) | 1.0                       |

---

## 2. Schema: shared_business_memory

### 2.1 Tabela Principal

```sql
CREATE TABLE shared_business_memory (
    id              BIGSERIAL PRIMARY KEY,
    client_id       UUID NOT NULL REFERENCES clientes_blu(id),
    entity_type     TEXT NOT NULL,
    entity_name     TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           JSONB NOT NULL DEFAULT '{}',
    category        TEXT,
    source          TEXT NOT NULL DEFAULT 'manual',
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    metadata        JSONB DEFAULT '{}',
    version         INTEGER NOT NULL DEFAULT 1,
    embedding       VECTOR(1536),              -- Fase 3 (Cohere multilingual)
    curated         BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at      TIMESTAMPTZ,               -- Soft-delete TTL
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unicidade: um fato por chave composta
    CONSTRAINT uq_shared_business_memory
        UNIQUE (client_id, entity_type, entity_name, key)
);

-- Índices
CREATE INDEX idx_sbm_client_lookup
    ON shared_business_memory (client_id, entity_type, entity_name);
CREATE INDEX idx_sbm_expires_at
    ON shared_business_memory (expires_at)
    WHERE expires_at IS NOT NULL AND curated = FALSE;
```

### 2.2 Colunas em Detalhe

| Coluna        | Tipo        | Obrigatório | Descrição                                            |
|--------------|-------------|:-----------:|------------------------------------------------------|
| `id`         | BIGINT (PK) |     sim     | ID auto-incrementável                                |
| `client_id`  | UUID (FK)   |     sim     | Cliente dono do fato (FK clientes_blu)               |
| `entity_type`| TEXT        |     sim     | Tipo da entidade (ver taxonomy na seção 4)           |
| `entity_name`| TEXT        |     sim     | Nome canônico da entidade (lowercase, sem acentos)   |
| `key`        | TEXT        |     sim     | Nome do fato (e.g. "contato_principal")              |
| `value`      | JSONB       |     sim     | Valor do fato (pode ser dict, list, string, number)  |
| `category`   | TEXT        |     não     | Categoria semântica para filtragem                   |
| `source`     | TEXT        |     não     | Fonte de escrita (default "manual")                  |
| `confidence` | FLOAT       |     não     | Confiança 0.0–1.0 (default 1.0)                     |
| `metadata`   | JSONB       |     não     | Metadados extras (frontmatter de snapshots, etc.)   |
| `version`    | INTEGER     |     sim     | Número da versão (default 1)                         |
| `embedding`  | VECTOR(1536)|     não     | Embedding Cohere para busca semântica (Fase 3)       |
| `curated`    | BOOLEAN     |     não     | Confirmado por humano? (default FALSE)               |
| `expires_at` | TIMESTAMPTZ |     não     | Data de expiração (NULL = não expira)                |
| `created_at` | TIMESTAMPTZ |     sim     | Timestamp de criação                                 |
| `updated_at` | TIMESTAMPTZ |     sim     | Timestamp da última atualização                      |

### 2.3 Tabela de Versões (Auditoria)

```sql
CREATE TABLE shared_business_memory_versions (
    id              BIGSERIAL PRIMARY KEY,
    memory_id       BIGINT NOT NULL REFERENCES shared_business_memory(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_name     TEXT NOT NULL,
    key             TEXT NOT NULL,
    value           JSONB NOT NULL,
    source          TEXT NOT NULL,
    confidence      DOUBLE PRECISION NOT NULL,
    metadata        JSONB DEFAULT '{}',
    version         INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL,
    archived_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sbmv_memory_id ON shared_business_memory_versions (memory_id);
```

### 2.4 Categorias Válidas

```python
_VALID_CATEGORIES = frozenset({
    "knowledge",       # Conhecimento geral sobre o domínio
    "rag",             # Dados vindos de RAG/documentos
    "documents",       # Referências a documentos
    "memory-agent",    # Dados do Memory Agent (aprendizado automático)
    "context",         # Contexto de negócio
    "decision",        # Decisões tomadas
    "preference",      # Preferências explícitas
})
```

---

## 3. Schema: shared_memory_links

### 3.1 Tabela de Links

```sql
CREATE TABLE shared_memory_links (
    id                    BIGSERIAL PRIMARY KEY,
    client_id             UUID NOT NULL REFERENCES clientes_blu(id),
    source_entity_type    TEXT NOT NULL,
    source_entity_name    TEXT NOT NULL,
    target_entity_type    TEXT NOT NULL,
    target_entity_name    TEXT NOT NULL,
    link_type             TEXT NOT NULL,
    source                TEXT NOT NULL DEFAULT 'manual',
    confidence            DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    metadata              JSONB DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_shared_memory_link
        UNIQUE (client_id, source_entity_type, source_entity_name,
                target_entity_type, target_entity_name, link_type)
);

CREATE INDEX idx_sml_source
    ON shared_memory_links (client_id, source_entity_type, source_entity_name);
CREATE INDEX idx_sml_target
    ON shared_memory_links (client_id, target_entity_type, target_entity_name);
```

### 3.2 Colunas em Detalhe

| Coluna               | Tipo        | Descrição                                      |
|---------------------|-------------|-------------------------------------------------|
| `id`                | BIGINT (PK) | ID auto-incrementável                           |
| `client_id`         | UUID (FK)   | Cliente dono do link                            |
| `source_entity_type`| TEXT        | Tipo da entidade origem                         |
| `source_entity_name`| TEXT        | Nome da entidade origem                         |
| `target_entity_type`| TEXT        | Tipo da entidade destino                        |
| `target_entity_name`| TEXT        | Nome da entidade destino                        |
| `link_type`         | TEXT        | Tipo de relacionamento (free-form)              |
| `source`            | TEXT        | Proveniência do link                            |
| `confidence`        | FLOAT       | Confiança 0.0–1.0                               |
| `metadata`          | JSONB       | Metadados extras                                |
| `created_at`        | TIMESTAMPTZ | Timestamp de criação                            |

### 3.3 Convenções de link_type

`link_type` é um campo livre, mas as seguintes convenções são recomendadas:

| link_type        | Significado                                      | Exemplo                                         |
|-----------------|--------------------------------------------------|-------------------------------------------------|
| `works_for`     | Contato trabalha para empresa                    | `contact:joao → works_for → supplier:distribuidora_x` |
| `applies_to`    | Fato de skill se aplica a contato/cliente        | `skill:cobranca → applies_to → client:empresa_acme` |
| `prefers`       | Preferência sobre canal/horário                  | `contact:joao → prefers → skill:comunicacao:canal_whatsapp` |
| `reports_to`    | Relação hierárquica                              | `contact:joao → reports_to → contact:maria`     |
| `depends_on`    | Dependência entre entidades                      | `snapshot:compras:semanal → depends_on → routine:compras_monitor` |
| `related_to`    | Relação genérica (fallback)                      | `contact:pedro → related_to → client:empresa_beta` |
| `derived_from`  | Um fato deriva de outro                          | `agent_result:domain_projection → derived_from → ...` |
| `confirmed_by`  | Fato confirmado por interação humana             | `skill:cobranca:tom_amigavel → confirmed_by → user:admin` |

---

## 4. Taxonomy de entity_type

### 4.1 Tipos de Entidade

```python
_VALID_ENTITY_TYPES = frozenset({
    "skill",           # Fatos derivados de skills/ferramentas
    "client",          # Dados de clientes (CRM)
    "contact",         # Contatos individuais (pessoas)
    "supplier",        # Fornecedores
    "user",            # Usuários da plataforma
    "snapshot",        # Snapshots por dimensão (T2.2)
    "routine",         # Rotinas automatizadas (Routine Engine)
    "agent_result",    # Resultados de execução de agentes
    "agent_metadata",  # Metadados operacionais de agentes
})
```

### 4.2 Naming Conventions

| entity_type  | entity_name (convenção)         | key (convenção)           | Exemplo                                     |
|-------------|--------------------------------|---------------------------|---------------------------------------------|
| `skill`     | `{skill_name}` (snake_case)    | `{fato_snake_case}`       | `skill:cobranca / tom_amigavel`            |
| `client`    | `{nome_empresa}` (snake_case)  | `{fato_snake_case}`       | `client:empresa_acme / contato_principal`   |
| `contact`   | `{nome_pessoa}` (snake_case)   | `{fato_snake_case}`       | `contact:joao_silva / preferencia_horario`  |
| `supplier`  | `{nome_fornecedor}`            | `{fato_snake_case}`       | `supplier:distribuidora_x / prazo_pagamento`|
| `user`      | `{user_id or email_norm}`      | `{fato_snake_case}`       | `user:admin@blu / preferencia_idioma`       |
| `snapshot`  | `{dimensao}:{periodo}`         | ISO timestamp              | `snapshot:financeiro:semanal / 2025-06-19T...` |
| `routine`   | `{routine_name}` (snake_case)  | `{fato_snake_case}`        | `routine:prune_shared_memory / ultima_execucao` |
| `agent_result` | `{agent_name}`              | `{descritivo_snake_case}`  | `agent_result:domain_projection / projecao_...` |
| `agent_metadata` | `{agent_name}`           | `{descritivo_snake_case}`  | `agent_metadata:frontdesk / turn_count`      |

**Regras:**
- `entity_name` e `key` são sempre **lowercase**, sem acentos, underscores.
- `entity_name` deve ser semanticamente único **dentro do** `entity_type` para um `client_id`.
- `key` + `entity_name` + `entity_type` + `client_id` formam a chave única.

### 4.3 Qual entity_type usar?

| Situação                                                  | entity_type    |
|-----------------------------------------------------------|---------------|
| Preferência sobre tom de voz na skill de cobrança         | `skill`       |
| Dado cadastral de um cliente (CNPJ, endereço)             | `client`      |
| Preferência de contato de uma pessoa (João prefere WhatsApp) | `contact`   |
| Prazo de pagamento de um fornecedor                       | `supplier`    |
| Preferência de idioma de um usuário                       | `user`        |
| Snapshot financeiro semanal                                | `snapshot`    |
| Última execução de rotina de limpeza                      | `routine`     |
| Resultado de handoff (agente A → agente B)                | `agent_result`|
| Metadados de execução de agente (turn count, latência)    | `agent_metadata` |

---

## 5. Catálogo de Ferramentas L1

### 5.1 Tools de Leitura

#### shared_memory_list

Lista todas as entidades com entradas na shared memory para o client_id.

```
Args:
    entity_type (str, opcional): Filtrar por tipo de entidade.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com total_entities, by_type, entities.
```

**Uso típico:** Explorar quais entidades existem antes de ler fatos específicos.

---

#### shared_memory_read

Lê um fato específico pela chave composta.

```
Args:
    entity_type (str): Tipo da entidade.
    entity_name (str): Nome da entidade (case-insensitive).
    key (str): Nome do fato.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com o registro completo (id, value, source, confidence, version, timestamps).
```

**Uso típico:** Agente destino lê fatos relevantes após receber um handoff.

---

#### shared_memory_meta_read

Lê uma entrada de metadados da `shared_business_memory_meta`.

```
Args:
    entity_type (str): Tipo da entidade.
    entity_name (str): Nome da entidade.
    key (str): Nome do fato.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com o registro completo da tabela meta.
```

---

#### shared_memory_meta_list

Lista entradas de metadados, opcionalmente filtradas por entity_type.

```
Args:
    entity_type (str, opcional): Filtrar por tipo.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com total e resultados.
```

---

### 5.2 Tools de Escrita

#### shared_memory_write

Escreve um novo fato na shared memory. Comportamento padrão: INSERT estrito.
Usar `supersede=True` para UPSERT.

```
Args:
    entity_type (str): Tipo da entidade.
    entity_name (str): Nome da entidade.
    key (str): Nome do fato.
    value (dict): Valor do fato.
    category (str, opcional): Categoria semântica.
    agent_id (str, opcional): UUID do agente (armazenado em metadata).
    ttl (int, opcional): TTL em segundos.
    priority (int, opcional): Prioridade 0-100.
    supersede (bool): Se True, upsert. Default False.
    source (str): Fonte de escrita.
    confidence (float): Confiança 0.0–1.0.
    ttl_tier (str, opcional): Tier de retenção.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com o registro escrito.
```

**Faz verificação de permissão de escrita** (`_check_write_permission`).

---

#### shared_memory_upsert

**Tool legada** (T0.5). Upsert com versionamento completo (arquiva versão anterior).

```
Args:
    entity_type (str), entity_name (str), key (str), body (dict),
    frontmatter (dict, opcional), source (str, default "manual"),
    confidence (float, default 1.0), ttl_tier (str, opcional),
    client_id (str, auto-injetado).

Returns:
    dict com o registro upsertado (incluindo version).
```

**Não faz verificação de permissão de escrita.** Mantida por compatibilidade.

---

#### shared_memory_meta_upsert

Insere ou atualiza uma entrada na `shared_business_memory_meta` (T4.2d).

```
Args:
    entity_type (str), entity_name (str), key (str), body (dict),
    source (str, default "manual"), confidence (float, default 1.0),
    client_id (str, auto-injetado).

Returns:
    dict com o registro escrito.
```

---

### 5.3 Tools de Busca

#### shared_memory_search

Busca semântica vetorial na shared memory via embedding Cohere.

```
Args:
    query (str): Texto de busca em linguagem natural.
    entity_type (str, opcional): Filtrar por tipo.
    category (str, opcional): Filtrar por categoria.
    match_count (int, default 10): Máximo de resultados.
    match_threshold (float, default 0.3): Similaridade mínima.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com query, total_results, results (ordenados por similarity).
```

**Mecanismo:** Gera embedding da query via Cohere `embed-multilingual-light-v3.0`,
chama RPC `search_shared_memory` no Supabase (similaridade de cosseno em pgvector).

**Fallback textual (planejado):** Para cenários sem Cohere, uma busca via
ILIKE + pg_trigram deve ser implementada (ver DQ3).

---

### 5.4 Tools de Links

#### shared_memory_link

Cria um link semântico entre duas entidades.

```
Args:
    source_entity_type (str), source_entity_name (str),
    target_entity_type (str), target_entity_name (str),
    link_type (str): Rótulo do relacionamento.
    source (str, default "manual"), confidence (float, default 1.0),
    metadata (str, opcional): JSON com metadados extras.
    client_id (str, auto-injetado).

Returns:
    dict com id, source, target, link_type, created_at.
```

**Uso típico:** Após escrever um fato, criar links para entidades relacionadas.

---

#### shared_memory_unlink

Remove um link pelo ID.

```
Args:
    id (int): ID do link a remover.
    client_id (str, auto-injetado).

Returns:
    dict com resultado da operação.
```

---

#### shared_memory_get_links

Busca links por entidade e/ou tipo.

```
Args:
    entity_type (str): Tipo da entidade para filtrar.
    entity_name (str): Nome da entidade para filtrar.
    link_type (str, opcional): Filtrar por tipo de link.
    direction (str, default "any"): "source" | "target" | "any".
    client_id (str, auto-injetado).

Returns:
    dict com total e results.
```

---

### 5.5 Tools de Ciclo de Vida

#### shared_memory_flush

Soft-delete (marca `flushed_at` em metadata). Entradas flushed não aparecem
em leituras mas permanecem no banco para auditoria.

```
Args:
    entity_type (str, opcional), entity_name (str, opcional),
    key (str, opcional), client_id (str, auto-injetado).

Returns:
    dict com flushed_count, total_scanned, flushed_at.
```

---

#### shared_memory_export

Exporta todos os fatos da shared memory para um client_id.

```
Args:
    entity_type (str, opcional), entity_name (str, opcional),
    client_id (str, auto-injetado).

Returns:
    dict com total_records e records.
```

---

### 5.6 Tools Planejadas (T1.3)

#### confirm_memory_item (T1.3.5)

Marca uma memória como `curated=true` por `memory_id`.

```
Args:
    memory_id (int): ID da entrada na shared_business_memory.
    client_id (str, auto-injetado): UUID do cliente.

Returns:
    dict com status e o registro atualizado.

Validação:
    - memory_id deve pertencer ao client_id.
    - Se a entrada não existir ou já estiver curated, retorna erro claro.
```

**Motivação:** Permite que agentes (ou o morning plan) confirmem explicitamente
fatos aprendidos. Uma vez `curated=true`, a entrada não expira mais
(`expires_at` zera).

---

### 5.7 Resumo das Tools

| Tool                    | Tier  | Categoria      | Status         |
|-------------------------|-------|----------------|----------------|
| shared_memory_list      | L1    | Leitura        | Implementado   |
| shared_memory_read      | L1    | Leitura        | Implementado   |
| shared_memory_meta_read | L1    | Leitura        | Implementado   |
| shared_memory_meta_list | L1    | Leitura        | Implementado   |
| shared_memory_write     | L1    | Escrita        | Implementado   |
| shared_memory_upsert    | L1    | Escrita (legado) | Implementado |
| shared_memory_meta_upsert | L1  | Escrita        | Implementado   |
| shared_memory_search    | L1    | Busca          | Implementado   |
| shared_memory_link      | L1    | Links          | Implementado   |
| shared_memory_unlink    | L1    | Links          | Implementado   |
| shared_memory_get_links | L1    | Links          | Implementado   |
| shared_memory_flush     | L1    | Ciclo de Vida  | Implementado   |
| shared_memory_export    | L1    | Ciclo de Vida  | Implementado   |
| **confirm_memory_item** | **L1**| **Escrita**    | **A implementar (T1.3.5)** |

---

## 6. T1.3 — Handoff Hook

### 6.1 Conceito

O handoff hook é a camada de integração que conecta o mecanismo de roteamento
de agentes (`route_to_specialist`) à shared memory. Sempre que o frontdesk
roteia uma tarefa de um agente para outro via `route_to_specialist`, o hook:

1. Extrai **learning notes** do estado do agente origem (se houver)
2. Escreve esses aprendizados na shared memory (`shared_memory_write`)
3. Carrega o contexto relevante da shared memory no agente destino
   (`shared_memory_read`)

### 6.2 Arquitetura

```
route_to_specialist(LANGGRAPH NODE)
        │
        ▼
┌───────────────────────────────┐
│   handoff_hook.py             │
│                               │
│   1. Verifica has_learning    │
│   2. Extrai learning_notes    │
│   3. Chama shared_memory_write│
│      (source="specialist",    │
│       confidence=0.8)         │
│   4. Registra agent_result    │
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│   shared_memory_context.py    │
│                               │
│   1. Lê shared_memory_read    │
│      para entidades relevantes│
│   2. Monta dict de contexto   │
│   3. Injeta no prompt/estado  │
│      do agente destino        │
└───────────────────────────────┘
        │
        ▼
   Agente destino
   (recebe contexto da shared memory)
```

### 6.3 Componentes

#### 6.3.1 `handoff_hook.py` — `libs/blu_agent_framework/src/blu_agent_framework/handoff/`

```python
async def run_handoff_hook(
    agent_state: AgentState,
    tool_pool_client: MCPClient,
) -> None:
    """Executa o hook de handoff após route_to_specialist.

    1. Se agent_state.has_learning for True, extrai learning_notes.
    2. Para cada note, chama shared_memory_write com:
       - entity_type: inferido do contexto (skill, contact, ou client)
       - entity_name: extraído do note
       - key: slug do aprendizado
       - value: conteúdo estruturado
       - source: "specialist"
       - confidence: 0.8 (inferido) ou 1.0 (se explícito no note)
    3. Registra agent_result para auditoria.
    4. Timeout de 2s — graceful degradation se timeout.
    """
```

**Parâmetros do hook:**

| Parâmetro     | Tipo         | Descrição                                           |
|---------------|--------------|-----------------------------------------------------|
| agent_state   | AgentState   | Estado do LangGraph (contém has_learning, learning_notes) |
| tool_pool_client | MCPClient | Cliente MCP para chamar shared_memory_write         |

**Decisão DQ1:** Sinalizado (não automático). O hook só escreve quando
`has_learning=True` e `learning_notes` não vazio. A extração automática
será feita pelo Memory Agent (Fase 2).

#### 6.3.2 `shared_memory_context.py` — `libs/blu_agent_framework/src/blu_agent_framework/handoff/`

```python
async def load_shared_memory_context(
    agent_type: str,
    entity_names: list[str],
    tool_pool_client: MCPClient,
) -> dict:
    """Carrega contexto da shared memory para o agente destino.

    Para cada entity_name em entity_names, chama shared_memory_read
    para todos os keys disponíveis.

    Args:
        agent_type: Tipo do agente destino (e.g. "financeiro", "compras").
        entity_names: Lista de entity_names para carregar contexto.
        tool_pool_client: Cliente MCP.

    Returns:
        dict com {entity_name: {key: value, ...}} para o agente usar.
    """
```

**Decisão DQ2:** Inline no mesmo pacote. Context Service 2.0 completo
será um serviço separado em fase futura.

#### 6.3.3 `__init__.py` — `libs/blu_agent_framework/src/blu_agent_framework/handoff/`

```python
from .handoff_hook import run_handoff_hook
from .shared_memory_context import load_shared_memory_context

__all__ = ["run_handoff_hook", "load_shared_memory_context"]
```

### 6.4 Fluxo Completo de Handoff

```ascii
Usuário: "analisa financeiro do fornecedor X"
        │
        ▼
┌──────────────────┐
│   Frontdesk      │  Classifica: "financeiro + compras"
│   (L4)           │  Roteia para specialist via route_to_specialist
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────────┐
│   route_to_specialist node       │  (LangGraph)
│                                  │
│   1. Salva estado atual          │
│   2. Chama handoff_hook.run()    │
│      ├─ has_learning?            │
│      │  ├─ Sim → shared_memory_write (learning notes)
│      │  └─ Não  → skip
│      └─ shared_memory_write      │
│         (agent_result: handoff)  │
│                                  │
│   3. Chama shared_memory_context │
│      ├─ shared_memory_read       │
│      │  (entity_type="supplier", │
│      │   entity_name="fornecedor_x") │
│      └─ Retorna contexto         │
│                                  │
│   4. Passa controle ao           │
│      specialist destino          │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│   Specialist X   │  Recebe contexto da shared memory
│   (L3)           │  Trabalha com dados atuais
└──────────────────┘
```

### 6.5 Controle de Handoff (R2)

Para evitar ciclos infinitos de handoff:

1. O hook só dispara em `route_to_specialist`, não em writes diretos na
   shared memory.
2. O estado do LangGraph inclui flag `skip_handoff_hook: bool` para casos
   onde o hook não deve rodar.
3. Timeout de 2s no hook. Se exceder, graceful degradation — o handoff
   prossegue sem escrita de learning notes.

### 6.6 Handoff e Permissões de Escrita

O hook escreve com `source="specialist"`. Pela matriz de permissões (seção 9
do write model), `specialist` pode escrever em:
- `skill`, `client`, `contact`, `supplier`, `user`
- `snapshot`, `agent_result`, `agent_metadata`
- **Não pode** escrever em `routine`

---

## 7. Entity Linking

### 7.1 O Conceito

Entity Linking é o processo de criar links semânticos entre entidades na
shared memory automaticamente, sempre que um fato é escrito. Por exemplo:

> Ao escrever `contact:joao_silva / trabalha_para` com valor
> `{"empresa": "Distribuidora X"}`, um link é automaticamente criado:
> `contact:joao_silva → works_for → supplier:distribuidora_x`

### 7.2 Mecanismo de Auto-Linking

A partir da Fase 3 (Issue #28), o auto-linking é implementado como um fluxo
automático disparado após cada escrita bem-sucedida na shared memory.

**Parâmetro `auto_link`:** A tool `shared_memory_write` aceita o parâmetro
`auto_link: bool = True`. Quando `auto_link=True` (padrão), o fluxo de
auto-linking é disparado automaticamente após o write. Quando
`auto_link=False`, a criação automática de links é desativada, e o write
prossegue normalmente sem quebrar — a única diferença é que a chamada a
`_auto_create_links` é omitida.

**Fluxo de funções (ordem canônica):**

1. `_auto_create_links` — entry point do auto-linking; verifica `auto_link`;
   serializa o `value`, atualiza `last_auto_link_at` (TIMESTAMPTZ, nullable)
   e `auto_link_count` na tabela `shared_business_memory`
2. `_extract_entity_references` — varre o `value` serializado em busca de
   referências a entidades conhecidas (entity_type + entity_name)
3. `_shared_memory_link_logic` — persiste cada link semântico encontrado
   via INSERT na tabela `shared_memory_links`

**Convenção de source e confidence:** Todos os links criados automaticamente
por este fluxo são inseridos com `source="system"` e `confidence=1.0`,
refletindo que são gerados deterministicamente pelo próprio sistema (não por
um agente ou humano).

**Fase 2:** Entity Linking completo será integrado ao Memory Agent, que fará
análise semântica de toda a conversa para detectar relações entre entidades.

### 7.3 Convenções para Links Automáticos

| Padrão no value                       | Link gerado                                |
|---------------------------------------|--------------------------------------------|
| `{"empresa": "distribuidora_x"}`      | `contact → works_for → supplier`           |
| `{"cliente": "empresa_acme"}`         | `contact → works_for → client`             |
| `{"skill": "cobranca"}`               | `user/specialist → applies_to → skill`     |
| `{"preferencia_canal": "whatsapp"}`   | `contact/→ prefers → skill:canal`          |

### 7.4 Prevenção de Duplicatas

A constraint `uq_shared_memory_link` previne links duplicados. Se o mesmo
link já existe, o auto-linking é ignorado (idempotente).

### 7.5 Tracking Columns (shared_business_memory)

Para rastrear a atividade de auto-linking, duas colunas foram adicionadas à
tabela `shared_business_memory` (migration Issue #28, behavior B1):

- `last_auto_link_at  TIMESTAMPTZ` — nullable. Timestamp da última execução
  de auto-linking (`NULL` até a primeira execução; permanece `NULL` quando
  `auto_link=False` é usado consistentemente).
- `auto_link_count  INTEGER  DEFAULT  0` — contador de execuções de
  auto-linking. Incrementado a cada execução bem-sucedida de
  `_auto_create_links`, independentemente do número de links gerados.

---

## 8. TTL e Ciclo de Vida

### 8.1 TTL Tiers

```python
_TTL_TIER_INTERVALS = {
    "curated":         None,   # Nunca expira
    "migration":       90,     # 90 dias
    "specialist":      30,     # 30 dias
    "memory_agent_hi": 14,     # 14 dias (alta confiança)
    "memory_agent_lo": 7,      # 7 dias (baixa confiança)
}
```

Default por `source`:

| source         | ttl_tier inferido    |
|----------------|----------------------|
| `curated`      | `curated` (nunca expira) |
| `migration`    | `migration` (90d)    |
| `specialist`   | `specialist` (30d)   |
| `memory_agent` | `memory_agent_lo` (7d) |

### 8.2 Ciclo de Vida

```ascii
Fato escrito (source=specialist, ttl_tier=specialist)
        │
        ├─ curated=false, expires_at = now + 30d
        │
        ├─ [Morning Plan] Usuário confirma → curated=true, expires_at=NULL
        │
        ├─ [Prune Job] 03:00 UTC → Se curated=false AND expires_at < now
        │   → soft_delete (flushed_at em metadata)
        │
        └─ [Archival] 90 dias após soft_delete → hard_delete
```

---

## 9. Design Decisions e ADRs

### 9.1 Decisões do Plan (DD1-DD4)

| ID   | Decisão | Rationale |
|------|---------|-----------|
| DD1  | **Handoff hook síncrono** (não fire-and-forget) | Agente destino precisa das memórias mais recentes. Fire-and-forget poderia entregar estado desatualizado. |
| DD2  | **shared_memory_write usa upsert** (ON CONFLICT DO UPDATE) | UNIQUE constraint em `(client_id, entity_type, entity_name, key)` é o ID natural. Evita duplicatas e permite atualização in-place. |
| DD3  | **Context Service leve inline** (nenhum serviço externo) | Context Service 2.0 do roadmap ainda não existe. Hook inline resolve o caso imediato sem nova infra. |
| DD4  | **source='specialist', confidence=0.8 (inferido) ou 1.0 (explícito)** | Dados extraídos da conversa pelo hook são de confiança média. Distingue de `manual` (humano) e `memory_agent` (futuro). |

### 9.2 Respostas a Design Questions (DQ1-DQ3)

| ID   | Questão | Resposta |
|------|---------|----------|
| DQ1  | Handoff hook extrai aprendizado automaticamente ou só quando sinalizado? | **Sinalizado** — Memory Agent (Fase 2) fará extração automática. Hook só escreve quando specialist sinaliza (`has_learning=True`). |
| DQ2  | Context Service: módulo separado ou inline no handoff_hook.py? | **Inline** — Context Service 2.0 completo será serviço separado em fase futura. |
| DQ3  | shared_memory_search: pgvector ou ILIKE/trigram? | **ILIKE + trigram** — pgvector requer extensão habilitada no Supabase e modelo de embedding definido. A busca vetorial (já implementada via Cohere) atende cenários semânticos. Uma busca textual via ILIKE deve ser adicionada como fallback. |

### 9.3 ADRs do Sistema (D1-D9 existentes + novas)

**ADRs existentes (herdadas de AGENT_SYSTEM.md):**

| ID  | Decisão |
|-----|---------|
| D1  | `execute_sql` absorveu `executar_sql_agent` (modo direct/agent) |
| D3  | Somente `data-entry` pode escrever transações via `ledger` skill |
| D5  | `parse_business_reply` absorveu `parse_supplier_reply` |
| D8  | 13 tools de fornecedores consolidadas em `compras_ops` |

**ADRs específicas da shared memory:**

| ID   | Decisão |
|------|---------|
| ADR-SM-01 | `entity_name` e `key` normalizados para lowercase + trimmed antes de qualquer operação |
| ADR-SM-02 | `source` inválido normalizado para `"manual"` (fallback seguro, mais restritivo) |
| ADR-SM-03 | Links usam chave composta `(client_id, source, target, link_type)` para unicidade |
| ADR-SM-04 | `shared_memory_upsert` (legado) mantida por compatibilidade, mas `shared_memory_write` é a tool canônica |
| ADR-SM-05 | Flush é soft-delete (marca `flushed_at`), não hard-delete. Hard-delete só após 90 dias |
| ADR-SM-06 | Entity types não são extensíveis por runtime — adicionar novo tipo requer deploy |
| ADR-SM-07 | `category` é opcional e não validada contra regras de escrita (apenas contra enum) |
| ADR-SM-08 | Handoff hook tem timeout de 2s. Se exceder, graceful degradation (handoff prossegue sem escrita) |

---

### 9.4 Riscos e Mitigações

| ID  | Risco | Mitigação |
|-----|-------|-----------|
| R1  | **Latência no handoff com hook síncrono** | Timeout 2s no hook. Graceful degradation se timeout. |
| R2  | **Ciclo infinito de handoff** | Hook só dispara em `route_to_specialist`, não em writes diretos. Flag `skip_handoff_hook` no estado. |
| R3  | **shared_memory_write sem permissão real** (migration proposta, não aplicada) | Tools usam `service_role` (bypass RLS). Migration precisa ser aplicada antes ou em paralelo. |
| R4  | **Dependência de Fase 0 migrations aplicadas** | Falha clara `relation not found` se tabela não existe. Coordenar aplicação com operações. |
| R5  | **Cohere embedding service indisponível** | shared_memory_search falha com `ToolError` claro. ILIKE/trigram como fallback textual (a implementar). |

---

## Apêndice A: Referência de Código

| Componente                    | Caminho |
|------------------------------|---------|
| Módulo principal de tools    | `services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py` |
| Handoff hook (a implementar) | `libs/blu_agent_framework/src/blu_agent_framework/handoff/handoff_hook.py` |
| Context loader (a implementar)| `libs/blu_agent_framework/src/blu_agent_framework/handoff/shared_memory_context.py` |
| Handoff init (a implementar) | `libs/blu_agent_framework/src/blu_agent_framework/handoff/__init__.py` |
| Schema de contexto           | `libs/blu_context_service/src/blu_context_service/context_schemas.py` |

## Apêndice B: Histórico de Revisões

| Data       | Versão | Autor          | Mudanças |
|------------|--------|----------------|----------|
| 2026-06    | 1.0    | factory-coder  | Documento inicial da Fase 1 (T1.3): visão geral, schemas, taxonomy, catálogo de tools, handoff hook design, entity linking, ADRs. Inclui conteúdo existente de T2.2 (snapshots) e T5.2 (permissões). |
