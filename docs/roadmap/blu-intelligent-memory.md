# Roadmap: Blu Intelligent Memory
**Iniciativa:** Contexto Vivo e Aprendizado Contínuo  
**PRD:** `docs/prd/blu-intelligent-memory.md`  
**Data:** 2025-05-26  
**Versão:** 0.1

---

## Visão Geral das Fases

| Fase | Nome | Duração estimada | Entrega principal |
|---|---|---|---|
| 1 | Fundação da Memória Estruturada | 3 semanas | shared_business_memory + Context Service 2.0 |
| 2 | Memory Agent | 2 semanas | Aprendizado em runtime pós-conversa |
| 3 | LightRAG — Documentos | 3 semanas | RAG documental com KG por cliente |
| 4 | Enriquecimento do Grafo | 2 semanas | Ciclo periódico SBM → LightRAG |
| 5 | Transparência e Controle | 2 semanas | UI de memória para o usuário |

**Total estimado:** ~12 semanas  
**Início sugerido:** Fase 1 pode começar imediatamente (sem dependências externas)

---

## Cronograma Visual

```
Semana →   1   2   3   4   5   6   7   8   9   10  11  12
Fase 1    ████████████
Fase 2                ██████████
Fase 3                ██████████████
Fase 4                                        ███████
Fase 5                                            ████████
```

> Fases 2 e 3 podem ser trabalhadas em paralelo se houver capacidade.

---

## Fase 1 — Fundação da Memória Estruturada
**Duração:** 3 semanas  
**Objetivo:** Criar a infraestrutura base de memória estruturada e enriquecer o Context Service. Nenhuma mudança visível para o usuário — é infraestrutura pura.  
**Critério de saída:** Um specialist consegue salvar e recuperar uma preferência da shared_business_memory via lookup exato. O Context Service carrega os novos campos.

### Por que essa fase primeiro

Tudo depende dela. O Memory Agent (Fase 2) precisa da tabela para escrever. O LightRAG (Fase 3) pode ser desenvolvido em paralelo, mas a shared_business_memory é a base de toda a cadeia. E os schemas do Context Service precisam estar prontos antes de qualquer specialist usar os novos campos.

### O que será construído

**1.1 — Migração Supabase: tabela `shared_business_memory`**

Criar a tabela com o schema completo:
- `entity_type` + `entity_name` + `key` + `body` + `embedding` (vector 1536)
- `client_id` como FK de `clientes_blu`
- Índices: btree em `(client_id, entity_type, entity_name)` + ivfflat em `embedding`
- Constraint unique em `(client_id, entity_type, entity_name, key)`
- `expires_at` para TTL de memórias não confirmadas (default: 14 dias a partir da criação)

**1.2 — L1 Tools: operações de memória**

4 tools novas registradas no `tool_pool_api`:

- `upsert_business_memory(client_id, entity_type, entity_name, key, body, source, confidence)` → faz upsert + gera embedding automaticamente
- `get_business_memory(client_id, entity_type, entity_name)` → lookup exato, retorna todas as keys
- `search_business_memory(client_id, query, top_k=5, entity_type=None)` → busca semântica com filtro opcional por tipo
- `confirm_memory_item(id)` → marca `curated=true`, zera `expires_at`

**1.3 — Context Service 2.0: schemas enriquecidos**

Atualizar `context_schemas.py` e `blu_client_context.py` com campos novos em cada seção:

- `company_profile`: adicionar `processes`, `projects`, `services`, `key_suppliers`, `key_clients_segments`
- `brand_voice`: adicionar `message_examples`, `avoided_patterns`, `channel_voice`
- `policies`: adicionar `user_preferences`, `service_policies`, `approval_by_action`
- `available_tools`: adicionar `tool_client_info` (dict por skill com notas de preferência)

> Todos os campos novos são **nullable** → zero breaking change nos clientes existentes.

**1.4 — Domain Projection: atualização dos filtros**

Revisar `get_domain_projection()` para incluir os novos campos nas projeções por domínio correto (ex: `tool_client_info` só para o domínio da skill relevante, não exposto globalmente).

**1.5 — Seed de onboarding**

Script de migração que popula `shared_business_memory` com dados do onboarding existente (company_profile atual) para clientes que já têm dados. Garante que a tabela não nasce vazia para clientes ativos.

### Riscos

- Habilitar a extensão `pgvector` no Supabase (confirmar se já está ativa no projeto)
- Performance do índice ivfflat com poucos registros (não é problema agora, mas lembrar de `ANALYZE` após volume crescer)

---

## Fase 2 — Memory Agent
**Duração:** 2 semanas  
**Dependência:** Fase 1 completa (precisa da tabela e das tools)  
**Objetivo:** O Blu começa a aprender automaticamente a partir das conversas.  
**Critério de saída:** Após uma conversa onde o usuário corrige ou confirma algo, o agente não precisar ser corrigido novamente na próxima sessão.

### O que será construído

**2.1 — Flag de aprendizado no estado do LangGraph**

Adicionar campo `has_learning: bool` + `learning_notes: list[str]` ao estado do grafo. Qualquer specialist pode sinalizar "aprendi algo nesta conversa" sem saber quem vai processar.

Exemplos de quando sinalizar:
- Usuário corrige o agente: "não, use tom mais formal"
- Usuário confirma uma sugestão: "isso mesmo, pode sempre fazer assim"
- Specialist detecta padrão novo sobre um contato ("João prefere WhatsApp")
- Skill falha e usuário explica o motivo → dado sobre limitação/preferência

**2.2 — Memory Agent: L2 Skill `memory_synthesis`**

Skill leve que roda pós-conversa quando `has_learning=True`:

```
Recebe: conversa completa + learning_notes dos specialists
Analisa: o que foi aprendido? Sobre quem? Com qual confiança?
Decide por entity_type: skill | client | contact | supplier | user
Chama: upsert_business_memory com source='memory_agent', curated=false, confidence=0.6
Retorna: lista de memórias salvas (para log)
```

A skill deve ser conservadora — preferir não salvar a salvar algo errado. Usa `confidence` baixa para observações inferidas, alta para correções explícitas do usuário.

**2.3 — Trigger no Routine Engine / Agent API**

Após cada conversa finalizada, verificar `has_learning` no estado. Se `true`, acionar `memory_synthesis` como step de cleanup (não bloqueia a resposta ao usuário — roda em background).

**2.4 — Confirmação matinal no Morning Plan**

Atualizar skill `morning_plan` para incluir bloco de confirmação de memórias:

```
📝 Aprendi 2 coisas ontem sobre seu negócio:
• Seu cliente João prefere ser contatado por WhatsApp
• Na skill de cobrança, você prefere evitar mencionar juros na primeira mensagem

Quer confirmar? [Sim / Corrigir / Ignorar]
```

Confirmação → `curated=true`, `expires_at=NULL`  
Correção → atualiza `body`  
Ignorar → permanece com TTL de 14 dias

**2.5 — Expiração automática**

Job periódico (diário, 03h) que deleta registros com `expires_at < now()` e `curated=false`. Simples, via Supabase cron ou rotina do Routine Engine.

### Riscos

- Custo de LLM por conversa: a skill deve ter um modelo barato (GPT-4o-mini ou similar) e só ser acionada quando há `has_learning=True`
- Falsos positivos: agente salvar algo incorreto com alta confiança. Mitigação: tudo começa `curated=false` e passa pelo morning plan

---

## Fase 3 — LightRAG — Documentos
**Duração:** 3 semanas  
**Dependência:** Pode ser desenvolvida em paralelo com Fase 2  
**Objetivo:** O Blu consegue responder perguntas sobre documentos do cliente usando um Knowledge Graph semântico.  
**Critério de saída:** Usuário faz upload de um contrato, e o agente responde perguntas sobre ele com contexto relacional ("o que foi combinado com o fornecedor X no contrato de março?").

### O que será construído

**3.1 — Setup LightRAG com Supabase/pgvector**

Integrar a biblioteca `HKUDS/LightRAG` com o Supabase existente:

```python
rag = LightRAG(
    workspace=f"client_{client_id}",
    kv_storage="PGKVStorage",
    vector_storage="PGVectorStorage",
    graph_storage="PGGraphStorage",
    doc_status_storage="PGDocStatusStorage",
    llm_model_func=...,
    embedding_func=...,
)
```

Confirmar se PGGraphStorage é suficiente ou se vale Neo4j para grafos maiores — decidir após spike.

**3.2 — Spike de validação técnica**

Antes de construir a integração completa, fazer um spike (1–2 dias) que responde:
- O PGGraphStorage funciona bem com Supabase?
- Qual o custo de LLM por documento de ~10 páginas (extração de entidades)?
- O modo `mix` com reranker tem latência aceitável (<3s)?
- Workspace isolation funciona corretamente (dois client_id não se cruzam)?

**3.3 — Pipeline de upload de documentos**

Quando usuário faz upload de arquivo (PDF, DOCX, TXT, etc.):
1. OCR/parsing do documento (já existe `extract_document` skill)
2. `rag.ainsert(text)` → LightRAG extrai entidades, relações, cria chunks
3. `doc_status` registra o documento como `PROCESSED`
4. Context Service atualiza `available_tools.knowledge_graph_summary` com novo estado do grafo

**3.4 — L2 Skill `rag_search`**

Skill que encapsula consultas ao LightRAG:

```python
async def rag_search(client_id: str, query: str, mode: str = "mix") -> str:
    rag = await get_client_rag(client_id)
    result = await rag.aquery(query, param=QueryParam(mode=mode))
    return result
```

Modos disponíveis para o specialist escolher:
- `local` — busca centrada em entidades específicas ("o que sei sobre fornecedor X?")
- `mix` — padrão — busca ampla combinando grafo e vetor

**3.5 — Integração nos specialists relevantes**

Specialists que se beneficiam do RAG documental:
- `documentos` — o mais óbvio, responsável por consultas a docs
- `crm` — pode buscar histórico de comunicações upadas
- `financeiro` — pode consultar contratos, NF-e, extratos
- `compras` — pode consultar cotações, pedidos anteriores

Cada um decide se chama `rag_search` com base na natureza da pergunta — não é chamado em toda interação.

### Riscos

- Custo de extração: LightRAG usa LLM para extrair entidades de cada chunk. Estimar custo antes de habilitar para todos os clientes.
- Modelo de embedding: trocar o modelo de embedding invalida todos os vetores existentes — escolher bem desde o início.
- Latência: modo `mix` pode levar 2–5s. Aceitar ou exibir indicador de "buscando nos documentos..."

---

## Fase 4 — Enriquecimento do Grafo
**Duração:** 2 semanas  
**Dependência:** Fases 1, 2 e 3 completas  
**Objetivo:** O LightRAG passa a conter não só documentos upados, mas também o conhecimento estruturado acumulado pelos agentes na shared_business_memory.  
**Critério de saída:** Uma query no LightRAG sobre um fornecedor retorna informações que vieram de documentos E de anotações aprendidas pelos agentes.

### O que será construído

**4.1 — Job de síntese periódica (semanal)**

Rotina que roda semanalmente (domingo à noite):
1. Busca todos os registros `curated=true` da `shared_business_memory` por cliente
2. Agrupa por `entity_type` + `entity_name`
3. Gera um documento síntese por entidade:
   ```
   Entidade: João da Distribuidora X (contato)
   Preferências: prefere WhatsApp, responde melhor de manhã
   Histórico: fornecedor desde jan/2024, principal de grãos
   Notas: negocia com folga de 5% no prazo de pagamento
   ```
4. Chama `rag.ainsert_custom_kg()` com entidade + relações + documento síntese
5. O grafo passa a conectar esse contato com skills, projetos, preferências

**4.2 — Deduplicação inteligente**

LightRAG faz merge automático de entidades com mesmo nome. O job deve:
- Usar `entity_name` normalizado (sem acentos, lowercase) como ID canônico
- Versionar as sínteses com `source_id = f"sbm_synthesis_{date}"` para rastrear a origem

**4.3 — Atualização do knowledge_graph_summary**

Após cada ciclo de enriquecimento, atualizar `available_tools.knowledge_graph_summary` no Context Service com:
- Total de documentos indexados
- Total de entidades no grafo
- Entidades mais relevantes (top 10 por grau de conexão)
- Última data de sincronização

### Riscos

- Volume de entidades pode crescer rápido. Monitorar tamanho do grafo e custo de queries.
- Merge indesejado: dois "João" diferentes sendo tratados como um. Usar identificadores únicos onde possível (email, CNPJ).

---

## Fase 5 — Transparência e Controle
**Duração:** 2 semanas  
**Dependência:** Fases 1 e 2 completas (para ter memórias para exibir)  
**Objetivo:** O usuário consegue ver, editar e deletar o que o Blu aprendeu sobre seu negócio.  
**Critério de saída:** Usuário acessa a tela "O que o Blu sabe sobre mim", corrige uma preferência errada, e na próxima conversa o agente usa a versão correta.

### O que será construído

**5.1 — Endpoint de leitura de memórias**

`GET /api/memory/{client_id}` — retorna memórias agrupadas por `entity_type`, com paginação.

**5.2 — Endpoint de edição e exclusão**

`PATCH /api/memory/{id}` — atualiza `body` e marca `curated=true`  
`DELETE /api/memory/{id}` — remove a memória

**5.3 — Tela no frontend (blu_v3)**

Seção "O que o Blu sabe" acessível via configurações:

```
📋 O que o Blu aprendeu sobre seu negócio

[Skills]
• Cobrança: prefere tom amigável mesmo após 30 dias   [✓ confirmado] [editar]
• Resumo diário: quer receber às 8h30               [pendente confirmação] [confirmar] [editar]

[Contatos]
• João da Distribuidora X: prefere WhatsApp, manhã   [✓ confirmado] [editar]

[Preferências do usuário]
• Prefere respostas curtas e diretas                 [✓ confirmado] [editar]
```

**5.4 — Notificação proativa**

Badge na interface quando há memórias novas não confirmadas: "O Blu aprendeu 3 coisas novas — revisar".

---

## Perguntas Abertas por Fase

**Fase 1:**
- [ ] pgvector já está habilitado no projeto Supabase? Confirmar antes de começar.
- [ ] Qual embedding model usar? (text-embedding-3-small 1536d ou 3-large 3072d)

**Fase 2:**
- [ ] Memory Agent como L2 skill ou L3 specialist leve? (recomendação: L2 skill — mais simples, sem roteamento)
- [ ] Quais specialists devem sinalizar `has_learning`? Começar só com frontdesk e crm ou todos?

**Fase 3:**
- [ ] PGGraphStorage do LightRAG ou Neo4j? (spike vai responder)
- [ ] Qual modelo LLM para extração de entidades? (menor custo possível — GPT-4o-mini?)
- [ ] Habilitar para todos os clientes desde o início ou feature flag por tier?

**Fase 4:**
- [ ] Periodicidade do enriquecimento: semanal é suficiente ou quinzenal resolve com menos custo?
- [ ] Como lidar com conflito entre doc upado e síntese da SBM sobre a mesma entidade?

**Fase 5:**
- [ ] A tela fica nas configurações ou no painel principal do Blu?
- [ ] Mostrar memórias do LightRAG também ou só da shared_business_memory?

---

## Dependências Técnicas Confirmadas

- `pgvector` no Supabase — verificar se já habilitado
- `HKUDS/LightRAG` — biblioteca open source, MIT license
- Modelo de embedding — definir na Fase 3 (nunca mais trocar)
- LLM barato para Memory Agent e extração LightRAG — GPT-4o-mini ou equivalente

---

## Próximos Passos Imediatos

1. Confirmar se pgvector está habilitado no Supabase
2. Escrever migration SQL da tabela `shared_business_memory`
3. Criar as 4 L1 tools de memória
4. Atualizar `context_schemas.py` com novos campos (Fase 1)
5. Fazer spike do LightRAG com Supabase (pode correr em paralelo com item 2-4)
