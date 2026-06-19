# patterns.md — Padrões de Código para T3.1

> Padrões, convenções e anti-padrões descobertos no codebase que devem guiar a implementação.
> Gerado em: 2026-06-19

## P1. Supabase Upsert Pattern (memory_module.py)

**Localização**: `_shared_memory_upsert_logic()` (linhas 187-261)

```python
payload = {
    "client_id": client_id,
    "entity_type": entity_type,
    "entity_name": entity_name,
    "key": key,
    "value": body,
    "metadata": frontmatter if frontmatter is not None else {},
    "source": source,
    "confidence": confidence,
}

result = await (
    db.schema("public")
    .table(_TABLE)
    .upsert(payload, on_conflict="client_id,entity_type,entity_name,key", default_to_null=False)
    .execute()
)
```

**Aplicação em T3.1b**: Adicionar campo `embedding` ao payload após chamar `get_embeddings()`.

```python
# Hook proposto (antes do db.upsert)
from blu_llm_service import get_embedding_model

embedding_model = get_embedding_model()
embedding_text = f"{entity_type}:{entity_name} | {key}: {json.dumps(body, ensure_ascii=False)}"
embeddings = embedding_model.embed_documents([embedding_text])
payload["embedding"] = embeddings[0]
```

**Atenção**: O `embed_documents()` do BluEmbeddingAPIClient usa `mode="document"` (prefixo E5). Se usar OpenAI/Ollama, esse modo pode não ser aplicável — T3.1e deve abstrair isso.

## P2. Embedding Client Pattern (blu_llm_service)

**Localização**: `BluEmbeddingAPIClient` (client.py linhas 151-185)

```python
class BluEmbeddingAPIClient(Embeddings):
    def __init__(self, base_url: str):
        self.api_url = f"{base_url.rstrip('/')}/embed"

    def _call_api(self, texts: list[str], mode: str = "document") -> list[list[float]]:
        import requests
        response = requests.post(
            self.api_url,
            json={"texts": texts, "mode": mode},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["embeddings"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._call_api(texts, mode="document")

    def embed_query(self, text: str) -> list[float]:
        return self._call_api([text], mode="query")[0]
```

**Aplicação em T3.1e**: Criar `embeddings.py` com função helper:

```python
# libs/blu_llm_service/src/blu_llm_service/embeddings.py
from typing import List
from .client import get_embedding_model

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Gera embeddings para uma lista de textos usando o modelo configurado."""
    model = get_embedding_model()
    return model.embed_documents(texts)
```

**Provider switching**: Usar env var `EMBEDDING_PROVIDER` (openai | ollama | embedding_service) com fallback para embedding_service existente.

## P3. Edge Function Vector Search Pattern (search-documents)

**Localização**: `supabase/functions/search-documents/index.ts` (212 linhas)

Estrutura canônica:
```typescript
import postgres from "https://deno.land/x/postgresjs@v3.4.5/mod.js";
import { corsHeaders, json } from "../_shared/cors.ts";

Deno.serve(async (req: Request) => {
    if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
    const sql = postgres(DB_URL, { prepare: false });
    try {
        const body = await req.json();
        const { query, client_id, match_count = 5, match_threshold = 0.3 } = body;

        // 1. Gerar embedding
        const queryEmbedding = await generateEmbedding(query);
        const embeddingStr = `[${queryEmbedding.join(",")}]`;

        // 2. Chamar RPC
        const results = await sql`
          SELECT * FROM match_shared_business_memory(
            ${client_id}::uuid,
            ${embeddingStr}::vector,
            ${match_count}::int,
            ${match_threshold}::float
          )
        `;

        return json({ results });
    } finally {
        await sql.end();
    }
});
```

**Aplicação em T3.1c**:
- Nome da função: `search-shared-memory`
- Embedding model: mesmo que T3.1e configurar (não hardcoded Cohere como search-documents)
- RPC: `match_shared_business_memory` com parâmetros: client_id, query_embedding, match_count, match_threshold, entity_type, category
- Filtros: entity_type, category, key prefix

**Cuidado com RLS**: search-documents usa `service_role` key. A nova EF deve injetar `app.client_id` via `set_config` antes da query:

```sql
PERFORM set_config('app.client_id', client_id_param::text, true);
```

## P4. Auth / Client ID Injection Pattern

**Localização**: memory_module.py (várias tools)

```python
@mcp_inject_client_id
async def shared_memory_upsert(
    ctx: Context,
    ...
    client_id: str | None = None,
) -> dict:
    if not client_id:
        raise ToolError("client_id is required")
```

O decorator `@mcp_inject_client_id` extrai o client_id do contexto MCP e injeta como parâmetro.

**Aplicação em T3.1b**: O hook de embedding NÃO precisa se preocupar com auth — ele roda dentro do mesmo contexto MCP. O client_id já estará disponível.

## P5. Migration SQL Pattern

**Localização**: `supabase/migrations/proposed/`

Convenções:
- Nome: `YYYYMMDDHHMMSS_descricao.sql`
- Dentro de `BEGIN; ... COMMIT;`
- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`
- `COMMENT ON TABLE/COLUMN` para documentação
- `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- `CREATE POLICY ... TO authenticated USING (...)` 
- `GRANT ... TO authenticated; GRANT ... TO service_role;`

**Aplicação em T3.1a**:
```sql
-- 20260619000003_shared_memory_vector.sql
ALTER TABLE public.shared_business_memory
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS idx_sbm_embedding_hnsw
  ON public.shared_business_memory
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

## P6. Batch / Backfill Pattern

**Localização**: Não existe padrão direto. Sugerido:

```python
# scripts/backfill_shared_memory_embeddings.py
BATCH_SIZE = 50
offset = 0
while True:
    rows = supabase.table("shared_business_memory") \
        .select("id, entity_type, entity_name, key, value") \
        .is_("embedding", "null") \
        .range(offset, offset + BATCH_SIZE - 1) \
        .execute()
    if not rows.data:
        break
    texts = [format_text_for_embedding(r) for r in rows.data]
    embeddings = get_embeddings(texts)
    for row, emb in zip(rows.data, embeddings):
        supabase.table("shared_business_memory") \
            .update({"embedding": emb}) \
            .eq("id", row["id"]) \
            .execute()
    offset += BATCH_SIZE
```

## P7. Test Pattern (pytest + mock Supabase)

**Localização**: `services/agent_api/tests/unit/test_routine_checkpoint.py`

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_routine_checkpoint():
    mock_db = AsyncMock()
    mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
        return_value=MockResponse(data=[{...}])
    )
    with patch("blu_supabase_client.get_supabase_client", return_value=mock_db):
        result = await some_function(client_id="test-id")
        assert result["key"] == "expected"
```

## Anti-Padrões a Evitar

1. **Não hardcodar modelo de embedding** — usar config/env (search-documents faz isso com Cohere, mas T3.1 deve ser configurável)
2. **Não esquecer timeout** — API de embedding pode ser lenta (5s timeout no write path)
3. **Não fazer N chamadas individuais** — usar batch `embed_documents()` sempre que possível
4. **Não logar embeddings completos** — são vetores de 1536 floats, log só os primeiros 5 valores como sanity check
5. **Não esquecer RLS na Edge Function** — a EF usa service_role, precisa injetar client_id manualmente
