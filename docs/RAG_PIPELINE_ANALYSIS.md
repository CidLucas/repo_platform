# RAG Pipeline — Metadata & Retrieval Analysis

> Generated: 2026-03-04 | Updated: 2026-03-10 | Status: **Most issues resolved** — see RAG Overhaul Phases 1–6
>
> This document was the original analysis that led to the RAG Overhaul. Issues marked with ✅ have been resolved.
> For the current as-built documentation, see `HYBRID_RETRIEVER_AS_BUILT.md`.

---

## 1. Architecture Overview

### Current Architecture (Post-Overhaul)

```
┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Frontend    │───▶│  process-document │───▶│  document_chunks   │
│  (Dashboard)  │    │  Edge Function    │    │  (vector_db)       │
└──────────────┘    │  (Cohere embed    │    │  WITH embeddings   │
                    │   inline)         │    │  + metadata        │
                    └──────────────────┘    └─────────┬──────────┘
                                                      │ FTS trigger
                                                      ▼
┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  rag_module   │◀──│ search-documents  │    │  generate_fts      │
│ (tool_pool)   │   │  Edge Function    │    │  (auto tsvector)   │
└──────────────┘    │  (Cohere embed)   │    └────────────────────┘
                    └──────────────────┘
```

> **Removed:** The `embed` Edge Function (gte-small), pgmq `embedding_jobs` queue, `queue_embedding_if_null` trigger, and `util.process_embeddings()` cron job have all been removed. Embedding is now inline in `process-document` using Cohere `embed-multilingual-light-v3.0`.

**Components in order of execution:**

| # | Component | Location | Role |
|---|-----------|----------|------|
| 1 | `knowledgeBaseService.ts` | `apps/vizu_dashboard/src/services/` | Upload file, create doc row, invoke Edge Function |
| 2 | `process-document` Edge Function | `supabase/functions/process-document/index.ts` | Download → parse → chunk → embed (Cohere) → enrich metadata → INSERT |
| 3 | ~~`queue_embedding_if_null` trigger~~ | ~~`vector_db` schema~~ | **REMOVED** — embedding is inline |
| 4 | ~~`util.process_embeddings()`~~ | ~~pg_cron~~ | **REMOVED** — no embedding queue |
| 5 | ~~`embed` Edge Function~~ | ~~`supabase/functions/embed/index.ts`~~ | **REMOVED** — replaced by Cohere in process-document |
| 6 | `search-documents` Edge Function | `supabase/functions/search-documents/index.ts` | Embed query (Cohere) → `hybrid_match_documents()` RPC → return results |
| 7 | `HybridRetriever` / `SupabaseVectorRetriever` | `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | LangChain retriever — calls search-documents, returns Documents |
| 8 | `CohereReranker` | `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py` | Re-scores candidates with calibrated 0–1 relevance scores |
| 9 | `MMRDiversifier` | `libs/vizu_rag_factory/src/vizu_rag_factory/diversity.py` | Reduces redundancy via Jaccard + same-document penalty |
| 10 | `create_rag_runnable` | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | Build LangChain chain: preprocess → retrieve → rerank → diversify → format → LLM |
| 11 | `rag_module.py` | `services/tool_pool_api/src/.../tool_modules/rag_module.py` | MCP tool entry point — resolves context, invokes RAG chain |

---

## 2. Database Schema

### `vector_db.documents`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID (PK) | `gen_random_uuid()` |
| `client_id` | UUID (NOT NULL) | FK-like, for RLS |
| `title` | TEXT | Optional |
| `file_name` | TEXT (NOT NULL) | Original filename |
| `file_type` | TEXT | Extension (txt, pdf, etc.) |
| `storage_path` | TEXT | Path in `knowledge-base` bucket |
| `source` | TEXT | Default `'upload'` |
| `processing_mode` | TEXT | Default `'simple'` |
| `status` | TEXT | `pending` → `processing` → `completed` / `failed` |
| `error_message` | TEXT | Populated on failure |
| `chunk_count` | INTEGER | Set by process-document |
| `created_at` | TIMESTAMPTZ | `now()` |
| `updated_at` | TIMESTAMPTZ | `now()` |

### `vector_db.document_chunks`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER (PK) | Auto-increment |
| `document_id` | UUID (NOT NULL) | FK to documents |
| `client_id` | UUID (NOT NULL) | Denormalized for RLS filtering |
| `content` | TEXT (NOT NULL) | Chunk text content |
| `embedding` | halfvec(384) | NULL until embed function processes it |
| `chunk_index` | INTEGER | Position within document |
| `metadata` | JSONB | Default `'{}'::jsonb` |
| `created_at` | TIMESTAMPTZ | `now()` |

### Indexes on `document_chunks`
| Index | Type | Column(s) |
|-------|------|-----------|
| `document_chunks_pkey` | btree (UNIQUE) | `id` |
| `idx_chunks_client_id` | btree | `client_id` |
| `idx_chunks_document_id` | btree | `document_id` |
| `idx_chunks_embedding` | HNSW | `embedding halfvec_cosine_ops` |

### Key Functions
| Function | Purpose |
|----------|---------|
| `vector_db.match_documents(client_id, embedding, count, threshold)` | Cosine similarity search with RLS filter |
| `vector_db.queue_embedding_if_null()` | Trigger function: send to pgmq if embedding IS NULL |
| `vector_db.chunk_content_fn(document_chunks)` | Returns `.content` for embed function |
| `vector_db.get_document_embedding_progress(doc_id)` | Returns total/embedded/progress_pct |
| `util.process_embeddings(batch_size, max_requests, timeout)` | pg_cron entry: poll pgmq → invoke embed |

---

## 3. Metadata Creation — Step by Step

### Step 1: Frontend Upload (`knowledgeBaseService.ts` L137-190)

The frontend uploads a file to Supabase Storage and creates a document row:

```typescript
// Insert into vector_db.documents
{
    client_id: clientId,
    file_name: file.name,
    file_type: ext.replace(".", ""),
    storage_path: storagePath,      // e.g. "uuid/uuid-filename.txt"
    source: "upload",               // or "chat"
    processing_mode: "simple",
    status: "processing",
}
```

Then invokes `process-document` Edge Function with:
```json
{
    "document_id": "uuid",
    "storage_path": "client_id/uuid-filename.ext",
    "client_id": "uuid",
    "file_name": "original.txt",
    "file_type": "txt"
}
```

**Metadata created at this stage:** Document-level metadata only (in `documents` table). No chunk-level metadata yet.

### Step 2: Chunking (`process-document/index.ts` L47-128)

The `chunkText()` function creates chunk-level metadata:

```typescript
const chunks = chunkText(parsedText, {
    source_file: fileName,    // ← ONLY metadata field
});
```

Each chunk gets:
```typescript
{
    text: "chunk content...",
    index: 0,
    metadata: { source_file: "brpolen_sobre_empresa.txt" }
}
```

**Chunk metadata contents: `{ source_file: string }` — one single field.**

### Step 3: INSERT into document_chunks (`process-document/index.ts` L302-315)

```typescript
await sql`
    INSERT INTO vector_db.document_chunks
      (document_id, client_id, content, chunk_index, metadata)
    VALUES (
      ${documentId}::uuid,
      ${clientId}::uuid,
      ${chunk.text},
      ${chunk.index},
      ${JSON.stringify(chunk.metadata)}::jsonb   // ⚠️ BUG HERE
    )
`;
```

### 🐛 BUG: Double-encoded metadata

`JSON.stringify(chunk.metadata)` produces the string `'{"source_file":"brpolen_sobre_empresa.txt"}'`.

When postgres.js parameterizes this and PostgreSQL casts with `::jsonb`, the result is a **JSONB string value** (type `"string"`), NOT a JSONB object:

```sql
-- What's stored:
SELECT jsonb_typeof(metadata) FROM vector_db.document_chunks;
-- Result: "string"    ← Should be "object"

-- The actual value:
SELECT metadata FROM vector_db.document_chunks LIMIT 1;
-- Result: "{\"source_file\":\"brpolen_sobre_empresa.txt\"}"
-- This is a JSON STRING containing JSON, not a JSON OBJECT
```

**Impact:** Downstream code that tries to treat metadata as a dict/object will break or need special handling (the `json.loads()` fix we added to `retriever.py` is a workaround).

**Fix:** Pass the object directly to postgres.js without `JSON.stringify()`:
```typescript
// CORRECT — let postgres.js handle JSONB serialization
${sql.json(chunk.metadata)}
// OR simply:
${chunk.metadata}::jsonb  // postgres.js serializes objects automatically
```

### Step 4: Trigger → pgmq (`queue_embedding_if_null`)

The trigger fires on INSERT and sends:
```json
{
    "id": 18,
    "schema": "vector_db",
    "table": "document_chunks",
    "contentFunction": "vector_db.chunk_content_fn",
    "embeddingColumn": "embedding"
}
```

**No metadata flows through this step.** The trigger only references the chunk ID — the embed function fetches content via `chunk_content_fn`.

### Step 5: Embed Function (`embed/index.ts` L44-86)

The embed function:
1. Calls `vector_db.chunk_content_fn(t)` to get content text
2. Runs `gte-small` with `mean_pool: true, normalize: true`
3. Updates `embedding` column with the 384-dim halfvec
4. Checks if all sibling chunks are embedded → marks document `'completed'`

**No metadata is read or modified.** The embed function only touches `content` (read) and `embedding` (write).

---

## 4. Retrieval Pipeline — Step by Step

### Step 1: Agent invokes `executar_rag_cliente` (`rag_module.py` L35-152)

The MCP tool:
1. Resolves `cliente_id` from request meta or JWT
2. Loads `VizuClientContext` via context service
3. Validates tool is enabled (`is_tool_enabled_for_client`)
4. Gets LLM via `get_model(tier=DEFAULT, task="rag")`
5. Calls `create_rag_runnable(vizu_context, llm=llm)`
6. Invokes chain with `{"question": query}`

### Step 2: RAG Chain Construction (`factory.py` L36-130)

```python
rag_chain = (
    RunnablePassthrough.assign(context=RunnableLambda(retrieve_and_format))
    | prompt
    | llm
    | StrOutputParser()
)
```

The chain:
1. Receives `{"question": "user query"}`
2. Calls `retrieve_and_format()` which invokes the retriever
3. Formats retrieved docs with `_format_docs()`
4. Passes `{context, question}` to the prompt template
5. Sends to LLM → returns string answer

### Step 3: Retriever calls search-documents (`retriever.py` L31-77)

```python
response = httpx.post(
    f"{self.supabase_url}/functions/v1/search-documents",
    json={
        "query": query,
        "client_id": self.client_id,
        "match_count": self.match_count,       # default 5
        "match_threshold": self.match_threshold, # default 0.5
    },
    headers={"Authorization": f"Bearer {self.supabase_service_key}"},
    timeout=30.0,
)
```

### Step 4: search-documents embeds + searches (`search-documents/index.ts` L53-72)

1. Embeds query text with `gte-small` (same model as storage)
2. Calls `vector_db.match_documents(client_id, embedding, count, threshold)`

### Step 5: `match_documents` RPC (PostgreSQL)

```sql
SELECT dc.id, dc.document_id, dc.content, dc.metadata,
       1 - (dc.embedding <=> p_query_embedding) AS similarity
FROM vector_db.document_chunks dc
WHERE dc.client_id = p_client_id
  AND dc.embedding IS NOT NULL
  AND 1 - (dc.embedding <=> p_query_embedding) > p_match_threshold
ORDER BY dc.embedding <=> p_query_embedding
LIMIT p_match_count;
```

**Returns:** `{ id, document_id, content, metadata, similarity }`

The `metadata` column returns as JSONB → serialized to JSON string by postgres.js.

### Step 6: Retriever builds LangChain Documents (`retriever.py` L64-77)

```python
Document(
    page_content=result["content"],
    metadata={
        **(json.loads(result["metadata"]) if isinstance(..., str) else ...),
        "document_id": result["document_id"],
        "similarity": result["similarity"],
    },
)
```

**Final Document.metadata contains:**
```python
{
    "source_file": "brpolen_sobre_empresa.txt",  # from chunk metadata (if object)
    "document_id": "uuid",                        # added by retriever
    "similarity": 0.907,                           # added by retriever
}
```

⚠️ Because of the double-encoding bug, `json.loads()` of the stored string returns ANOTHER string `'{"source_file":"..."}` — which then needs a SECOND `json.loads()`. The current workaround only does one level of parsing.

### Step 7: Context formatting (`factory.py` L24-29)

```python
def _format_docs(docs):
    return "\n\n---\n\n".join([d.page_content for d in docs])
```

**⚠️ METADATA IS COMPLETELY DISCARDED.** Only `page_content` is used. The `source_file`, `document_id`, and `similarity` stored in `Document.metadata` are never passed to the LLM.

### Step 8: Prompt template (`templates.py` L485-503)

```
Você é um assistente da Vizu. Use os seguintes trechos de contexto para responder à pergunta.
O contexto é soberano. Se você não sabe a resposta com base no contexto,
apenas diga que não sabe. Não tente inventar uma resposta.

CONTEXTO:
{context}

---

PERGUNTA:
{question}

RESPOSTA:
```

The prompt receives plain text context with `---` separators between chunks. No source attribution, no similarity scores, no chunk ordering information.

---

## 5. Issues Found

### 🐛 Critical

| # | Issue | Location | Impact | Status |
|---|-------|----------|--------|--------|
| C1 | **Double-encoded metadata** | `process-document/index.ts` L310 | Metadata stored as JSONB string instead of JSONB object. | ✅ **RESOLVED** — Fixed with `sql.json()`. Migration `20260305_fix_metadata_and_upgrade_match_documents.sql` |
| C2 | **Metadata lost in context formatting** | `factory.py` (`_format_docs`) | `source_file`, `document_id`, `similarity` discarded — LLM never sees source. | ✅ **RESOLVED** — `_format_docs` now renders `[Fonte: file | Relevância: 85% | Escopo: type]` headers using `_get_display_score()` with priority: `rerank_score > combined_score > similarity` |

### ⚠️ Important

| # | Issue | Location | Impact | Status |
|---|-------|----------|--------|--------|
| I1 | **Minimal chunk metadata** | `process-document/index.ts` | Only `source_file` stored. | ✅ **RESOLVED** — `process-document` now enriches with `word_cloud`, `theme`, `usage_context` via LLM (Cohere + metadata enrichment). Migration `20260310_add_metadata_columns_and_enrich_fts.sql` |
| I2 | **No document-level join in search** | `match_documents` SQL | No `file_name` / `title` in results. | ✅ **RESOLVED** — `hybrid_match_documents` joins `documents` table, returns `file_name`. |
| I3 | **Overlap contaminates content** | `process-document/index.ts` | Overlap may break sentence boundaries. | ⚠️ **MITIGATED** — Chunking now uses sentence-aware splitting (`OVERLAP_SENTENCES=2`), not character-based overlap. |
| I4 | **Chunking by chars, not tokens** | `process-document/index.ts` | Inconsistent token counts. | ✅ **RESOLVED** — Now uses `estimateTokens()` heuristic with `TARGET_TOKENS=400` (Cohere max = 512). |
| I5 | **No deduplication on re-upload** | `process-document/index.ts` | Duplicate chunks on re-upload. | ✅ **RESOLVED** — `content_hash` (SHA-256) unique constraint per `(document_id, content_hash)`. Migration `20260305_add_content_hash_deduplication.sql` |
| I6 | **Retriever uses sync httpx** | `retriever.py` | Blocks event loop in async. | ✅ **RESOLVED** — Both sync and async methods implemented in `_BaseSupabaseRetriever`. |
| I7 | **`queue_embedding_if_null` fragile search_path** | Trigger function | Empty search path is fragile. | ✅ **RESOLVED** — Trigger removed entirely (`20260310_remove_legacy_embed_infrastructure.sql`). Embedding is inline. |
| I8 | **No retry on embed failure** | `embed/index.ts` | No max-retry or DLQ. | ✅ **RESOLVED** — `embed` EF removed. Embedding is inline in `process-document`. If embedding fails, the document status is set to `failed`. |

### 💡 Minor

| # | Issue | Location | Impact | Status |
|---|-------|----------|--------|--------|
| M1 | **No attached_document_ids filtering** | `rag_module.py` / `retriever.py` | Can't scope search to specific uploaded docs. | ✅ **RESOLVED** — `HybridRetriever` supports `document_ids` filtering via `hybrid_match_documents(p_document_ids)`. |
| M2 | **Hardcoded match defaults** | `retriever.py` | No per-query tuning. | ✅ **RESOLVED** — All defaults configurable via `RagSearchConfig` per-client. Defaults: `top_k=10`, `score_threshold=0.3`. |
| M3 | **No reranking** | Pipeline | Raw cosine similarity as final ranking. | ✅ **RESOLVED** — Three reranker options: `CohereReranker` (default), `CrossEncoderReranker`, `LLMReranker`. Plus `MMRDiversifier` for result diversity. |

---

## 6. Proposed Improvements — Resolution Status

> All proposed improvements have been implemented as part of the RAG Overhaul (Phases 1–6).

### Phase A — Bug Fixes ✅ COMPLETE

| Item | Status | Resolution |
|------|--------|------------|
| A1: Fix double-encoded metadata | ✅ | `sql.json()` in `process-document`. Migration backfilled existing data. |
| A2: Include metadata in LLM context | ✅ | `_format_docs` renders `[Fonte: file | Relevância: 85% | Escopo: type]` headers. Score priority: `rerank_score > combined_score > similarity`. |

### Phase B — Richer Metadata ✅ COMPLETE

| Item | Status | Resolution |
|------|--------|------------|
| B1: Expand chunk metadata | ✅ | `process-document` enriches with `word_cloud`, `theme`, `usage_context` via LLM. |
| B2: JOIN documents in match_documents | ✅ | `hybrid_match_documents` joins `documents` table, returns `file_name`. |
| B3: document_ids filter for chat | ✅ | `HybridRetriever` supports `document_ids` via `p_document_ids` in SQL RPC. |

### Phase C — Quality Improvements ✅ COMPLETE

| Item | Status | Resolution |
|------|--------|------------|
| C1: Token-aware chunking | ✅ | `estimateTokens()` heuristic with `TARGET_TOKENS=400` (Cohere max = 512). |
| C2: Smarter overlap | ✅ | `OVERLAP_SENTENCES=2` — sentence-boundary overlap instead of character-based. |
| C3: Content deduplication | ✅ | `content_hash` (SHA-256) unique constraint. Migration `20260305_add_content_hash_deduplication.sql`. |
| C4: Async retriever | ✅ | Both sync and async methods in `_BaseSupabaseRetriever`. |
| C5: Reranking | ✅ | Three options: `CohereReranker` (default), `CrossEncoderReranker`, `LLMReranker`. Plus `MMRDiversifier`. |
| C6: Dead-letter queue for embeddings | ✅ | N/A — `embed` EF removed. Embedding is inline in `process-document`. Failure sets document status to `failed`. |

---

## 7. Data Flow Summary (Updated)

```
User uploads file
    │
    ▼
knowledgeBaseService.uploadSimpleFile()
    ├── Storage: knowledge-base/{client_id}/{uuid}-{filename}
    ├── DB: INSERT vector_db.documents (status='pending')
    └── Edge Function: process-document
            ├── Download from Storage
            ├── Parse (txt/pdf/docx/csv/json/xml/html)
            ├── Chunk (TARGET_TOKENS=400, OVERLAP_SENTENCES=2)
            ├── Embed each chunk (Cohere embed-multilingual-light-v3.0, 384d)
            ├── Enrich metadata via LLM (word_cloud, theme, usage_context)
            ├── INSERT document_chunks WITH embedding + metadata
            │       │
            │       ▼ TRIGGER: generate_fts_on_insert
            │       Auto-generates tsvector (Portuguese + unaccent)
            │
            └── UPDATE documents (status='completed', chunk_count=N)

User asks question:
    │
    ▼
rag_module._executar_rag_cliente_logic(query)
    ├── Resolve VizuClientContext
    ├── create_rag_runnable(context, llm)
    │       │
    │       ├── (Optional) QueryPreprocessor — FAST LLM rewrites query
    │       │
    │       ├── HybridRetriever (pool_size = top_k × pool_multiplier)
    │       │       POST search-documents { query, client_id, ... }
    │       │           ├── Cohere embed-multilingual-light-v3.0(query) → embedding
    │       │           └── hybrid_match_documents(embedding, query_text, ...)
    │       │               → { content, metadata, combined_score, similarity, file_name }
    │       │
    │       ├── CohereReranker → rerank_score (0–1 calibrated)
    │       │
    │       ├── MMRDiversifier → top_k diverse results
    │       │
    │       ├── _format_docs(docs) using _get_display_score()
    │       │       → "[Fonte: file.pdf | Relevância: 85% | Escopo: client]\nchunk..."
    │       │
    │       └── ChatPromptTemplate + LLM + StrOutputParser
    │
    └── Return LLM answer string
```

---

## 8. Priority Matrix — Final Status

| Priority | Item | Effort | Impact | Status |
|----------|------|--------|--------|--------|
| 🔴 P0 | A1: Fix double-encoded metadata | 1h | Data integrity | ✅ Done |
| 🔴 P0 | A2: Include metadata in LLM context | 30min | Answer quality | ✅ Done |
| 🟡 P1 | B2: JOIN documents in match_documents | 1h | Source attribution | ✅ Done |
| 🟡 P1 | B3: document_ids filter for chat | 2h | Scoped RAG | ✅ Done |
| 🟡 P1 | B1: Richer chunk metadata | 1h | Traceability | ✅ Done |
| 🟢 P2 | C4: Async retriever | 30min | Performance | ✅ Done |
| 🟢 P2 | C1: Token-aware chunking | 3h | Embedding quality | ✅ Done |
| 🟢 P2 | C2: Smarter overlap | 2h | Chunk boundary quality | ✅ Done |
| 🟢 P2 | C3: Content deduplication | 2h | Storage efficiency | ✅ Done |
| 🔵 P3 | C5: Reranking | 4h | Retrieval precision | ✅ Done |
| 🔵 P3 | C6: Dead-letter queue | 2h | Operational resilience | ✅ N/A (embed EF removed) |
