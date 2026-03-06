-- ============================================================
-- HYBRID RETRIEVER SCHEMA — Phase 1 + Phase 2
-- Adds: scope, description, category columns; FTS with tsvector;
-- hybrid_match_documents RPC; metadata enrichment pipeline (pgmq).
-- ============================================================

-- ============================================================
-- 1.1 Enable Extensions
-- ============================================================
-- unaccent is required for accent-insensitive FTS on Brazilian Portuguese
-- pg_trgm already exists (skip)
CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA extensions;

-- ============================================================
-- 1.2 Add `scope` column to documents
-- ============================================================
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

-- ============================================================
-- 1.3 Add `description` and `category` to documents
-- ============================================================
ALTER TABLE vector_db.documents
  ADD COLUMN description TEXT,
  ADD COLUMN category    TEXT;

CREATE INDEX idx_documents_category ON vector_db.documents(category);

-- ============================================================
-- 1.4 Add `scope` and `category` to document_chunks (denormalized)
-- ============================================================
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

-- Composite index for hybrid_match_documents: filters scope + client_id
-- before the expensive cosine search over the HNSW embedding index.
CREATE INDEX idx_chunks_scope_client
  ON vector_db.document_chunks(scope, client_id)
  WHERE embedding IS NOT NULL;

-- ============================================================
-- 1.5 Add `fts` tsvector column with trigger + GIN index
-- ============================================================

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

-- Backfill existing chunks with tsvector
UPDATE vector_db.document_chunks
SET fts = to_tsvector(
  'portuguese',
  vector_db.immutable_unaccent(content)
)
WHERE fts IS NULL;

-- ============================================================
-- 1.6 Update RLS Policies for Platform Scope
-- ============================================================

-- Documents: users can read platform docs + their own
DROP POLICY IF EXISTS "Users can view own documents" ON vector_db.documents;
CREATE POLICY "Users can view own or platform documents"
  ON vector_db.documents FOR SELECT
  USING (scope = 'platform' OR client_id = auth.uid());

-- Documents: INSERT/UPDATE/DELETE policies already enforce client_id = auth.uid(),
-- which auto-excludes platform docs (client_id IS NULL). No changes needed.

-- Chunks: users can read platform chunks + their own
DROP POLICY IF EXISTS "Users can view own chunks" ON vector_db.document_chunks;
CREATE POLICY "Users can view own or platform chunks"
  ON vector_db.document_chunks FOR SELECT
  USING (scope = 'platform' OR client_id = auth.uid());

-- ============================================================
-- 1.7 New RPC: hybrid_match_documents
-- ============================================================

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
  -- Semantic candidates (cosine similarity) — scope-filtered BEFORE ranking
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
      -- Scope filter: narrow candidate set before expensive cosine search
      AND dc.scope = ANY(p_scope)
      AND (dc.scope = 'platform' OR dc.client_id = p_client_id)
      AND (1 - (dc.embedding <=> p_query_embedding)) > p_match_threshold
      AND (p_document_ids IS NULL OR dc.document_id = ANY(p_document_ids))
      AND (p_categories  IS NULL OR dc.category = ANY(p_categories))
    ORDER BY dc.embedding <=> p_query_embedding
    LIMIT p_match_count * 3  -- fetch wider pool for fusion
  ),

  -- Keyword candidates (ts_rank on GIN index) — scope-filtered BEFORE ranking
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
      -- Scope filter: narrow candidate set before expensive FTS ranking
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

-- ============================================================
-- Phase 2 — Metadata Enrichment Pipeline
-- ============================================================

-- 2.1 New pgmq queues for metadata jobs
SELECT pgmq.create('metadata_jobs');
SELECT pgmq.create('metadata_jobs_dlq');

-- 2.2 Trigger: queue metadata job on chunk insert
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

-- 2.3 pg_cron schedule for metadata processing
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
  '30 seconds',
  $$ SELECT util.process_metadata(); $$
);
