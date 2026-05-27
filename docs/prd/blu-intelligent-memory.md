# PRD: Blu Intelligent Memory — Contexto Vivo e Aprendizado Contínuo

**Status:** Rascunho
**Autor:** Lucas Cruz
**Data:** 2025-05-26
**Versão:** 0.2
**Changelog:** Arquitetura revisada — LightRAG como motor de conhecimento documental, shared_business_memory como memória estruturada híbrida, Memory Agent em runtime, ciclo de enriquecimento periódico.

---

## Problema / Oportunidade

O Blu hoje sabe _quem_ é o cliente (nome, tier, CNPJ), mas não sabe _como_ ele opera. Cada conversa começa do zero: o agente não lembra que a Maria prefere receber cobranças com tom amigável, que o fornecedor principal é o João da Distribuidora X, que a empresa fecha às sextas às 17h.

Isso cria três problemas concretos:

1. **Respostas genéricas** — o agente responde como se fosse o primeiro dia, mesmo após meses de uso
2. **Retrabalho do usuário** — o dono da PME precisa re-explicar contexto a cada interação
3. **Agentes desconectados** — o CRM specialist não sabe o que o financeiro specialist aprendeu semana passada

O resultado: o Blu funciona como uma ferramenta, não como um sócio que aprende.

---

## Usuário Alvo

Dono de PME brasileira com 3–50 funcionários, usando o Blu há pelo menos 30 dias. Tem dados conectados (pelo menos uma fonte), faz perguntas recorrentes, e está começando a confiar no agente para tarefas operacionais.

---

## Metas

- [ ] Após 30 dias de uso, o agente demonstra ao menos 3 preferências aprendidas do cliente sem que ele precise repetir
- [ ] Taxa de reexplicação de contexto cai para menos de 10% das interações (vs. ~60% hoje)
- [ ] Cada specialist recebe apenas as seções de contexto relevantes ao seu domínio (zero ruído de prompt)
- [ ] O cliente consegue ver e corrigir o que o Blu aprendeu sobre ele (transparência + controle)

---

## Non-Goals (fora do escopo)

- Não vamos construir LightRAG do zero — usar integração com a biblioteca existente (HKUDS/LightRAG)
- Não vamos fazer análise de sentimento ou emoção do usuário
- Não vamos substituir o onboarding estruturado — este PRD é sobre aprendizado contínuo pós-onboarding
- Não vamos expor o grafo de conhecimento via UI nesta fase (só via agente)
- Não vamos mexer nos prompts dos specialists agora — o foco é a infraestrutura de memória

---

## Background e Contexto

### O que já existe

**Context Service** (`blu_context_service`): serviço que carrega e cacheia (Redis, TTL 5min) o contexto do cliente para injeção nos prompts. É um dicionário dinâmico — qualquer atualização na fonte é refletida na próxima carga. Tem 6 seções JSONB no Supabase (`clientes_blu`):

- `company_profile` — identidade básica
- `brand_voice` — tom de comunicação
- `team_structure` — equipe e contatos
- `policies` — regras e limites
- `data_schema` — tabelas conectadas (enriquecido dinamicamente por `sql_table_config`)
- `available_tools` — tools habilitadas e permissões

**Domain Projection** (`get_domain_projection`): filtra quais seções cada specialist recebe com base no domínio (ex: `analytics` → só `data_schema + available_tools + company_profile`).

**Context Gatherer** (L3 specialist): agente que registra transações, mapeia dados, cria rotinas. Já produz informação estruturada — mas ela não fica salva como memória aprendida.

**Routine Engine**: executa rotinas em steps (`function` | `skill` | `artifact`). Tem semáforo por cliente, circuit breaker, timeout 120s. Base ideal para rodar ciclos de consolidação.

### O que falta

As 6 seções são **configuradas no onboarding e raramente atualizadas**. Não há mecanismo para o Blu aprender com as interações e enriquecer esse contexto automaticamente. Não há memória de preferências por skill, por contato ou por usuário final. E não há base de conhecimento documental para consulta semântica.

---

## Solução Proposta

### Visão Geral — 3 Camadas de Memória

```
┌──────────────────────────────────────────────────────────────────┐
│                     CONTEXT SERVICE                              │
│        Dicionário dinâmico · Redis cache · domain projection     │
│  company_profile · brand_voice · team_structure                  │
│  policies · data_schema · available_tools                        │
│  → injetado deterministicamente em todos os specialists          │
└─────────────────────────┬────────────────────────────────────────┘
                          │ carrega dinamicamente
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                  SHARED BUSINESS MEMORY                          │
│   Supabase · lookup exato + busca semântica (pgvector)           │
│   Preferências por skill · anotações de contatos/clientes        │
│   Memória de usuário final · preferências operacionais           │
│   → escrito pelo Memory Agent em runtime                         │
│   → consultado pelo Context Service e diretamente por skills     │
└─────────────────────────┬────────────────────────────────────────┘
                          │ periodicamente gera documentos síntese
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                       LIGHTRAG                                   │
│   Knowledge Graph + pgvector · workspace por client_id           │
│   Documentos upados pelo usuário · sínteses periódicas           │
│   → consultado via rag_search skill (query semântica/grafo)      │
└──────────────────────────────────────────────────────────────────┘
```

---

### Módulo 1 — Context Service 2.0 (Seções Enriquecidas)

O Context Service já é dinâmico — qualquer atualização na shared_business_memory é refletida automaticamente na próxima carga. O que muda é o **enriquecimento dos schemas** das 6 seções:

#### `company_profile` — De identidade para operação

**Adicionar:**

- `processes` — lista de processos mapeados (onboarding de clientes, ciclo de vendas, entrega, etc.)
- `projects` — projetos ativos e históricos relevantes
- `services` — catálogo de serviços/produtos que a empresa oferece
- `key_suppliers` — fornecedores principais com contexto
- `key_clients_segments` — segmentos de clientes atendidos

#### `brand_voice` — De descrição para exemplos reais

**Adicionar:**

- `message_examples` — mensagens reais aprovadas pelo usuário (few-shot para o agente)
- `avoided_patterns` — padrões de escrita que o usuário reprovou
- `channel_voice` — tom diferente por canal (WhatsApp vs email vs relatório)

#### `policies` — Adicionar preferências do usuário

**Adicionar:**

- `user_preferences` — preferências comportamentais: "prefere resumos curtos", "quer ser avisado antes de qualquer envio de WhatsApp"
- `service_policies` — políticas por serviço/processo
- `approval_by_action` — granularidade de aprovação por tipo de ação

#### `available_tools` — Transformar em memória operacional por skill

**Adicionar:**

- `tool_client_info` — dict por tool/skill com preferências observadas e histórico:
  ```json
  {
    "collection_messages": {
      "preference_notes": "tom amigável mesmo para 30+ dias, nunca mencionar juros na primeira mensagem",
      "approved_examples": ["Oi João, tudo bem? ..."],
      "last_updated": "2025-05-26"
    }
  }
  ```
- `knowledge_graph_summary` — resumo do estado do LightRAG: docs indexados, entidades conhecidas, gaps

---

### Módulo 2 — shared_business_memory (Memória Estruturada Híbrida)

Tabela Supabase que armazena preferências, anotações e aprendizados de forma estruturada, com suporte a **lookup exato e busca semântica**.

```sql
CREATE TABLE shared_business_memory (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id     uuid NOT NULL REFERENCES clientes_blu(client_id),

    -- lookup exato: quem é essa memória?
    entity_type   text NOT NULL,  -- 'client' | 'skill' | 'contact' | 'supplier' | 'user'
    entity_name   text NOT NULL,  -- 'João da Distribuidora' | 'collection_messages' | etc.

    -- conteúdo
    key           text NOT NULL,  -- 'tom_comunicacao' | 'preferencia_projeto' | etc.
    body          text NOT NULL,  -- descrição rica (com limite fixo de chars)

    -- busca semântica
    embedding     vector(1536),   -- pgvector, gerado no upsert

    -- rastreabilidade
    source        text,           -- 'memory_agent' | 'onboarding' | 'user_confirmed'
    curated       boolean DEFAULT false,
    confidence    float DEFAULT 0.5,   -- 0.0 a 1.0
    expires_at    timestamptz,         -- memórias não confirmadas expiram em 14 dias
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now(),

    UNIQUE (client_id, entity_type, entity_name, key)
);

-- índices
CREATE INDEX ON shared_business_memory (client_id, entity_type, entity_name);
CREATE INDEX ON shared_business_memory USING ivfflat (embedding vector_cosine_ops);
```

#### Tipos de entidade (entity_type)

| entity_type | entity_name exemplo       | Uso                                         |
| ----------- | ------------------------- | ------------------------------------------- |
| `skill`     | `collection_messages`     | Preferências do cliente por skill           |
| `client`    | `Maria Padaria Central`   | Anotações sobre clientes da PME             |
| `contact`   | `João da Distribuidora X` | Fornecedores, parceiros, pessoas-chave      |
| `supplier`  | `Distribuidora X`         | Contexto de fornecedores                    |
| `user`      | `maria@padaria.com`       | Preferências do usuário final da plataforma |

#### Dois modos de consulta

**Lookup exato** (Context Service e skills com contexto conhecido):

```python
# Tudo sobre a skill collection_messages para esse cliente
memories = await get_business_memory(
    client_id=client_id,
    entity_type="skill",
    entity_name="collection_messages"
)
```

**Busca semântica** (quando o contexto é ambíguo):

```python
# "O que sei sobre comunicação com clientes inadimplentes?"
memories = await search_business_memory(
    client_id=client_id,
    query="comunicação clientes inadimplentes",
    top_k=5
)
```

---

### Módulo 3 — Memory Agent (Escrita em Runtime)

Agente leve que roda **ao fim de cada conversa**, mas apenas quando há algo novo a registrar. Não substitui o ciclo noturno — complementa com atualização imediata.

**Trigger:** specialist sinaliza que aprendeu algo novo durante a conversa (flag no estado do LangGraph).

**Fluxo:**

```
Conversa termina com flag de aprendizado
        ↓
Memory Agent analisa a conversa
        ↓
Decide o que registrar:
  → Preferência de skill observada → shared_business_memory (entity_type=skill)
  → Informação nova sobre contato → shared_business_memory (entity_type=contact)
  → Preferência do usuário final → shared_business_memory (entity_type=user)
  → Documento upado pelo usuário → LightRAG (já acontece no upload)
  → Nada relevante → encerra sem escrita
        ↓
upsert shared_business_memory com source='memory_agent', curated=false, confidence=0.6
        ↓
Context Service carrega dinamicamente → próxima interação já tem o contexto
```

**Confirmação pelo usuário:**

- Morning plan inclui: "Aprendi algo sobre seu negócio ontem. Quer revisar?"
- Usuário confirma → `curated=true`, `confidence=1.0`, `expires_at=NULL`
- Usuário corrige → atualiza o `body` com a versão correta
- Usuário ignora → expira em 14 dias

---

### Módulo 4 — LightRAG (Conhecimento Documental e Grafo)

Motor de conhecimento semântico para documentos e conhecimento acumulado de longo prazo.

**O que entra no LightRAG:**

1. **Documentos upados pelo usuário** — contratos, manuais, relatórios, NF-e, etc. (incremental — cada upload é processado sem reprocessar o existente)
2. **Sínteses periódicas da shared_business_memory** — a cada período (semanal/mensal), o sistema gera documentos síntese por entidade e os indexa, enriquecendo o grafo com conhecimento estruturado acumulado

**Configuração:**

```python
rag = LightRAG(
    workspace=f"client_{client_id}",  # isolamento por cliente
    kv_storage="PGKVStorage",
    vector_storage="PGVectorStorage",
    graph_storage="PGGraphStorage",   # ou Neo4JStorage para grafos grandes
    doc_status_storage="PGDocStatusStorage",
    llm_model_func=...,
    embedding_func=...,
)
```

**Query modes usados:**

- `local` — perguntas sobre entidades específicas ("o que você sabe sobre o fornecedor X?")
- `mix` — perguntas abertas que combinam grafo e vetor (recomendado com reranker)

**Integração com Context Service:**

- `available_tools.knowledge_graph_summary` — atualizado periodicamente com estado do grafo (docs indexados, entidades conhecidas, gaps identificados)

---

### Fluxo Completo de Leitura (Runtime)

```
Usuário envia mensagem
        ↓
L4 Orchestrator roteia para specialist
        ↓
Context Service injeta contexto base (determinístico):
  → company_profile, brand_voice, policies... filtrados por domínio
  → tool_client_info da skill que será usada (da shared_business_memory via lookup exato)
        ↓
Specialist processa a pergunta
        ↓
[Se a pergunta requer RAG sobre documentos]
  → rag_search skill consulta LightRAG (semântico/grafo)
        ↓
[Se a pergunta menciona um contato/cliente específico]
  → specialist consulta shared_business_memory por entity_type+entity_name
        ↓
Specialist responde com contexto completo
```

---

### Fluxo Completo de Escrita (Runtime + Periódico)

```
RUNTIME (ao fim de cada conversa com aprendizado)
  Memory Agent → upsert shared_business_memory
  Context Service carrega dinamicamente

PERIÓDICO — consolidação (semanal)
  Rotina noturna → confirma memórias pendentes com o usuário
  Rotina noturna → resolve conflitos entre memórias
  Rotina noturna → atualiza seções do Context Service (company_profile, policies...)

PERIÓDICO — enriquecimento do LightRAG (semanal/mensal)
  shared_business_memory → gera documentos síntese por entidade
  → ainsert_custom_kg no LightRAG
  → grafo passa a conter conhecimento estruturado acumulado
```

---

### Impacto na Arquitetura

**L4 Orchestrator:** sem mudanças diretas — se beneficia do contexto mais rico automaticamente.

**L3 Specialists:**

- `context-gatherer` — passa a sinalizar flag de aprendizado ao fim de conversas relevantes
- `frontdesk` — recebe domain projection mais rica
- Todos os outros — se beneficiam de `policies.user_preferences` e `available_tools.tool_client_info`

**L2 Skills:**

- Nova skill: `memory_synthesis` — Memory Agent, roda pós-conversa
- Nova skill: `rag_search` — consulta LightRAG no modo adequado
- Skill existente `morning_plan` — inclui confirmação de memórias pendentes

**L1 Tools:**

- Nova tool: `upsert_business_memory` — upsert na shared_business_memory com geração de embedding
- Nova tool: `get_business_memory` — lookup exato por entity_type + entity_name
- Nova tool: `search_business_memory` — busca semântica por query + client_id
- Nova tool: `confirm_memory_item` — marca `curated=true`
- Tool existente `executar_rag_cliente` — passa a usar LightRAG com workspace por client_id

**Libs afetadas:**

- `blu_context_service` — novos schemas das 6 seções, integração com shared_business_memory
- `blu_models` — atualizar `context_schemas.py` com campos novos
- `blu_agent_framework` — nova skill `memory_synthesis` e `rag_search` no SKILL_REGISTRY

**Supabase:**

- Nova tabela: `shared_business_memory` com pgvector
- Alteração em `clientes_blu`: colunas JSONB ganham campos novos (retrocompatível — nullable)
- LightRAG: instância por ambiente, workspace por client_id (tabelas prefixadas no Supabase)

**Frontend (blu_v3):**

- Tela "O que o Blu sabe sobre mim" — listagem das memórias por entity_type, com editar/deletar
- Notificação matinal de confirmação de memórias novas

---

## Métricas de Sucesso

| Métrica                                          | Baseline | Meta (90 dias)     |
| ------------------------------------------------ | -------- | ------------------ |
| % interações sem reexplicação de contexto        | ~40%     | >90%               |
| Memórias curadas por cliente ativo (30d+)        | 0        | ≥10                |
| Satisfação com respostas do agente (NPS interno) | —        | +15 pts            |
| Taxa de confirmação matinal                      | —        | >60%               |
| Latência de injeção de contexto                  | ~200ms   | <150ms (cache hit) |

---

## Plano de Fases

- **Fase 1 — Fundação:** shared_business_memory (schema + tabela + pgvector) + Context Service 2.0 (schemas enriquecidos) + tools de leitura/escrita. Sem mudança de UX.
- **Fase 2 — Memory Agent:** skill `memory_synthesis`, flag de aprendizado nos specialists, confirmação matinal no morning_plan.
- **Fase 3 — LightRAG:** integração da biblioteca, workspace por client_id, rag_search skill, upload de documentos indexando no LightRAG.
- **Fase 4 — Enriquecimento do Grafo:** ciclo periódico que converte shared_business_memory em documentos síntese e os indexa no LightRAG.
- **Fase 5 — Transparência:** tela "O que o Blu sabe sobre mim" no frontend.

Rollout por tenant: começar com clientes beta (tier PREMIUM, uso >30 dias). Feature flag por `client_id`.

---

## Perguntas Abertas

- [ ] Quanto tempo um item não curado pode ficar antes de expirar? (proposto: 14 dias)
- [ ] O LightRAG ficará na mesma instância Supabase (pgvector) ou precisará de infra separada?
- [ ] Como lidar com conflito entre memórias — duas memórias contraditórias sobre o mesmo entity_type+key?
- [ ] O Memory Agent roda como L2 skill ou como L3 specialist leve?
- [ ] Qual a periodicidade ideal do ciclo de enriquecimento do LightRAG (semanal? mensal? por volume)?
- [ ] O grafo do LightRAG deve incluir histórico de conversas além de documentos e sínteses?
