# repo-index.md — T3.1 Pipeline de Indexação Vetorial

> Mapa do codebase relevante para implementação das subtarefas T3.1a a T3.1f.
> Gerado em: 2026-06-19 | Branch: phase-3/issue-25-pipeline-indexacao-vector-store

## Status das Migrations

| Migration | Status | Relevância T3.1 |
|-----------|--------|-----------------|
| `proposed/20260619000000_shared_business_memory.sql` | **proposed (não aplicada)** | BASE: tabela que vai receber coluna embedding |
| `proposed/20260619000001_shared_memory_links.sql` | **proposed (não aplicada)** | Links entre entidades, pode usar embedding p/ sugestão |
| `proposed/20260619000002_shared_memory_integrity.sql` | **proposed (não aplicada)** | Validação pre-INSERT (não conflita com embedding) |
| `proposed/20260619000003_snapshot_templates.sql` | **proposed** | Snapshot (Fase 2, #22), não diretamente relevante |
| `proposed/20260619000003_routine_checkpoint_rpc.sql` | **proposed** | Checkpoint (Fase 2, #21) |

**Conclusão**: Toda a tabela base de shared memory está em proposed. A migration T3.1a será a primeira a tocar nela após aplicação.

## Arquivos Relevantes por Subtarefa

### T3.1a — Migration SQL (embedding + pgvector index)
- **Schema base**: `supabase/migrations/proposed/20260619000000_shared_business_memory.sql`
  - Colunas: id, client_id, entity_type, entity_name, key, category, value, source, confidence, metadata, created_at, updated_at
  - **NÃO** tem coluna `embedding` nem `version` (version é referenciado no memory_module mas não existe na tabela)
  - RLS: policy `client_own_shared_memory` usando `current_setting('app.client_id')`
- **Nova migration a criar**: `20260619000003_shared_memory_vector.sql`
- **pgvector**: extensão não encontrada em migrations applied. Verificar se existe na instância Supabase target (`CREATE EXTENSION IF NOT EXISTS vector`)

### T3.1b — Hook embedding no write/upsert
- **`services/tool_pool_api/src/tool_pool_api/server/tool_modules/memory_module.py`** (1262 linhas)
  - `_shared_memory_upsert_logic()` — principal alvo para hook (linha 187-261)
  - `shared_memory_write` tool (linha 930-1018) — também precisa de hook quando `supersede=false`
  - `_VALID_ENTITY_TYPES`: {"skill", "client", "contact", "supplier", "user", "snapshot"}
  - `_TABLE = "shared_business_memory"`
  - Importa: `blu_supabase_client`, `blu_auth.mcp.auth_middleware`
  - **Padrão**: payload dict → `db.upsert()` com `on_conflict="client_id,entity_type,entity_name,key"`
- **Ponto de inserção do hook**: entre a construção do `payload` e a chamada `db.upsert()`
- **Representação textual para embedding**: `f"{entity_type}:{entity_name} | {key}: {json.dumps(value, ensure_ascii=False)}"`

### T3.1c — Edge Function busca vetorial
- **Modelo a seguir**: `supabase/functions/search-documents/index.ts` (212 linhas)
  - Usa Cohere embed-multilingual-light-v3.0 (384 dims)
  - Chama RPC `vector_db.match_documents()` ou `vector_db.hybrid_match_documents()`
  - Injeção de client_id via payload (não header) — **atenção**: RLS espera `current_setting('app.client_id')`
  - Padrão: Deno.serve → postgres() → embed → RPC → json response
- **Nova Edge Function a criar**: `supabase/functions/search-shared-memory/index.ts`
- **RPC a criar**: `match_shared_business_memory()` ou usar query direta com `<=>` operator
- **Diferença crucial**: search-documents usa `vector_db` schema. Shared memory está em `public`.

### T3.1d — Job de backfill
- **Script a criar**: `scripts/backfill_shared_memory_embeddings.py`
- **pg_cron migration**: `supabase/migrations/proposed/20260619000005_backfill_embeddings_cron.sql`
- **Depende de**: T3.1a (coluna existe) + T3.1b (embedding client disponível)
- **Query**: `SELECT * FROM shared_business_memory WHERE embedding IS NULL`
- **Batch**: usar `embed_documents()` do BluEmbeddingAPIClient com batch size configurável

### T3.1e — blu_llm_service: cliente de embeddings
- **`libs/blu_llm_service/src/blu_llm_service/client.py`** (685 linhas)
  - `BluEmbeddingAPIClient` (linha 151-185): chama embedding_service HTTP (`/embed`)
  - `get_embedding_model()` (linha 593-597): factory que retorna BluEmbeddingAPIClient
  - Suporta modos E5: `mode="document"` e `mode="query"`
- **`libs/blu_llm_service/src/blu_llm_service/config.py`** (128 linhas)
  - `EMBEDDING_SERVICE_URL` default: `http://embedding_service:11435`
  - Também tem `OPENAI_API_KEY`, `HF_TOKEN` (para HuggingFace)
- **Arquivo a criar**: `libs/blu_llm_service/src/blu_llm_service/embeddings.py`
  - Função `get_embeddings(texts: list[str]) -> list[list[float]]`
  - Suporte a múltiplos providers: embedding_service (E5), OpenAI (text-embedding-3-small), Ollama (nomic-embed-text)
  - Config via env: `EMBEDDING_PROVIDER`, `EMBEDDING_DIM`

### T3.1f — Testes
- **Testes existentes**: `services/tool_pool_api/tests/` (estrutura pytest)
  - `services/agent_api/tests/unit/test_routine_checkpoint.py` — padrão de teste com mock de Supabase
- **Arquivos a criar**:
  - `tests/unit/test_shared_memory_vector.py`
  - `tests/integration/test_shared_memory_vector_search.py`

## Dependências entre Arquivos

```
migrations/proposed/20260619000003_shared_memory_vector.sql  (T3.1a)
    ├── memory_module.py  (T3.1b) — hook no upsert/write
    │   └── blu_llm_service/embeddings.py  (T3.1e) — cliente
    ├── supabase/functions/search-shared-memory/index.ts  (T3.1c)
    │   └── RPC match_shared_business_memory  (T3.1c mesmo arquivo)
    └── scripts/backfill_shared_memory_embeddings.py  (T3.1d)
        └── pg_cron job  (T3.1d)
```

## Pontos de Atenção no Codebase

1. **Coluna `version` referenciada mas não existe** no schema da migration 00000. O memory_module.py retorna `version` (linhas 176, 258) mas a migration não define essa coluna. Deve ser adicionada ao schema base OU removida do código.
2. **RLS com `current_setting('app.client_id')`** — a Edge Function precisa injetar esse setting via `SELECT set_config('app.client_id', $1, true)` antes da query.
3. **`_VALID_CATEGORIES`** no memory_module (definida em linha ~34 mas não visível no trecho lido) — verificar se inclui 'rag' (provavelmente sim, baseado nos CHECK constraints da migration).
