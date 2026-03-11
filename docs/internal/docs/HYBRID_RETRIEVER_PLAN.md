# Hybrid Retriever & Rich Metadata — Implementation Plan

> **Goal**: Evolve the current pure-vector retrieval pipeline into a hybrid ranking
> system that fuses PostgreSQL full-text search (`ts_rank`) with cosine similarity
> from pgvector. Add document scoping (`platform` vs `client`), rich LLM-generated
> metadata at ingestion time, configurable fusion strategies (RRF + weighted linear),
> and a cross-encoder reranker for final relevance scoring.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          QUERY FLOW (hybrid)                                │
│                                                                             │
│  User Query                                                                 │
│     │                                                                       │
│     ▼                                                                       │
│  HybridRetriever (Python)                                                   │
│     │                                                                       │
│     ├─── POST search-documents EF ──► embed query (gte-small)               │
│     │                                  + parse keywords                     │
│     │                                     │                                 │
│     │                                     ▼                                 │
│     │                            hybrid_match_documents RPC                 │
│     │                                     │                                 │
│     │                              Scope Filter                             │
│     │                         (platform + client_id)                        │
│     │                                     │                                 │
│     │                            ┌────────┴─────────┐                       │
│     │                            │                    │                     │
│     │                      Semantic Search       Keyword Search             │
│     │                      (cosine on HNSW)      (ts_rank on GIN)          │
│     │                            │                    │                     │
│     │                            └────────┬─────────┘                       │
│     │                                     │                                 │
│     │                              Fusion (RRF or Weighted)                 │
│     │                                     │                                 │
│     │◄──────────── ranked results ────────┘                                 │
│     │                                                                       │
│     ▼                                                                       │
│  CrossEncoderReranker (bge-reranker-v2-m3)                                 │
│     │                                                                       │
│     ▼                                                                       │
│  Format + LLM Answer                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INGESTION FLOW (enriched)                            │
│                                                                             │
│  Upload (Dashboard)                                                         │
│     │ description, category (user-provided)                                 │
│     │                                                                       │
│     ▼                                                                       │
│  vector_db.documents  ──► scope, description, category columns              │
│     │                                                                       │
│     ▼                                                                       │
│  process-document EF   ──► chunk text, insert document_chunks               │
│     │                       (scope denormalized from parent)                │
│     │                                                                       │
│     ├──► TRIGGER: queue_embedding_if_null  ──► pgmq(embedding_jobs)         │
│     │         └──► pg_cron → embed EF → halfvec(384)                        │
│     │                                                                       │
│     └──► TRIGGER: generate_fts_on_insert                                    │
│     │         └──► tsvector('portuguese', unaccent(content))                │
│     │                                                                       │
│     └──► TRIGGER: queue_metadata_if_null  ──► pgmq(metadata_jobs)           │
│               └──► pg_cron → enrich-metadata EF                             │
│                    ├── word_cloud (salient terms)                            │
│                    ├── theme (controlled vocabulary)                         │
│                    └── usage_context (free-form hint)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Collection Model

No separate `collections` table. Scoping is done via columns on the existing tables:

| Column | Table | Purpose |
|--------|-------|---------|
| `scope` | `documents` + `document_chunks` | `'platform'` (shared) or `'client'` (RLS-enforced) |
| `description` | `documents` | User-provided on upload |
| `category` | `documents` + `document_chunks` | User-selected on upload, denormalized for filter perf |
| `metadata.word_cloud` | `document_chunks` | LLM-generated salient terms (array) |
| `metadata.theme` | `document_chunks` | LLM-classified theme from controlled vocabulary |
| `metadata.usage_context` | `document_chunks` | LLM-generated usage hint |

Platform-scoped documents (`scope = 'platform'`) have `client_id = NULL` and are readable
by all clients. Categories for platform knowledge:

- `statistical_knowledge` — Mean, median, distributions, hypothesis testing
- `tax_knowledge` — BR tax rules, fiscal calendar, ICMS/PIS/COFINS
- `business_knowledge` — KPIs, forecasting, unit economics, financial analysis
- `task_specific` — Data analysis playbooks, methodology guides
- `dados_negocio` — Client-specific business data
- `contexto_empresa` — Client-specific business context
- `documentos` — Client-uploaded documents (contracts, policies, etc.)
- `conhecimento_ia` — AI-built business logic for this client

---

## Current State (as-is)

| Component | Current Implementation | File |
|-----------|----------------------|------|
| Vector store | pgvector `halfvec(384)` HNSW | `vector_db.document_chunks` |
| Embedding | `gte-small` via Supabase Edge Runtime | `supabase/functions/embed/index.ts` |
| Search | Cosine similarity only via `match_documents` RPC | `supabase/functions/search-documents/index.ts` |
| Retriever | `SupabaseVectorRetriever(BaseRetriever)` | `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` |
| Reranker | `LLMReranker` (LLM scoring 0-10, off by default) | `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py` |
| Chain | `create_rag_runnable()` → retriever → prompt → LLM | `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` |
| Metadata | `{source_file, chunk_index, char_start, char_end, estimated_tokens, total_chunks}` | Set by `process-document` EF |
| Scope | Single-tenant (all docs have `client_id NOT NULL`) | No platform/shared knowledge |
| FTS | Not implemented | — |
| Keyword search | Not implemented | — |
| Cross-encoder | Not implemented | — |

---

## Phase 1 — Schema Evolution (Supabase Migration)

**Migration file**: `supabase/migrations/YYYYMMDD_hybrid_retriever_schema.sql`

### 1.1 Enable Extensions

```sql
CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_trgm   SCHEMA extensions;
```

**Why**: `unaccent` is required for accent-insensitive FTS on Brazilian Portuguese content
(`café` → `cafe`). `pg_trgm` enables fuzzy/trigram matching for future use.

### 1.2 Add `scope` Column to `documents`

```sql
ALTER TABLE vector_db.documents
  ADD COLUMN scope TEXT NOT NULL DEFAULT 'client'
    CHECK (scope IN ('platform', 'client'));

-- Platform docs don't belong to a client — relax NOT NULL
ALTER TABLE vector_db.documents
  ALTER COLUMN client_id DROP NOT NULL;

-- Add constraint: client scope requires client_id, platform allows NULL
ALTER TABLE vector_db.documents
  ADD CONSTRAINT documents_scope_client_check
    CHECK (
      (scope = 'client'   AND client_id IS NOT NULL) OR
      (scope = 'platform' AND client_id IS NULL)
    );

CREATE INDEX idx_documents_scope ON vector_db.documents(scope);
```

### 1.3 Add `description` and `category` to `documents`

```sql
ALTER TABLE vector_db.documents
  ADD COLUMN description TEXT,
  ADD COLUMN category    TEXT;

CREATE INDEX idx_documents_category ON vector_db.documents(category);
```

### 1.4 Add `scope` and `category` to `document_chunks` (denormalized)

```sql
ALTER TABLE vector_db.document_chunks
  ADD COLUMN scope    TEXT NOT NULL DEFAULT 'client'
    CHECK (scope IN ('platform', 'client')),
  ADD COLUMN category TEXT;

-- Relax client_id NOT NULL for platform chunks
ALTER TABLE vector_db.document_chunks
  ALTER COLUMN client_id DROP NOT NULL;

ALTER TABLE vector_db.document_chunks
  ADD CONSTRAINT chunks_scope_client_check
    CHECK (
      (scope = 'client'   AND client_id IS NOT NULL) OR
      (scope = 'platform' AND client_id IS NULL)
    );

CREATE INDEX idx_chunks_scope    ON vector_db.document_chunks(scope);
CREATE INDEX idx_chunks_category ON vector_db.document_chunks(category);
```

### 1.5 Add `fts` tsvector Column with Trigger + GIN Index

```sql
-- Immutable unaccent wrapper (required for tsvector index/trigger)
CREATE OR REPLACE FUNCTION vector_db.immutable_unaccent(text)
RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
AS $$ SELECT extensions.unaccent($1); $$;

-- FTS column
ALTER TABLE vector_db.document_chunks
  ADD COLUMN fts TSVECTOR;

-- Auto-generate tsvector on INSERT or content UPDATE
CREATE OR REPLACE FUNCTION vector_db.generate_fts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.fts := to_tsvector(
    'portuguese',
    vector_db.immutable_unaccent(NEW.content)
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER generate_fts_on_insert_or_update
  BEFORE INSERT OR UPDATE OF content
  ON vector_db.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION vector_db.generate_fts();

-- GIN index for fast full-text search
CREATE INDEX idx_chunks_fts ON vector_db.document_chunks USING GIN (fts);

-- Backfill existing chunks
UPDATE vector_db.document_chunks
SET fts = to_tsvector(
  'portuguese',
  vector_db.immutable_unaccent(content)
)
WHERE fts IS NULL;
```

### 1.6 Update RLS Policies for Platform Scope

```sql
-- Documents: users can read platform docs + their own
DROP POLICY IF EXISTS "Users can view own documents" ON vector_db.documents;
CREATE POLICY "Users can view own or platform documents"
  ON vector_db.documents FOR SELECT
  USING (scope = 'platform' OR client_id = auth.uid());

-- Documents: users can only INSERT/UPDATE/DELETE their own (not platform)
-- (existing INSERT/UPDATE/DELETE policies already enforce client_id = auth.uid(),
--  which automatically excludes platform docs since they have client_id = NULL)

-- Chunks: users can read platform chunks + their own
DROP POLICY IF EXISTS "Users can view own chunks" ON vector_db.document_chunks;
CREATE POLICY "Users can view own or platform chunks"
  ON vector_db.document_chunks FOR SELECT
  USING (scope = 'platform' OR client_id = auth.uid());
```

### 1.7 New RPC: `hybrid_match_documents`

```sql
CREATE OR REPLACE FUNCTION vector_db.hybrid_match_documents(
  p_client_id       UUID,
  p_query_embedding extensions.halfvec(384),
  p_query_text      TEXT,
  p_match_count     INT     DEFAULT 5,
  p_match_threshold FLOAT   DEFAULT 0.5,
  p_document_ids    UUID[]  DEFAULT NULL,
  p_scope           TEXT[]  DEFAULT '{platform,client}',
  p_categories      TEXT[]  DEFAULT NULL,
  p_fusion_strategy TEXT    DEFAULT 'rrf',   -- 'rrf' or 'weighted'
  p_keyword_weight  FLOAT   DEFAULT 0.4,
  p_vector_weight   FLOAT   DEFAULT 0.6
)
RETURNS TABLE (
  id              INTEGER,
  document_id     UUID,
  content         TEXT,
  metadata        JSONB,
  similarity      FLOAT,
  keyword_score   FLOAT,
  combined_score  FLOAT,
  file_name       TEXT,
  document_title  TEXT,
  scope           TEXT,
  category        TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = 'extensions', 'vector_db', 'public'
AS $$
DECLARE
  v_tsquery TSQUERY;
BEGIN
  -- Build tsquery from user text (websearch syntax supports natural phrases)
  v_tsquery := websearch_to_tsquery(
    'portuguese',
    vector_db.immutable_unaccent(p_query_text)
  );

  RETURN QUERY
  WITH
  -- Semantic candidates (cosine similarity)
  semantic AS (
    SELECT
      dc.id,
      dc.document_id,
      dc.content,
      dc.metadata,
      (1 - (dc.embedding <=> p_query_embedding))::float AS similarity,
      0::float AS keyword_score,
      d.file_name,
      d.title AS document_title,
      dc.scope,
      dc.category,
      ROW_NUMBER() OVER (ORDER BY dc.embedding <=> p_query_embedding) AS sem_rank
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE dc.embedding IS NOT NULL
      AND d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
      AND (1 - (dc.embedding <=> p_query_embedding)) > p_match_threshold
      AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
      AND (p_categories  IS NULL OR dc.category = ANY(p_categories))
    ORDER BY dc.embedding <=> p_query_embedding
    LIMIT p_match_count * 3  -- fetch wider pool for fusion
  ),

  -- Keyword candidates (ts_rank on GIN index)
  keyword AS (
    SELECT
      dc.id,
      dc.document_id,
      dc.content,
      dc.metadata,
      0::float AS similarity,
      ts_rank_cd(dc.fts, v_tsquery)::float AS keyword_score,
      d.file_name,
      d.title AS document_title,
      dc.scope,
      dc.category,
      ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC) AS kw_rank
    FROM vector_db.document_chunks dc
    JOIN vector_db.documents d ON d.id = dc.document_id
    WHERE dc.fts @@ v_tsquery
      AND d.status = 'completed'
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
      AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
      AND (p_categories  IS NULL OR dc.category = ANY(p_categories))
    ORDER BY ts_rank_cd(dc.fts, v_tsquery) DESC
    LIMIT p_match_count * 3
  ),

  -- Merge all unique candidates
  all_candidates AS (
    SELECT id, document_id, content, metadata,
           similarity, keyword_score, file_name, document_title,
           scope, category, sem_rank, NULL::bigint AS kw_rank
    FROM semantic
    UNION ALL
    SELECT id, document_id, content, metadata,
           similarity, keyword_score, file_name, document_title,
           scope, category, NULL::bigint AS sem_rank, kw_rank
    FROM keyword
  ),

  -- Deduplicate and merge scores per chunk
  merged AS (
    SELECT
      ac.id,
      ac.document_id,
      MAX(ac.content) AS content,
      MAX(ac.metadata) AS metadata,
      COALESCE(MAX(ac.similarity), 0) AS similarity,
      COALESCE(MAX(ac.keyword_score), 0) AS keyword_score,
      MAX(ac.file_name) AS file_name,
      MAX(ac.document_title) AS document_title,
      MAX(ac.scope) AS scope,
      MAX(ac.category) AS category,
      MIN(ac.sem_rank) AS sem_rank,      -- best semantic rank
      MIN(ac.kw_rank)  AS kw_rank        -- best keyword rank
    FROM all_candidates ac
    GROUP BY ac.id, ac.document_id
  ),

  -- Score fusion
  scored AS (
    SELECT
      m.*,
      CASE p_fusion_strategy
        WHEN 'rrf' THEN
          -- Reciprocal Rank Fusion: 1/(k+rank), k=60
          COALESCE(1.0 / (60 + m.sem_rank), 0) +
          COALESCE(1.0 / (60 + m.kw_rank), 0)
        WHEN 'weighted' THEN
          -- Weighted linear: normalize scores to [0,1]
          (p_vector_weight  * m.similarity) +
          (p_keyword_weight * LEAST(m.keyword_score * 10, 1.0))
        ELSE
          m.similarity  -- fallback to pure semantic
      END AS combined_score
    FROM merged m
  )

  SELECT
    s.id, s.document_id, s.content, s.metadata,
    s.similarity, s.keyword_score, s.combined_score,
    s.file_name, s.document_title, s.scope, s.category
  FROM scored s
  ORDER BY s.combined_score DESC
  LIMIT p_match_count;
END;
$$;
```

### 1.8 Keep Old `match_documents` (backward compat)

The old RPC remains untouched. It will be used when `search_mode = "semantic"` or as
a fallback.

---

## Phase 2 — Metadata Enrichment Pipeline (Async)

**Files touched**:
- `supabase/migrations/YYYYMMDD_hybrid_retriever_schema.sql` (same migration, second half)
- `supabase/functions/enrich-metadata/index.ts` (new Edge Function)

### 2.1 New pgmq Queue: `metadata_jobs`

```sql
SELECT pgmq.create('metadata_jobs');
```

### 2.2 Trigger: Queue Metadata Job on Chunk Insert

```sql
CREATE OR REPLACE FUNCTION vector_db.queue_metadata_if_null()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  -- Only queue if word_cloud hasn't been generated yet
  IF NEW.metadata IS NULL
     OR NEW.metadata->>'word_cloud' IS NULL THEN
    PERFORM pgmq.send(
      queue_name => 'metadata_jobs',
      msg => jsonb_build_object(
        'chunk_id', NEW.id,
        'document_id', NEW.document_id,
        'content', LEFT(NEW.content, 2000)  -- cap payload size
      )
    );
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER enrich_metadata_on_insert
  AFTER INSERT ON vector_db.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION vector_db.queue_metadata_if_null();
```

### 2.3 pg_cron Schedule for Metadata Processing

```sql
-- Process metadata jobs function
CREATE OR REPLACE FUNCTION util.process_metadata(
  batch_size int = 10,
  max_requests int = 5,
  timeout_milliseconds int = 5 * 60 * 1000
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  job_batches jsonb[];
  batch jsonb;
BEGIN
  WITH
    numbered_jobs AS (
      SELECT
        message || jsonb_build_object('jobId', msg_id) AS job_info,
        (row_number() OVER (ORDER BY 1) - 1) / batch_size AS batch_num
      FROM pgmq.read(
        queue_name => 'metadata_jobs',
        vt => timeout_milliseconds / 1000,
        qty => max_requests * batch_size
      )
    ),
    batched_jobs AS (
      SELECT jsonb_agg(job_info) AS batch_array, batch_num
      FROM numbered_jobs
      GROUP BY batch_num
    )
  SELECT array_agg(batch_array)
  FROM batched_jobs
  INTO job_batches;

  IF job_batches IS NULL THEN RETURN; END IF;

  FOREACH batch IN ARRAY job_batches LOOP
    PERFORM util.invoke_edge_function(
      name => 'enrich-metadata',
      body => batch,
      timeout_milliseconds => timeout_milliseconds
    );
  END LOOP;
END;
$$;

SELECT cron.schedule(
  'process-metadata',
  '10 seconds',
  $$ SELECT util.process_metadata(); $$
);
```

### 2.4 New Edge Function: `enrich-metadata`

**File**: `supabase/functions/enrich-metadata/index.ts`

Consumes batches from `metadata_jobs` via pgmq → pg_cron → pg_net. For each chunk:

1. Calls a lightweight LLM (OpenAI gpt-4.1-mini or similar FAST tier) with the chunk content
2. Prompt extracts:
   - `word_cloud`: Top 10-15 salient terms as a JSON string array
   - `theme`: One of the controlled vocabulary values
   - `usage_context`: One-sentence free-form description of when this chunk is useful
3. Updates `document_chunks.metadata` by merging new fields into existing JSONB
4. Deletes processed message from pgmq
5. On failure after 3 retries → DLQ (`metadata_jobs_dlq`) + logs

**Controlled vocabulary for `theme`**:
```
statistical_analysis, tax_regulation, business_operations,
financial_reporting, data_engineering, customer_service,
product_knowledge, legal_compliance, market_analysis,
human_resources, sales_strategy, operational_procedures, general
```

**LLM Prompt** (will be managed via Langfuse):
```
You are a document metadata classifier. Given the following text chunk,
extract structured metadata.

TEXT:
{content}

Respond in JSON only:
{
  "word_cloud": ["term1", "term2", ...],  // 10-15 most salient terms
  "theme": "one_of_controlled_list",       // see list below
  "usage_context": "one sentence describing when this content is useful"
}

Allowed themes: statistical_analysis, tax_regulation, business_operations,
financial_reporting, data_engineering, customer_service, product_knowledge,
legal_compliance, market_analysis, human_resources, sales_strategy,
operational_procedures, general
```

### 2.5 Update `process-document` EF

When inserting chunks, propagate `scope` and `category` from the parent document:

```typescript
// After fetching document row, read scope + category
const [docRow] = await sql`
  SELECT scope, category FROM vector_db.documents WHERE id = ${documentId}::uuid
`;

// In chunk INSERT, add scope and category columns
await sql`
  INSERT INTO vector_db.document_chunks
    (document_id, client_id, content, chunk_index, metadata, content_hash, scope, category)
  VALUES (
    ${documentId}::uuid,
    ${clientId}::uuid,  -- NULL for platform docs
    ${chunk.text},
    ${chunk.index},
    ${sql.json(chunk.metadata)},
    ${contentHash},
    ${docRow.scope},
    ${docRow.category}
  )
  ON CONFLICT (document_id, content_hash) DO UPDATE
  SET content = EXCLUDED.content,
      chunk_index = EXCLUDED.chunk_index,
      metadata = EXCLUDED.metadata,
      embedding = NULL
`;
```

---

## Phase 3 — Hybrid Retriever (Python)

**Files touched**:
- `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py`
- `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`
- `supabase/functions/search-documents/index.ts`

### 3.1 New `HybridRetriever` Class

Add to `retriever.py` alongside `SupabaseVectorRetriever`:

```python
class HybridRetriever(BaseRetriever):
    """Hybrid retriever combining semantic + keyword search with configurable fusion."""

    supabase_url: str
    supabase_service_key: str
    client_id: str
    match_count: int = 5
    match_threshold: float = 0.5
    document_ids: list[str] | None = None

    # Hybrid-specific
    search_mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    fusion_strategy: Literal["rrf", "weighted"] = "rrf"
    keyword_weight: float = 0.4
    vector_weight: float = 0.6
    scope: list[str] = ["platform", "client"]
    categories: list[str] | None = None

    def _build_payload(self, query: str) -> dict[str, Any]:
        payload = {
            "query": query,
            "client_id": self.client_id,
            "match_count": self.match_count,
            "match_threshold": self.match_threshold,
            "search_mode": self.search_mode,
            "fusion_strategy": self.fusion_strategy,
            "keyword_weight": self.keyword_weight,
            "vector_weight": self.vector_weight,
            "scope": self.scope,
        }
        if self.document_ids:
            payload["document_ids"] = self.document_ids
        if self.categories:
            payload["categories"] = self.categories
        return payload

    # ... _get_relevant_documents / _aget_relevant_documents
    # Same HTTP call pattern as SupabaseVectorRetriever
    # but POST payload includes all hybrid params
```

### 3.2 Update `search-documents` Edge Function

Accept new parameters. Route to `hybrid_match_documents` when `search_mode != "semantic"`:

```typescript
const {
    query,
    client_id,
    match_count = 5,
    match_threshold = 0.5,
    document_ids = null,
    // New hybrid params
    search_mode = "hybrid",
    fusion_strategy = "rrf",
    keyword_weight = 0.4,
    vector_weight = 0.6,
    scope = ["platform", "client"],
    categories = null,
} = body;

if (search_mode === "semantic") {
    // Legacy path — call match_documents as before
    const results = await sql`SELECT * FROM vector_db.match_documents(...)`;
    // ...
} else {
    // Hybrid path — embed query + pass raw text
    const queryEmbedding = await session.run(query, { mean_pool: true, normalize: true });
    const results = await sql`
      SELECT * FROM vector_db.hybrid_match_documents(
        ${client_id}::uuid,
        ${embeddingStr}::vector::halfvec(384),
        ${query},       -- raw text for FTS
        ${match_count}::int,
        ${match_threshold}::float,
        ${docIdsParam}::uuid[],
        ${scopeParam}::text[],
        ${categoriesParam}::text[],
        ${fusion_strategy},
        ${keyword_weight}::float,
        ${vector_weight}::float
      )
    `;
}
```

### 3.3 Update `factory.py`

Read new config keys from `rag_search_config` and instantiate `HybridRetriever`:

```python
search_mode = search_config.get("search_mode", "hybrid") if search_config else "hybrid"

if search_mode == "semantic":
    retriever = SupabaseVectorRetriever(...)  # legacy
else:
    retriever = HybridRetriever(
        supabase_url=os.environ["SUPABASE_URL"],
        supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
        client_id=str(contexto.id),
        match_count=search_config.get("top_k", 5),
        match_threshold=search_config.get("score_threshold", 0.5),
        document_ids=document_ids,
        search_mode=search_mode,
        fusion_strategy=search_config.get("fusion_strategy", "rrf"),
        keyword_weight=search_config.get("keyword_weight", 0.4),
        vector_weight=search_config.get("vector_weight", 0.6),
        scope=search_config.get("scope", ["platform", "client"]),
        categories=search_config.get("categories"),
    )
```

### 3.4 Update `_format_docs`

Show combined score + search mode info:

```python
def _format_docs(docs):
    parts = []
    for doc in docs:
        source = doc.metadata.get("file_name") or doc.metadata.get("source_file", "desconhecido")
        combined = doc.metadata.get("combined_score")
        similarity = doc.metadata.get("similarity", 0)
        keyword = doc.metadata.get("keyword_score", 0)
        scope = doc.metadata.get("scope", "client")

        score_str = f"Relevância: {combined:.0%}" if combined else f"Relevância: {similarity:.0%}"
        header = f"[Fonte: {source} | {score_str} | Escopo: {scope}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts) or "Nenhum contexto encontrado."
```

---

## Phase 4 — Cross-Encoder Reranker

**Files touched**:
- `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py`
- `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`
- `libs/vizu_rag_factory/pyproject.toml`

### 4.1 Add Dependencies

```toml
# In vizu_rag_factory/pyproject.toml
sentence-transformers = ">=3.0.0"
torch = {version = ">=2.0.0", optional = true}  # or onnxruntime for lighter weight
```

### 4.2 New `CrossEncoderReranker` Class

```python
class CrossEncoderReranker:
    """Reranks documents using a cross-encoder model (bge-reranker-v2-m3).

    Multilingual, supports PT-BR natively, 278M params.
    Much faster and cheaper than LLM-based reranking per query.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name, device=device)

    async def arerank(
        self,
        question: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        if not documents or len(documents) <= 1:
            return documents

        # Cross-encoder expects list of [query, passage] pairs
        pairs = [[question, doc.page_content[:1500]] for doc in documents]

        # Run in thread pool to avoid blocking event loop
        scores = await asyncio.to_thread(self.model.predict, pairs)

        scored = sorted(
            zip(documents, scores),
            key=lambda x: x[1],
            reverse=True
        )

        result = []
        for doc, score in scored[:top_k]:
            doc.metadata["rerank_score"] = float(score)
            result.append(doc)
        return result

    def rerank(self, question, documents, top_k=None):
        return asyncio.get_event_loop().run_until_complete(
            self.arerank(question, documents, top_k)
        )
```

### 4.3 Update `factory.py` Reranker Selection

```python
reranker_type = search_config.get("reranker_type", "cross-encoder") if search_config else "cross-encoder"

if rerank_enabled:
    if reranker_type == "cross-encoder":
        reranker = CrossEncoderReranker()
    else:
        reranker = LLMReranker(llm=llm)
```

### 4.4 Model Loading Strategy

The `bge-reranker-v2-m3` model (~1.1GB) should be loaded once at service startup
(singleton pattern), not per-request. Options:

- **Option A**: Module-level singleton in `reranker.py` (lazy-loaded on first use)
- **Option B**: Pass pre-loaded model via `factory.py` from app startup
- **Option C**: Use ONNX quantized version (~300MB) for faster CPU inference

**Recommendation**: Option A with lazy loading — simplest, model cached after first request.

---

## Phase 5 — Platform Knowledge Management

**Files touched**:
- `scripts/seed_platform_knowledge.py` (new)
- Platform knowledge source files in `seeds/`

### 5.1 Seeding Script

Python script that ingests platform-curated knowledge documents into `vector_db` with
`scope = 'platform'`, `client_id = NULL`:

```python
async def seed_platform_document(
    supabase_client,
    file_path: str,
    category: str,
    description: str,
):
    """Upload a platform knowledge document through the standard pipeline."""
    # 1. Upload file to Supabase Storage (knowledge-base bucket, platform/ prefix)
    # 2. INSERT into vector_db.documents with scope='platform', client_id=NULL
    # 3. Invoke process-document Edge Function
    # 4. Embedding + metadata enrichment happens automatically via pgmq
```

### 5.2 Platform Knowledge Documents

Prepare markdown/text files for each category in `seeds/platform_knowledge/`:

| File | Category | Description |
|------|----------|-------------|
| `statistical_methods.md` | `statistical_knowledge` | Mean, median, mode, std dev, distributions, hypothesis testing, correlation |
| `br_tax_guide.md` | `tax_knowledge` | ICMS, PIS, COFINS, ISS, fiscal calendar, NF-e rules |
| `business_fundamentals.md` | `business_knowledge` | KPIs, unit economics, forecasting, P&L, cash flow |
| `data_analysis_playbook.md` | `task_specific` | Existing playbook from `seeds/data_analysis_Playbook.md` |

### 5.3 Admin Management

Initially: CLI-only via the seeding script. Future: Vizu admin panel for
upload/management of platform-scoped documents (out of scope for this implementation).

---

## Phase 6 — Frontend Upload Enhancements

**Files touched**:
- `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx`
- `apps/vizu_dashboard/src/services/knowledgeBaseService.ts`
- `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts`

### 6.1 Upload Modal Enhancements

Add to the upload flow:

- **Description** (textarea) — User describes the document content
- **Category** (dropdown) — User selects from predefined list:
  - `dados_negocio` — Dados de Negócio
  - `contexto_empresa` — Contexto da Empresa
  - `documentos` — Documentos
  - `conhecimento_ia` — Conhecimento da IA

### 6.2 Update `knowledgeBaseService.ts`

```typescript
interface UploadOptions {
  forceComplex?: boolean;
  description?: string;
  category?: string;
}

async uploadSimpleFile(file: File, clientId: string, options?: UploadOptions) {
  // ... existing upload logic ...
  // Add description + category to documents row
  const { data: docData } = await supabase
    .from('documents')
    .insert({
      client_id: clientId,
      file_name: file.name,
      file_type: ext,
      storage_path: storagePath,
      source: 'upload',
      processing_mode: 'simple',
      description: options?.description || null,
      category: options?.category || null,
      scope: 'client',  // always client when uploaded from dashboard
    })
    .select()
    .single();
  // ...
}
```

### 6.3 Display Enriched Metadata

After a document finishes processing (status = `completed`), the documents table
shows additional columns:

- **Category** badge
- **Theme** (from first chunk's metadata, as a tag)
- **Description** (truncated, with tooltip)

---

## Phase 7 — Config & Backward Compatibility

**Files touched**:
- `libs/vizu_models/src/vizu_models/knowledge_base_config.py`
- `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py`

### 7.1 Extended `rag_search_config` Shape

All new keys have sensible defaults — existing clients continue working without changes:

```json
{
  "top_k": 5,
  "score_threshold": 0.5,
  "rerank": true,
  "rerank_top_k": 3,
  "search_mode": "hybrid",
  "fusion_strategy": "rrf",
  "keyword_weight": 0.4,
  "vector_weight": 0.6,
  "scope": ["platform", "client"],
  "categories": null,
  "reranker_type": "cross-encoder"
}
```

### 7.2 Backward Compatibility Guarantees

| Component | Strategy |
|-----------|----------|
| `match_documents` RPC | Untouched. Used when `search_mode = "semantic"` |
| `SupabaseVectorRetriever` | Remains in codebase. Factory selects based on `search_mode` |
| `LLMReranker` | Remains in codebase. Used when `reranker_type = "llm"` |
| `search-documents` EF | Default params match current behavior; new params are optional |
| `rag_search_config` JSON | All new keys have defaults; missing keys = current behavior |
| Client documents | Backfill migration adds `scope = 'client'` (already the default) |
| Existing chunks | Backfill adds `fts` tsvector; `scope`/`category` defaulted |

---

## Coding Sessions Plan

### Session 1 — Foundation: Schema + Metadata Pipeline (Phases 1 & 2)

**Effort**: High — complex SQL migration, new triggers, new Edge Function, pgmq integration.

**Rationale**: Phases 1 and 2 are tightly coupled database-layer work. The metadata
pipeline depends on the schema changes (scope, fts, category columns). Both are pure
Supabase (SQL + Edge Functions) with no Python changes. Completing them together gives
us the full enriched data layer before building the retriever.

| Step | Description | Est. Effort |
|------|-------------|-------------|
| 1.1 | Write migration SQL: extensions, scope columns, constraints, indexes | Medium |
| 1.2 | Write `immutable_unaccent` + tsvector trigger + GIN index + backfill | Medium |
| 1.3 | Update RLS policies for platform scope | Low |
| 1.4 | Write `hybrid_match_documents` RPC (full SQL with RRF + weighted fusion) | High |
| 1.5 | Create `metadata_jobs` queue + trigger + `process_metadata` cron function | Medium |
| 1.6 | Create `enrich-metadata` Edge Function (LLM call + JSONB merge + DLQ) | High |
| 1.7 | Update `process-document` EF to propagate scope + category to chunks | Low |
| 1.8 | Apply migration to Supabase (via `supabase db push` or migration tool) | Low |
| 1.9 | Test: insert test chunks, verify tsvector, verify metadata queue, verify RLS | Medium |

**Deliverables**:
- Migration file `supabase/migrations/YYYYMMDD_hybrid_retriever_schema.sql`
- Edge Function `supabase/functions/enrich-metadata/index.ts`
- Updated `supabase/functions/process-document/index.ts`
- All triggers, indexes, RLS policies, RPCs verified working

**Verification**:
```sql
-- After migration, verify:
SELECT count(*) FROM vector_db.document_chunks WHERE fts IS NULL;      -- Should be 0
SELECT * FROM vector_db.hybrid_match_documents(
  'client-uuid', embed('test query'), 'test query', 5, 0.3
);
-- Insert a test chunk, verify pgmq metadata_jobs has a message
-- Verify platform doc is readable by any client_id via RLS
```

---

### Session 2 — Hybrid Retriever + Config (Phases 3 & 7)

**Effort**: Medium — Python class + Edge Function update + config wiring. Well-scoped.

**Rationale**: The hybrid retriever is the core Python-side change. Phase 7 (config) is
a direct dependency — the retriever reads fusion strategy, weights, and scope from the
config. These should be built and tested together to ensure end-to-end flow.

| Step | Description | Est. Effort |
|------|-------------|-------------|
| 2.1 | Create `HybridRetriever` class in `retriever.py` | Medium |
| 2.2 | Update `search-documents` EF to accept hybrid params + route to new RPC | Medium |
| 2.3 | Update `factory.py` to read new config keys + instantiate `HybridRetriever` | Medium |
| 2.4 | Update `_format_docs` to show combined score + scope | Low |
| 2.5 | Update `_build_documents` to parse new fields (keyword_score, combined_score, scope, category) | Low |
| 2.6 | Add defaults to `rag_search_config` shape (no DB migration needed) | Low |
| 2.7 | Unit tests: mock HTTP calls, verify payload construction, fusion param passing | Medium |
| 2.8 | Integration test: end-to-end query through hybrid flow | Medium |
| 2.9 | Lint + format (`ruff check --fix` + `ruff format`) | Low |

**Deliverables**:
- Updated `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py`
- Updated `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`
- Updated `supabase/functions/search-documents/index.ts`
- Test files in `libs/vizu_rag_factory/tests/`

**Verification**:
```python
# Test that a hybrid query returns results from both semantic + keyword paths
# Test that scope=["platform"] returns only platform docs
# Test that scope=["client"] returns only that client's docs
# Test that categories filter works
# Test backward compat: search_mode="semantic" uses old SupabaseVectorRetriever
```

---

### Session 3 — Cross-Encoder Reranker (Phase 4)

**Effort**: Medium — self-contained, but needs dependency management + model loading strategy.

**Rationale**: The cross-encoder is independent from the hybrid retriever — it operates
on *any* list of documents regardless of how they were retrieved. It has its own dependency
chain (`sentence-transformers`, `torch`/`onnxruntime`) that affects Docker image size and
startup time, so it should be handled in a focused session.

| Step | Description | Est. Effort |
|------|-------------|-------------|
| 3.1 | Add `sentence-transformers` (+ `torch` or `onnxruntime`) to `pyproject.toml` | Low |
| 3.2 | Implement `CrossEncoderReranker` class with lazy model loading | Medium |
| 3.3 | Update `factory.py` reranker selection logic (`reranker_type` config key) | Low |
| 3.4 | Unit test: verify scoring + sorting with mock model | Medium |
| 3.5 | Integration test: actual model inference on sample PT-BR query-doc pairs | Medium |
| 3.6 | Benchmark: measure latency per rerank call (aim < 200ms for 10 docs on CPU) | Medium |
| 3.7 | Docker: verify image builds with new deps, check size impact | Medium |
| 3.8 | Lint + format | Low |

**Deliverables**:
- Updated `libs/vizu_rag_factory/src/vizu_rag_factory/reranker.py` (new class + existing preserved)
- Updated `libs/vizu_rag_factory/pyproject.toml`
- Updated `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`
- Test + benchmark results

**Verification**:
```python
# Load bge-reranker-v2-m3, rerank 10 PT-BR docs for a business query
# Verify top-ranked doc is the most relevant
# Verify rerank_score is populated in metadata
# Benchmark: < 200ms for 10 documents on CPU
# Verify lazy loading: model only loaded on first rerank call
```

**Decision Point**: If `torch` dependency makes the Docker image too large (>2GB increase),
pivot to ONNX runtime or a hosted inference endpoint (HuggingFace Inference API, Replicate).

---

### Session 4 — Platform Knowledge + Frontend (Phases 5 & 6)

**Effort**: Medium — seeding script is straightforward; frontend is UI changes with
existing patterns.

**Rationale**: These are the user-facing layers that depend on all previous sessions.
Platform knowledge seeding requires the scope column (Session 1) and triggers the
metadata pipeline (Session 1). The frontend upload changes save description + category
to the documents table (Session 1) and display enriched metadata. Both are independent
of each other but share the same dependency, so they're grouped for efficiency.

| Step | Description | Est. Effort |
|------|-------------|-------------|
| 4.1 | Write platform knowledge markdown files in `seeds/platform_knowledge/` | Medium |
| 4.2 | Write `scripts/seed_platform_knowledge.py` seeding script | Medium |
| 4.3 | Run seeding script → verify platform docs are ingested + enriched | Low |
| 4.4 | Update `AdminKnowledgeBasePage.tsx` upload modal (description + category fields) | Medium |
| 4.5 | Update `knowledgeBaseService.ts` (pass description + category on upload) | Low |
| 4.6 | Update documents table UI (show category badge, theme tag, description) | Medium |
| 4.7 | Verify: upload with metadata → processing → enrichment → display | Medium |
| 4.8 | Lint (Python + TypeScript) | Low |

**Deliverables**:
- `seeds/platform_knowledge/` directory with curated knowledge files
- `scripts/seed_platform_knowledge.py`
- Updated `AdminKnowledgeBasePage.tsx`
- Updated `knowledgeBaseService.ts`

**Verification**:
```
- Platform knowledge visible in hybrid search results (scope: platform)
- Upload a client doc with description + category → verify stored correctly
- After processing, enriched metadata (word_cloud, theme) visible in UI
- Platform docs NOT editable/deletable by clients via dashboard
```

---

## Session Dependency Graph

```
Session 1 (Schema + Metadata Pipeline)
    │
    ├──────────────┐
    │              │
    ▼              ▼
Session 2       Session 3
(Retriever)     (Reranker)
    │              │
    └──────┬───────┘
           │
           ▼
      Session 4
  (Platform KB + Frontend)
```

Sessions 2 and 3 can run **in parallel** — they are independent of each other.
Session 4 depends on Session 1 (for schema) and benefits from Sessions 2+3 being
complete (for end-to-end testing).

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `hybrid_match_documents` RPC is slow on large chunk tables | High latency on search | Pre-filter by scope+client before expensive cosine op; EXPLAIN ANALYZE on real data; add composite indexes if needed |
| `bge-reranker-v2-m3` model bloats Docker image | +2GB image size, slow cold starts | Use ONNX quantized version or hosted inference endpoint |
| `enrich-metadata` LLM costs at scale | Cost per chunk ~$0.001 (gpt-4.1-mini), but 10K chunks = $10 | Batch chunks, skip metadata for very short chunks, cap with budget alert |
| tsvector `'portuguese'` config misses English terms | Reduced keyword recall for English content | Consider `'simple'` config as fallback or multi-language tsvector |
| Platform knowledge goes stale | Incorrect shared context | Version flag + periodic review cron; `updated_at` tracking on platform docs |
| Backfill tsvector on 100K+ chunks is slow | Migration timeout | Run in batches: `WHERE fts IS NULL LIMIT 1000` in a loop; or use `pg_cron` batch job |

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|---------------|
| Retrieval relevance | +15% nDCG vs pure semantic | A/B test on labeled query set (Langfuse evaluation) |
| Keyword+semantic recall | Top-5 should contain both statistical terms AND business context for mixed queries | Manual evaluation on 20 representative queries |
| Metadata coverage | 100% of chunks have `word_cloud` + `theme` within 5 min of upload | Monitor `metadata_jobs` queue length + DLQ |
| Search latency (p95) | < 500ms including reranking | Langfuse trace latency dashboard |
| Platform knowledge availability | Shared docs returned for all clients when `scope` includes `platform` | Automated test per client tier |
