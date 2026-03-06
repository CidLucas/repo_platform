# RAG Pipeline — Metadata & Retrieval Analysis

> Generated: 2026-03-04 | Status: Active analysis with actionable improvements

---

## 1. Architecture Overview

```
┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   Frontend    │───▶│  process-document │───▶│  document_chunks   │
│  (Dashboard)  │    │  Edge Function    │    │  (vector_db)       │
└──────────────┘    └──────────────────┘    └─────────┬──────────┘
                                                      │ TRIGGER
                                                      ▼
┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐
│  rag_module   │◀──│ search-documents  │◀──│  pgmq → pg_cron    │
│ (tool_pool)   │   │  Edge Function    │   │  → embed EF        │
└──────────────┘    └──────────────────┘    └────────────────────┘
```

**Components in order of execution:**

| # | Component | Location | Role |
|---|-----------|----------|------|
| 1 | `knowledgeBaseService.ts` | `apps/vizu_dashboard/src/services/` | Upload file, create doc row, invoke Edge Function |
| 2 | `process-document` Edge Function | `supabase/functions/process-document/index.ts` | Download → parse → chunk → INSERT into `document_chunks` |
| 3 | `queue_embedding_if_null` trigger | `vector_db` schema (PostgreSQL) | On INSERT: queue each chunk to pgmq `embedding_jobs` |
| 4 | `util.process_embeddings()` | PostgreSQL function (pg_cron, 10s) | Read pgmq queue → batch → invoke `embed` Edge Function |
| 5 | `embed` Edge Function | `supabase/functions/embed/index.ts` | Generate gte-small embeddings, update chunk rows, mark doc complete |
| 6 | `search-documents` Edge Function | `supabase/functions/search-documents/index.ts` | Embed query → `match_documents()` RPC → return results |
| 7 | `SupabaseVectorRetriever` | `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | LangChain retriever — calls search-documents, returns Documents |
| 8 | `create_rag_runnable` | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | Build LangChain chain: retriever → prompt → LLM |
| 9 | `rag_module.py` | `services/tool_pool_api/src/.../tool_modules/rag_module.py` | MCP tool entry point — resolves context, invokes RAG chain |

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

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| C1 | **Double-encoded metadata** | `process-document/index.ts` L310 | Metadata stored as JSONB string instead of JSONB object. `jsonb_typeof(metadata) = 'string'`. Every consumer needs double-decode workarounds. |
| C2 | **Metadata lost in context formatting** | `factory.py` L24-29 (`_format_docs`) | `source_file`, `document_id`, `similarity` are all discarded — LLM never sees which file a chunk came from. |

### ⚠️ Important

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| I1 | **Minimal chunk metadata** | `process-document/index.ts` L292 | Only `source_file` is stored. Missing: `chunk_index`, `total_chunks`, `file_type`, `document_title`, character offsets. |
| I2 | **No document-level join in search** | `match_documents` SQL | Search returns raw `document_id` but not `file_name` or `title` from `documents` table. Consumer can't show source without extra query. |
| I3 | **Overlap contaminates content** | `process-document/index.ts` L124-128 | Overlap is prepended as raw text — may break sentence boundaries or inject partial words into embeddings. |
| I4 | **Chunking by chars, not tokens** | `process-document/index.ts` L35 | 500-char chunks may produce inconsistent token counts for gte-small (max 512 tokens). Long words/Unicode can cause truncation. |
| I5 | **No deduplication on re-upload** | `process-document/index.ts` | Re-uploading the same file creates duplicate chunks. No content hash or upsert logic. |
| I6 | **Retriever uses sync httpx** | `retriever.py` L41 | `httpx.post()` is synchronous — blocks the event loop in async contexts. Should use `httpx.AsyncClient`. |
| I7 | **`queue_embedding_if_null` has `SET search_path TO ''`** | Trigger function | The empty search path works because it fully qualifies `pgmq.send`, but it's fragile. Should match the pattern used in `match_documents` (`'extensions', 'vector_db', 'public'`). |
| I8 | **No retry on embed failure** | `embed/index.ts` | Failed jobs are logged but the pgmq message visibility timeout eventually expires and the job is retried by pgmq — but there's no max-retry or dead-letter queue logic. |

### 💡 Minor

| # | Issue | Location | Impact |
|---|-------|----------|--------|
| M1 | **No attached_document_ids filtering** | `rag_module.py` / `retriever.py` | ChatPanel passes `attached_document_ids` in context but RAG search ignores them — can't scope search to specific uploaded docs. |
| M2 | **Hardcoded match defaults** | `retriever.py` L26-27 | `match_count=5` and `match_threshold=0.5` are hardcoded defaults; no per-query tuning from tool_pool. |
| M3 | **No reranking** | Pipeline | Raw cosine similarity used as final ranking. No cross-encoder reranking step. |

---

## 6. Proposed Improvements

### Phase A — Bug Fixes (Immediate)

#### A1. Fix double-encoded metadata
**File:** `supabase/functions/process-document/index.ts` L310

```typescript
// BEFORE (buggy):
${JSON.stringify(chunk.metadata)}::jsonb

// AFTER (correct):
${sql.json(chunk.metadata)}
```

Then fix existing data:
```sql
UPDATE vector_db.document_chunks
SET metadata = metadata::text::jsonb
WHERE jsonb_typeof(metadata) = 'string';
```

#### A2. Include metadata in LLM context
**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`

```python
def _format_docs(docs):
    if not docs:
        return "Nenhum contexto encontrado."
    parts = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source_file", "desconhecido")
        similarity = doc.metadata.get("similarity", 0)
        parts.append(
            f"[Fonte: {source} | Relevância: {similarity:.0%}]\n{doc.page_content}"
        )
    return "\n\n---\n\n".join(parts)
```

### Phase B — Richer Metadata (Short-term)

#### B1. Expand chunk metadata in process-document

```typescript
const chunks = chunkText(parsedText, {
    source_file: fileName,
    file_type: fileType,
    document_id: documentId,
    document_title: fileName.replace(/\.[^.]+$/, ''),
    total_chars: parsedText.length,
});

// In chunkText, add per-chunk fields:
chunks.push({
    text: currentChunk.trim(),
    index: chunkIndex++,
    metadata: {
        ...metadata,
        chunk_index: chunkIndex,
        char_start: charOffset,
        char_end: charOffset + currentChunk.length,
    },
});
```

#### B2. JOIN documents table in match_documents

```sql
CREATE OR REPLACE FUNCTION vector_db.match_documents(...)
RETURNS TABLE(
    id integer, document_id uuid, content text,
    metadata jsonb, similarity double precision,
    file_name text, document_title text  -- NEW
)
AS $$
  SELECT dc.id, dc.document_id, dc.content, dc.metadata,
         1 - (dc.embedding <=> p_query_embedding) AS similarity,
         d.file_name, d.title AS document_title
  FROM vector_db.document_chunks dc
  JOIN vector_db.documents d ON d.id = dc.document_id
  WHERE dc.client_id = p_client_id
    AND dc.embedding IS NOT NULL
    AND d.status = 'completed'
    AND 1 - (dc.embedding <=> p_query_embedding) > p_match_threshold
  ORDER BY dc.embedding <=> p_query_embedding
  LIMIT p_match_count;
$$;
```

#### B3. Support document_ids filter for chat context

Add optional `document_ids` parameter to `search-documents` and `match_documents`:

```sql
-- In match_documents:
AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
```

### Phase C — Quality Improvements (Medium-term)

#### C1. Token-aware chunking
Replace char-based chunking (500 chars) with token-based chunking using a tokenizer compatible with gte-small's tokenizer (512 token max).

#### C2. Smarter overlap
Instead of raw character overlap, overlap at sentence boundaries to avoid mid-word splits.

#### C3. Content deduplication
Add a `content_hash` column (SHA-256 of content) with a unique constraint per `(document_id, content_hash)` to prevent duplicate chunks on re-upload.

#### C4. Async retriever
Replace `httpx.post()` with `httpx.AsyncClient.post()` and implement `_aget_relevant_documents()` in the retriever for proper async support.

#### C5. Reranking
Add an optional cross-encoder reranking step after initial vector search to improve precision for top-K results.

#### C6. Dead-letter queue for failed embeddings
Track retry count in pgmq message metadata. After N failures, move to a dead-letter queue and mark the document as `'partially_failed'`.

---

## 7. Data Flow Summary

```
User uploads file
    │
    ▼
knowledgeBaseService.uploadSimpleFile()
    ├── Storage: knowledge-base/{client_id}/{uuid}-{filename}
    ├── DB: INSERT vector_db.documents (status='processing')
    └── Edge Function: process-document
            ├── Download from Storage
            ├── Parse (txt/pdf/docx/csv/json/xml/html)
            ├── Chunk (500 chars, 50 overlap)
            │   metadata = { source_file: fileName }  ← ONLY FIELD
            ├── INSERT document_chunks (embedding=NULL)
            │       │
            │       ▼ TRIGGER: queue_embedding_if_null
            │       pgmq.send('embedding_jobs', {id, schema, table, ...})
            │
            └── UPDATE documents (status='processing', chunk_count=N)

Every 10 seconds (pg_cron):
    util.process_embeddings()
        ├── pgmq.read('embedding_jobs', batch=10)
        └── invoke embed Edge Function
                ├── chunk_content_fn(row) → content text
                ├── gte-small → 384-dim halfvec
                ├── UPDATE document_chunks SET embedding = ...
                └── IF all chunks embedded → UPDATE documents SET status='completed'

User asks question:
    │
    ▼
rag_module._executar_rag_cliente_logic(query)
    ├── Resolve VizuClientContext
    ├── create_rag_runnable(context, llm)
    │       ├── SupabaseVectorRetriever
    │       │       POST search-documents { query, client_id, match_count, threshold }
    │       │           ├── gte-small(query) → embedding
    │       │           └── match_documents(client_id, embedding, count, threshold)
    │       │               → { id, document_id, content, metadata, similarity }
    │       │
    │       ├── _format_docs(docs)
    │       │       → "chunk1\n\n---\n\nchunk2\n\n---\n\nchunk3"
    │       │         ⚠️ metadata discarded here
    │       │
    │       └── ChatPromptTemplate + LLM + StrOutputParser
    │
    └── Return LLM answer string
```

---

## 8. Priority Matrix

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| 🔴 P0 | A1: Fix double-encoded metadata | 1h | Data integrity |
| 🔴 P0 | A2: Include metadata in LLM context | 30min | Answer quality — LLM can cite sources |
| 🟡 P1 | B2: JOIN documents in match_documents | 1h | Source attribution in search results |
| 🟡 P1 | B3: document_ids filter for chat | 2h | Scoped RAG for attached files |
| 🟡 P1 | B1: Richer chunk metadata | 1h | Better traceability |
| 🟢 P2 | C4: Async retriever | 30min | Performance under load |
| 🟢 P2 | C1: Token-aware chunking | 3h | Embedding quality |
| 🟢 P2 | C2: Smarter overlap | 2h | Chunk boundary quality |
| 🟢 P2 | C3: Content deduplication | 2h | Storage efficiency |
| 🔵 P3 | C5: Reranking | 4h | Retrieval precision |
| 🔵 P3 | C6: Dead-letter queue | 2h | Operational resilience |
