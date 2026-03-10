# RAG Pipeline Overhaul Plan

> **Status:** ✅ Complete (All Phases 1–6 implemented)
> **Created:** 2026-03-10
> **Goal:** Fix zero/poor answers from the RAG pipeline by addressing score display, retrieval quality, chunk sizing, query preprocessing, and cleanup of deprecated infra.

---

## Current Architecture (As-Is)

```
User Query
    │
    ▼
tool_pool_api/rag_module.py  ─── executar_rag_cliente MCP tool
    │
    ▼
vizu_rag_factory/factory.py  ─── create_rag_runnable()
    │  Reads RagSearchConfig from clientes_vizu.available_tools
    │  Gate: "executar_rag_cliente" must be in enabled_tools
    │
    ├── HybridRetriever  ─── HTTP POST to search-documents EF
    │       │
    │       ▼
    │   search-documents/index.ts
    │       │  Embeds query with Cohere embed-multilingual-light-v3.0 (384d)
    │       │  Calls hybrid_match_documents RPC
    │       │
    │       ▼
    │   hybrid_match_documents (PostgreSQL)
    │       │  Semantic CTE: cosine sim > threshold, HNSW index
    │       │  Keyword CTE: ts_rank via GIN index (portuguese)
    │       │  Fusion: RRF 1/(60+rank) or weighted linear
    │       │  Returns: combined_score, similarity, keyword_score
    │       │
    │       ▼
    ├── CohereReranker  ─── Cohere rerank-multilingual-v3.0
    │       │  Adds rerank_score (0.0-1.0) to metadata
    │       │  Does NOT modify combined_score
    │       │
    ├── MMRDiversifier  ─── Maximal Marginal Relevance
    │       │  Reads rerank_score > combined_score > similarity
    │       │  Adds mmr_score to metadata
    │       │
    ├── _format_docs()  ─── Formats context for LLM
    │       │  ⚠️ BUG: Uses combined_score (RRF: max ~3%)
    │       │  Ignores rerank_score entirely
    │       │
    └── RAG_TOOL_PROMPT + LLM → StrOutputParser
            LLM sees "Relevância: 2%" → ignores context → "não sei"
```

### Document Ingestion

```
Dashboard upload → Supabase Storage → process-document EF
    │  Downloads file from Storage
    │  Parses (PDF/DOCX/CSV/TXT/MD/JSON/XML/HTML)
    │  Chunks: TARGET_TOKENS=250, OVERLAP_SENTENCES=2
    │  Embeds: Cohere embed-multilingual-light-v3.0 (384d, input_type: "search_document")
    │  Enriches: Ollama Cloud LLM (word_cloud, theme, usage_context)
    │  INSERTs chunks with embeddings + metadata in single transaction
    │  Sets document status = 'completed'
    └── Document is searchable immediately
```

### Legacy `embed` EF (DEPRECATED — to be removed)

The `embed` Edge Function uses **OpenAI text-embedding-3-small** (different model family than Cohere). It processes jobs from pgmq `embedding_jobs` queue. The triggers that fed this queue were already removed in migration `20260306_remove_embed_and_metadata_triggers.sql`. The cron jobs were removed in `20260306_drop_embedding_cron_jobs.sql`. The EF is dormant — no new work reaches it. It should be deleted to avoid confusion.

---

## Root Causes Identified

### RC-1: Score Display Bug (CRITICAL — Primary cause of "no answer")

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` L39-44

`_format_docs()` displays `combined_score` from RRF fusion. RRF scores are `1/(60+rank)` — the theoretical maximum is `1/61 + 1/61 ≈ 0.033` (3.3%). When formatted with `:.0%`, this produces headers like `Relevância: 2%`.

The RAG prompt says: *"Cada trecho inclui metadados no formato [Fonte: ... | Relevância: percentual | Escopo: tipo]"*. The LLM interprets "2% relevance" as "virtually irrelevant" and refuses to use the context.

Meanwhile, the Cohere reranker produces `rerank_score` in the 0.0–1.0 range (proper relevance probability), but `_format_docs` **completely ignores it**. The `MMRDiversifier._get_score()` in `diversity.py` correctly prioritizes `rerank_score > combined_score > similarity`, but `_format_docs` was never updated to match.

### RC-2: score_threshold 0.5 Overrides SQL Default 0.3

**File:** `libs/vizu_models/src/vizu_models/knowledge_base_config.py` L55

`RagSearchConfig.score_threshold` defaults to `0.5`. This is sent explicitly to the `search-documents` EF, which passes it to `hybrid_match_documents` as `p_match_threshold`. The SQL function's own default is `0.3` (set in migration `20260306`), but it's always overridden by the Python value.

For Cohere multilingual embeddings, 0.5 cosine similarity is quite restrictive. Many relevant chunks score between 0.3 and 0.5 and get silently filtered out.

### RC-3: Chunk Size Too Small (250 tokens)

**File:** `supabase/functions/process-document/index.ts` L53

`TARGET_TOKENS = 250` (~175 words). This is too short for self-contained context — topic introduction and detail often end up in different chunks. The Cohere model supports up to 512 tokens, so there's room to increase.

### RC-4: No Programmatic Query Preprocessing

The raw query string from the agent goes directly to embedding and keyword search with zero transformation. The system prompt instructs the *calling agent* to rewrite queries, but this is unreliable — the Langfuse trace shows the agent passed a multi-concept raw query `"modelo de negócios da Pólen negócio modelo, utilização de análise de dados..."` that matched generic data analysis chunks instead of business model content.

### RC-5: Enriched Metadata Unused at Retrieval

`process-document` enriches each chunk with `theme` (one of 13 categories), `word_cloud`, and `usage_context` via LLM. This metadata is stored in `document_chunks.metadata` JSONB but is **never used during search** — `hybrid_match_documents` only filters by the document-level `category` column, not chunk-level `theme`.

### RC-6: Legacy `embed` EF Still Deployed

The `embed` Edge Function uses OpenAI embeddings. While its triggers and cron jobs have been removed, it remains deployed and could cause confusion. Any manual invocation would produce incompatible embeddings.

---

## Overhaul Phases

### Phase 1 — Critical Score Fix + Threshold Alignment

**Priority:** CRITICAL — highest-impact fix
**Estimated effort:** ~30 minutes
**Dependency:** None

| # | Task | File | Details |
|---|------|------|---------|
| 1.1 | Fix `_format_docs` score priority | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` L39-44 | Change score selection to match `_get_score()` from `diversity.py`: use `rerank_score` first (0–1 from Cohere), then `combined_score`, then `similarity`. All are displayed as `:.0%`. |
| 1.2 | Lower `score_threshold` default to 0.3 | `libs/vizu_models/src/vizu_models/knowledge_base_config.py` L55 | Change `score_threshold: float = 0.5` → `0.3`. Aligns with SQL function default. |
| 1.3 | Update `RagSearchConfig` docstring example | `libs/vizu_models/src/vizu_models/knowledge_base_config.py` L40 | Update the JSON example to show `"score_threshold": 0.3` |
| 1.4 | Add score debug logging | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | Log `rerank_score`, `combined_score`, and `similarity` values for top-3 docs before formatting, so score flow is visible in debug logs. |
| 1.5 | Run lint + tests | All modified files | `ruff check --fix` + `pytest` on `vizu_rag_factory` and `vizu_models` |

**Verification:**
- Re-run the same Langfuse trace query
- Context headers should now show `Relevância: 85%` (Cohere rerank scores) instead of `2%`
- The LLM should use the context to generate an answer

#### Implementation Details for 1.1

Current code (`factory.py` L39-44):
```python
combined = doc.metadata.get("combined_score")
similarity = doc.metadata.get("similarity", 0)

score_str = (
    f"Relevância: {combined:.0%}"
    if combined is not None
    else f"Relevância: {similarity:.0%}"
)
```

Target code:
```python
# Priority: rerank_score (Cohere 0-1) > combined_score (RRF) > similarity (cosine)
rerank = doc.metadata.get("rerank_score")
combined = doc.metadata.get("combined_score")
similarity = doc.metadata.get("similarity", 0)

if rerank is not None:
    display_score = max(0.0, min(1.0, float(rerank)))
elif combined is not None:
    display_score = float(combined)
else:
    display_score = float(similarity)

score_str = f"Relevância: {display_score:.0%}"
```

---

### Phase 2 — Chunk Size Increase + Re-ingestion

**Priority:** HIGH
**Estimated effort:** ~1 hour (code change small; re-processing takes time)
**Dependency:** None (independent of Phase 1)

| # | Task | File | Details |
|---|------|------|---------|
| 2.1 | Increase `TARGET_TOKENS` from 250 → 400 | `supabase/functions/process-document/index.ts` L53 | 400 tokens stays within Cohere's 512-token limit while producing more coherent chunks (~280 words). |
| 2.2 | Deploy updated `process-document` EF | Supabase CLI | `supabase functions deploy process-document` |
| 2.3 | Re-process all existing documents | SQL + API | Reset document statuses to `processing`, delete old chunks, re-invoke `process-document` per document. This also ensures all embeddings are Cohere-uniform. |
| 2.4 | Verify new chunk quality | SQL query | Check `SELECT content, length(content), estimated_tokens FROM vector_db.document_chunks WHERE document_id = '...' LIMIT 10` |

#### Implementation Details for 2.1

```typescript
// Before
const TARGET_TOKENS = 250; // target tokens per chunk

// After
const TARGET_TOKENS = 400; // target tokens per chunk (Cohere max = 512)
```

#### Implementation Details for 2.3

Re-ingestion script (run from SQL editor or Node script):
```sql
-- 1. Find all documents to re-process
SELECT id, storage_path, client_id, file_name, file_type
FROM vector_db.documents
WHERE status = 'completed';

-- 2. For each: delete old chunks and reset status
UPDATE vector_db.documents SET status = 'processing', updated_at = now()
WHERE id = '<doc_id>';

DELETE FROM vector_db.document_chunks WHERE document_id = '<doc_id>';

-- 3. Re-invoke process-document EF per document (via HTTP or dashboard re-upload)
```

---

### Phase 3 — Query Preprocessing

**Priority:** HIGH
**Estimated effort:** ~2 hours
**Dependency:** None (independent of Phases 1–2)

| # | Task | File | Details |
|---|------|------|---------|
| 3.1 | Create `QueryPreprocessor` class | `libs/vizu_rag_factory/src/vizu_rag_factory/query_preprocessor.py` (NEW) | Lightweight LLM call (tier=FAST) that rewrites the user query for better retrieval. Outputs a search-optimized string. |
| 3.2 | Add `RAG_QUERY_REWRITE_PROMPT` | `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py` | New prompt template for query rewriting. Instructions: decompose multi-topic queries, expand with synonyms, remove filler, optimize for embedding similarity. Output must be a single rewritten query string. |
| 3.3 | Add `query_preprocessing` config field | `libs/vizu_models/src/vizu_models/knowledge_base_config.py` | New field `query_preprocessing: bool = True` in `RagSearchConfig`. Allows per-client disable. |
| 3.4 | Integrate into `create_rag_runnable` | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | Insert preprocessor step before retrieval in `retrieve_and_format` / `aretrieve_and_format`. |
| 3.5 | Run lint + tests | All modified files | |

#### Implementation Details for 3.1

```python
# libs/vizu_rag_factory/src/vizu_rag_factory/query_preprocessor.py

class QueryPreprocessor:
    """Rewrites user queries for optimal RAG retrieval.

    Uses a fast LLM tier to:
    1. Decompose multi-topic queries into key concepts
    2. Expand with synonyms and related terms
    3. Remove conversational filler
    4. Produce a search-optimized query string
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def arewrite(self, query: str) -> str:
        """Async rewrite query for retrieval."""
        ...

    def rewrite(self, query: str) -> str:
        """Sync rewrite query for retrieval."""
        ...
```

#### Implementation Details for 3.4

In `retrieve_and_format` / `aretrieve_and_format`, before `retriever.invoke(question)`:

```python
# Before retrieval — rewrite query for better embedding match
if preprocessor:
    question = await preprocessor.arewrite(question)
    logger.debug(f"RAG preprocessed query: '{question[:100]}...'")
```

---

### Phase 4 — Deprecate & Remove Legacy `embed` EF

**Priority:** MEDIUM
**Estimated effort:** ~30 minutes
**Dependency:** Phase 2 complete (all docs re-processed with Cohere via process-document)

| # | Task | File | Details |
|---|------|------|---------|
| 4.1 | Delete embed EF directory | `supabase/functions/embed/` | Remove the entire directory. |
| 4.2 | Clean up pgmq queues | New SQL migration | Drop `embedding_jobs` and `embedding_jobs_dlq` queues; drop `util.process_embeddings()` function; drop `vector_db.queue_embedding_if_null()` trigger function. |
| 4.3 | Remove stale trigger function | Same migration | Drop `clear_chunk_embedding_on_update` trigger (no longer needed — process-document replaces entire chunk set on re-process). |
| 4.4 | Update `embedding_model` field reference | `libs/vizu_models/src/vizu_models/knowledge_base_config.py` L110 | Change default from `"gte-small"` to `"embed-multilingual-light-v3.0"` and update description. |

#### Implementation Details for 4.2

```sql
-- Migration: Remove legacy embedding queue infrastructure
-- Reason: process-document EF handles all embedding inline via Cohere.
-- The embed EF, pgmq queues, and related functions are no longer used.

-- Drop queues
SELECT pgmq.drop_queue('embedding_jobs');
SELECT pgmq.drop_queue('embedding_jobs_dlq');

-- Drop queue-related functions
DROP FUNCTION IF EXISTS util.process_embeddings();
DROP FUNCTION IF EXISTS vector_db.queue_embedding_if_null();

-- Drop stale trigger
DROP TRIGGER IF EXISTS clear_chunk_embedding_on_update ON vector_db.document_chunks;
DROP FUNCTION IF EXISTS vector_db.clear_chunk_embedding_on_update();
```

---

### Phase 5 — Metadata-Powered Retrieval (Enhancement)

**Priority:** LOW
**Estimated effort:** ~3 hours
**Dependency:** Phases 1-2 complete

| # | Task | File | Details |
|---|------|------|---------|
| 5.1 | Promote `theme` to a column | New SQL migration | `ALTER TABLE vector_db.document_chunks ADD COLUMN theme TEXT;` + backfill from `metadata->>'theme'` + B-tree index. |
| 5.2 | Update `process-document` to write theme column | `supabase/functions/process-document/index.ts` | Write `theme` to both the column and metadata JSONB (backward compat). |
| 5.3 | Add `theme` filter to `hybrid_match_documents` | SQL migration | New optional `p_themes TEXT[]` parameter; filter: `AND (p_themes IS NULL OR dc.theme = ANY(p_themes))`. |
| 5.4 | Pass `themes` from Python retriever | `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | Add `themes` field to `HybridRetriever`, pass through to EF payload. |
| 5.5 | Add `themes` to `RagSearchConfig` | `libs/vizu_models/src/vizu_models/knowledge_base_config.py` | New optional field. |
| 5.6 | Update `search-documents` EF | `supabase/functions/search-documents/index.ts` | Accept and forward `themes` parameter. |

---

### Phase 6 — Observability & Documentation

**Priority:** LOW
**Estimated effort:** ~1 hour
**Dependency:** All previous phases complete

| # | Task | File | Details |
|---|------|------|---------|
| 6.1 | Update `HYBRID_RETRIEVER_AS_BUILT.md` | `docs/HYBRID_RETRIEVER_AS_BUILT.md` | Fix stale references: `gte-small` → Cohere, `TARGET_TOKENS=400` → matches code, pgmq pipeline → inline, add query preprocessor section. |
| 6.2 | Update `RAG_PIPELINE_ANALYSIS.md` | `docs/RAG_PIPELINE_ANALYSIS.md` | Mark resolved issues, update architecture diagram, note embed EF removal. |
| 6.3 | Remove `RAG_MIGRATION_GUIDE.md` if stale | `docs/RAG_MIGRATION_GUIDE.md` | Review and either update or archive. |

---

## Working Sessions Plan

### Session 1: Score Fix + Threshold (Phase 1)
**Agent scope:** Python only — `vizu_rag_factory` + `vizu_models`

Files to modify:
- `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` — Fix `_format_docs()`, add debug logging
- `libs/vizu_models/src/vizu_models/knowledge_base_config.py` — Lower threshold, update docstring

Validation: `ruff check --fix` + `pytest` on both packages.

### Session 2: Chunk Size + Re-ingestion (Phase 2)
**Agent scope:** TypeScript EF + SQL

Files to modify:
- `supabase/functions/process-document/index.ts` — Change `TARGET_TOKENS`

Post-deploy: Re-process documents via Supabase (manual or scripted).

### Session 3: Query Preprocessor (Phase 3)
**Agent scope:** Python — `vizu_rag_factory` + `vizu_prompt_management` + `vizu_models`

Files to create:
- `libs/vizu_rag_factory/src/vizu_rag_factory/query_preprocessor.py`

Files to modify:
- `libs/vizu_prompt_management/src/vizu_prompt_management/templates.py` — New prompt
- `libs/vizu_prompt_management/src/vizu_prompt_management/__init__.py` — Export
- `libs/vizu_models/src/vizu_models/knowledge_base_config.py` — New config field
- `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` — Integrate preprocessor
- `libs/vizu_rag_factory/src/vizu_rag_factory/__init__.py` — Export

Validation: `ruff check --fix` + `pytest`.

### Session 4: Deprecate embed EF + Cleanup (Phase 4)
**Agent scope:** TypeScript deletion + SQL migration + Python model update

Actions:
- Delete `supabase/functions/embed/` directory
- Write new SQL migration to drop queues/functions/triggers
- Update `KnowledgeBaseConfigBase.embedding_model` default

### Session 5: Metadata Retrieval Enhancement (Phase 5)
**Agent scope:** SQL migration + TypeScript EF + Python retriever/config

Files to modify:
- New SQL migration (theme column + filter)
- `supabase/functions/process-document/index.ts`
- `supabase/functions/search-documents/index.ts`
- `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py`
- `libs/vizu_models/src/vizu_models/knowledge_base_config.py`

### Session 6: Documentation Update (Phase 6)
**Agent scope:** Markdown docs only

Files to modify:
- `docs/HYBRID_RETRIEVER_AS_BUILT.md`
- `docs/RAG_PIPELINE_ANALYSIS.md`
- `docs/RAG_MIGRATION_GUIDE.md`

---

## Expected Outcome (To-Be Architecture)

```
User Query
    │
    ▼
rag_module.py ─── executar_rag_cliente
    │
    ▼
factory.py ─── create_rag_runnable()
    │
    ├── QueryPreprocessor (NEW — Phase 3)
    │       │  LLM tier=FAST rewrites query
    │       │  Decomposes, expands, removes filler
    │       │
    ├── HybridRetriever ─── threshold=0.3 (Phase 1)
    │       │  Larger chunk pool (400-token chunks, Phase 2)
    │       │  Optional theme filtering (Phase 5)
    │       │
    ├── CohereReranker ─── rerank_score (0.0-1.0)
    │       │
    ├── MMRDiversifier ─── Uses rerank_score
    │       │
    ├── _format_docs() ─── FIXED: displays rerank_score (Phase 1)
    │       │  "Relevância: 85%" instead of "2%"
    │       │
    └── RAG_TOOL_PROMPT + LLM
            LLM sees high relevance → uses context → good answer ✅
```

### Ingestion (simplified)

```
Dashboard upload → process-document EF (Cohere only)
    │  Chunks: TARGET_TOKENS=400
    │  Embeds: Cohere embed-multilingual-light-v3.0
    │  Enriches: theme, word_cloud, usage_context
    │  FTS trigger auto-populates fts column
    └── No legacy embed EF, no pgmq, no cron
```
