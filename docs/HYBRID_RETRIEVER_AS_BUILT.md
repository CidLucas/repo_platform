# Hybrid Retriever — As-Built Documentation

> **Last updated:** 2026-03-06
> **Migration:** `20260305_hybrid_retriever_schema.sql`
> **Status:** Production-ready (Phase 1 + Phase 2 complete)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [End-to-End Data Flow](#2-end-to-end-data-flow)
   - [Document Ingestion Flow](#21-document-ingestion-flow)
   - [Query / Retrieval Flow](#22-query--retrieval-flow)
3. [Database Layer (Supabase / PostgreSQL)](#3-database-layer)
4. [Edge Functions (Deno)](#4-edge-functions)
5. [Python RAG Pipeline](#5-python-rag-pipeline)
6. [Frontend (vizu_dashboard)](#6-frontend)
7. [Configuration & Tuning Reference](#7-configuration--tuning-reference)
8. [Prompt Management](#8-prompt-management)
9. [Seeding Platform Knowledge](#9-seeding-platform-knowledge)
10. [Tests](#10-tests)
11. [File Index](#11-file-index)

---

## 1. Architecture Overview

```
┌──────────────┐     ┌────────────────────┐     ┌─────────────────────┐
│   Frontend   │────▶│  Supabase Storage  │     │  Supabase Edge Fns  │
│  (React/CUI) │     │  knowledge-base/   │     │                     │
└──────────────┘     └────────────────────┘     │  process-document   │
       │                                         │  search-documents   │
       │   REST / Supabase JS                    │  enrich-metadata    │
       ▼                                         └─────────┬───────────┘
┌──────────────┐                                           │
│ Python Agent │◀── create_rag_runnable() ────────────────▶│
│ (LangChain)  │     factory.py                            │
└──────┬───────┘                                           │
       │                                                   │
       │  HTTP POST (service_role key)                     │
       ▼                                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                    PostgreSQL (Supabase)                      │
│                                                              │
│  vector_db.documents          vector_db.document_chunks      │
│  ┌──────────────────┐         ┌──────────────────────────┐   │
│  │ id, client_id    │  1───N  │ id, document_id          │   │
│  │ scope, category  │─────────│ content, embedding       │   │
│  │ status, file_name│         │ fts (tsvector), metadata │   │
│  └──────────────────┘         │ scope, category          │   │
│                               └──────────────────────────┘   │
│                                                              │
│  RPCs: match_documents, hybrid_match_documents               │
│  Queues: pgmq (metadata_jobs, metadata_jobs_dlq)            │
│  Cron: pg_cron → util.process_metadata (every 30s)          │
└──────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **halfvec(384)** instead of vector(384) | 2× less storage, HNSW index fits in memory |
| **gte-small** (built-in Supabase AI) | Zero-cost embedding, runs in Edge Runtime |
| **Portuguese tsvector** + `immutable_unaccent` | Brazilian-Portuguese keyword search with accent tolerance |
| **pgmq** for async pipelines | Reliable queue with retry/DLQ, no external infra |
| **Scope (platform/client)** | Shared knowledge accessible to all clients without duplication |
| **Cross-encoder reranker** (default) | Faster + cheaper than LLM reranking, better accuracy |

---

## 2. End-to-End Data Flow

### 2.1 Document Ingestion Flow

```
User uploads file via Dashboard
         │
         ▼
┌─────────────────────────┐
│ knowledgeBaseService.ts  │  uploadFile()
│ apps/vizu_dashboard/     │  1. Stores file in Supabase Storage (knowledge-base bucket)
│ src/services/            │  2. INSERTs row into vector_db.documents (status='pending')
│ knowledgeBaseService.ts  │  3. Invokes process-document Edge Function
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ process-document EF      │  supabase/functions/process-document/index.ts
│                          │  1. Downloads file from Storage
│                          │  2. Parses (PDF/DOCX/CSV/TXT/MD/JSON/XML/HTML)
│                          │  3. Chunks with token-aware splitter (TARGET=400 tokens, overlap=2 sentences)
│                          │  4. INSERTs chunks into document_chunks (embedding=NULL)
│                          │  5. Updates documents.status = 'processing'
└────────────┬────────────┘
             │  (INSERT trigger fires)
             ▼
┌─────────────────────────┐
│ DB Trigger:              │
│ generate_fts_on_insert   │  → Generates tsvector (Portuguese + unaccent)
│ embed_on_insert (*)      │  → Queues chunk to embed-documents pgmq queue
│ enrich_metadata_on_insert│  → Queues chunk to metadata_jobs pgmq queue
└────────────┬────────────┘
             │  (pg_cron every 30s)
             ▼
┌─────────────────────────┐
│ pg_cron: process_metadata│  util.process_metadata(batch_size=10, max_requests=5)
│                          │  Reads metadata_jobs queue → batches → invokes enrich-metadata EF
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ enrich-metadata EF       │  supabase/functions/enrich-metadata/index.ts
│                          │  1. Calls OpenAI gpt-4.1-mini (configurable via env)
│                          │  2. Extracts: word_cloud, theme, usage_context
│                          │  3. Merges into chunk metadata JSONB
│                          │  4. On failure: retry (max 3) or → metadata_jobs_dlq
│                          │  Concurrency: 5 parallel LLM calls per batch
└─────────────────────────┘
```

> (*) The `embed_on_insert` trigger and embedding Edge Function are part of the base vector_db schema (pre-existing), not part of this hybrid retriever migration.

### 2.2 Query / Retrieval Flow

```
Agent receives user question
         │
         ▼
┌─────────────────────────┐
│ factory.py               │  create_rag_runnable()
│ vizu_rag_factory         │  1. Reads RagSearchConfig from client context
│                          │  2. Creates HybridRetriever or SupabaseVectorRetriever
│                          │  3. Optionally creates a reranker (CrossEncoder or LLM)
│                          │  4. Builds LangChain Runnable chain
└────────────┬────────────┘
             │  .invoke({"question": "..."})
             ▼
┌─────────────────────────┐
│ retriever.py             │  HybridRetriever._build_payload() + HTTP POST
│ _BaseSupabaseRetriever   │  → POST /functions/v1/search-documents
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ search-documents EF      │  supabase/functions/search-documents/index.ts
│                          │  1. Validates input (search_mode, fusion_strategy, etc.)
│                          │  2. Embeds query via gte-small (built-in)
│                          │  3. Routes to SQL RPC:
│                          │     - semantic → match_documents (cosine only)
│                          │     - hybrid  → hybrid_match_documents (fusion)
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ hybrid_match_documents   │  SQL RPC (plpgsql)
│                          │  1. Semantic CTE: cosine similarity via HNSW index
│                          │  2. Keyword CTE: ts_rank_cd via GIN index
│                          │  3. Merge + deduplicate candidates
│                          │  4. Score fusion (RRF or weighted linear)
│                          │  5. Return top N by combined_score
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ (Optional) Reranker      │  reranker.py — CrossEncoderReranker or LLMReranker
│                          │  Re-scores top candidates, returns top_k best
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ _format_docs → prompt    │  factory.py — Formats context with source/score headers
│ → LLM → StrOutputParser  │  RAG_TOOL_PROMPT template fills {context} + {question}
│                          │  LLM generates grounded answer
└─────────────────────────┘
```

---

## 3. Database Layer

**Migration file:** `supabase/migrations/20260305_hybrid_retriever_schema.sql`

### 3.1 Schema Changes

#### `vector_db.documents` — new columns

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `scope` | `TEXT NOT NULL` | `'client'` | `'platform'` (shared) or `'client'` (tenant-owned) |
| `description` | `TEXT` | NULL | Human description of the document |
| `category` | `TEXT` | NULL | Categorical tag (e.g. `tax_knowledge`, `dados_negocio`) |

**Constraints:** `scope = 'client' → client_id IS NOT NULL`, `scope = 'platform' → client_id IS NULL`
**Indexes:** `idx_documents_scope`, `idx_documents_category`

#### `vector_db.document_chunks` — new columns

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `scope` | `TEXT NOT NULL` | `'client'` | Denormalized from parent document |
| `category` | `TEXT` | NULL | Denormalized from parent document |
| `fts` | `TSVECTOR` | auto-generated | Full-text search vector (Portuguese + unaccent) |

**Indexes:**
- `idx_chunks_scope` — B-tree on `scope`
- `idx_chunks_category` — B-tree on `category`
- `idx_chunks_scope_client` — Composite on `(scope, client_id) WHERE embedding IS NOT NULL`
- `idx_chunks_fts` — GIN on `fts` for full-text search

### 3.2 Functions & Triggers

| Name | Type | Purpose | Location |
|------|------|---------|----------|
| `vector_db.immutable_unaccent(text)` | Function | Immutable wrapper for `extensions.unaccent()` — required for index expressions | Migration L87-89 |
| `vector_db.generate_fts()` | Trigger function | Generates `tsvector` on INSERT or content UPDATE | Migration L98-106 |
| `generate_fts_on_insert_or_update` | Trigger | Fires BEFORE INSERT/UPDATE OF content on document_chunks | Migration L108-111 |
| `vector_db.queue_metadata_if_null()` | Trigger function | Queues chunk to pgmq `metadata_jobs` if word_cloud not set | Migration L321-337 |
| `enrich_metadata_on_insert` | Trigger | Fires AFTER INSERT on document_chunks | Migration L339-342 |
| `util.process_metadata()` | Function | Reads pgmq queue, batches jobs, invokes enrich-metadata EF via pg_net | Migration L345-380 |

### 3.3 RPC: `hybrid_match_documents`

**Signature:**
```sql
vector_db.hybrid_match_documents(
  p_client_id       UUID,
  p_query_embedding halfvec(384),
  p_query_text      TEXT,
  p_match_count     INT     DEFAULT 5,
  p_match_threshold FLOAT   DEFAULT 0.5,
  p_document_ids    UUID[]  DEFAULT NULL,
  p_scope           TEXT[]  DEFAULT '{platform,client}',
  p_categories      TEXT[]  DEFAULT NULL,
  p_fusion_strategy TEXT    DEFAULT 'rrf',
  p_keyword_weight  FLOAT   DEFAULT 0.4,
  p_vector_weight   FLOAT   DEFAULT 0.6
)
```

**Algorithm (4 CTEs):**
1. **`semantic`** — Cosine similarity via HNSW index. Filters by scope, client_id, status, threshold. Fetches `match_count × 3` candidates.
2. **`keyword`** — `ts_rank_cd` via GIN index using `websearch_to_tsquery('portuguese', ...)`. Same filters. Fetches `match_count × 3` candidates.
3. **`merged`** — UNION ALL + GROUP BY to deduplicate and take best rank from each method.
4. **`scored`** — Applies fusion:
   - **RRF:** `1/(60+sem_rank) + 1/(60+kw_rank)` (k=60)
   - **Weighted:** `vector_weight * similarity + keyword_weight * min(keyword_score * 10, 1.0)`
5. Final: ORDER BY `combined_score` DESC, LIMIT `match_count`.

### 3.4 RLS Policies

| Policy | Table | Rule |
|--------|-------|------|
| `Users can view own or platform documents` | `documents` | `scope = 'platform' OR client_id = auth.uid()` |
| `Users can view own or platform chunks` | `document_chunks` | `scope = 'platform' OR client_id = auth.uid()` |

### 3.5 pgmq Queues

| Queue | Purpose | Consumer |
|-------|---------|----------|
| `metadata_jobs` | Chunks needing metadata enrichment | `enrich-metadata` EF (via pg_cron) |
| `metadata_jobs_dlq` | Failed after 3 retries | Manual inspection |

**Cron schedule:** `process-metadata` runs every **30 seconds**, batch_size=10, max_requests=5.

---

## 4. Edge Functions

### 4.1 `process-document`

**File:** `supabase/functions/process-document/index.ts` (~470 lines)
**Endpoint:** `POST /functions/v1/process-document`

**Request body:**
```json
{
  "document_id": "uuid",
  "storage_path": "client_id/filename.pdf",
  "client_id": "uuid",
  "file_name": "report.pdf",
  "file_type": "pdf"
}
```

**Key functions:**

| Function | Line | Purpose |
|----------|------|---------|
| `estimateTokens(text)` | ~34 | Heuristic token count (~3.5 chars/token Latin, ~1 CJK) |
| `splitIntoSentences(text)` | ~51 | Regex split on sentence boundaries and paragraph breaks |
| `chunkText(text, metadata)` | ~58 | Token-aware chunking. TARGET_TOKENS=400, OVERLAP_SENTENCES=2 |
| `parsePdf(data)` | ~165 | PDF → text via `pdf-parse` |
| `parseDocx(data)` | ~178 | DOCX → text via `mammoth` |
| `parseCsv(data)` | ~125 | CSV → "header: value" per row |
| `parseTxtMd(data)` | ~120 | Plain text / Markdown passthrough |
| `parseJson(data)` | ~135 | JSON → structured text |
| `parseXmlHtml(data)` | ~148 | Strip tags, collapse whitespace |
| `getParser(fileType)` | ~183 | Router: file extension → parser function |
| `processDocument(...)` | ~200 | Main pipeline: download → parse → chunk → INSERT |

**Tuning parameters:**
- `TARGET_TOKENS = 400` — Target tokens per chunk (gte-small max is 512)
- `OVERLAP_SENTENCES = 2` — Sentence overlap between chunks

**To change:** Edit constants at the top of the file.

### 4.2 `search-documents`

**File:** `supabase/functions/search-documents/index.ts` (~170 lines)
**Endpoint:** `POST /functions/v1/search-documents`

**Request body:**
```json
{
  "query": "What are the tax rates?",
  "client_id": "uuid",
  "match_count": 5,
  "match_threshold": 0.5,
  "search_mode": "hybrid",
  "fusion_strategy": "rrf",
  "keyword_weight": 0.4,
  "vector_weight": 0.6,
  "scope": ["platform", "client"],
  "categories": null,
  "document_ids": null
}
```

**Validation:**
- Required: `query`, `client_id`
- `search_mode` must be `"semantic"` or `"hybrid"`
- `fusion_strategy` must be `"rrf"` or `"weighted"`

**Routing:**
- `search_mode === "semantic"` → calls `match_documents` RPC (legacy cosine-only)
- `search_mode === "hybrid"` → calls `hybrid_match_documents` RPC (fusion)

**Embedding:** Uses Supabase built-in `Supabase.ai.Session("gte-small")` — no external API call.

### 4.3 `enrich-metadata`

**File:** `supabase/functions/enrich-metadata/index.ts` (~263 lines)
**Endpoint:** `POST /functions/v1/enrich-metadata` (called internally by pg_cron)

**Input:** Array of `MetadataJob` objects from pgmq.

**LLM Config (env-driven, defaults from `vizu_llm_service.LLMSettings`):**

| Env Variable | Default | Description |
|---|---|---|
| `METADATA_ENRICHMENT_MODEL` | `gpt-4.1-mini` | OpenAI model |
| `METADATA_ENRICHMENT_MAX_TOKENS` | `500` | Max response tokens |
| `METADATA_ENRICHMENT_TEMPERATURE` | `0` | Deterministic output |
| `METADATA_ENRICHMENT_SYSTEM_PROMPT` | (built-in) | Override the entire system prompt |

**Extracted metadata:**
```json
{
  "word_cloud": ["receita", "tributação", "IRPJ", ...],
  "theme": "tax_regulation",
  "usage_context": "Útil quando o usuário pergunta sobre alíquotas de IRPJ."
}
```

**Allowed themes:** `statistical_analysis`, `tax_regulation`, `business_operations`, `financial_reporting`, `data_engineering`, `customer_service`, `product_knowledge`, `legal_compliance`, `market_analysis`, `human_resources`, `sales_strategy`, `operational_procedures`, `general`

**Concurrency:** Processes up to **5 LLM calls in parallel** per batch (`Promise.allSettled`).

**Retry logic:** Up to `MAX_RETRIES=3`. On exhaustion → dead-letter queue (`metadata_jobs_dlq`).

**To change the theme vocabulary:** Edit `ALLOWED_THEMES` Set in the EF **and** update `METADATA_ENRICHMENT_PROMPT` in `vizu_prompt_management/templates.py`.

---

## 5. Python RAG Pipeline

### 5.1 Library: `vizu_rag_factory`

**Location:** `libs/vizu_rag_factory/`
**pyproject.toml:** `libs/vizu_rag_factory/pyproject.toml`
**Dependencies:** `langchain-core`, `sentence-transformers`, `httpx`, `vizu_llm_service`, `vizu_context_service`, `vizu_models`, `vizu_prompt_management`

#### Module: `retriever.py`

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` (~247 lines)

**Class hierarchy:**

```
BaseRetriever (LangChain)
  └── _BaseSupabaseRetriever (private base)
        ├── SupabaseVectorRetriever   (semantic-only)
        └── HybridRetriever           (hybrid fusion)
```

| Class | Purpose | Key Override |
|-------|---------|-------------|
| `_BaseSupabaseRetriever` | Shared HTTP logic, sync/async retrieval, auth headers | — |
| `SupabaseVectorRetriever` | Pure cosine-similarity search | `_build_payload()` — sends basic params |
| `HybridRetriever` | Semantic + keyword fusion | `_build_payload()` — adds `search_mode`, `fusion_strategy`, weights, `scope`, `categories` |

**Helper functions:**
- `_parse_result_metadata(result)` — Parses JSONB metadata (handles double-encoded strings from legacy data)
- `_build_documents(results)` — Converts Edge Function JSON response to LangChain `Document` objects

**HTTP call:** Both classes POST to `{supabase_url}/functions/v1/search-documents` with `Bearer {service_role_key}`. Timeout: 30s.

#### Module: `reranker.py`

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py` (~295 lines)

| Class | Strategy | Model | Speed | Accuracy |
|-------|----------|-------|-------|----------|
| `CrossEncoderReranker` | Cross-encoder scoring | `BAAI/bge-reranker-v2-m3` (278M params) | Fast (~10ms/doc) | High |
| `LLMReranker` | LLM prompt scoring (0-10) | Any `BaseChatModel` (FAST tier) | Slower (~200ms/doc) | Good |

**CrossEncoderReranker details:**
- Model loaded as **module-level singleton** with double-checked locking (`_cross_encoder_lock`)
- First call triggers download (~1.1 GB) from HuggingFace
- Async: runs inference in thread pool via `asyncio.to_thread()`
- Default device: `cpu` (can set to `cuda` / `mps`)
- Passage truncation: 1500 chars

**LLMReranker details:**
- Uses `RAG_RERANK_PROMPT` from `vizu_prompt_management`
- Scores all docs concurrently via `asyncio.gather()`
- Fallback on scoring failure: `similarity × 10`
- Sync wrapper handles nested event loops safely

**To change the reranker model:** Instantiate `CrossEncoderReranker(model_name="your/model")`.

#### Module: `factory.py`

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` (~220 lines)

**Main entry point:** `create_rag_runnable(contexto, llm, document_ids=None) → Runnable | None`

**Flow:**
1. Validates LLM is provided
2. Checks `"executar_rag_cliente"` is in `contexto.enabled_tools`
3. Parses `RagSearchConfig` from `contexto.available_tools["rag_search_config"]`
4. Creates retriever: `HybridRetriever` (default) or `SupabaseVectorRetriever` (if `search_mode == "semantic"`)
5. Optionally creates reranker: `CrossEncoderReranker` (default) or `LLMReranker`
6. Builds LangChain chain:

```python
RunnablePassthrough.assign(context=retrieval_runnable) | prompt | llm | StrOutputParser()
```

**Helper:** `_format_docs(docs)` — Formats retrieved documents with headers:
```
[Fonte: arquivo.pdf | Relevância: 82% | Escopo: client]
<chunk content>
```

**Environment variables required:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

#### Module: `__init__.py`

**Exports:** `create_rag_runnable`, `CrossEncoderReranker`, `HybridRetriever`, `LLMReranker`, `SupabaseVectorRetriever`

### 5.2 Configuration Model: `RagSearchConfig`

**File:** `libs/vizu_models/src/vizu_models/knowledge_base_config.py`
**Class:** `RagSearchConfig(BaseModel)`

Stored in `clientes_vizu.available_tools.rag_search_config` (JSONB).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `top_k` | `int` | `5` | Number of results to return |
| `score_threshold` | `float` | `0.5` | Minimum similarity threshold |
| `rerank` | `bool` | `False` | Enable reranking step |
| `rerank_top_k` | `int` | `3` | Final documents after reranking |
| `search_mode` | `Literal` | `"hybrid"` | `"semantic"`, `"keyword"`, or `"hybrid"` |
| `fusion_strategy` | `Literal` | `"rrf"` | `"rrf"` or `"weighted"` |
| `keyword_weight` | `float` | `0.4` | Keyword score weight (weighted fusion) |
| `vector_weight` | `float` | `0.6` | Vector similarity weight (weighted fusion) |
| `scope` | `list[str]` | `["platform", "client"]` | Which scopes to search |
| `categories` | `list[str] \| None` | `None` | Filter by category |
| `reranker_type` | `Literal` | `"cross-encoder"` | `"cross-encoder"` or `"llm"` |

**To tune per-client:** Update the `rag_search_config` key in the client's `available_tools` JSONB column in the `clientes_vizu` table.

### 5.3 LLM Configuration

**File:** `libs/vizu_llm_service/src/vizu_llm_service/config.py`
**Class:** `LLMSettings(BaseSettings)`

Relevant fields for the hybrid retriever:

| Field | Default | Used By |
|-------|---------|---------|
| `METADATA_ENRICHMENT_MODEL` | `gpt-4.1-mini` | `enrich-metadata` EF (via env var) |
| `METADATA_ENRICHMENT_MAX_TOKENS` | `500` | `enrich-metadata` EF (via env var) |
| `METADATA_ENRICHMENT_TEMPERATURE` | `0.0` | `enrich-metadata` EF (via env var) |

These are set as environment variables for the Supabase Edge Functions (they can't import Python). The Python `LLMSettings` is the **source of truth** for default values.

---

## 6. Frontend

### 6.1 Knowledge Base Service

**File:** `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` (~311 lines)

| Function | Purpose |
|----------|---------|
| `listDocuments(clientId)` | `SELECT * FROM vector_db.documents WHERE client_id = ?` |
| `uploadFile(file, clientId, forceComplex, source, options)` | Stores file → INSERT document → invoke `process-document` EF |
| `deleteDocument(docId, storagePath)` | Deletes chunks + document + storage file |
| `getEmbeddingProgress(documentId)` | Returns `{total_chunks, embedded_chunks, progress_pct}` |
| `isComplexFile(fileName, forceComplex)` | Decides if file needs Python/docling processing |

**Types:** `KBDocument`, `UploadOptions`, `EmbeddingProgress`
**Categories constant:** `KB_CATEGORIES` — user-facing category labels for document upload.

### 6.2 Knowledge Base Hook

**File:** `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts` (~116 lines)

| Export | Purpose |
|--------|---------|
| `useKnowledgeBase()` | Returns `{ documents, loading, uploading, error, upload, remove, refresh }` |

**Auto-polling:** When any document has `status === "pending" || "processing"`, the hook polls every **5 seconds** until all documents are completed/failed.

### 6.3 Admin Page

**File:** `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx` (~549 lines)

**UI Features:**
- Document table with status badges, file type icons, chunk count
- Upload modal with description text area + category select
- Bulk delete with checkboxes
- Enriched metadata display (word_cloud tags, theme badge)
- Progress bar for embedding status

---

## 7. Configuration & Tuning Reference

### 7.1 Quick Tuning Guide

| What to tune | Where | Default | Effect |
|---|---|---|---|
| **Result count** | `RagSearchConfig.top_k` | 5 | More results = broader context, slower |
| **Similarity threshold** | `RagSearchConfig.score_threshold` | 0.5 | Higher = stricter, fewer results |
| **Enable reranking** | `RagSearchConfig.rerank` | `false` | Significantly improves relevance |
| **Reranker type** | `RagSearchConfig.reranker_type` | `"cross-encoder"` | `"llm"` for no model download |
| **Rerank top-K** | `RagSearchConfig.rerank_top_k` | 3 | Final doc count after reranking |
| **Search mode** | `RagSearchConfig.search_mode` | `"hybrid"` | `"semantic"` for pure vector search |
| **Fusion strategy** | `RagSearchConfig.fusion_strategy` | `"rrf"` | `"weighted"` for tunable score weights |
| **Keyword weight** | `RagSearchConfig.keyword_weight` | 0.4 | Higher = more keyword influence |
| **Vector weight** | `RagSearchConfig.vector_weight` | 0.6 | Higher = more semantic influence |
| **Scope** | `RagSearchConfig.scope` | `["platform", "client"]` | Remove `"platform"` to search only client docs |
| **Category filter** | `RagSearchConfig.categories` | `null` | e.g. `["tax_knowledge"]` to scope to a domain |
| **Chunk size** | `process-document: TARGET_TOKENS` | 400 | Bigger = more context per chunk, less precision |
| **Chunk overlap** | `process-document: OVERLAP_SENTENCES` | 2 | More overlap = better continuity, more chunks |
| **Metadata enrichment model** | Env: `METADATA_ENRICHMENT_MODEL` | `gpt-4.1-mini` | Upgrade for better theme/tag quality |
| **Metadata batch interval** | pg_cron SQL | 30 seconds | More frequent = faster enrichment, more load |
| **LLM reranker prompt** | `RAG_RERANK_PROMPT` in templates.py | (see §8) | Improve scoring instructions |
| **RAG answer prompt** | `RAG_TOOL_PROMPT` in templates.py | (see §8) | Change how the LLM uses context |
| **Frontend poll interval** | `useKnowledgeBase: POLL_INTERVAL_MS` | 5000ms | Speed vs. network cost |

### 7.2 Per-Client Configuration

Each client's RAG behavior is controlled by the JSON stored in:

```sql
UPDATE clientes_vizu
SET available_tools = jsonb_set(
  available_tools,
  '{rag_search_config}',
  '{
    "top_k": 8,
    "score_threshold": 0.4,
    "rerank": true,
    "rerank_top_k": 5,
    "search_mode": "hybrid",
    "fusion_strategy": "rrf",
    "scope": ["platform", "client"],
    "categories": ["dados_negocio", "tax_knowledge"],
    "reranker_type": "cross-encoder"
  }'::jsonb
)
WHERE client_id = 'your-client-uuid';
```

Missing fields fall back to `RagSearchConfig` defaults — **all fields are optional**.

### 7.3 Fusion Strategy Details

**RRF (Reciprocal Rank Fusion)** — `k = 60`
- Score = `1/(60 + semantic_rank) + 1/(60 + keyword_rank)`
- Rank-based, magnitude-agnostic
- Best when scores across methods aren't comparable
- **Recommended for general use**

**Weighted Linear**
- Score = `vector_weight × similarity + keyword_weight × min(keyword_score × 10, 1.0)`
- Score-based, requires comparable magnitudes
- The `× 10` normalizer on keyword_score accounts for ts_rank_cd typically producing small values
- Best when you want explicit control over semantic vs. keyword balance

---

## 8. Prompt Management

All RAG-related prompts are centralized in `vizu_prompt_management`:

**File:** `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py`

| Constant | Langfuse Name | Used By | Variables |
|----------|---------------|---------|-----------|
| `RAG_TOOL_PROMPT` | `tool/rag-query` | `factory.py` — main RAG answer template | `{context}`, `{question}` |
| `RAG_RERANK_PROMPT` | `rag/rerank` | `reranker.py` — LLMReranker scoring | `{question}`, `{passage}` |
| `METADATA_ENRICHMENT_PROMPT` | `rag/metadata-enrichment` | `enrich-metadata` EF (reference copy) | `{content}` |

**How to edit prompts:**
1. Edit the `content` field of the `PromptTemplateConfig` in `templates.py`
2. For `RAG_TOOL_PROMPT` and `RAG_RERANK_PROMPT`: The Python code picks up changes automatically on next deploy
3. For `METADATA_ENRICHMENT_PROMPT`: Also update the matching `SYSTEM_PROMPT` in `enrich-metadata/index.ts` (or set `METADATA_ENRICHMENT_SYSTEM_PROMPT` env var to override without code change)

**Prompt sync note:** The enrich-metadata Edge Function has its own copy of the system prompt because it runs in Deno (can't import Python). The `METADATA_ENRICHMENT_PROMPT` in Python is the **documentation source of truth**. Keep both in sync.

---

## 9. Seeding Platform Knowledge

**Script:** `scripts/seed_platform_knowledge.py` (~301 lines)

**Purpose:** Uploads curated markdown files as platform-scoped documents (shared across all clients).

**Usage:**
```bash
python scripts/seed_platform_knowledge.py            # Seed all documents
python scripts/seed_platform_knowledge.py --dry-run   # Preview without changes
python scripts/seed_platform_knowledge.py --category tax_knowledge  # Seed specific category
```

**Document manifest:** Defined in `DOCUMENTS` list in the script. Each entry specifies `filename`, `category`, `description`, `title`.

**Source files:** `seeds/platform_knowledge/` directory.

**Flow:** For each document:
1. Check if already exists (by `file_name` + `scope='platform'`)
2. Upload to Supabase Storage under `platform/` prefix
3. INSERT into `vector_db.documents` with `scope='platform'`, `client_id=NULL`
4. Invoke `process-document` Edge Function
5. Automated pipeline handles: chunking → embedding → metadata enrichment

**Deduplication:** Uses `content_hash` (SHA-256) unique constraint per `(document_id, content_hash)`. Re-uploads update existing chunks.

---

## 10. Tests

**Test directory:** `libs/vizu_rag_factory/tests/unit/`

| Test File | Coverage | Tests |
|-----------|----------|-------|
| `test_retriever.py` | `SupabaseVectorRetriever` + `HybridRetriever` | 7 tests: sync/async retrieval, payload params, category/doc filters, empty results, HTTP errors |
| `test_reranker.py` | `CrossEncoderReranker` + `LLMReranker` + factory selection | 11 tests: sort, top_k, empty, single doc, truncation, async, metadata preservation, factory wiring |
| `test_factory.py` | `create_rag_runnable` | 2 tests: success path + disabled tool |

**Run tests:**
```bash
poetry run pytest libs/vizu_rag_factory/tests/ -v
```

---

## 11. File Index

### Database

| File | Purpose |
|------|---------|
| `supabase/migrations/20260305_hybrid_retriever_schema.sql` | Schema: scope, FTS, hybrid RPC, metadata pipeline, RLS, indexes |

### Supabase Edge Functions

| File | Purpose |
|------|---------|
| `supabase/functions/process-document/index.ts` | File parsing, chunking, chunk insertion |
| `supabase/functions/search-documents/index.ts` | Query embedding + hybrid search dispatch |
| `supabase/functions/enrich-metadata/index.ts` | LLM metadata extraction worker |

### Python Libraries

| File | Purpose |
|------|---------|
| `libs/vizu_rag_factory/src/vizu_rag_factory/__init__.py` | Public exports |
| `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | `create_rag_runnable()` — main entry point |
| `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | `_BaseSupabaseRetriever`, `SupabaseVectorRetriever`, `HybridRetriever` |
| `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py` | `LLMReranker`, `CrossEncoderReranker` |
| `libs/vizu_rag_factory/pyproject.toml` | Package config and dependencies |
| `libs/vizu_models/src/vizu_models/knowledge_base_config.py` | `RagSearchConfig` Pydantic model |
| `libs/vizu_llm_service/src/vizu_llm_service/config.py` | `LLMSettings` — centralized LLM configuration |
| `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py` | `RAG_TOOL_PROMPT`, `RAG_RERANK_PROMPT`, `METADATA_ENRICHMENT_PROMPT` |

### Frontend

| File | Purpose |
|------|---------|
| `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` | Supabase client for document CRUD + upload |
| `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts` | React hook with auto-polling |
| `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx` | Admin UI for knowledge base management |

### Scripts & Seeds

| File | Purpose |
|------|---------|
| `scripts/seed_platform_knowledge.py` | Seed platform-scoped documents |
| `seeds/platform_knowledge/*.md` | Curated platform knowledge files |

### Tests

| File | Purpose |
|------|---------|
| `libs/vizu_rag_factory/tests/unit/test_retriever.py` | Retriever unit tests (7 tests) |
| `libs/vizu_rag_factory/tests/unit/test_reranker.py` | Reranker unit tests (11 tests) |
| `libs/vizu_rag_factory/tests/unit/test_factory.py` | Factory unit tests (2 tests) |
