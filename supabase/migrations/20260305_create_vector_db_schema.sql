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
CREATE OR REPLACE FUNCTION vector_db.chunk_content_fn(rec vector_db.document_chunks)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
  RETURN rec.content;
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

-- ============================================================
-- 10. STORAGE BUCKET for knowledge base files
-- ============================================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('knowledge-base', 'knowledge-base', false)
ON CONFLICT (id) DO NOTHING;
