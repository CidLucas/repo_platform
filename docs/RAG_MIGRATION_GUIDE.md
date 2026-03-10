# RAG Migration Guide — Qdrant → Supabase

> **Status:** ⚠️ ARCHIVED — Migration completed, document is historical reference only
> **Created:** 2026-03-04
> **Archived:** 2026-03-10
>
> ---
>
> **⚠️ This document is outdated.** The Qdrant → Supabase migration has been fully completed
> and the RAG pipeline has been significantly overhauled since this plan was written.
>
> **Key changes since this plan:**
> - `embed` Edge Function (gte-small) **removed** — embedding is now inline in `process-document` using **Cohere embed-multilingual-light-v3.0**
> - pgmq `embedding_jobs` queue, cron jobs, and embedding triggers **removed**
> - `search-documents` uses **Cohere** for query embedding (not gte-small)
> - `process-document` chunks at **400 tokens** (not 500 chars), sentence-aware overlap
> - Hybrid retrieval with **RRF/weighted fusion**, **Cohere reranker**, **MMR diversifier**, and optional **query preprocessing**
> - `score_threshold` lowered to **0.3** (was 0.5)
> - `theme` column added to `document_chunks` for chunk-level filtering
>
> **For current documentation, see:**
> - [`HYBRID_RETRIEVER_AS_BUILT.md`](./HYBRID_RETRIEVER_AS_BUILT.md) — Complete as-built reference
> - [`RAG_PIPELINE_ANALYSIS.md`](./RAG_PIPELINE_ANALYSIS.md) — Original analysis with resolution status
> - [`RAG_OVERHAUL_PLAN.md`](./RAG_OVERHAUL_PLAN.md) — Overhaul plan (Phases 1–6, all complete)
>
> ---

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Phase 1 — Database Schema (`vector_db`)](#phase-1--database-schema-vector_db)
3. [Phase 2 — Edge Functions](#phase-2--edge-functions)
4. [Phase 3 — Docling in `vizu_parsers`](#phase-3--docling-in-vizu_parsers)
5. [Phase 4 — Dashboard: Knowledge Base Admin Page](#phase-4--dashboard-knowledge-base-admin-page)
6. [Phase 5 — Refactor `file_upload_api` for Complex Files](#phase-5--refactor-file_upload_api-for-complex-files)
7. [Phase 6 — Migrate RAG Retrieval](#phase-6--migrate-rag-retrieval)
8. [Phase 7 — ChatPanel File Upload Button](#phase-7--chatpanel-file-upload-button)
9. [Phase 8 — Deprecation & Cleanup](#phase-8--deprecation--cleanup)
10. [Verification Checklist](#verification-checklist)
11. [Key Decisions & Rationale](#key-decisions--rationale)
12. [File Reference Map](#file-reference-map)

---

## 1. Architecture Overview

### Current State (broken)

```
file_upload_api ──► Supabase Storage     (files sit unprocessed)
file_processing_worker ──► GCS + Pub/Sub ──► Qdrant  (disconnected from upload API)
vizu_rag_factory ──► Qdrant retriever    (requires separate Qdrant service)
vizu_parsers lib ──► NOT USED by either service
Dashboard ──► no upload UI for RAG
ChatPanel ──► "Anexar" button exists but is non-functional
```

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                     UPLOAD PATHS                            │
├─────────────────────┬───────────────────────────────────────┤
│  SIMPLE FILES       │  COMPLEX FILES                       │
│  (≤6MB, text-based) │  (scanned PDFs, images, OCR needed)  │
│                     │                                       │
│  Dashboard/Chat     │  Dashboard/Chat                       │
│       │             │       │                               │
│       ▼             │       ▼                               │
│  Supabase Storage   │  Supabase Storage (TUS resumable)     │
│  (standard upload   │       │                               │
│   from frontend)    │       ▼                               │
│       │             │  file_upload_api /v1/upload/process    │
│       ▼             │  (Python: docling parse + chunk)       │
│  Edge Fn:           │       │                               │
│  process-document   │       ▼                               │
│  (Deno: parse,      │  INSERT chunks into                   │
│   chunk, embed      │  vector_db.document_chunks            │
│   with gte-small)   │  (no embedding)                       │
│       │             │       │                               │
│       ▼             │       ▼                               │
│  INSERT chunks WITH │  pgmq queue ──► Edge Fn: embed        │
│  embedding directly │  (gte-small, async, auto-retry)       │
│  into vector_db     │       │                               │
├─────────────────────┴───────┴───────────────────────────────┤
│                  vector_db.document_chunks                   │
│            (halfvec(384), HNSW index, RLS by client_id)     │
├─────────────────────────────────────────────────────────────┤
│                     RETRIEVAL                               │
│  Edge Fn: search-documents                                  │
│  (embed query with gte-small ──► match_documents RPC)       │
│       │                                                     │
│       ▼                                                     │
│  SupabaseVectorRetriever (LangChain BaseRetriever)          │
│  in vizu_rag_factory ──► agent chain                        │
└─────────────────────────────────────────────────────────────┘
```

### File Classification

| Category | Extensions | Processing Path | Parser |
|----------|-----------|-----------------|--------|
| **Simple** | `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html` | Edge Function `process-document` | Deno native (text read, CSV split, XML/HTML strip tags) |
| **Simple** | `.pdf` (text-only, small) | Edge Function `process-document` | `pdf-parse` via npm in Deno |
| **Simple** | `.docx` (text-only) | Edge Function `process-document` | `mammoth` via npm in Deno (extracts raw text) |
| **Complex** | `.pdf` (scanned, images, complex tables) | `file_upload_api` → Python | `docling` (OCR, table extraction, layout analysis) |
| **Complex** | `.pptx`, `.xlsx` | `file_upload_api` → Python | `docling` (structured extraction) |
| **Complex** | Any file with images/ML needs | `file_upload_api` → Python | `docling` |

**Routing decision is made client-side** based on file extension + optional user toggle for "advanced processing".

---

## Phase 1 — Database Schema (`vector_db`)

### Goal
Create the `vector_db` schema in Supabase with tables, RLS, triggers, queue infrastructure, and search RPC.

### Files to Create/Modify

| File | Action |
|------|--------|
| `supabase/migrations/20260305_create_vector_db_schema.sql` | **CREATE** |
| `supabase/config.toml` | **MODIFY** — expose `vector_db` schema |

### Step 1.1 — Migration SQL

Create `supabase/migrations/20260305_create_vector_db_schema.sql`:

```sql
-- ============================================================
-- VECTOR DB SCHEMA — RAG document storage with auto-embeddings
-- ============================================================

-- 1. Create schema
CREATE SCHEMA IF NOT EXISTS vector_db;

-- 2. Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgmq;
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS hstore WITH SCHEMA extensions;

-- 3. Utility schema + functions
CREATE SCHEMA IF NOT EXISTS util;

-- Project URL from Vault (needed to invoke Edge Functions from pg_net)
CREATE FUNCTION util.project_url()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  secret_value text;
BEGIN
  SELECT decrypted_secret INTO secret_value
  FROM vault.decrypted_secrets
  WHERE name = 'project_url';
  RETURN secret_value;
END;
$$;

-- Generic Edge Function invoker
CREATE OR REPLACE FUNCTION util.invoke_edge_function(
  name text,
  body jsonb,
  timeout_milliseconds int = 5 * 60 * 1000
)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
  headers_raw text;
  auth_header text;
BEGIN
  headers_raw := current_setting('request.headers', true);
  auth_header := CASE
    WHEN headers_raw IS NOT NULL THEN (headers_raw::json->>'authorization')
    ELSE NULL
  END;
  PERFORM net.http_post(
    url => util.project_url() || '/functions/v1/' || name,
    headers => jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', auth_header
    ),
    body => body,
    timeout_milliseconds => timeout_milliseconds
  );
END;
$$;

-- Generic trigger to clear a column on update (for re-embedding)
CREATE OR REPLACE FUNCTION util.clear_column()
RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
  clear_column text := TG_ARGV[0];
BEGIN
  NEW := NEW #= hstore(clear_column, NULL);
  RETURN NEW;
END;
$$;

-- 4. pgmq queue for embedding jobs
SELECT pgmq.create('embedding_jobs');

-- Generic trigger function to queue embedding jobs
CREATE OR REPLACE FUNCTION util.queue_embeddings()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  content_function text = TG_ARGV[0];
  embedding_column text = TG_ARGV[1];
BEGIN
  PERFORM pgmq.send(
    queue_name => 'embedding_jobs',
    msg => jsonb_build_object(
      'id', NEW.id,
      'schema', TG_TABLE_SCHEMA,
      'table', TG_TABLE_NAME,
      'contentFunction', content_function,
      'embeddingColumn', embedding_column
    )
  );
  RETURN NEW;
END;
$$;

-- Process embedding jobs from queue (called by pg_cron)
CREATE OR REPLACE FUNCTION util.process_embeddings(
  batch_size int = 10,
  max_requests int = 10,
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
        queue_name => 'embedding_jobs',
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
      name => 'embed',
      body => batch,
      timeout_milliseconds => timeout_milliseconds
    );
  END LOOP;
END;
$$;

-- Schedule embedding processing every 10 seconds
SELECT cron.schedule(
  'process-embeddings',
  '10 seconds',
  $$ SELECT util.process_embeddings(); $$
);

-- ============================================================
-- 5. TABLES
-- ============================================================

-- Documents table (file-level metadata)
CREATE TABLE vector_db.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES public.clientes_vizu(client_id) ON DELETE CASCADE,
  title TEXT,
  file_name TEXT NOT NULL,
  file_type TEXT,  -- extension: pdf, docx, csv, etc.
  storage_path TEXT,  -- path in Supabase Storage bucket
  source TEXT NOT NULL DEFAULT 'upload' CHECK (source IN ('upload', 'chat', 'url', 'api')),
  processing_mode TEXT NOT NULL DEFAULT 'simple' CHECK (processing_mode IN ('simple', 'complex')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  error_message TEXT,
  chunk_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_documents_client_id ON vector_db.documents(client_id);
CREATE INDEX idx_documents_status ON vector_db.documents(status);

-- Document chunks with embeddings
CREATE TABLE vector_db.document_chunks (
  id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  document_id UUID NOT NULL REFERENCES vector_db.documents(id) ON DELETE CASCADE,
  client_id UUID NOT NULL,  -- denormalized for RLS performance
  content TEXT NOT NULL,
  embedding extensions.halfvec(384),  -- gte-small dimensions
  chunk_index INTEGER NOT NULL DEFAULT 0,
  metadata JSONB DEFAULT '{}',  -- lean: { source_file, page, section }
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chunks_client_id ON vector_db.document_chunks(client_id);
CREATE INDEX idx_chunks_document_id ON vector_db.document_chunks(document_id);
CREATE INDEX idx_chunks_embedding ON vector_db.document_chunks
  USING hnsw (embedding extensions.halfvec_cosine_ops);

-- ============================================================
-- 6. EMBEDDING TRIGGERS (only for chunks inserted WITHOUT embedding)
-- ============================================================

-- Content function for embedding input
CREATE OR REPLACE FUNCTION vector_db.chunk_content_fn(row vector_db.document_chunks)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN row.content;
END;
$$;

-- Trigger: queue embedding job on insert ONLY if embedding is NULL
-- (simple path inserts WITH embedding, complex path inserts WITHOUT)
CREATE OR REPLACE FUNCTION vector_db.queue_embedding_if_null()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  IF NEW.embedding IS NULL THEN
    PERFORM pgmq.send(
      queue_name => 'embedding_jobs',
      msg => jsonb_build_object(
        'id', NEW.id,
        'schema', TG_TABLE_SCHEMA,
        'table', TG_TABLE_NAME,
        'contentFunction', 'vector_db.chunk_content_fn',
        'embeddingColumn', 'embedding'
      )
    );
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER embed_chunk_on_insert
  AFTER INSERT ON vector_db.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION vector_db.queue_embedding_if_null();

-- Clear embedding on content update (forces re-embed)
CREATE TRIGGER clear_chunk_embedding_on_update
  BEFORE UPDATE OF content
  ON vector_db.document_chunks
  FOR EACH ROW
  EXECUTE FUNCTION util.clear_column('embedding');

-- ============================================================
-- 7. SEARCH RPC
-- ============================================================

CREATE OR REPLACE FUNCTION vector_db.match_documents(
  p_client_id UUID,
  p_query_embedding extensions.halfvec(384),
  p_match_count INT DEFAULT 5,
  p_match_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE (
  id INTEGER,
  document_id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.metadata,
    1 - (dc.embedding <=> p_query_embedding) AS similarity
  FROM vector_db.document_chunks dc
  WHERE dc.client_id = p_client_id
    AND dc.embedding IS NOT NULL
    AND 1 - (dc.embedding <=> p_query_embedding) > p_match_threshold
  ORDER BY dc.embedding <=> p_query_embedding
  LIMIT p_match_count;
END;
$$;

-- ============================================================
-- 8. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE vector_db.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE vector_db.document_chunks ENABLE ROW LEVEL SECURITY;

-- Documents RLS
CREATE POLICY "Users can view own documents"
  ON vector_db.documents FOR SELECT
  USING (client_id = auth.uid());

CREATE POLICY "Users can insert own documents"
  ON vector_db.documents FOR INSERT
  WITH CHECK (client_id = auth.uid());

CREATE POLICY "Users can delete own documents"
  ON vector_db.documents FOR DELETE
  USING (client_id = auth.uid());

CREATE POLICY "Users can update own documents"
  ON vector_db.documents FOR UPDATE
  USING (client_id = auth.uid());

CREATE POLICY "Service role full access to documents"
  ON vector_db.documents FOR ALL
  USING (auth.role() = 'service_role');

-- Chunks RLS
CREATE POLICY "Users can view own chunks"
  ON vector_db.document_chunks FOR SELECT
  USING (client_id = auth.uid());

CREATE POLICY "Users can insert own chunks"
  ON vector_db.document_chunks FOR INSERT
  WITH CHECK (client_id = auth.uid());

CREATE POLICY "Users can delete own chunks"
  ON vector_db.document_chunks FOR DELETE
  USING (client_id = auth.uid());

CREATE POLICY "Service role full access to chunks"
  ON vector_db.document_chunks FOR ALL
  USING (auth.role() = 'service_role');

-- ============================================================
-- 9. HELPER: count embedded chunks for a document
-- ============================================================

CREATE OR REPLACE FUNCTION vector_db.get_document_embedding_progress(p_document_id UUID)
RETURNS TABLE (
  total_chunks INTEGER,
  embedded_chunks INTEGER,
  progress_pct FLOAT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    COUNT(*)::INTEGER AS total_chunks,
    COUNT(dc.embedding)::INTEGER AS embedded_chunks,
    CASE WHEN COUNT(*) > 0
      THEN (COUNT(dc.embedding)::FLOAT / COUNT(*)::FLOAT) * 100
      ELSE 0
    END AS progress_pct
  FROM vector_db.document_chunks dc
  WHERE dc.document_id = p_document_id;
$$;
```

### Step 1.2 — Expose schema in config.toml

**File:** `supabase/config.toml`

Add `vector_db` to the schemas list:

```diff
 [api]
 port = 54321
-schemas = ["public", "analytics_v2"]
-extra_search_path = ["public", "extensions"]
+schemas = ["public", "analytics_v2", "vector_db"]
+extra_search_path = ["public", "extensions", "vector_db"]
 max_rows = 1000
```

### Step 1.3 — Add Vault secret

**For local dev**, add to `supabase/seed.sql`:
```sql
SELECT vault.create_secret('http://api.supabase.internal:8000', 'project_url');
```

**For production**, run in SQL Editor:
```sql
SELECT vault.create_secret('https://<project-id>.supabase.co', 'project_url');
```

### Step 1.4 — Create Storage Bucket

Create `knowledge-base` bucket via Supabase Dashboard or migration:
```sql
INSERT INTO storage.buckets (id, name, public) VALUES ('knowledge-base', 'knowledge-base', false);
```

### Completion Criteria
- [ ] Migration applies without errors via `supabase db push` or `supabase migration up`
- [ ] `vector_db.documents` and `vector_db.document_chunks` tables exist
- [ ] RLS policies are active
- [ ] `vector_db.match_documents()` RPC is callable
- [ ] pgmq queue `embedding_jobs` exists
- [ ] pg_cron job `process-embeddings` is scheduled
- [ ] `knowledge-base` Storage bucket exists

---

## Phase 2 — Edge Functions

### Goal
Create 3 Edge Functions: `embed` (auto-embed worker), `process-document` (simple file parser), `search-documents` (retrieval endpoint).

### Files to Create/Modify

| File | Action |
|------|--------|
| `supabase/functions/embed/index.ts` | **CREATE** |
| `supabase/functions/process-document/index.ts` | **CREATE** |
| `supabase/functions/search-documents/index.ts` | **CREATE** |
| `supabase/config.toml` | **MODIFY** — register new functions |

### Step 2.1 — `embed` Edge Function (auto-embed worker)

**File:** `supabase/functions/embed/index.ts`

Called internally by `pg_net` via the pgmq cron job. Processes batched embedding jobs.

```typescript
// Overview of what this function does:
// 1. Receives a batch of jobs from pgmq (via pg_net HTTP call)
// 2. For each job: fetches content from vector_db.document_chunks
// 3. Generates embedding using built-in gte-small model
// 4. Updates the embedding column in the DB
// 5. Deletes processed jobs from the queue

// Key dependencies:
// - Supabase.ai.Session('gte-small') — built-in, zero API key
// - postgres (postgresjs) — direct DB connection via SUPABASE_DB_URL
// - zod — request validation

// Pattern: follows Supabase automatic-embeddings docs exactly
// See: https://supabase.com/docs/guides/ai/automatic-embeddings#step-4-create-the-edge-function
```

**Implementation details:**
- Model: `gte-small` (384 dimensions, built into Supabase Edge Runtime)
- Embedding call: `session.run(input, { mean_pool: true, normalize: true })`
- DB connection: `postgres(Deno.env.get('SUPABASE_DB_URL')!)`
- Batch processing: iterates jobs, embeds one-by-one, tracks completed/failed
- Error handling: failed jobs stay in pgmq queue (visibility timeout expires → auto-retry)
- Config: `verify_jwt = false` (internal only, called by pg_net)

### Step 2.2 — `process-document` Edge Function (simple file parser)

**File:** `supabase/functions/process-document/index.ts`

Handles parsing, chunking, and embedding for simple files directly in Deno.

```typescript
// Request: POST { document_id, storage_path, client_id, file_name, file_type }
// Response: 202 Accepted { document_id, status: "processing" }
// (actual work runs in background via EdgeRuntime.waitUntil)

// Processing pipeline:
// 1. Download file from Supabase Storage (knowledge-base bucket)
// 2. Parse based on file_type:
//    - txt, md: read as UTF-8 text
//    - csv: split rows, format each row as "col1: val1, col2: val2, ..."
//    - json: stringify each top-level entry
//    - xml, html: strip tags, extract text content
//    - pdf (text-only): use pdf-parse (npm:pdf-parse)
//    - docx (text-only): use mammoth (npm:mammoth) for raw text extraction
// 3. Chunk text: sliding window ~500 chars, 50 char overlap, split on \\n\\n then \\n then sentence
// 4. Embed each chunk: Supabase.ai.Session('gte-small')
// 5. Batch INSERT into vector_db.document_chunks WITH embedding (bypasses pgmq queue)
// 6. Update vector_db.documents: status=completed, chunk_count=N

// Pattern: same as run-sync (fire-and-forget with EdgeRuntime.waitUntil)
```

**Deno dependencies (npm imports):**
```typescript
import pdfParse from "npm:pdf-parse@1.1.1";
import mammoth from "npm:mammoth@1.8.0";
```

**Chunking algorithm (implement in Deno):**
```
1. Split text on double newlines (paragraphs)
2. For each paragraph > target_size: split on single newlines, then sentences
3. Accumulate chunks up to target_size (500 chars)
4. Overlap: include last 50 chars of previous chunk as prefix
5. Return array of { text, index, metadata: { page?, section? } }
```

**Config:** `verify_jwt = true` (called by authenticated frontend)

### Step 2.3 — `search-documents` Edge Function (retrieval)

**File:** `supabase/functions/search-documents/index.ts`

```typescript
// Request: POST { query: string, client_id: string, match_count?: number, match_threshold?: number }
// Response: { results: [{ id, document_id, content, metadata, similarity }] }

// Pipeline:
// 1. Embed query text using gte-small (same model as storage → consistency)
// 2. Call vector_db.match_documents RPC via direct Postgres
// 3. Return results

// Auth: verify_jwt = true (called by Python backend with service_role key,
//        or by frontend with user JWT)
```

### Step 2.4 — Register in config.toml

```toml
[functions.embed]
verify_jwt = false

[functions.process-document]
verify_jwt = true

[functions.search-documents]
verify_jwt = true
```

### Completion Criteria
- [ ] `supabase functions serve` starts all 3 functions without errors
- [ ] `curl POST /functions/v1/embed` with sample job batch → updates embedding column
- [ ] `curl POST /functions/v1/process-document` with a simple file → creates chunks with embeddings
- [ ] `curl POST /functions/v1/search-documents` with query → returns relevant results
- [ ] Edge functions deployed with `supabase functions deploy`

---

## Phase 3 — Docling in `vizu_parsers`

### Goal
Add docling as an optional dependency for complex document parsing (OCR, scanned PDFs, PPTX, XLSX). Keep existing parsers for simple formats. Add a routing helper `is_complex_file()`.

### Files to Create/Modify

| File | Action |
|------|--------|
| `libs/vizu_parsers/pyproject.toml` | **MODIFY** — add docling optional dep |
| `libs/vizu_parsers/src/vizu_parsers/parsers/docling_parser.py` | **CREATE** |
| `libs/vizu_parsers/src/vizu_parsers/parsers/router.py` | **MODIFY** — add extensions + `is_complex_file()` |
| `libs/vizu_parsers/src/vizu_parsers/parsers/__init__.py` | **MODIFY** — export new parser |

### Step 3.1 — Add docling dependency

**File:** `libs/vizu_parsers/pyproject.toml`

```toml
[tool.poetry.dependencies]
python = "^3.11"
pypdf = ">=4.0.0"
pandas = ">=2.0.0"

[tool.poetry.extras]
docling = ["docling"]

[tool.poetry.dependencies.docling]
version = ">=2.0.0"
optional = true
```

### Step 3.2 — Create DoclingParser

**File:** `libs/vizu_parsers/src/vizu_parsers/parsers/docling_parser.py`

```python
"""Parser using docling for complex document extraction (OCR, tables, images)."""

from io import BytesIO
from typing import BinaryIO

from vizu_parsers.parsers.base_parser import BaseParser


class DoclingParser(BaseParser):
    """Handles complex documents: scanned PDFs, DOCX with images, PPTX, XLSX.

    Requires the 'docling' extra: pip install vizu_parsers[docling]
    """

    def __init__(self):
        try:
            from docling.document_converter import DocumentConverter
            self._converter_cls = DocumentConverter
        except ImportError:
            raise ImportError(
                "docling is required for complex document parsing. "
                "Install with: pip install vizu_parsers[docling]"
            )

    def parse(self, file_stream: BytesIO | BinaryIO) -> str:
        """Extract text from complex documents using docling."""
        import tempfile
        import os

        # docling needs a file path, write stream to temp file
        file_stream.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            tmp.write(file_stream.read())
            tmp_path = tmp.name

        try:
            converter = self._converter_cls()
            result = converter.convert(tmp_path)
            return result.document.export_to_markdown()
        finally:
            os.unlink(tmp_path)
```

### Step 3.3 — Update ParserRouter

**File:** `libs/vizu_parsers/src/vizu_parsers/parsers/router.py`

Add these changes:

```python
# New constant: file extensions that need Python-side processing (docling)
COMPLEX_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}  # Note: .pdf CAN be simple too

# Extensions that Edge Functions can handle
SIMPLE_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".html", ".yaml", ".yml"}

def is_complex_file(filename: str) -> bool:
    """Returns True if the file likely needs Python/docling processing.

    Used by frontend to decide upload path:
    - True → TUS resumable upload → file_upload_api /v1/upload/process
    - False → standard upload → process-document Edge Function

    Note: .pdf and .docx can be either simple or complex.
    Default conservative: mark them as complex. Frontend can offer
    a toggle "Use advanced processing" for these ambiguous types.
    """
    ext = Path(filename).suffix.lower()
    return ext in COMPLEX_EXTENSIONS

# Add to PARSER_MAP:
# ".docx" → DoclingParser (try-import, fallback to warning)
# ".pptx" → DoclingParser
# ".xlsx" → DoclingParser
```

### Step 3.4 — SmartPDFParser (optional enhancement)

For the Python path, create a smart PDF parser that tries pypdf first and falls back to docling if the text extraction is too sparse (indicating a scanned document):

```python
class SmartPDFParser(BaseParser):
    """Try fast pypdf extraction first; fall back to docling for scanned/image PDFs."""

    def parse(self, file_stream: BytesIO | BinaryIO) -> str:
        from vizu_parsers.parsers.pdf_parser import PDFParser

        # First try: fast text extraction
        text = PDFParser().parse(file_stream)

        # Heuristic: if extracted text is very short relative to file size, likely scanned
        file_stream.seek(0, 2)  # seek to end
        file_size = file_stream.tell()
        file_stream.seek(0)

        chars_per_kb = len(text) / max(file_size / 1024, 1)

        if chars_per_kb < 10 and file_size > 5000:  # likely scanned
            try:
                from vizu_parsers.parsers.docling_parser import DoclingParser
                text = DoclingParser().parse(file_stream)
            except ImportError:
                pass  # docling not installed, return whatever pypdf got

        return text
```

### Completion Criteria
- [ ] `from vizu_parsers.parsers.docling_parser import DoclingParser` works when docling installed
- [ ] `ImportError` with helpful message when docling not installed
- [ ] `is_complex_file("report.pdf")` returns `True`
- [ ] `is_complex_file("data.csv")` returns `False`
- [ ] `DoclingParser().parse(docx_stream)` returns markdown text
- [ ] `SmartPDFParser` falls back to docling for scanned PDFs

---

## Phase 4 — Dashboard: Knowledge Base Admin Page

### Goal
New admin page at `/dashboard/admin/knowledge-base` with file upload (simple + complex paths), document list, status tracking, and delete capability.

### Files to Create/Modify

| File | Action |
|------|--------|
| `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx` | **CREATE** |
| `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts` | **CREATE** |
| `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` | **CREATE** |
| `apps/vizu_dashboard/src/components/admin/AdminSidebar.tsx` | **MODIFY** — add sidebar item |
| `apps/vizu_dashboard/src/routes/dashboardRoutes.tsx` | **MODIFY** — add route |
| `apps/vizu_dashboard/src/pages/admin/index.ts` | **MODIFY** — export new page |

### Step 4.1 — Service Layer

**File:** `apps/vizu_dashboard/src/services/knowledgeBaseService.ts`

```typescript
// Key functions:
export async function listDocuments(clientId: string): Promise<KBDocument[]>
  // supabase.from('vector_db.documents').select('*').eq('client_id', clientId).order('created_at', { ascending: false })

export async function deleteDocument(documentId: string, storagePath: string): Promise<void>
  // 1. supabase.storage.from('knowledge-base').remove([storagePath])
  // 2. supabase.from('vector_db.documents').delete().eq('id', documentId)
  // (chunks auto-deleted via ON DELETE CASCADE)

export async function getDocumentProgress(documentId: string): Promise<EmbeddingProgress>
  // supabase.rpc('get_document_embedding_progress', { p_document_id: documentId })

export async function uploadSimpleFile(file: File, clientId: string): Promise<string>
  // 1. Generate storage path: `${clientId}/${uuid}-${file.name}`
  // 2. supabase.storage.from('knowledge-base').upload(path, file)
  // 3. supabase.from('vector_db.documents').insert({
  //      client_id: clientId, file_name: file.name,
  //      file_type: extension, storage_path: path,
  //      source: 'upload', processing_mode: 'simple', status: 'processing'
  //    })
  // 4. supabase.functions.invoke('process-document', { body: { document_id, storage_path, client_id, file_name, file_type } })
  // 5. Return document_id

export async function uploadComplexFile(file: File, clientId: string): Promise<string>
  // 1. Generate storage path: `${clientId}/${uuid}-${file.name}`
  // 2. Upload via TUS resumable upload to Supabase Storage
  //    (use tus-js-client library, endpoint: `${supabaseUrl}/storage/v1/upload/resumable`)
  // 3. supabase.from('vector_db.documents').insert({
  //      client_id: clientId, file_name: file.name,
  //      file_type: extension, storage_path: path,
  //      source: 'upload', processing_mode: 'complex', status: 'pending'
  //    })
  // 4. POST to file_upload_api /v1/upload/process with { storage_path, file_name, client_id, document_id }
  // 5. Return document_id

// Helper: classify file
export function isComplexFile(fileName: string): boolean
  // Complex: .pptx, .xlsx, or user-selected "advanced processing"
  // Simple: .txt, .md, .csv, .json, .xml, .html, .pdf, .docx (default)
  // Note: .pdf and .docx default to SIMPLE (Edge Function handles text-only)
  //       User can toggle "Advanced processing" for these if they have images/tables
```

**Types:**
```typescript
interface KBDocument {
  id: string;
  client_id: string;
  title: string | null;
  file_name: string;
  file_type: string | null;
  storage_path: string | null;
  source: 'upload' | 'chat' | 'url' | 'api';
  processing_mode: 'simple' | 'complex';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

interface EmbeddingProgress {
  total_chunks: number;
  embedded_chunks: number;
  progress_pct: number;
}
```

### Step 4.2 — Hook

**File:** `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts`

```typescript
export function useKnowledgeBase() {
  const { clientId } = useAuth();
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  // Fetch documents on mount + poll every 5s while any doc is processing
  // Upload file (auto-routes simple vs complex)
  // Delete document
  // Refresh manually
}
```

### Step 4.3 — Page Component

**File:** `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx`

```
┌─────────────────────────────────────────────────────┐
│  AdminLayout                                        │
│  ┌───────────────────────────────────────────────┐  │
│  │ Header: "Base de Conhecimento"                │  │
│  │ Subtitle: "Upload documents for your AI..."   │  │
│  ├───────────────────────────────────────────────┤  │
│  │ Upload Zone (drag-and-drop + file picker)     │  │
│  │ ┌───────────────────────────────────────────┐ │  │
│  │ │  📁 Arraste arquivos ou clique para       │ │  │
│  │ │  selecionar                                │ │  │
│  │ │  PDF, DOCX, CSV, TXT, MD, JSON, XML, HTML │ │  │
│  │ │                                            │ │  │
│  │ │  ☐ Processamento avançado (OCR/tabelas)   │ │  │
│  │ └───────────────────────────────────────────┘ │  │
│  ├───────────────────────────────────────────────┤  │
│  │ Documents Table                               │  │
│  │ ┌──────┬──────┬────────┬───────┬───────┬────┐ │  │
│  │ │ Nome │ Tipo │ Status │ Chunks│ Data  │ 🗑 │ │  │
│  │ ├──────┼──────┼────────┼───────┼───────┼────┤ │  │
│  │ │ f.pdf│ pdf  │ ✅done │ 24    │ 03/04 │ 🗑 │ │  │
│  │ │ d.csv│ csv  │ ⏳ 80% │ 10/12 │ 03/04 │ 🗑 │ │  │
│  │ │ r.doc│ docx │ ❌fail │ 0     │ 03/03 │ 🗑 │ │  │
│  │ └──────┴──────┴────────┴───────┴───────┴────┘ │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Key UI details:**
- **Drag-and-drop zone**: Uses `onDragOver`/`onDrop` + hidden `<input type="file" multiple>`
- **Advanced processing toggle**: Checkbox. When checked, even .pdf/.docx go through the complex path (docling). Default: unchecked.
- **Status badges**: `pending` (gray), `processing` (blue spinner), `completed` (green check), `failed` (red X with hover tooltip showing `error_message`)
- **Embedding progress**: For processing docs, show `embedded_chunks / total_chunks` with a small progress bar
- **Auto-refresh**: Poll `listDocuments()` every 5s while any doc has status `pending` or `processing`
- **Empty state**: Illustration + "Upload your first document" message

### Step 4.4 — Sidebar + Route

**Sidebar** (`AdminSidebar.tsx`): Add between "Minhas fontes" and "Dados e privacidade":
```tsx
<SidebarItem to="/dashboard/admin/knowledge-base" icon={FiBook} label="Base de Conhecimento" />
```

**Route** (`dashboardRoutes.tsx`): Add:
```tsx
{ path: "/dashboard/admin/knowledge-base", element: <AdminKnowledgeBasePage /> }
```

### Step 4.5 — Install tus-js-client

```bash
cd apps/vizu_dashboard && npm install tus-js-client
```

### Completion Criteria
- [ ] Sidebar shows "Base de Conhecimento" item with book icon
- [ ] Page renders with upload zone and documents table
- [ ] Uploading a `.txt` file: goes through simple path (standard upload → `process-document` Edge Function)
- [ ] Uploading a `.pptx` file: goes through complex path (TUS upload → `file_upload_api`)
- [ ] Checking "Processamento avançado" + uploading `.pdf`: goes through complex path
- [ ] Documents list shows status with auto-refresh
- [ ] Delete removes document, chunks, and storage file
- [ ] RLS: only shows documents belonging to the logged-in client

---

## Phase 5 — Refactor `file_upload_api` for Complex Files

### Goal
Add a new endpoint that receives pre-uploaded files (already in Supabase Storage) and processes them with docling.

### Files to Create/Modify

| File | Action |
|------|--------|
| `services/file_upload_api/src/file_upload_api/api/router.py` | **MODIFY** — add `POST /v1/upload/process` |
| `services/file_upload_api/src/file_upload_api/api/dependencies.py` | **MODIFY** — fix auth stub |
| `services/file_upload_api/src/file_upload_api/services/processing_service.py` | **CREATE** |
| `services/file_upload_api/src/file_upload_api/schemas/upload_schemas.py` | **MODIFY** — add new schemas |
| `services/file_upload_api/pyproject.toml` | **MODIFY** — add vizu_parsers[docling] dep |

### Step 5.1 — Fix Auth

**File:** `services/file_upload_api/src/file_upload_api/api/dependencies.py`

Replace the hardcoded `DUMMY_CLIENTE_VIZU_ID` with real JWT extraction:

```python
from vizu_auth import verify_api_key, extract_client_id_from_jwt

async def get_client_id_from_token(request: Request) -> uuid.UUID:
    """Extract client_id from JWT Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth_header.split(" ", 1)[1]
    client_id = extract_client_id_from_jwt(token)
    return uuid.UUID(client_id)
```

### Step 5.2 — Processing Service

**File:** `services/file_upload_api/src/file_upload_api/services/processing_service.py`

```python
class DocumentProcessingService:
    """Processes complex files: download from Storage → parse with docling → chunk → insert to vector_db."""

    async def process_document(
        self,
        document_id: str,
        storage_path: str,
        file_name: str,
        client_id: str,
    ) -> dict:
        # 1. Update document status to 'processing'
        supabase.from_('vector_db.documents').update({'status': 'processing'}).eq('id', document_id).execute()

        try:
            # 2. Download file from Supabase Storage
            file_bytes = supabase.storage.from_('knowledge-base').download(storage_path)

            # 3. Parse and chunk using vizu_parsers (with docling for complex formats)
            from vizu_parsers.pipeline import parse_and_chunk
            chunks = parse_and_chunk(
                file_stream=BytesIO(file_bytes),
                filename=file_name,
                chunk_size=500,
                chunk_overlap=50,
            )

            # 4. Batch insert chunks into vector_db.document_chunks (WITHOUT embedding)
            chunk_records = [
                {
                    'document_id': document_id,
                    'client_id': client_id,
                    'content': chunk.text,
                    'chunk_index': chunk.index,
                    'metadata': {
                        'source_file': file_name,
                        **(chunk.metadata or {}),
                    },
                    # embedding is NULL → trigger queues to pgmq → embed Edge Function handles it
                }
                for chunk in chunks
            ]

            # Insert in batches of 100
            for i in range(0, len(chunk_records), 100):
                batch = chunk_records[i:i+100]
                supabase.from_('vector_db.document_chunks').insert(batch).execute()

            # 5. Update document status
            supabase.from_('vector_db.documents').update({
                'status': 'completed',
                'chunk_count': len(chunks),
            }).eq('id', document_id).execute()

            return {'status': 'completed', 'chunk_count': len(chunks)}

        except Exception as e:
            supabase.from_('vector_db.documents').update({
                'status': 'failed',
                'error_message': str(e),
            }).eq('id', document_id).execute()
            raise
```

### Step 5.3 — New Endpoint

**File:** `services/file_upload_api/src/file_upload_api/api/router.py`

```python
class ProcessRequest(BaseModel):
    document_id: str
    storage_path: str
    file_name: str
    client_id: str

@router.post("/process", response_model=ProcessResponse)
async def process_uploaded_file(
    request: ProcessRequest,
    client_id: UUID = Depends(get_client_id_from_token),
    service: DocumentProcessingService = Depends(get_processing_service),
):
    """Process a file already uploaded to Supabase Storage.

    Used for complex files that need Python-side processing (docling).
    Simple files are handled by the process-document Edge Function instead.
    """
    # Validate client_id matches
    if str(client_id) != request.client_id:
        raise HTTPException(status_code=403, detail="Client ID mismatch")

    # Run processing in background task
    background_tasks.add_task(
        service.process_document,
        document_id=request.document_id,
        storage_path=request.storage_path,
        file_name=request.file_name,
        client_id=request.client_id,
    )

    return ProcessResponse(document_id=request.document_id, status="processing")
```

### Step 5.4 — Add dependency

**File:** `services/file_upload_api/pyproject.toml`

```toml
[tool.poetry.dependencies]
vizu-parsers = {path = "../../libs/vizu_parsers", develop = true, extras = ["docling"]}
```

### Completion Criteria
- [ ] `POST /v1/upload/process` accepts pre-uploaded file metadata
- [ ] Processing downloads file from Storage, parses with docling, inserts chunks
- [ ] Chunks appear in `vector_db.document_chunks` with `embedding IS NULL`
- [ ] pgmq + embed Edge Function fills embeddings asynchronously
- [ ] Document status updates: `pending` → `processing` → `completed` / `failed`
- [ ] Real JWT auth replaces dummy client ID
- [ ] Existing `POST /v1/upload/` still works (backward compat)

---

## Phase 6 — Migrate RAG Retrieval

### Goal
Replace the Qdrant-based retriever in `vizu_rag_factory` with a Supabase-based retriever that calls the `search-documents` Edge Function.

### Files to Create/Modify

| File | Action |
|------|--------|
| `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | **CREATE** |
| `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | **MODIFY** |
| `libs/vizu_rag_factory/pyproject.toml` | **MODIFY** |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py` | **MODIFY** (minimal) |
| `services/tool_pool_api/src/tool_pool_api/server/resources.py` | **MODIFY** |

### Step 6.1 — SupabaseVectorRetriever

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py`

```python
"""Custom LangChain retriever backed by Supabase vector_db."""

import httpx
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from pydantic import Field


class SupabaseVectorRetriever(BaseRetriever):
    """Retrieves documents from Supabase vector_db via the search-documents Edge Function."""

    supabase_url: str = Field(description="Supabase project URL")
    supabase_service_key: str = Field(description="Service role key for auth")
    client_id: str = Field(description="Client UUID for RLS filtering")
    match_count: int = Field(default=5)
    match_threshold: float = Field(default=0.5)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        """Call search-documents Edge Function and convert to LangChain Documents."""
        response = httpx.post(
            f"{self.supabase_url}/functions/v1/search-documents",
            json={
                "query": query,
                "client_id": self.client_id,
                "match_count": self.match_count,
                "match_threshold": self.match_threshold,
            },
            headers={
                "Authorization": f"Bearer {self.supabase_service_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        return [
            Document(
                page_content=result["content"],
                metadata={
                    **(result.get("metadata") or {}),
                    "document_id": result["document_id"],
                    "similarity": result["similarity"],
                },
            )
            for result in data.get("results", [])
        ]
```

### Step 6.2 — Rewrite factory.py

**File:** `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py`

Key changes:
```python
# REMOVE these imports:
# from vizu_qdrant_client import get_qdrant_client
# from vizu_llm_service import get_embedding_model

# ADD this import:
from vizu_rag_factory.retriever import SupabaseVectorRetriever

# In create_rag_runnable():
# REPLACE:
#   embeddings = get_embedding_model()
#   client = get_qdrant_client()
#   retriever = client.get_langchain_retriever(collection_name, embeddings, search_k=4)

# WITH:
import os
retriever = SupabaseVectorRetriever(
    supabase_url=os.environ["SUPABASE_URL"],
    supabase_service_key=os.environ["SUPABASE_SERVICE_KEY"],
    client_id=str(contexto.id),
    match_count=search_config.get("top_k", 5) if search_config else 5,
    match_threshold=search_config.get("score_threshold", 0.5) if search_config else 0.5,
)

# Keep the rest of the chain unchanged:
# RunnablePassthrough.assign(context=retrieve_and_format) | prompt | llm | StrOutputParser()
```

### Step 6.3 — Update pyproject.toml

**File:** `libs/vizu_rag_factory/pyproject.toml`

```diff
-vizu-qdrant-client = {path = "../vizu_qdrant_client", develop = true}
-langchain-qdrant = ">=0.2.0"
+httpx = ">=0.27.0"
+vizu-supabase-client = {path = "../vizu_supabase_client", develop = true}
```

### Step 6.4 — Update rag_module.py (minimal)

**File:** `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py`

- Remove any `collection_name` lookups from context
- The factory now only needs `contexto.id` (client_id) for isolation — no collection name
- Everything else stays the same (context loading, tool gating, chain invocation)

### Step 6.5 — Update resources.py

**File:** `services/tool_pool_api/src/tool_pool_api/server/resources.py`

Replace `_get_knowledge_summary()`:
```python
# BEFORE: queries Qdrant collection info
# AFTER: queries vector_db tables
async def _get_knowledge_summary(client_id: str) -> dict:
    supabase = get_supabase_client()
    docs = supabase.from_('vector_db.documents').select('id, file_name, status, chunk_count').eq('client_id', client_id).execute()
    return {
        "document_count": len(docs.data),
        "total_chunks": sum(d["chunk_count"] for d in docs.data),
        "documents": [{"file_name": d["file_name"], "status": d["status"], "chunks": d["chunk_count"]} for d in docs.data],
    }
```

### Completion Criteria
- [ ] `SupabaseVectorRetriever` returns LangChain `Document` objects from Supabase
- [ ] `create_rag_runnable()` builds a working chain with the new retriever
- [ ] `executar_rag_cliente` MCP tool returns answers using Supabase-stored documents
- [ ] No imports of `vizu_qdrant_client` remain in the active code path
- [ ] Knowledge summary resource returns data from `vector_db`
- [ ] `ruff check` passes on all modified files

---

## Phase 7 — ChatPanel File Upload Button

### Goal
Wire up the existing "Anexar" button in ChatPanel to let users upload files that provide context to the agent conversation. Files are processed through the same RAG pipeline and the agent can reference them.

### Files to Create/Modify

| File | Action |
|------|--------|
| `apps/vizu_dashboard/src/components/ChatPanel.tsx` | **MODIFY** |
| `apps/vizu_dashboard/src/services/chatService.ts` | **MODIFY** |
| `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` | **MODIFY** (reuse upload logic) |

### Step 7.1 — Wire up "Anexar" button

**File:** `apps/vizu_dashboard/src/components/ChatPanel.tsx`

Current state: The "Anexar" button (with `AttachmentIcon`) at line ~468 has **no onClick handler**.

Changes:
```tsx
// 1. Add hidden file input ref
const fileInputRef = useRef<HTMLInputElement>(null);
const [uploadingFile, setUploadingFile] = useState(false);
const [attachedFiles, setAttachedFiles] = useState<{name: string; documentId: string}[]>([]);

// 2. Handle file selection
const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const files = e.target.files;
  if (!files || files.length === 0) return;
  setUploadingFile(true);
  try {
    for (const file of Array.from(files)) {
      // Reuse the knowledge base upload service (simple path for most chat files)
      const documentId = await uploadSimpleFile(file, clientId);
      setAttachedFiles(prev => [...prev, { name: file.name, documentId }]);

      // Add a system message showing the file was uploaded
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        content: `📎 Arquivo "${file.name}" enviado e processado para contexto.`,
        sender: 'user',
        timestamp: new Date(),
      }]);
    }
  } catch (err) {
    // Show error toast
  } finally {
    setUploadingFile(false);
    e.target.value = ''; // reset input
  }
};

// 3. Wire up the existing Anexar button
<IconButton
  icon={<AttachmentIcon />}
  aria-label="Anexar arquivo"
  onClick={() => fileInputRef.current?.click()}
  isLoading={uploadingFile}
  // ... existing styles
/>
<input
  type="file"
  ref={fileInputRef}
  onChange={handleFileUpload}
  accept=".pdf,.docx,.csv,.txt,.md,.json,.xml,.html,.xlsx,.pptx"
  multiple
  style={{ display: 'none' }}
/>

// 4. Show attached files above input (optional chip display)
{attachedFiles.length > 0 && (
  <HStack spacing={2} px={4} py={1}>
    {attachedFiles.map(f => (
      <Tag key={f.documentId} size="sm" colorScheme="blue" borderRadius="full">
        <TagLabel>{f.name}</TagLabel>
        <TagCloseButton onClick={() => setAttachedFiles(prev => prev.filter(af => af.documentId !== f.documentId))} />
      </Tag>
    ))}
  </HStack>
)}
```

### Step 7.2 — Include file context in chat request

**File:** `apps/vizu_dashboard/src/services/chatService.ts`

Update `ChatRequest` to include document references:
```typescript
interface ChatRequest {
  message: string;
  session_id?: string;
  context?: {
    current_page?: string;
    selected_filters?: Record<string, string>;
    attached_document_ids?: string[];  // NEW: document IDs from vector_db
  };
}
```

The agent backend (`atendente_core`) can then use these document IDs to scope the RAG search to specific documents (filter by `document_id IN (...)` in the `match_documents` query).

### Step 7.3 — Atendente Core Support (backend)

The `atendente_core` service needs to:
1. Accept `attached_document_ids` in the chat request
2. Pass them through to the RAG tool so it can filter search results to those specific documents
3. This is a **future enhancement** — initially, uploaded files just join the client's knowledge base and the RAG tool searches across all client documents

### Completion Criteria
- [ ] "Anexar" button opens file picker when clicked
- [ ] Selected file uploads to Supabase Storage + creates document + triggers processing
- [ ] Chat shows "📎 Arquivo uploaded" system message
- [ ] File chips appear above input area
- [ ] File chips can be dismissed
- [ ] Loading state shown during upload

---

## Phase 8 — Deprecation & Cleanup

### Goal
Remove Qdrant, `file_processing_worker`, and consolidate file tracking tables.

### Files to Modify

| File | Action |
|------|--------|
| `docker-compose.yml` | **MODIFY** — remove `qdrant_db` + `file_processing_worker` services |
| `services/file_processing_worker/README.md` | **MODIFY** — add deprecation notice |
| `libs/vizu_qdrant_client/README.md` | **MODIFY** — add deprecation notice |
| `libs/vizu_models/src/vizu_models/knowledge_base_config.py` | **MODIFY** — update defaults |

### Step 8.1 — Docker Compose

Remove from `docker-compose.yml`:
- `qdrant_db` service (ports 6333, 6334) + `qdrant_data` volume
- `file_processing_worker` service (port 8002)
- Any `depends_on: qdrant_db` references in other services

### Step 8.2 — Deprecation Notices

Add to `services/file_processing_worker/README.md`:
```markdown
> **⚠️ DEPRECATED** — This service is replaced by the Supabase-based RAG pipeline.
> Simple files are processed by the `process-document` Edge Function.
> Complex files are processed by `file_upload_api /v1/upload/process` with docling.
> See docs/RAG_MIGRATION_GUIDE.md for details.
```

Add to `libs/vizu_qdrant_client/README.md`:
```markdown
> **⚠️ DEPRECATED** — Vector storage has been migrated to Supabase `vector_db` schema.
> Use `SupabaseVectorRetriever` from `vizu_rag_factory` instead.
> See docs/RAG_MIGRATION_GUIDE.md for details.
```

### Step 8.3 — Update KnowledgeBaseConfig Model

**File:** `libs/vizu_models/src/vizu_models/knowledge_base_config.py`

```diff
-embedding_model: str = Field(default="text-embedding-3-small")
+embedding_model: str = Field(default="gte-small")
-collection_name: str  # Qdrant collection name
+# collection_name removed — isolation is by client_id in vector_db schema
```

### Step 8.4 — Consolidate File Tracking

Multiple overlapping tables exist:
- `fonte_de_dados` (used by old `file_upload_api`)
- `uploaded_files_metadata` (migration)
- `client_data_uploads` (used by dashboard `useUploadedFiles`)
- `vector_db.documents` (new, single source of truth)

**Plan:**
1. Update `useUploadedFiles` hook to query `vector_db.documents` instead of `client_data_uploads`
2. Keep old tables for now (data connectors still use `fonte_de_dados`)
3. Future: migrate non-RAG file tracking to a unified approach

### Completion Criteria
- [ ] `docker compose up` works without Qdrant or file_processing_worker
- [ ] `tool_pool_api` starts without Qdrant connection
- [ ] Deprecation notices added
- [ ] `KnowledgeBaseConfig` updated
- [ ] Dashboard file list reads from `vector_db.documents`

---

## Verification Checklist

### End-to-End Tests

| # | Test | Expected |
|---|------|----------|
| 1 | **Simple upload E2E**: Dashboard → upload `test.txt` (≤6MB) | Row in `vector_db.documents` → chunks with embeddings → searchable |
| 2 | **Complex upload E2E**: Dashboard → upload `report.pdf` with "Advanced" checked | TUS upload → `file_upload_api` → docling → chunks → async embed → searchable |
| 3 | **Edge Function embed**: Insert chunk with NULL embedding | pgmq picks up → embed Edge Function fills embedding within ~10s |
| 4 | **Search**: `search-documents` with query text | Returns relevant chunks with similarity scores |
| 5 | **RAG tool E2E**: Call `executar_rag_cliente` via agent | SupabaseVectorRetriever → search-documents → LLM answer |
| 6 | **Chat upload**: Click "Anexar" in ChatPanel → upload file | File processed, available for agent context |
| 7 | **RLS isolation**: Client A uploads → Client B queries | Client B sees 0 results |
| 8 | **Delete cascade**: Delete document from dashboard | Chunks deleted, storage file deleted, embedding jobs cancelled |
| 9 | **Error recovery**: Upload corrupt file | Status = `failed`, error_message populated, user sees error in UI |
| 10 | **Progress tracking**: Upload large file (many chunks) | Dashboard shows `X/Y chunks embedded` progress |

### Code Quality
- [ ] `ruff check` passes on all modified Python packages
- [ ] `npx eslint` passes on all modified TypeScript files
- [ ] No hardcoded URLs or keys (all from env vars)
- [ ] No `vizu_qdrant_client` imports in active code paths

---

## Key Decisions & Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| **Embedding model** | `gte-small` (384 dims) | Built into Supabase Edge Runtime. Zero API keys, zero latency. Upgradeable later. |
| **Vector storage** | pgvector in `vector_db` schema | Mature, proven. Storage Vector Buckets are still alpha. |
| **Data isolation** | Single table + RLS on `client_id` | Simpler than per-client tables. Supabase-native. Denormalized `client_id` in chunks for RLS query perf. |
| **Two-tier processing** | Edge Function (simple) + Python (complex) | Simple files don't need a Python runtime. Complex files (OCR, tables) need docling. |
| **Edge Function parsing** | `pdf-parse`, `mammoth` via npm | Available in Deno via `npm:` imports. Handles text-only PDFs and DOCX well. |
| **Complex parsing** | `docling` (optional dep) | Best quality for scanned docs, tables, images. Only installed where needed. |
| **Upload strategy** | Standard (simple ≤6MB) + TUS (complex/large) | Frontend decision. Standard is simpler; TUS handles large files reliably. |
| **Auto-embed** | pgmq + pg_cron + Edge Function | Async, resilient, auto-retry. ~10s delay acceptable. Simple path embeds inline (no delay). |
| **Metadata** | Lean jsonb: `{source_file, page, section}` | Per Supabase best practices. Content in dedicated column, not metadata. |
| **Chat file upload** | Reuse KB upload service via "Anexar" button | Already exists as non-functional UI. Same pipeline, tagged with `source='chat'`. |

---

## File Reference Map

Quick lookup for all files involved in this migration:

### New Files

| File | Phase | Purpose |
|------|-------|---------|
| `supabase/migrations/20260305_create_vector_db_schema.sql` | 1 | Schema + tables + triggers + RLS |
| `supabase/functions/embed/index.ts` | 2 | Auto-embed worker (pgmq consumer) |
| `supabase/functions/process-document/index.ts` | 2 | Simple file parser + embedder |
| `supabase/functions/search-documents/index.ts` | 2 | Similarity search endpoint |
| `libs/vizu_parsers/src/vizu_parsers/parsers/docling_parser.py` | 3 | Complex doc parser |
| `apps/vizu_dashboard/src/pages/admin/AdminKnowledgeBasePage.tsx` | 4 | Admin upload UI |
| `apps/vizu_dashboard/src/hooks/useKnowledgeBase.ts` | 4 | KB data hook |
| `apps/vizu_dashboard/src/services/knowledgeBaseService.ts` | 4 | KB service layer |
| `services/file_upload_api/src/file_upload_api/services/processing_service.py` | 5 | Complex file processor |
| `libs/vizu_rag_factory/src/vizu_rag_factory/retriever.py` | 6 | Supabase vector retriever |

### Modified Files

| File | Phase | Change |
|------|-------|--------|
| `supabase/config.toml` | 1,2 | Add `vector_db` schema + edge function configs |
| `libs/vizu_parsers/pyproject.toml` | 3 | Add docling optional dep |
| `libs/vizu_parsers/src/vizu_parsers/parsers/router.py` | 3 | Add extensions + `is_complex_file()` |
| `apps/vizu_dashboard/src/components/admin/AdminSidebar.tsx` | 4 | Add KB sidebar item |
| `apps/vizu_dashboard/src/routes/dashboardRoutes.tsx` | 4 | Add KB route |
| `apps/vizu_dashboard/src/pages/admin/index.ts` | 4 | Export KB page |
| `services/file_upload_api/src/file_upload_api/api/router.py` | 5 | Add `/process` endpoint |
| `services/file_upload_api/src/file_upload_api/api/dependencies.py` | 5 | Fix auth |
| `services/file_upload_api/pyproject.toml` | 5 | Add vizu_parsers[docling] |
| `libs/vizu_rag_factory/src/vizu_rag_factory/factory.py` | 6 | Use SupabaseVectorRetriever |
| `libs/vizu_rag_factory/pyproject.toml` | 6 | Swap deps |
| `services/tool_pool_api/src/tool_pool_api/server/tool_modules/rag_module.py` | 6 | Remove collection_name |
| `services/tool_pool_api/src/tool_pool_api/server/resources.py` | 6 | Query vector_db |
| `apps/vizu_dashboard/src/components/ChatPanel.tsx` | 7 | Wire file upload button |
| `apps/vizu_dashboard/src/services/chatService.ts` | 7 | Add attached_document_ids |
| `docker-compose.yml` | 8 | Remove qdrant + worker |
| `libs/vizu_models/src/vizu_models/knowledge_base_config.py` | 8 | Update defaults |

### Deprecated

| File/Service | Replaced By |
|-------------|-------------|
| `services/file_processing_worker/` | Edge Function `process-document` + `file_upload_api /v1/upload/process` |
| `libs/vizu_qdrant_client/` | `vector_db` schema + `SupabaseVectorRetriever` |
| `qdrant_db` Docker service | Supabase pgvector |
| External embedding service | Built-in `gte-small` in Edge Functions |

---

## Implementation Order (Recommended)

```
Phase 1 (DB Schema)     ← START HERE, blocks everything
    │
    ├── Phase 2 (Edge Functions)  ← blocks Phase 4 simple path + Phase 6 retrieval
    │       │
    │       ├── Phase 4 (Dashboard UI)  ← can start sidebar/route while Edge Fns in progress
    │       │
    │       └── Phase 6 (RAG Retrieval) ← needs search-documents Edge Fn
    │
    ├── Phase 3 (Docling)         ← independent, can parallel with Phase 2
    │       │
    │       └── Phase 5 (file_upload_api) ← needs docling + DB schema
    │
    ├── Phase 7 (ChatPanel)       ← needs Phase 4 service layer
    │
    └── Phase 8 (Cleanup)         ← LAST, after all else verified
```

**Suggested session breakdown:**
- **Session 1:** Phase 1 (migration SQL) + Phase 2 (3 Edge Functions)
- **Session 2:** Phase 3 (docling) + Phase 5 (file_upload_api refactor)
- **Session 3:** Phase 4 (dashboard page + service + hook)
- **Session 4:** Phase 6 (RAG retrieval migration)
- **Session 5:** Phase 7 (ChatPanel button) + Phase 8 (cleanup)
