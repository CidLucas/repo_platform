# resolution.md — Resolução de Conflitos e Decisões T3.1

> Análise de consistência entre plan.json (intake) e codebase real.
> Gerado em: 2026-06-19

---

## 1. Conflitos Detectados

### C-01: Modelo de Embedding — plan vs codebase

**Plan (DD-02)**: text-embedding-3-small (OpenAI, 1536 dims) OU nomic-embed-text (Ollama, 768 dims)
**Codebase real**: `BluEmbeddingAPIClient` chama `embedding_service` interno (E5, dimensão desconhecida)

**Análise**: O `BluEmbeddingAPIClient` atual é um wrapper HTTP que não suporta OpenAI nem Ollama diretamente. O endpoint `/embed` esperado usa modelo E5 (prefixo `passage:` / `query:`). Isso é inconsistente com o plano de usar text-embedding-3-small ou nomic-embed-text.

**Resolução**:
- **T3.1e deve criar um novo módulo `embeddings.py`** que abstrai a escolha do provider
- Provider padrão: usar `embedding_service` existente (E5) como fallback
- Adicionar suporte a OpenAI via `EMBEDDING_PROVIDER=openai` (usa `OPENAI_API_KEY` já existente no config.py)
- Adicionar suporte a Ollama via `EMBEDDING_PROVIDER=ollama` (requer endpoint Ollama)
- Dimensão do embedding deve ser detectada automaticamente na primeira chamada e validada contra a coluna `vector(N)` da migration

**Impacto**: T3.1e ganha escopo. Não quebra nada existente — é aditivo.

### C-02: Coluna `version` inexistente na migration base

**memory_module.py** referencia `version` (linhas 176, 258) no retorno de `shared_memory_read` e `shared_memory_upsert`.
**Migration 00000**: NÃO define coluna `version` na tabela `shared_business_memory`.

**Resolução**: A coluna `version` deve ser adicionada à migration base (00000) ANTES de T3.1a. Alternativa: T3.1a pode incluir `ADD COLUMN version INTEGER DEFAULT 1`. O factory-coder de T3.1a deve receber essa instrução.

**Impacto**: Não é bloqueante para T3.1, mas é uma inconsistência que precisa ser resolvida para o `shared_memory_upsert` funcionar corretamente com versionamento.

### C-03: search-documents usa Cohere (384 dims) vs T3.1 (1536 dims)

**search-documents**: Cohere embed-multilingual-light-v3.0, 384 dims, coluna `halfvec(384)`
**T3.1 plan**: text-embedding-3-small 1536 dims, coluna `vector(1536)`

**Análise**: Não é um conflito real — são pipelines separados (documentos vs shared memory). Mas a Edge Function search-shared-memory deve ser configurável quanto ao provider de embedding, para consistência com T3.1e.

**Resolução**: A search-shared-memory deve usar o mesmo `get_embeddings()` de T3.1e (via chamada HTTP ao backend Python) OU replicar a lógica de provider switching no TypeScript. Recomendação: chamar o backend Python para manter single source of truth.

**Impacto**: T3.1c precisa de um endpoint no backend para gerar embedding da query. Alternativa mais simples: Edge Function chama diretamente OpenAI/Ollama com a mesma config.

---

## 2. Design Questions — Respostas

### DQ-01: Categoria 'rag' deve ter prioridade no embedding?

**Resposta**: NÃO na representação textual. A categoria 'rag' pode ser usada como filtro na busca (parâmetro `category` da Edge Function), mas não deve ter weight diferente no embedding em si. O embedding deve representar o conteúdo semântico completo do fato, independente da categoria.

**Justificativa**: Weight no embedding distorce o espaço vetorial e reduz a qualidade da busca para outras categorias. Filtro pós-busca por categoria é mais limpo e reversível.

**Ação**: Incluir `category` como campo retornado na busca e permitir filtrar por `category IN ('rag', ...)`.

### DQ-02: Incluir metadata no embedding?

**Resposta**: SIM, mas apenas campos estáveis de metadata (source, agent_id), não campos voláteis (timestamps, TTL).

**Justificativa**: Metadata como `source: memory_agent` ou `agent_id: uuid` fornece contexto de proveniência que melhora a qualidade da busca semântica. Ex: fatos do mesmo agente tendem a ser semanticamente relacionados.

**Representação textual ajustada**:
```
f"{entity_type}:{entity_name} | {key}: {json.dumps(value)} | source:{source} agent:{agent_id}"
```

**Ação**: T3.1b deve incluir source e agent_id (se disponível) na string de embedding.

### DQ-03: HNSW params — defaults vs tunados?

**Resposta**: Usar **defaults do pgvector** (`m=16, ef_construction=64`) inicialmente. Adicionar env vars `HNSW_M` e `HNSW_EF_CONSTRUCTION` para tuning futuro sem re-migration.

**Justificativa**: Defaults do pgvector são otimizados para datasets até ~1M vetores. Com 100k fatos esperados, defaults são mais que suficientes. Over-tuning prematuro pode piorar performance.

**Ação**: T3.1a usa defaults. Documentar que tuning pode ser feito via `ALTER INDEX ... SET (ef_search = ...)` em runtime, sem reindex.

### DQ-04: Backfill por tenant ou global?

**Resposta**: **GLOBAL** (todos os clientes), mas em batches por client_id para evitar locks longos.

**Justificativa**: Backfill é one-off. Processar todos os tenants de uma vez é mais simples e não tem risco de inconsistência porque a tabela é nova (sem dados legados significativos). Mesmo que haja dados, o `WHERE embedding IS NULL` garante idempotência.

**Ação**: T3.1d implementa loop: `for client_id in all_clients: process_batch(client_id)`. pg_cron job único (não por tenant).

---

## 3. Avaliação de Riscos

### R-01: Latência de embedding no write path

**Severidade**: MÉDIA (não ALTA como no plano)
**Análise**: O BluEmbeddingAPIClient já tem timeout de 60s. Para o write path, podemos reduzir para 5s. Se o embedding_service estiver saudável, latência típica é <500ms para E5.

**Mitigação concreta**:
1. Timeout de 5s no write path (embedding_service local é rápido)
2. Fallback: gravar `embedding = NULL` e logar warning (backfill pega depois)
3. Cache em memória: `functools.lru_cache(maxsize=1000)` para textos idênticos
4. Métrica: logar p95 latency do embedding no write path

### R-02: Custo de API (OpenAI embeddings)

**Severidade**: BAIXA (com mitigação)
**Análise**: text-embedding-3-small custa $0.02/1M tokens ≈ $0.00002 por fato de ~100 tokens. Com 100k fatos = $2.00 total. Backfill one-off de $2.00 é irrisório.

**Mitigação concreta**:
1. Provider padrão: embedding_service local (E5, custo zero)
2. OpenAI apenas se explicitamente configurado via `EMBEDDING_PROVIDER=openai`
3. Batch API no backfill (até 2048 textos por chamada)

### R-03: RLS na busca vetorial

**Severidade**: ALTA
**Análise**: A Edge Function usa service_role key (bypass RLS). Se não injetar `app.client_id` corretamente, a busca retorna dados de outros clientes. Isso é uma vulnerabilidade de isolamento multi-tenant.

**Mitigação concreta**:
1. Edge Function recebe `client_id` no payload (validado)
2. Antes da query: `SELECT set_config('app.client_id', $client_id::text, true)`
3. Query usa `WHERE client_id = current_setting('app.client_id')::uuid`
4. Teste de integração: criar fatos para 2 clientes, buscar para cliente A, verificar que não retorna dados de B
5. Log de auditoria: logar client_id + query em cada requisição

---

## 4. Verificações de Consistência (Lint)

| Check | Status | Detalhe |
|-------|--------|---------|
| Coluna `version` existe? | ❌ FALHA | Migration 00000 não define `version`, mas memory_module.py referencia |
| Coluna `embedding` existe? | ❌ FALHA | Não existe — T3.1a vai criar |
| pgvector extension instalada? | ⚠️ NÃO VERIFICADO | Não encontrada em migrations applied; precisa ser verificada na instância Supabase |
| `_VALID_CATEGORIES` inclui 'rag'? | ✅ PROVÁVEL | Migration CHECK constraint inclui 'rag' |
| `_VALID_ENTITY_TYPES` inclui 'snapshot'? | ✅ SIM | memory_module.py linha 35 |
| RLS policy cobre nova coluna? | ✅ SIM | Policy `client_own_shared_memory` é `FOR ALL` — cobre novas colunas automaticamente |
| HNSW vs IVFFLAT? | ✅ HNSW | Decisão DD-03 alinhada com melhores práticas pgvector |
| Timeout no write path? | ✅ CONFIGURÁVEL | BluEmbeddingAPIClient aceita timeout parameter |
